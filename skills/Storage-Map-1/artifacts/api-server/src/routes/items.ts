import { Router, type IRouter } from "express";
import { db, itemsTable, furnitureTable, spacesTable, locationHistoryTable } from "@workspace/db";
import { eq, ilike, or, sql, and } from "drizzle-orm";

const router: IRouter = Router();

router.get("/furniture/:furnitureId/items", async (req, res) => {
  try {
    const items = await db.select().from(itemsTable)
      .where(eq(itemsTable.furnitureId, req.params.furnitureId))
      .orderBy(itemsTable.name);
    res.json(items.map(formatItem));
  } catch (err) {
    req.log.error({ err }, "Failed to list items by furniture");
    res.status(500).json({ error: "Failed to list items" });
  }
});

router.get("/items", async (req, res) => {
  try {
    const { q, spaceId } = req.query as { q?: string; spaceId?: string };

    const rows = await db
      .select({
        item: itemsTable,
        furniture: furnitureTable,
        space: spacesTable,
      })
      .from(itemsTable)
      .innerJoin(furnitureTable, eq(furnitureTable.id, itemsTable.furnitureId))
      .innerJoin(spacesTable, eq(spacesTable.id, furnitureTable.spaceId))
      .where(and(
        spaceId ? eq(spacesTable.id, spaceId) : undefined,
        q ? or(
          ilike(itemsTable.name, `%${q}%`),
          ilike(itemsTable.memo, `%${q}%`),
          ilike(itemsTable.tags, `%${q}%`),
        ) : undefined,
      ))
      .orderBy(itemsTable.updatedAt);

    res.json(rows.map(r => ({
      ...formatItem(r.item),
      furnitureName: r.furniture.name,
      spaceId: r.space.id,
      spaceName: r.space.name,
      zoneName: null,
    })));
  } catch (err) {
    req.log.error({ err }, "Failed to list items");
    res.status(500).json({ error: "Failed to list items" });
  }
});

router.post("/items", async (req, res) => {
  try {
    const { name, furnitureId, zoneId, category, tags, memo, quantity, context } = req.body;
    if (!name) return res.status(400).json({ error: "name is required" });
    if (!furnitureId) return res.status(400).json({ error: "furnitureId is required" });

    const furniture = await db.select().from(furnitureTable).where(eq(furnitureTable.id, furnitureId));
    if (!furniture.length) return res.status(400).json({ error: "Furniture not found" });

    const tagsStr = Array.isArray(tags) ? tags.join(",") : (tags ?? null);

    const [item] = await db.insert(itemsTable).values({
      name,
      furnitureId,
      zoneId: zoneId ?? null,
      category: category ?? null,
      tags: tagsStr,
      memo: memo ?? null,
      quantity: quantity ?? 1,
      context: context ?? null,
    }).returning();

    await db.insert(locationHistoryTable).values({
      itemId: item.id,
      fromFurnitureId: null,
      fromFurnitureName: null,
      toFurnitureId: item.furnitureId,
      toFurnitureName: furniture[0].name,
      fromZoneId: null,
      toZoneId: item.zoneId ?? null,
    });

    res.status(201).json(formatItem(item));
  } catch (err) {
    req.log.error({ err }, "Failed to create item");
    res.status(500).json({ error: "Failed to create item" });
  }
});

router.get("/items/:itemId", async (req, res) => {
  try {
    const [row] = await db
      .select({
        item: itemsTable,
        furniture: furnitureTable,
        space: spacesTable,
      })
      .from(itemsTable)
      .innerJoin(furnitureTable, eq(furnitureTable.id, itemsTable.furnitureId))
      .innerJoin(spacesTable, eq(spacesTable.id, furnitureTable.spaceId))
      .where(eq(itemsTable.id, req.params.itemId));

    if (!row) return res.status(404).json({ error: "Item not found" });
    res.json({
      ...formatItem(row.item),
      furnitureName: row.furniture.name,
      spaceId: row.space.id,
      spaceName: row.space.name,
      zoneName: null,
    });
  } catch (err) {
    req.log.error({ err }, "Failed to get item");
    res.status(500).json({ error: "Failed to get item" });
  }
});

router.put("/items/:itemId", async (req, res) => {
  try {
    const { name, furnitureId, zoneId, category, tags, memo, quantity, context } = req.body;

    const [currentItem] = await db.select().from(itemsTable).where(eq(itemsTable.id, req.params.itemId));
    if (!currentItem) return res.status(404).json({ error: "Item not found" });

    const tagsStr = Array.isArray(tags) ? tags.join(",") : (tags ?? currentItem.tags);

    const updateData: Record<string, unknown> = { updatedAt: new Date() };
    if (name !== undefined) updateData.name = name;
    if (furnitureId !== undefined) updateData.furnitureId = furnitureId;
    if (zoneId !== undefined) updateData.zoneId = zoneId;
    if (category !== undefined) updateData.category = category;
    if (tags !== undefined) updateData.tags = tagsStr;
    if (memo !== undefined) updateData.memo = memo;
    if (quantity !== undefined) updateData.quantity = quantity;
    if (context !== undefined) updateData.context = context;

    const [item] = await db.update(itemsTable)
      .set(updateData as Parameters<typeof db.update>[0] extends { set: (v: infer V) => unknown } ? V : never)
      .where(eq(itemsTable.id, req.params.itemId))
      .returning();

    const newFurnitureId = furnitureId ?? currentItem.furnitureId;
    if (furnitureId && furnitureId !== currentItem.furnitureId) {
      const [fromFurniture] = await db.select().from(furnitureTable).where(eq(furnitureTable.id, currentItem.furnitureId));
      const [toFurniture] = await db.select().from(furnitureTable).where(eq(furnitureTable.id, furnitureId));
      if (toFurniture) {
        await db.insert(locationHistoryTable).values({
          itemId: item.id,
          fromFurnitureId: currentItem.furnitureId,
          fromFurnitureName: fromFurniture?.name ?? null,
          toFurnitureId: furnitureId,
          toFurnitureName: toFurniture.name,
          fromZoneId: currentItem.zoneId ?? null,
          toZoneId: zoneId ?? item.zoneId ?? null,
        });
      }
    }

    res.json(formatItem(item));
  } catch (err) {
    req.log.error({ err }, "Failed to update item");
    res.status(500).json({ error: "Failed to update item" });
  }
});

router.delete("/items/:itemId", async (req, res) => {
  try {
    await db.delete(itemsTable).where(eq(itemsTable.id, req.params.itemId));
    res.status(204).send();
  } catch (err) {
    req.log.error({ err }, "Failed to delete item");
    res.status(500).json({ error: "Failed to delete item" });
  }
});

router.get("/items/:itemId/history", async (req, res) => {
  try {
    const history = await db.select().from(locationHistoryTable)
      .where(eq(locationHistoryTable.itemId, req.params.itemId))
      .orderBy(locationHistoryTable.movedAt);
    res.json(history.map(h => ({
      ...h,
      movedAt: h.movedAt.toISOString(),
    })));
  } catch (err) {
    req.log.error({ err }, "Failed to get item history");
    res.status(500).json({ error: "Failed to get item history" });
  }
});

function formatItem(item: typeof itemsTable.$inferSelect) {
  return {
    ...item,
    tags: item.tags ? item.tags.split(",").filter(Boolean) : [],
    createdAt: item.createdAt.toISOString(),
    updatedAt: item.updatedAt.toISOString(),
  };
}

export default router;
