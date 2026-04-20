import { int, mysqlEnum, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

/**
 * Core user table backing auth flow.
 * Extend this file with additional tables as your product grows.
 * Columns use camelCase to match both database fields and generated types.
 */
export const users = mysqlTable("users", {
  /**
   * Surrogate primary key. Auto-incremented numeric value managed by the database.
   * Use this for relations between tables.
   */
  id: int("id").autoincrement().primaryKey(),
  /** Manus OAuth identifier (openId) returned from the OAuth callback. Unique per user. */
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/**
 * Grading Session: 채점 세션 정보
 * 시험명, 생성자, 생성일시 등을 저장하여 채점 작업을 그룹화합니다.
 */
export const gradingSessions = mysqlTable("grading_sessions", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("user_id").notNull(),
  sessionName: varchar("session_name", { length: 255 }).notNull(),
  description: text("description"),
  totalQuestions: int("total_questions").default(0),
  createdAt: timestamp("created_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().onUpdateNow().notNull(),
});

export type GradingSession = typeof gradingSessions.$inferSelect;
export type InsertGradingSession = typeof gradingSessions.$inferInsert;

/**
 * Student Answer: 학생 답안 정보
 * 학생 이름, 업로드된 PDF, OCR 추출 결과를 저장합니다.
 */
export const studentAnswers = mysqlTable("student_answers", {
  id: int("id").autoincrement().primaryKey(),
  sessionId: int("session_id").notNull(),
  studentName: varchar("student_name", { length: 255 }).notNull(),
  pdfUrl: text("pdf_url").notNull(),
  ocrText: text("ocr_text"),
  extractedAnswers: text("extracted_answers"), // JSON 형식
  uploadedAt: timestamp("uploaded_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().onUpdateNow().notNull(),
});

export type StudentAnswer = typeof studentAnswers.$inferSelect;
export type InsertStudentAnswer = typeof studentAnswers.$inferInsert;

/**
 * Answer Key: 정답 정보
 * 정답 PDF와 OCR 추출 결과를 저장합니다.
 */
export const answerKeys = mysqlTable("answer_keys", {
  id: int("id").autoincrement().primaryKey(),
  sessionId: int("session_id").notNull(),
  pdfUrl: text("pdf_url").notNull(),
  ocrText: text("ocr_text"),
  extractedAnswers: text("extracted_answers"), // JSON 형식
  uploadedAt: timestamp("uploaded_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().onUpdateNow().notNull(),
});

export type AnswerKey = typeof answerKeys.$inferSelect;
export type InsertAnswerKey = typeof answerKeys.$inferInsert;

/**
 * Grading Result: 채점 결과
 * 각 학생의 채점 결과(정오, 점수, 분석 내용)를 저장합니다.
 */
export const gradingResults = mysqlTable("grading_results", {
  id: int("id").autoincrement().primaryKey(),
  studentAnswerId: int("student_answer_id").notNull(),
  sessionId: int("session_id").notNull(),
  totalQuestions: int("total_questions").notNull(),
  correctCount: int("correct_count").notNull(),
  score: varchar("score", { length: 50 }).notNull(), // 점수 (예: "85/100")
  questionResults: text("question_results"), // JSON 형식: [{questionNum, correct, analysis}]
  resultPdfUrl: text("result_pdf_url"), // 최종 결과 PDF URL
  analysisData: text("analysis_data"), // JSON 형식: LLM 분석 내용
  gradedAt: timestamp("graded_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().onUpdateNow().notNull(),
});

export type GradingResult = typeof gradingResults.$inferSelect;
export type InsertGradingResult = typeof gradingResults.$inferInsert;

/**
 * Analysis Data: 분석 데이터
 * LLM 분석 파일의 내용을 저장합니다.
 */
export const analysisDataTable = mysqlTable("analysis_data", {
  id: int("id").autoincrement().primaryKey(),
  sessionId: int("session_id").notNull(),
  studentAnswerId: int("student_answer_id"),
  fileUrl: text("file_url").notNull(),
  fileType: varchar("file_type", { length: 50 }).notNull(), // "json" or "pdf"
  analysisContent: text("analysis_content"), // JSON 형식으로 파싱된 분석 내용
  uploadedAt: timestamp("uploaded_at").defaultNow().notNull(),
  updatedAt: timestamp("updated_at").defaultNow().onUpdateNow().notNull(),
});

export type AnalysisData = typeof analysisDataTable.$inferSelect;
export type InsertAnalysisData = typeof analysisDataTable.$inferInsert;