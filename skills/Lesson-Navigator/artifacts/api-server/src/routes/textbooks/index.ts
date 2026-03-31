import { Router, type IRouter } from "express";
import multer from "multer";
import path from "path";
import fs from "fs";
import { createRequire } from "module";
const require = createRequire(import.meta.url);
const pdfParse = require("pdf-parse") as (buffer: Buffer) => Promise<{ text: string; numpages: number }>;
import { db } from "@workspace/db";
import { textbooksTable, lessonsTable } from "@workspace/db";
import { eq, and, isNull, asc } from "drizzle-orm";
import { openai } from "@workspace/integrations-openai-ai-server";

const router: IRouter = Router();

const uploadsDir = path.join(process.cwd(), "uploads");
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: uploadsDir,
  filename: (_req, file, cb) => {
    const uniqueSuffix = Date.now() + "-" + Math.round(Math.random() * 1e9);
    cb(null, uniqueSuffix + "-" + file.originalname);
  },
});

const upload = multer({
  storage,
  fileFilter: (_req, file, cb) => {
    if (file.mimetype === "application/pdf") {
      cb(null, true);
    } else {
      cb(new Error("PDF 파일만 업로드 가능합니다."));
    }
  },
  limits: { fileSize: 50 * 1024 * 1024 },
});

async function analyzePdfWithAI(pdfText: string, textbookId: number) {
  const prompt = `다음은 교사용 지도서/교과서의 PDF 텍스트입니다. 이 텍스트를 분석하여 수업 단원 구조를 파악해주세요.

각 단원/차시를 계층적으로 정리하여 JSON 형태로 반환해주세요.
- level 1: 대단원 (예: 1단원, 2단원, Chapter 1 등)
- level 2: 소단원 (예: 1-1, 1-2 등)  
- level 3: 차시 (예: 1차시, 2차시 등 개별 수업)

반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{
  "lessons": [
    {
      "chapterNumber": "1",
      "title": "단원명",
      "description": "단원 설명",
      "pageStart": 10,
      "pageEnd": 30,
      "level": 1,
      "children": [
        {
          "chapterNumber": "1-1",
          "title": "소단원명",
          "description": "소단원 설명",
          "pageStart": 10,
          "pageEnd": 20,
          "level": 2,
          "children": [
            {
              "chapterNumber": "1차시",
              "title": "차시명",
              "description": "학습 내용",
              "pageStart": 10,
              "pageEnd": 15,
              "level": 3,
              "children": []
            }
          ]
        }
      ]
    }
  ]
}

만약 명확한 계층 구조가 없다면 level 1 단원들만 반환해도 됩니다.
pageStart와 pageEnd가 불분명하면 null로 설정하세요.
반드시 유효한 JSON만 반환하세요.

PDF 텍스트 (처음 8000자):
${pdfText.substring(0, 8000)}`;

  const response = await openai.chat.completions.create({
    model: "gpt-5.2",
    max_completion_tokens: 8192,
    messages: [
      {
        role: "system",
        content: "당신은 교육 전문가입니다. 교과서나 교사용 지도서의 구조를 분석하여 JSON으로 반환합니다. 항상 유효한 JSON만 반환합니다."
      },
      { role: "user", content: prompt }
    ],
  });

  const content = response.choices[0]?.message?.content ?? "{}";
  
  const jsonMatch = content.match(/\{[\s\S]*\}/);
  if (!jsonMatch) throw new Error("AI 응답에서 JSON을 찾을 수 없습니다.");
  
  return JSON.parse(jsonMatch[0]);
}

interface LessonNode {
  chapterNumber?: string;
  title: string;
  description?: string;
  pageStart?: number | null;
  pageEnd?: number | null;
  level: number;
  children?: LessonNode[];
}

async function saveLessons(textbookId: number, lessons: LessonNode[], parentId: number | null = null, orderStart = 0): Promise<number> {
  let order = orderStart;
  for (const lesson of lessons) {
    const [inserted] = await db.insert(lessonsTable).values({
      textbookId,
      orderIndex: order++,
      chapterNumber: lesson.chapterNumber ?? null,
      title: lesson.title,
      description: lesson.description ?? null,
      pageStart: lesson.pageStart ?? null,
      pageEnd: lesson.pageEnd ?? null,
      level: lesson.level,
      parentId,
      isCompleted: false,
    }).returning();

    if (lesson.children && lesson.children.length > 0) {
      order = await saveLessons(textbookId, lesson.children, inserted.id, order);
    }
  }
  return order;
}

