import * as pdfjsLib from "pdfjs-dist";
import { PDFDocument, PDFPage, rgb } from "pdf-lib";


// PDF.js 워커 설정 (Node.js 환경에서는 필요 없음)
// pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

/**
 * PDF 파일을 이미지로 변환
 * @param pdfBuffer PDF 파일 버퍼
 * @returns 이미지 데이터 배열 (base64 형식)
 */
export async function convertPdfToImages(pdfBuffer: Buffer): Promise<string[]> {
  const pdf = await pdfjsLib.getDocument({ data: pdfBuffer }).promise;
  const images: string[] = [];

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const viewport = page.getViewport({ scale: 2 });

    // Canvas 생성 (Node.js 환경에서는 canvas 라이브러리 필요)
    // 여기서는 간단히 페이지 정보만 반환
    const textContent = await page.getTextContent();
    const text = textContent.items.map((item: any) => item.str).join(" ");
    images.push(text);
  }

  return images;
}

/**
 * PDF에서 텍스트 추출 (OCR 없이 기존 텍스트만 추출)
 * @param pdfBuffer PDF 파일 버퍼
 * @returns 추출된 텍스트
 */
export async function extractTextFromPdf(pdfBuffer: Buffer): Promise<string> {
  const pdf = await pdfjsLib.getDocument({ data: pdfBuffer }).promise;
  let fullText = "";

  for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
    const page = await pdf.getPage(pageNum);
    const textContent = await page.getTextContent();
    const pageText = textContent.items.map((item: any) => item.str).join(" ");
    fullText += `\n--- Page ${pageNum} ---\n${pageText}`;
  }

  return fullText;
}

/**
 * 추출된 텍스트에서 답안 파싱
 * 형식: "1. A", "2. B", "3. C" 등
 * @param text 추출된 텍스트
 * @returns 파싱된 답안 객체 배열
 */
export function parseAnswersFromText(text: string): Array<{ questionNum: number; answer: string }> {
  const answers: Array<{ questionNum: number; answer: string }> = [];

  // 정규표현식으로 "숫자. 답" 형식 찾기
  const regex = /(\d+)\s*[\\.\\)\\-]\\s*([A-Z가-힣0-9])/gi;
  let match;

  while ((match = regex.exec(text)) !== null) {
    answers.push({
      questionNum: parseInt(match[1]),
      answer: match[2].toUpperCase(),
    });
  }

  return answers;
}

/**
 * 두 답안 배열을 비교하여 채점
 * @param studentAnswers 학생 답안
 * @param correctAnswers 정답
 * @returns 채점 결과
 */
export function gradeAnswers(
  studentAnswers: Array<{ questionNum: number; answer: string }>,
  correctAnswers: Array<{ questionNum: number; answer: string }>
): {
  totalQuestions: number;
  correctCount: number;
  score: string;
  questionResults: Array<{ questionNum: number; correct: boolean; studentAnswer: string; correctAnswer: string }>;
} {
  const questionResults: Array<{
    questionNum: number;
    correct: boolean;
    studentAnswer: string;
    correctAnswer: string;
  }> = [];
  let correctCount = 0;

  // 정답 맵 생성
  const correctAnswerMap = new Map(correctAnswers.map((a) => [a.questionNum, a.answer]));

  // 모든 문제 번호 수집
  const allQuestionNums = new Set([
    ...studentAnswers.map((a) => a.questionNum),
    ...correctAnswers.map((a) => a.questionNum),
  ]);

  // 각 문제별로 채점
  for (const questionNum of Array.from(allQuestionNums).sort((a, b) => a - b)) {
    const studentAnswer = studentAnswers.find((a) => a.questionNum === questionNum)?.answer || "";
    const correctAnswer = correctAnswerMap.get(questionNum) || "";
    const correct = studentAnswer.toUpperCase() === correctAnswer.toUpperCase();

    if (correct) {
      correctCount++;
    }

    questionResults.push({
      questionNum,
      correct,
      studentAnswer,
      correctAnswer,
    });
  }

  const totalQuestions = allQuestionNums.size;
  const score = `${correctCount}/${totalQuestions}`;

  return {
    totalQuestions,
    correctCount,
    score,
    questionResults,
  };
}

/**
 * PDF에 텍스트 오버레이 추가
 * @param pdfBuffer 원본 PDF 버퍼
 * @param overlayText 오버레이할 텍스트
 * @returns 수정된 PDF 버퍼
 */
export async function addOverlayToPdf(pdfBuffer: Buffer, overlayData: any): Promise<Buffer> {
  const pdfDoc = await PDFDocument.load(pdfBuffer);
  const pages = pdfDoc.getPages();

  // 첫 페이지에 채점 결과 추가
  if (pages.length > 0) {
    const firstPage = pages[0];
    const { width, height } = firstPage.getSize();

    // 채점 결과 텍스트 추가
    firstPage.drawText(`채점 결과: ${overlayData.score}`, {
      x: 50,
      y: height - 50,
      size: 16,
      color: rgb(0, 0, 0),
    });

    // 정오 표시 추가
    let yPosition = height - 100;
    for (const result of overlayData.questionResults.slice(0, 10)) {
      const status = result.correct ? "✓" : "✗";
      const text = `Q${result.questionNum}: ${status} (정답: ${result.correctAnswer}, 답: ${result.studentAnswer})`;
      firstPage.drawText(text, {
        x: 50,
        y: yPosition,
        size: 10,
        color: result.correct ? rgb(0, 128, 0) : rgb(255, 0, 0),
      });
      yPosition -= 20;
    }
  }

  return Buffer.from(await pdfDoc.save());
}

/**
 * JSON 분석 파일 파싱
 * @param jsonContent JSON 문자열
 * @returns 파싱된 분석 데이터
 */
export function parseAnalysisJson(jsonContent: string): any {
  try {
    return JSON.parse(jsonContent);
  } catch (error) {
    console.error("Failed to parse JSON analysis:", error);
    return null;
  }
}
