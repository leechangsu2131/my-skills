import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router, protectedProcedure } from "./_core/trpc";
import { z } from "zod";
import { nanoid } from "nanoid";
import { eq } from "drizzle-orm";
import {
  getSpacesByUserId,
  getSpaceById,
  getFurnitureBySpaceId,
  getFurnitureById,
  getZonesByFurnitureId,
  getZoneById,
  getItemsByUserId,
  getItemsByFurnitureId,
  getItemById,
  searchItems,
  getHistoryByItemId,
  getDataQualityMetrics,
  getDb,
} from "./db";
import { spaces, furniture, zones, items, history, InsertSpace, InsertFurniture, InsertZone, InsertItem, InsertHistory } from "../drizzle/schema";

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),

  // ========== StorageMap Routers ==========

  space: router({
    list: protectedProcedure.query(async ({ ctx }) => {
      return getSpacesByUserId(ctx.user.id);
    }),

    get: protectedProcedure
      .input(z.object({ spaceId: z.string() }))
      .query(async ({ input }) => {
        return getSpaceById(input.spaceId);
      }),

    create: protectedProcedure
      .input(z.object({ name: z.string().min(1), description: z.string().optional() }))
      .mutation(async ({ input, ctx }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        const spaceId = nanoid(36);
        const newSpace: InsertSpace = {
          spaceId,
          userId: ctx.user.id,
          name: input.name,
          description: input.description,
        };

        await db.insert(spaces).values(newSpace);
        return newSpace;
      }),

    update: protectedProcedure
      .input(z.object({ spaceId: z.string(), name: z.string().optional(), description: z.string().optional() }))
      .mutation(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        const updates: Record<string, any> = {};
        if (input.name) updates.name = input.name;
        if (input.description !== undefined) updates.description = input.description;

        await db.update(spaces).set(updates).where(eq(spaces.spaceId, input.spaceId));
        return getSpaceById(input.spaceId);
      }),

    delete: protectedProcedure
      .input(z.object({ spaceId: z.string() }))
      .mutation(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        await db.delete(spaces).where(eq(spaces.spaceId, input.spaceId));
        return { success: true };
      }),
  }),

  furniture: router({
    listBySpace: protectedProcedure
      .input(z.object({ spaceId: z.string() }))
      .query(async ({ input }) => {
        return getFurnitureBySpaceId(input.spaceId);
      }),

    get: protectedProcedure
      .input(z.object({ furnitureId: z.string() }))
      .query(async ({ input }) => {
        return getFurnitureById(input.furnitureId);
      }),

    create: protectedProcedure
      .input(
        z.object({
          spaceId: z.string(),
          name: z.string().min(1),
          type: z.string().optional(),
          photoUrl: z.string().optional(),
          color: z.string().optional(),
          notes: z.string().optional(),
        })
      )
      .mutation(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        const furnitureId = nanoid(36);
        const newFurniture: InsertFurniture = {
          furnitureId,
          spaceId: input.spaceId,
          name: input.name,
          type: input.type as any,
          photoUrl: input.photoUrl,
          color: input.color || "#9333ea",
          notes: input.notes,
        };

        await db.insert(furniture).values(newFurniture);
        return { ...newFurniture };
      }),

    update: protectedProcedure
      .input(
        z.object({
          furnitureId: z.string(),
          name: z.string().optional(),
          type: z.string().optional(),
          photoUrl: z.string().optional(),
          posX: z.number().optional(),
          posY: z.number().optional(),
          width: z.number().optional(),
          height: z.number().optional(),
          color: z.string().optional(),
          notes: z.string().optional(),
        })
      )
      .mutation(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        const updates: Record<string, any> = {};
        if (input.name) updates.name = input.name;
        if (input.type) updates.type = input.type;
        if (input.photoUrl !== undefined) updates.photoUrl = input.photoUrl;
        if (input.posX !== undefined) updates.posX = input.posX;
        if (input.posY !== undefined) updates.posY = input.posY;
        if (input.width !== undefined) updates.width = input.width;
        if (input.height !== undefined) updates.height = input.height;
        if (input.color) updates.color = input.color;
        if (input.notes !== undefined) updates.notes = input.notes;

        await db.update(furniture).set(updates).where(eq(furniture.furnitureId, input.furnitureId));
        return getFurnitureById(input.furnitureId);
      }),

    delete: protectedProcedure
      .input(z.object({ furnitureId: z.string() }))
      .mutation(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        await db.delete(furniture).where(eq(furniture.furnitureId, input.furnitureId));
        return { success: true };
      }),
  }),

  zone: router({
    listByFurniture: protectedProcedure
      .input(z.object({ furnitureId: z.string() }))
      .query(async ({ input }) => {
        return getZonesByFurnitureId(input.furnitureId);
      }),

    get: protectedProcedure
      .input(z.object({ zoneId: z.string() }))
      .query(async ({ input }) => {
        return getZoneById(input.zoneId);
      }),

    create: protectedProcedure
      .input(
        z.object({
          furnitureId: z.string(),
          name: z.string().min(1),
          positionDesc: z.string().optional(),
          photoUrl: z.string().optional(),
        })
      )
      .mutation(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        const zoneId = nanoid(36);
        const newZone: InsertZone = {
          zoneId,
          furnitureId: input.furnitureId,
          name: input.name,
          positionDesc: input.positionDesc,
          photoUrl: input.photoUrl,
        };

        await db.insert(zones).values(newZone);
        return { ...newZone };
      }),

    update: protectedProcedure
      .input(
        z.object({
          zoneId: z.string(),
          name: z.string().optional(),
          positionDesc: z.string().optional(),
          photoUrl: z.string().optional(),
        })
      )
      .mutation(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        const updates: Record<string, any> = {};
        if (input.name) updates.name = input.name;
        if (input.positionDesc !== undefined) updates.positionDesc = input.positionDesc;
        if (input.photoUrl !== undefined) updates.photoUrl = input.photoUrl;

        await db.update(zones).set(updates).where(eq(zones.zoneId, input.zoneId));
        return getZoneById(input.zoneId);
      }),

    delete: protectedProcedure
      .input(z.object({ zoneId: z.string() }))
      .mutation(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        await db.delete(zones).where(eq(zones.zoneId, input.zoneId));
        return { success: true };
      }),
  }),

  item: router({
    list: protectedProcedure.query(async ({ ctx }) => {
      return getItemsByUserId(ctx.user.id);
    }),

    listByFurniture: protectedProcedure
      .input(z.object({ furnitureId: z.string() }))
      .query(async ({ input }) => {
        return getItemsByFurnitureId(input.furnitureId);
      }),

    get: protectedProcedure
      .input(z.object({ itemId: z.string() }))
      .query(async ({ input }) => {
        return getItemById(input.itemId);
      }),

    search: protectedProcedure
      .input(z.object({ query: z.string() }))
      .query(async ({ input, ctx }) => {
        return searchItems(ctx.user.id, input.query);
      }),

    create: protectedProcedure
      .input(
        z.object({
          name: z.string().min(1),
          furnitureId: z.string(),
          zoneId: z.string().optional(),
          category: z.string().optional(),
          tags: z.array(z.string()).optional(),
          memo: z.string().optional(),
          photoUrl: z.string().optional(),
          quantity: z.number().default(1),
          context: z.string().optional(),
        })
      )
      .mutation(async ({ input, ctx }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        const itemId = nanoid(36);
        const newItem: InsertItem = {
          itemId,
          userId: ctx.user.id,
          name: input.name,
          furnitureId: input.furnitureId,
          zoneId: input.zoneId,
          category: input.category as any,
          tags: input.tags,
          memo: input.memo,
          photoUrl: input.photoUrl,
          quantity: input.quantity,
          context: (input.context as any) || "home",
        };

        await db.insert(items).values(newItem);
        return { ...newItem };
      }),

    update: protectedProcedure
      .input(
        z.object({
          itemId: z.string(),
          name: z.string().optional(),
          furnitureId: z.string().optional(),
          zoneId: z.string().optional(),
          category: z.string().optional(),
          tags: z.array(z.string()).optional(),
          memo: z.string().optional(),
          photoUrl: z.string().optional(),
          quantity: z.number().optional(),
        })
      )
      .mutation(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        // Get current item to check if furniture changed
        const currentItem = await getItemById(input.itemId);
        if (!currentItem) throw new Error("Item not found");

        const updates: Record<string, any> = {};
        if (input.name) updates.name = input.name;
        if (input.category) updates.category = input.category;
        if (input.tags !== undefined) updates.tags = input.tags;
        if (input.memo !== undefined) updates.memo = input.memo;
        if (input.photoUrl !== undefined) updates.photoUrl = input.photoUrl;
        if (input.quantity !== undefined) updates.quantity = input.quantity;
        if (input.zoneId !== undefined) updates.zoneId = input.zoneId;

        // If furniture changed, record in history
        if (input.furnitureId && input.furnitureId !== currentItem.furnitureId) {
          updates.furnitureId = input.furnitureId;

          const historyId = nanoid(36);
          const historyEntry: InsertHistory = {
            historyId,
            itemId: input.itemId,
            fromFurnitureId: currentItem.furnitureId,
            fromZoneId: currentItem.zoneId,
            toFurnitureId: input.furnitureId,
            toZoneId: input.zoneId,
          };
          await db.insert(history).values(historyEntry);
        }

        await db.update(items).set(updates).where(eq(items.itemId, input.itemId));
        return getItemById(input.itemId);
      }),

    delete: protectedProcedure
      .input(z.object({ itemId: z.string() }))
      .mutation(async ({ input }) => {
        const db = await getDb();
        if (!db) throw new Error("Database not available");

        await db.delete(items).where(eq(items.itemId, input.itemId));
        return { success: true };
      }),
  }),

  history: router({
    listByItem: protectedProcedure
      .input(z.object({ itemId: z.string() }))
      .query(async ({ input }) => {
        return getHistoryByItemId(input.itemId);
      }),
  }),

  metrics: router({
    getQuality: protectedProcedure.query(async ({ ctx }) => {
      return getDataQualityMetrics(ctx.user.id);
    }),
  }),
});

export type AppRouter = typeof appRouter;
