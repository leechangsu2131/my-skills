import { eq, and, desc } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { InsertUser, users, textbooks, lessonExtractions, recentAccesses, Textbook, LessonExtraction, RecentAccess, InsertTextbook, InsertLessonExtraction, InsertRecentAccess } from "../drizzle/schema";
import { ENV } from './_core/env';

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

export async function createTextbook(data: InsertTextbook): Promise<Textbook> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  const result = await db.insert(textbooks).values(data);
  const id = result[0].insertId as number;
  
  const textbook = await db.select().from(textbooks).where(eq(textbooks.id, id)).limit(1);
  return textbook[0]!;
}

export async function getTextbooksByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  
  return db.select().from(textbooks).where(eq(textbooks.userId, userId));
}

export async function getTextbookById(id: number) {
  const db = await getDb();
  if (!db) return undefined;
  
  const result = await db.select().from(textbooks).where(eq(textbooks.id, id)).limit(1);
  return result[0];
}

export async function deleteTextbook(id: number) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  await db.delete(textbooks).where(eq(textbooks.id, id));
}

export async function createLessonExtraction(data: InsertLessonExtraction): Promise<LessonExtraction> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  const result = await db.insert(lessonExtractions).values(data);
  const id = result[0].insertId as number;
  
  const lesson = await db.select().from(lessonExtractions).where(eq(lessonExtractions.id, id)).limit(1);
  return lesson[0]!;
}

export async function getLessonsByTextbookId(textbookId: number) {
  const db = await getDb();
  if (!db) return [];
  
  return db.select().from(lessonExtractions).where(eq(lessonExtractions.textbookId, textbookId));
}

export async function getLessonByNumber(textbookId: number, lessonNumber: number) {
  const db = await getDb();
  if (!db) return undefined;
  
  const result = await db.select().from(lessonExtractions)
    .where(and(eq(lessonExtractions.textbookId, textbookId), eq(lessonExtractions.lessonNumber, lessonNumber)))
    .limit(1);
  return result[0];
}

export async function addRecentAccess(data: InsertRecentAccess): Promise<RecentAccess> {
  const db = await getDb();
  if (!db) throw new Error("Database not available");
  
  const result = await db.insert(recentAccesses).values(data);
  const id = result[0].insertId as number;
  
  const access = await db.select().from(recentAccesses).where(eq(recentAccesses.id, id)).limit(1);
  return access[0]!;
}

export async function getRecentAccessesByUserId(userId: number, limit: number = 10) {
  const db = await getDb();
  if (!db) return [];
  
  return db.select().from(recentAccesses)
    .where(eq(recentAccesses.userId, userId))
    .orderBy(desc(recentAccesses.accessedAt))
    .limit(limit);
}

// TODO: add more feature queries here as your schema grows.
