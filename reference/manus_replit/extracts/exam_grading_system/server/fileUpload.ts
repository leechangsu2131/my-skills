import { storagePut } from "./storage";

/**
 * PDF 파일을 S3에 업로드
 * @param fileBuffer 파일 버퍼
 * @param fileName 파일명
 * @param folder 폴더 경로
 * @returns S3 URL
 */
export async function uploadPdfToS3(
  fileBuffer: Buffer,
  fileName: string,
  folder: string
): Promise<string> {
  try {
    // 파일명에서 확장자 제거 후 타임스탐프 추가
    const nameWithoutExt = fileName.replace(/\.[^/.]+$/, "");
    const timestamp = Date.now();
    const randomSuffix = Math.random().toString(36).substring(7);
    const fileKey = `${folder}/${nameWithoutExt}-${timestamp}-${randomSuffix}.pdf`;

    const { url } = await storagePut(fileKey, fileBuffer, "application/pdf");
    return url;
  } catch (error) {
    console.error("Failed to upload PDF to S3:", error);
    throw error;
  }
}

/**
 * JSON 파일을 S3에 업로드
 * @param jsonContent JSON 내용
 * @param fileName 파일명
 * @param folder 폴더 경로
 * @returns S3 URL
 */
export async function uploadJsonToS3(
  jsonContent: string,
  fileName: string,
  folder: string
): Promise<string> {
  try {
    const nameWithoutExt = fileName.replace(/\.[^/.]+$/, "");
    const timestamp = Date.now();
    const randomSuffix = Math.random().toString(36).substring(7);
    const fileKey = `${folder}/${nameWithoutExt}-${timestamp}-${randomSuffix}.json`;

    const { url } = await storagePut(fileKey, Buffer.from(jsonContent), "application/json");
    return url;
  } catch (error) {
    console.error("Failed to upload JSON to S3:", error);
    throw error;
  }
}

/**
 * URL에서 파일 다운로드
 * @param url 파일 URL
 * @returns 파일 버퍼
 */
export async function downloadFileFromUrl(url: string): Promise<Buffer> {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to download file: ${response.statusText}`);
    }
    return Buffer.from(await response.arrayBuffer());
  } catch (error) {
    console.error("Failed to download file:", error);
    throw error;
  }
}