router.get("/", async (req, res) => {
  try {
    const textbooks = await db.select().from(textbooksTable).orderBy(asc(textbooksTable.createdAt));
    
    const result = await Promise.all(textbooks.map(async (tb) => {
      const lessons = await db.select().from(lessonsTable).where(eq(lessonsTable.textbookId, tb.id));
      const leafLessons = lessons.filter(l => !lessons.some(l2 => l2.parentId === l.id));
      const completedLessons = leafLessons.filter(l => l.isCompleted).length;
      return {
        ...tb,
        totalLessons: leafLessons.length,
        completedLessons,
        subject: tb.subject ?? null,
        grade: tb.grade ?? null,
      };
    }));
    
    res.json(result);
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ error: "교과서 목록 조회 실패" });
  }
});

router.post("/", upload.single("file"), async (req, res) => {
  if (!req.file) {
    res.status(400).json({ error: "PDF 파일이 필요합니다." });
    return;
  }

  const { title, subject, grade } = req.body;
  if (!title) {
    res.status(400).json({ error: "제목이 필요합니다." });
    return;
  }

  try {
    const [textbook] = await db.insert(textbooksTable).values({
      title,
      subject: subject || null,
      grade: grade || null,
      fileName: req.file.originalname,
      filePath: req.file.path,
      status: "analyzing",
    }).returning();

    res.status(201).json({
      ...textbook,
      totalLessons: 0,
      completedLessons: 0,
    });

    setImmediate(async () => {
      try {
        const fileBuffer = fs.readFileSync(req.file!.path);
        const pdfData = await pdfParse(fileBuffer);
        const pdfText = pdfData.text;

        const aiResult = await analyzePdfWithAI(pdfText, textbook.id);
        
        if (aiResult.lessons && Array.isArray(aiResult.lessons) && aiResult.lessons.length > 0) {
          await saveLessons(textbook.id, aiResult.lessons);
        }

        await db.update(textbooksTable)
          .set({ status: "ready" })
          .where(eq(textbooksTable.id, textbook.id));
      } catch (err) {
        console.error("PDF 분석 오류:", err);
        await db.update(textbooksTable)
          .set({ status: "error" })
          .where(eq(textbooksTable.id, textbook.id));
      }
    });

  } catch (err) {
    req.log.error(err);
    res.status(500).json({ error: "교과서 생성 실패" });
  }
});

router.get("/:id", async (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    res.status(400).json({ error: "유효하지 않은 ID" });
    return;
  }

  try {
    const [textbook] = await db.select().from(textbooksTable).where(eq(textbooksTable.id, id));
    if (!textbook) {
      res.status(404).json({ error: "교과서를 찾을 수 없습니다." });
      return;
    }

    const lessons = await db.select().from(lessonsTable)
      .where(eq(lessonsTable.textbookId, id))
      .orderBy(asc(lessonsTable.orderIndex));
    
    const leafLessons = lessons.filter(l => !lessons.some(l2 => l2.parentId === l.id));
    const completedLessons = leafLessons.filter(l => l.isCompleted).length;

    res.json({
      ...textbook,
      totalLessons: leafLessons.length,
      completedLessons,
      lessons: lessons.map(l => ({
        ...l,
        chapterNumber: l.chapterNumber ?? null,
        description: l.description ?? null,
        pageStart: l.pageStart ?? null,
        pageEnd: l.pageEnd ?? null,
        parentId: l.parentId ?? null,
        completedAt: l.completedAt?.toISOString() ?? null,
        notes: l.notes ?? null,
      })),
      subject: textbook.subject ?? null,
      grade: textbook.grade ?? null,
    });
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ error: "교과서 조회 실패" });
  }
});

router.delete("/:id", async (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    res.status(400).json({ error: "유효하지 않은 ID" });
    return;
  }

  try {
    const [textbook] = await db.select().from(textbooksTable).where(eq(textbooksTable.id, id));
    if (!textbook) {
      res.status(404).json({ error: "교과서를 찾을 수 없습니다." });
      return;
    }

    if (textbook.filePath && fs.existsSync(textbook.filePath)) {
      fs.unlinkSync(textbook.filePath);
    }

    await db.delete(lessonsTable).where(eq(lessonsTable.textbookId, id));
    await db.delete(textbooksTable).where(eq(textbooksTable.id, id));

    res.json({ success: true });
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ error: "교과서 삭제 실패" });
  }
});

