import { int, mysqlEnum, mysqlTable, text, timestamp, varchar, longtext } from "drizzle-orm/mysql-core";
import { relations } from "drizzle-orm";

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
 * Textbooks table - stores teacher's textbook PDFs
 */
export const textbooks = mysqlTable("textbooks", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  title: varchar("title", { length: 255 }).notNull(),
  subject: varchar("subject", { length: 100 }).notNull(),
  grade: int("grade").notNull(),
  semester: int("semester").notNull(),
  publisher: varchar("publisher", { length: 255 }),
  fileKey: varchar("fileKey", { length: 500 }).notNull(),
  fileUrl: text("fileUrl").notNull(),
  totalPages: int("totalPages"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Textbook = typeof textbooks.$inferSelect;
export type InsertTextbook = typeof textbooks.$inferInsert;

/**
 * Lesson Extractions table - stores extracted lesson content
 */
export const lessonExtractions = mysqlTable("lesson_extractions", {
  id: int("id").autoincrement().primaryKey(),
  textbookId: int("textbookId").notNull(),
  lessonNumber: int("lessonNumber").notNull(),
  title: varchar("title", { length: 255 }),
  startPage: int("startPage"),
  endPage: int("endPage"),
  content: longtext("content"),
  extractedAt: timestamp("extractedAt").defaultNow().notNull(),
});

export type LessonExtraction = typeof lessonExtractions.$inferSelect;
export type InsertLessonExtraction = typeof lessonExtractions.$inferInsert;

/**
 * Recent Access table - tracks user's recent lesson views
 */
export const recentAccesses = mysqlTable("recent_accesses", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  textbookId: int("textbookId").notNull(),
  lessonNumber: int("lessonNumber"),
  accessedAt: timestamp("accessedAt").defaultNow().notNull(),
});

export type RecentAccess = typeof recentAccesses.$inferSelect;
export type InsertRecentAccess = typeof recentAccesses.$inferInsert;

/**
 * Relations
 */
export const textbooksRelations = relations(textbooks, ({ many }) => ({
  lessons: many(lessonExtractions),
}));

export const lessonExtractionsRelations = relations(lessonExtractions, ({ one }) => ({
  textbook: one(textbooks, {
    fields: [lessonExtractions.textbookId],
    references: [textbooks.id],
  }),
}));