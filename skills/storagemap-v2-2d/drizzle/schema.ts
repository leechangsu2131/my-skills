import { int, json, mysqlEnum, mysqlTable, text, timestamp, varchar, decimal, index } from "drizzle-orm/mysql-core";
import { sql } from "drizzle-orm";

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

// ========== StorageMap Tables ==========

/**
 * L1: 공간(Space) - 관리 대상의 최상위 단위
 * 예: "우리 집", "3학년 2반"
 */
export const spaces = mysqlTable("spaces", {
  spaceId: varchar("spaceId", { length: 36 }).primaryKey(),
  userId: int("userId").notNull(),
  name: varchar("name", { length: 100 }).notNull(),
  description: text("description"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
}, (table) => ({
  userIdIdx: index("spaces_userId_idx").on(table.userId),
}));

export type Space = typeof spaces.$inferSelect;
export type InsertSpace = typeof spaces.$inferInsert;

/**
 * L3: 가구(Furniture) - 수납 기능이 있는 물리적 가구
 * 2D 평면도에서 마커로 표시됨
 * 예: "TV 장식장", "앞 교구장"
 */
export const furniture = mysqlTable("furniture", {
  furnitureId: varchar("furnitureId", { length: 36 }).primaryKey(),
  spaceId: varchar("spaceId", { length: 36 }).notNull(),
  name: varchar("name", { length: 30 }).notNull(),
  type: mysqlEnum("type", [
    "drawer",
    "wardrobe",
    "bookshelf",
    "shelf",
    "storage_box",
    "cabinet",
    "desk",
    "locker",
    "other"
  ]),
  photoUrl: text("photoUrl"),
  posX: int("posX").default(0).notNull(),
  posY: int("posY").default(0).notNull(),
  width: int("width").default(100).notNull(),
  height: int("height").default(60).notNull(),
  color: varchar("color", { length: 7 }).default("#9333ea").notNull(), // 기본값: 보라색
  zonesJson: json("zonesJson"), // [{zoneId, name, position, photoUrl}]
  notes: text("notes"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
}, (table) => ({
  spaceIdIdx: index("furniture_spaceId_idx").on(table.spaceId),
}));

export type Furniture = typeof furniture.$inferSelect;
export type InsertFurniture = typeof furniture.$inferInsert;

/**
 * L4: 구획(Zone) - 가구 내 물리적으로 구분되는 최소 단위
 * 예: "1번 서랍", "상단 칸", "오른쪽 2단"
 */
export const zones = mysqlTable("zones", {
  zoneId: varchar("zoneId", { length: 36 }).primaryKey(),
  furnitureId: varchar("furnitureId", { length: 36 }).notNull(),
  name: varchar("name", { length: 20 }).notNull(),
  positionDesc: varchar("positionDesc", { length: 50 }),
  photoUrl: text("photoUrl"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
}, (table) => ({
  furnitureIdIdx: index("zones_furnitureId_idx").on(table.furnitureId),
}));

export type Zone = typeof zones.$inferSelect;
export type InsertZone = typeof zones.$inferInsert;

/**
 * 물건(Item) - 핵심 스키마
 * 필수: itemId, name, furnitureId, createdAt, updatedAt
 * 선택: zoneId, category, tags, memo, photoUrl, quantity, context
 */
export const items = mysqlTable("items", {
  itemId: varchar("itemId", { length: 36 }).primaryKey(),
  userId: int("userId").notNull(),
  name: varchar("name", { length: 60 }).notNull(),
  furnitureId: varchar("furnitureId", { length: 36 }).notNull(),
  zoneId: varchar("zoneId", { length: 36 }),
  category: mysqlEnum("category", [
    "electronics",
    "clothing",
    "living_goods",
    "documents",
    "tools",
    "teaching_materials",
    "stationery",
    "other"
  ]),
  tags: json("tags"), // Array<string>
  memo: text("memo"),
  photoUrl: text("photoUrl"),
  quantity: int("quantity").default(1).notNull(),
  context: mysqlEnum("context", ["home", "classroom", "office", "common"]).default("home").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
}, (table) => ({
  userIdIdx: index("items_userId_idx").on(table.userId),
  furnitureIdIdx: index("items_furnitureId_idx").on(table.furnitureId),
  zoneIdIdx: index("items_zoneId_idx").on(table.zoneId),
  nameIdx: index("items_name_idx").on(table.name),
}));

export type Item = typeof items.$inferSelect;
export type InsertItem = typeof items.$inferInsert;

/**
 * 이동 이력(History) - 물건의 위치 변경 추적
 * 이전 위치를 지우지 않고 기록으로 남긴다
 */
export const history = mysqlTable("history", {
  historyId: varchar("historyId", { length: 36 }).primaryKey(),
  itemId: varchar("itemId", { length: 36 }).notNull(),
  fromFurnitureId: varchar("fromFurnitureId", { length: 36 }),
  fromZoneId: varchar("fromZoneId", { length: 36 }),
  toFurnitureId: varchar("toFurnitureId", { length: 36 }).notNull(),
  toZoneId: varchar("toZoneId", { length: 36 }),
  movedAt: timestamp("movedAt").defaultNow().notNull(),
  note: text("note"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
}, (table) => ({
  itemIdIdx: index("history_itemId_idx").on(table.itemId),
  movedAtIdx: index("history_movedAt_idx").on(table.movedAt),
}));

export type History = typeof history.$inferSelect;
export type InsertHistory = typeof history.$inferInsert;