router.get("/:id/lessons", async (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    res.status(400).json({ error: "유효하지 않은 ID" });
    return;
  }

  try {
    const lessons = await db.select().from(lessonsTable)
      .where(eq(lessonsTable.textbookId, id))
      .orderBy(asc(lessonsTable.orderIndex));

    res.json(lessons.map(l => ({
      ...l,
      chapterNumber: l.chapterNumber ?? null,
      description: l.description ?? null,
      pageStart: l.pageStart ?? null,
      pageEnd: l.pageEnd ?? null,
      parentId: l.parentId ?? null,
      completedAt: l.completedAt?.toISOString() ?? null,
      notes: l.notes ?? null,
    })));
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ error: "단원 목록 조회 실패" });
  }
});

router.get("/:id/current-lesson", async (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    res.status(400).json({ error: "유효하지 않은 ID" });
    return;
  }

  try {
    const lessons = await db.select().from(lessonsTable)
      .where(eq(lessonsTable.textbookId, id))
      .orderBy(asc(lessonsTable.orderIndex));

    const leafLessons = lessons.filter(l => !lessons.some(l2 => l2.parentId === l.id));
    const completedCount = leafLessons.filter(l => l.isCompleted).length;
    const total = leafLessons.length;
    const percentage = total > 0 ? Math.round((completedCount / total) * 100) : 0;

    const currentLesson = leafLessons.find(l => !l.isCompleted);
    const currentIndex = currentLesson ? leafLessons.indexOf(currentLesson) : -1;
    const nextLesson = currentIndex >= 0 && currentIndex + 1 < leafLessons.length
      ? leafLessons[currentIndex + 1]
      : null;

    const toLesson = (l: typeof leafLessons[0]) => ({
      ...l,
      chapterNumber: l.chapterNumber ?? null,
      description: l.description ?? null,
      pageStart: l.pageStart ?? null,
      pageEnd: l.pageEnd ?? null,
      parentId: l.parentId ?? null,
      completedAt: l.completedAt?.toISOString() ?? null,
      notes: l.notes ?? null,
    });

    res.json({
      currentLesson: currentLesson ? toLesson(currentLesson) : null,
      nextLesson: nextLesson ? { id: nextLesson.id, title: nextLesson.title } : null,
      progress: {
        completed: completedCount,
        total,
        percentage,
      },
    });
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ error: "현재 수업 조회 실패" });
  }
});

router.post("/:id/notion-sync", async (req, res) => {
  const id = parseInt(req.params.id);
  const { notionPageId } = req.body;

  if (!notionPageId) {
    res.status(400).json({ error: "노션 페이지 ID가 필요합니다." });
    return;
  }

  try {
    const notionToken = process.env.NOTION_TOKEN;
    if (!notionToken) {
      res.status(400).json({ error: "노션이 연동되지 않았습니다." });
      return;
    }

    const { Client } = await import("@notionhq/client");
    const notion = new Client({ auth: notionToken });

    const [textbook] = await db.select().from(textbooksTable).where(eq(textbooksTable.id, id));
    if (!textbook) {
      res.status(404).json({ error: "교과서를 찾을 수 없습니다." });
      return;
    }

    const lessons = await db.select().from(lessonsTable)
      .where(eq(lessonsTable.textbookId, id))
      .orderBy(asc(lessonsTable.orderIndex));

    const leafLessons = lessons.filter(l => !lessons.some(l2 => l2.parentId === l.id));
    const completed = leafLessons.filter(l => l.isCompleted).length;
    const total = leafLessons.length;
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

    const content = [
      {
        object: "block" as const,
        type: "heading_2" as const,
        heading_2: {
          rich_text: [{ type: "text" as const, text: { content: `📚 ${textbook.title} 수업 진도` } }]
        }
      },
      {
        object: "block" as const,
        type: "paragraph" as const,
        paragraph: {
          rich_text: [{ type: "text" as const, text: { content: `진도: ${completed}/${total} (${percentage}%)` } }]
        }
      },
      {
        object: "block" as const,
        type: "divider" as const,
        divider: {}
      },
    ];

    for (const lesson of leafLessons.slice(0, 50)) {
      const status = lesson.isCompleted ? "✅" : "⬜";
      const completedDate = lesson.completedAt ? ` (${new Date(lesson.completedAt).toLocaleDateString("ko-KR")})` : "";
      content.push({
        object: "block" as const,
        type: "paragraph" as const,
        paragraph: {
          rich_text: [{
            type: "text" as const,
            text: {
              content: `${status} ${lesson.chapterNumber ? `[${lesson.chapterNumber}] ` : ""}${lesson.title}${completedDate}`
            }
          }]
        }
      });
    }

    await notion.blocks.children.append({
      block_id: notionPageId,
      children: content,
    });

    res.json({
      success: true,
      message: "노션에 진도 현황이 동기화되었습니다.",
      notionPageUrl: null,
    });
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ error: "노션 동기화 실패" });
  }
});

export default router;
