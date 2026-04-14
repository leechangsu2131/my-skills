/**
 * Extract text from PDF buffer using pdfjs-dist
 */
export async function extractTextFromPDF(pdfBuffer: Buffer): Promise<{
  text: string;
  pages: string[];
  totalPages: number;
}> {
  // Using pdfjs-dist for text extraction
  const pdfjsLib = await import("pdfjs-dist");
  const { getDocument } = pdfjsLib;
  
  const pdf = await getDocument({ data: pdfBuffer }).promise;
  const totalPages = pdf.numPages;
  
  const pages: string[] = [];
  let fullText = "";
  
  for (let i = 1; i <= totalPages; i++) {
    const page = await pdf.getPage(i);
    const textContent = await page.getTextContent();
    const pageText = textContent.items
      .map((item: any) => item.str)
      .join(" ");
    pages.push(pageText);
    fullText += pageText + "\n";
  }
  
  return {
    text: fullText,
    pages,
    totalPages,
  };
}

/**
 * Detect lessons from PDF text
 * Looks for patterns like "차시 1", "단원 1", "Lesson 1", etc.
 */
export function detectLessons(text: string): Array<{
  lessonNumber: number;
  title?: string;
  startIndex: number;
  endIndex: number;
}> {
  const lessons: Array<{
    lessonNumber: number;
    title?: string;
    startIndex: number;
    endIndex: number;
  }> = [];

  // Pattern to match lesson numbers: "차시 1", "단원 1", "Lesson 1", etc.
  const lessonPattern = /(?:차시|단원|lesson|unit)\s*(\d+)(?:\s*[:\-]?\s*(.+?))?(?=\n|$)/gi;
  
  let match;
  while ((match = lessonPattern.exec(text)) !== null) {
    const lessonNumber = parseInt(match[1], 10);
    const title = match[2]?.trim();
    
    lessons.push({
      lessonNumber,
      title: title || undefined,
      startIndex: match.index,
      endIndex: match.index + match[0].length,
    });
  }

  // Remove duplicates and sort by lesson number
  const uniqueLessons = Array.from(
    new Map(lessons.map((l) => [l.lessonNumber, l])).values()
  ).sort((a, b) => a.lessonNumber - b.lessonNumber);

  return uniqueLessons;
}

/**
 * Extract content for a specific lesson
 */
export function extractLessonContent(
  fullText: string,
  lessonNumber: number,
  lessons: Array<{
    lessonNumber: number;
    title?: string;
    startIndex: number;
    endIndex: number;
  }>
): {
  content: string;
  title?: string;
  startPage?: number;
  endPage?: number;
} {
  const lesson = lessons.find((l) => l.lessonNumber === lessonNumber);
  
  if (!lesson) {
    return { content: "", title: undefined };
  }

  // Find the next lesson to determine where this lesson ends
  const nextLesson = lessons.find((l) => l.lessonNumber > lessonNumber);
  
  const startIndex = lesson.startIndex;
  const endIndex = nextLesson ? nextLesson.startIndex : fullText.length;
  
  const content = fullText.substring(startIndex, endIndex).trim();
  
  return {
    content,
    title: lesson.title,
    startPage: undefined,
    endPage: undefined,
  };
}

/**
 * Parse lesson structure from detected lessons
 */
export function parseLessonStructure(
  fullText: string,
  detectedLessons: Array<{
    lessonNumber: number;
    title?: string;
    startIndex: number;
    endIndex: number;
  }>
): Array<{
  lessonNumber: number;
  title?: string;
  preview: string;
}> {
  return detectedLessons.map((lesson) => {
    const content = extractLessonContent(fullText, lesson.lessonNumber, detectedLessons);
    const preview = content.content.substring(0, 200).replace(/\n/g, " ");
    
    return {
      lessonNumber: lesson.lessonNumber,
      title: lesson.title || content.title,
      preview,
    };
  });
}
