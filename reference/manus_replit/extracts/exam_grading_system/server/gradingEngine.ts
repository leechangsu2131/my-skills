import { extractTextFromPdf, parseAnswersFromText, gradeAnswers, addOverlayToPdf } from "./ocr";
import { createGradingResult, createAnalysisData } from "./db";
import { storagePut, storageGet } from "./storage";

/**
 * 학생 답안과 정답을 비교하여 채점 수행
 * @param studentPdfBuffer 학생 답안 PDF 버퍼
 * @param answerKeyPdfBuffer 정답 PDF 버퍼
 * @param sessionId 세션 ID
 * @param studentAnswerId 학생 답안 ID
 * @returns 채점 결과
 */
export async function performGrading(
  studentPdfBuffer: Buffer,
  answerKeyPdfBuffer: Buffer,
  sessionId: number,
  studentAnswerId: number
) {
  try {
    // 1. PDF에서 텍스트 추출
    const studentText = await extractTextFromPdf(studentPdfBuffer);
    const answerKeyText = await extractTextFromPdf(answerKeyPdfBuffer);

    // 2. 텍스트에서 답안 파싱
    const studentAnswers = parseAnswersFromText(studentText);
    const correctAnswers = parseAnswersFromText(answerKeyText);

    // 3. 채점
    const gradingResult = gradeAnswers(studentAnswers, correctAnswers);

    // 4. 결과 PDF 생성 (원본 PDF에 오버레이)
    const resultPdfBuffer = await addOverlayToPdf(studentPdfBuffer, gradingResult);

    // 5. 결과 PDF를 S3에 업로드
    const resultFileKey = `grading-results/${sessionId}/${studentAnswerId}-result.pdf`;
    const { url: resultPdfUrl } = await storagePut(resultFileKey, resultPdfBuffer, "application/pdf");

    // 6. 데이터베이스에 채점 결과 저장
    await createGradingResult(
      studentAnswerId,
      sessionId,
      gradingResult.totalQuestions,
      gradingResult.correctCount,
      gradingResult.score,
      JSON.stringify(gradingResult.questionResults),
      resultPdfUrl
    );

    return {
      success: true,
      score: gradingResult.score,
      correctCount: gradingResult.correctCount,
      totalQuestions: gradingResult.totalQuestions,
      resultPdfUrl,
      questionResults: gradingResult.questionResults,
    };
  } catch (error) {
    console.error("Grading failed:", error);
    throw error;
  }
}

/**
 * LLM 분석 파일 통합
 * @param sessionId 세션 ID
 * @param studentAnswerId 학생 답안 ID
 * @param analysisFileUrl 분석 파일 URL
 * @param fileType 파일 타입 ("json" 또는 "pdf")
 * @returns 통합된 분석 데이터
 */
export async function integrateAnalysisData(
  sessionId: number,
  studentAnswerId: number,
  analysisFileUrl: string,
  fileType: string
) {
  try {
    let analysisContent: any = null;

    if (fileType === "json") {
      // JSON 파일인 경우 직접 파싱
      const response = await fetch(analysisFileUrl);
      const jsonData = await response.json();
      analysisContent = jsonData;
    } else if (fileType === "pdf") {
      // PDF 파일인 경우 텍스트 추출 후 저장
      const response = await fetch(analysisFileUrl);
      const pdfBuffer = Buffer.from(await response.arrayBuffer());
      const text = await extractTextFromPdf(pdfBuffer);
      analysisContent = { extractedText: text };
    }

    // 분석 데이터 저장
    await createAnalysisData(
      sessionId,
      analysisFileUrl,
      fileType,
      JSON.stringify(analysisContent),
      studentAnswerId
    );

    return analysisContent;
  } catch (error) {
    console.error("Analysis integration failed:", error);
    throw error;
  }
}

/**
 * 채점 결과와 분석 데이터를 통합한 최종 결과 생성
 * @param gradingResult 채점 결과
 * @param analysisData 분석 데이터
 * @returns 통합된 결과
 */
export function mergeGradingAndAnalysis(gradingResult: any, analysisData: any) {
  return {
    ...gradingResult,
    analysis: analysisData,
    mergedAt: new Date().toISOString(),
  };
}
