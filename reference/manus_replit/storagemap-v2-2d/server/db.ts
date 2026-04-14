import { eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { nanoid } from "nanoid";
import { InsertUser, users, items, furniture, zones, history, InsertHistory } from "../drizzle/schema";
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

// ========== StorageMap Query Helpers ==========

import { spaces } from "../drizzle/schema";
import { and, like, or } from "drizzle-orm";

// Space queries
export async function getSpacesByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(spaces).where(eq(spaces.userId, userId));
}

export async function getSpaceById(spaceId: string) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(spaces).where(eq(spaces.spaceId, spaceId)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

// Furniture queries
export async function getFurnitureBySpaceId(spaceId: string) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(furniture).where(eq(furniture.spaceId, spaceId));
}

export async function getFurnitureById(furnitureId: string) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(furniture).where(eq(furniture.furnitureId, furnitureId)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

// Zone queries
export async function getZonesByFurnitureId(furnitureId: string) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(zones).where(eq(zones.furnitureId, furnitureId));
}

export async function getZoneById(zoneId: string) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(zones).where(eq(zones.zoneId, zoneId)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

// Item queries
export async function getItemsByUserId(userId: number) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(items).where(eq(items.userId, userId));
}

export async function getItemsByFurnitureId(furnitureId: string) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(items).where(eq(items.furnitureId, furnitureId));
}

export async function getItemById(itemId: string) {
  const db = await getDb();
  if (!db) return undefined;
  const result = await db.select().from(items).where(eq(items.itemId, itemId)).limit(1);
  return result.length > 0 ? result[0] : undefined;
}

// Search items with priority: exact name > partial name > tags > memo
export async function searchItems(userId: number, query: string) {
  const db = await getDb();
  if (!db) return [];
  
  const userItems = await db.select().from(items).where(eq(items.userId, userId));
  
  const queryLower = query.toLowerCase();
  
  // 필터링: 검색어와 매칭되는 항목만 선택
  const filtered = userItems.filter(item => {
    const nameMatch = item.name.toLowerCase().includes(queryLower);
    const tagsMatch = (item.tags as string[] || []).some(tag => tag.toLowerCase().includes(queryLower));
    const memoMatch = (item.memo || "").toLowerCase().includes(queryLower);
    return nameMatch || tagsMatch || memoMatch;
  });
  
  // 우선순위에 따라 정렬
  const results = filtered.sort((a, b) => {
    const aNameLower = a.name.toLowerCase();
    const bNameLower = b.name.toLowerCase();
    
    // 1. Exact name match
    if (aNameLower === queryLower && bNameLower !== queryLower) return -1;
    if (bNameLower === queryLower && aNameLower !== queryLower) return 1;
    
    // 2. Partial name match
    const aHasName = aNameLower.includes(queryLower);
    const bHasName = bNameLower.includes(queryLower);
    if (aHasName && !bHasName) return -1;
    if (bHasName && !aHasName) return 1;
    
    // 3. Tag match
    const aTags = a.tags as string[] || [];
    const bTags = b.tags as string[] || [];
    const aHasTag = aTags.some(tag => tag.toLowerCase().includes(queryLower));
    const bHasTag = bTags.some(tag => tag.toLowerCase().includes(queryLower));
    if (aHasTag && !bHasTag) return -1;
    if (bHasTag && !aHasTag) return 1;
    
    // 4. Memo match
    const aMemo = a.memo?.toLowerCase() || "";
    const bMemo = b.memo?.toLowerCase() || "";
    const aHasMemo = aMemo.includes(queryLower);
    const bHasMemo = bMemo.includes(queryLower);
    if (aHasMemo && !bHasMemo) return -1;
    if (bHasMemo && !aHasMemo) return 1;
    
    return 0;
  });
  
  return results;
}

// History queries
export async function getHistoryByItemId(itemId: string) {
  const db = await getDb();
  if (!db) return [];
  return db.select().from(history).where(eq(history.itemId, itemId));
}

// Data quality metrics
export async function getDataQualityMetrics(userId: number) {
  const db = await getDb();
  if (!db) return null;
  
  const userItems = await db.select().from(items).where(eq(items.userId, userId));
  
  if (userItems.length === 0) {
    return {
      requiredFieldsCompleteness: 100,
      furnitureAssignmentRate: 100,
      nameDuplicateRate: 0,
      dataFreshnessRate: 100,
    };
  }
  
  // 1. Required fields completeness (name, furnitureId)
  const completeItems = userItems.filter(item => item.name && item.furnitureId);
  const requiredFieldsCompleteness = (completeItems.length / userItems.length) * 100;
  
  // 2. Furniture assignment rate
  const assignedItems = userItems.filter(item => item.furnitureId);
  const furnitureAssignmentRate = (assignedItems.length / userItems.length) * 100;
  
  // 3. Name duplicate rate
  const nameCounts = new Map<string, number>();
  userItems.forEach(item => {
    const count = nameCounts.get(item.name) || 0;
    nameCounts.set(item.name, count + 1);
  });
  const duplicateItems = Array.from(nameCounts.values()).filter(count => count > 1).reduce((a, b) => a + b, 0);
  const nameDuplicateRate = (duplicateItems / userItems.length) * 100;
  
  // 4. Data freshness (30 days)
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  const freshItems = userItems.filter(item => item.updatedAt > thirtyDaysAgo);
  const dataFreshnessRate = (freshItems.length / userItems.length) * 100;
  
  return {
    requiredFieldsCompleteness: Math.round(requiredFieldsCompleteness),
    furnitureAssignmentRate: Math.round(furnitureAssignmentRate),
    nameDuplicateRate: Math.round(nameDuplicateRate),
    dataFreshnessRate: Math.round(dataFreshnessRate),
  };
}

// Update item with history tracking for zone-only changes
export async function updateItemWithHistory(itemId: string, updates: Record<string, any>) {
  const db = await getDb();
  if (!db) throw new Error("Database not available");

  const currentItem = await getItemById(itemId);
  if (!currentItem) throw new Error("Item not found");

  // 검사: furniture 또는 zone 변경시 History 기록
  const furnitureChanged = updates.furnitureId && updates.furnitureId !== currentItem.furnitureId;
  const zoneChanged = updates.zoneId !== undefined && updates.zoneId !== currentItem.zoneId;

  if (furnitureChanged || zoneChanged) {
    const historyId = nanoid(36);
    const historyEntry: InsertHistory = {
      historyId,
      itemId,
      fromFurnitureId: currentItem.furnitureId,
      fromZoneId: currentItem.zoneId,
      toFurnitureId: updates.furnitureId || currentItem.furnitureId,
      toZoneId: updates.zoneId !== undefined ? updates.zoneId : currentItem.zoneId,
    };
    await db.insert(history).values(historyEntry);
  }

  await db.update(items).set(updates).where(eq(items.itemId, itemId));
  return getItemById(itemId);
}
