import { Router, type IRouter } from "express";
import { db } from "@workspace/db";
import { lessonsTable } from "@workspace/db";
import { eq } from "drizzle-orm";

const router: IRouter = Router();

router.post("/:id/complete", async (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    res.status(400).json({ error: "유효하지 않은 ID" });
    return;
  }

  try {
    const { notes, taughtAt } = req.body;
    const completedAt = taughtAt ? new Date(taughtAt) : new Date();

    const [lesson] = await db.update(lessonsTable)
      .set({
        isCompleted: true,
        completedAt,
        notes: notes ?? null,
      })
      .where(eq(lessonsTable.id, id))
      .returning();

    if (!lesson) {
      res.status(404).json({ error: "수업을 찾을 수 없습니다." });
      return;
    }

    res.json({
      ...lesson,
      chapterNumber: lesson.chapterNumber ?? null,
      description: lesson.description ?? null,
      pageStart: lesson.pageStart ?? null,
      pageEnd: lesson.pageEnd ?? null,
      parentId: lesson.parentId ?? null,
      completedAt: lesson.completedAt?.toISOString() ?? null,
      notes: lesson.notes ?? null,
    });
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ error: "수업 완료 처리 실패" });
  }
});

router.post("/:id/uncomplete", async (req, res) => {
  const id = parseInt(req.params.id);
  if (isNaN(id)) {
    res.status(400).json({ error: "유효하지 않은 ID" });
    return;
  }

  try {
    const [lesson] = await db.update(lessonsTable)
      .set({
        isCompleted: false,
        completedAt: null,
      })
      .where(eq(lessonsTable.id, id))
      .returning();

    if (!lesson) {
      res.status(404).json({ error: "수업을 찾을 수 없습니다." });
      return;
    }

    res.json({
      ...lesson,
      chapterNumber: lesson.chapterNumber ?? null,
      description: lesson.description ?? null,
      pageStart: lesson.pageStart ?? null,
      pageEnd: lesson.pageEnd ?? null,
      parentId: lesson.parentId ?? null,
      completedAt: lesson.completedAt?.toISOString() ?? null,
      notes: lesson.notes ?? null,
    });
  } catch (err) {
    req.log.error(err);
    res.status(500).json({ error: "수업 완료 취소 실패" });
  }
});

export default router;
