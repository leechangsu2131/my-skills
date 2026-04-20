import { eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { InsertUser, users } from "../drizzle/schema";
import { ENV } from './_core/env';
import {
  gradingSessions,
  studentAnswers,
  answerKeys,
  gradingResults,
  analysisDataTable,
} from "../drizzle/schema";

let _db: ReturnType<typeof drizzle> | null = null;

// Lazily create the drizzle instance so local tooling can run without a DB.
export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) {
    throw new Error("User openId is required for upsert");
  }

  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot upsert user: database not available");
    return;
  }

  try {
    const values: InsertUser = {
      openId: user.openId,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "email", "loginMethod"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }
    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    } else if (user.openId === ENV.ownerOpenId) {
      values.role = 'admin';
      updateSet.role = 'admin';
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

// ===== Grading Session Queries =====
export async function createGradingSession(userId: number, sessionName: string, description?: string, totalQuestions?: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(gradingSessions).values({
    userId,
    sessionName,
    description,
    totalQuestions: totalQuestions ?? 0,
  });

  // 생성된 세션 조회
  const sessions = await db.select().from(gradingSessions)
    .where(eq(gradingSessions.userId, userId))
    .orderBy((t) => t.id);
  
  const newSession = sessions[sessions.length - 1];
  return newSession || { id: 0 };
}

export async function getGradingSessionById(sessionId: number) {
  const db = await getDb();
  if (!db) return undefined;

  const result = await db.select().from(gradingSessions).where(eq(gradingSessions.id, sessionId)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

export async function getUserGradingSessions(userId: number) {
  const db = await getDb();
  if (!db) return [];

  return await db.select().from(gradingSessions).where(eq(gradingSessions.userId, userId));
}

// ===== Student Answer Queries =====
export async function createStudentAnswer(
  sessionId: number,
  studentName: string,
  pdfUrl: string,
  ocrText?: string,
  extractedAnswers?: string
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(studentAnswers).values({
    sessionId,
    studentName,
    pdfUrl,
    ocrText,
    extractedAnswers,
  });

  return result;
}

export async function getStudentAnswerById(answerId: number) {
  const db = await getDb();
  if (!db) return undefined;

  const result = await db.select().from(studentAnswers).where(eq(studentAnswers.id, answerId)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

export async function getSessionStudentAnswers(sessionId: number) {
  const db = await getDb();
  if (!db) return [];

  return await db.select().from(studentAnswers).where(eq(studentAnswers.sessionId, sessionId));
}

// ===== Answer Key Queries =====
export async function createAnswerKey(
  sessionId: number,
  pdfUrl: string,
  ocrText?: string,
  extractedAnswers?: string
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(answerKeys).values({
    sessionId,
    pdfUrl,
    ocrText,
    extractedAnswers,
  });

  return result;
}

export async function getAnswerKeyBySessionId(sessionId: number) {
  const db = await getDb();
  if (!db) return undefined;

  const result = await db.select().from(answerKeys).where(eq(answerKeys.sessionId, sessionId)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

// ===== Grading Result Queries =====
export async function createGradingResult(
  studentAnswerId: number,
  sessionId: number,
  totalQuestions: number,
  correctCount: number,
  score: string,
  questionResults?: string,
  resultPdfUrl?: string,
  analysisData?: string
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(gradingResults).values({
    studentAnswerId,
    sessionId,
    totalQuestions,
    correctCount,
    score,
    questionResults,
    resultPdfUrl,
    analysisData,
  });

  return result;
}

export async function getGradingResultByStudentAnswerId(studentAnswerId: number) {
  const db = await getDb();
  if (!db) return undefined;

  const result = await db.select().from(gradingResults).where(eq(gradingResults.studentAnswerId, studentAnswerId)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

export async function getSessionGradingResults(sessionId: number) {
  const db = await getDb();
  if (!db) return [];

  return await db.select().from(gradingResults).where(eq(gradingResults.sessionId, sessionId));
}

// ===== Analysis Data Queries =====
export async function createAnalysisData(
  sessionId: number,
  fileUrl: string,
  fileType: string,
  analysisContent?: string,
  studentAnswerId?: number
) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const result = await db.insert(analysisDataTable).values({
    sessionId,
    studentAnswerId,
    fileUrl,
    fileType,
    analysisContent,
  });

  return result;
}

export async function getAnalysisDataBySessionId(sessionId: number) {
  const db = await getDb();
  if (!db) return [];

  return await db.select().from(analysisDataTable).where(eq(analysisDataTable.sessionId, sessionId));
}

