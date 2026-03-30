import { Router, type IRouter } from "express";
import { db, furnitureTable, itemsTable } from "@workspace/db";
import { eq, count } from "drizzle-orm";

const router: IRouter = Router();

router.get("/spaces/:spaceId/furniture", async (req, res) => {
  try {
    const rows = await db
      .select({
        furniture: furnitureTable,
        itemCount: count(itemsTable.id),
      })
      .from(furnitureTable)
      .leftJoin(itemsTable, eq(itemsTable.furnitureId, furnitureTable.id))
      .where(eq(furnitureTable.spaceId, req.params.spaceId))
      .groupBy(furnitureTable.id)
      .orderBy(furnitureTable.createdAt);

    res.json(rows.map(r => ({
      ...r.furniture,
      itemCount: Number(r.itemCount),
      createdAt: r.furniture.createdAt.toISOString(),
      updatedAt: r.furniture.updatedAt.toISOString(),
    })));
  } catch (err) {
    req.log.error({ err }, "Failed to list furniture");
    res.status(500).json({ error: "Failed to list furniture" });
  }
});

router.post("/spaces/:spaceId/furniture", async (req, res) => {
  try {
    const { name, type, posX, posY, width, height, zonesJson, notes } = req.body;
    if (!name) return res.status(400).json({ error: "name is required" });
    const [furniture] = await db.insert(furnitureTable).values({
      spaceId: req.params.spaceId,
      name,
      type: type ?? null,
      posX: posX ?? 50,
      posY: posY ?? 50,
      width: width ?? 100,
      height: height ?? 60,
      zonesJson: zonesJson ?? null,
      notes: notes ?? null,
    }).returning();
    res.status(201).json({
      ...furniture,
      itemCount: 0,
      createdAt: furniture.createdAt.toISOString(),
      updatedAt: furniture.updatedAt.toISOString(),
    });
  } catch (err) {
    req.log.error({ err }, "Failed to create furniture");
    res.status(500).json({ error: "Failed to create furniture" });
  }
});

router.put("/furniture/:furnitureId", async (req, res) => {
  try {
    const { name, type, posX, posY, width, height, zonesJson, notes } = req.body;

    const [existing] = await db.select().from(furnitureTable).where(eq(furnitureTable.id, req.params.furnitureId));
    if (!existing) return res.status(404).json({ error: "Furniture not found" });

    const [furniture] = await db.update(furnitureTable)
      .set({
        name: name ?? existing.name,
        type: type !== undefined ? type : existing.type,
        posX: posX !== undefined ? posX : existing.posX,
        posY: posY !== undefined ? posY : existing.posY,
        width: width !== undefined ? width : existing.width,
        height: height !== undefined ? height : existing.height,
        zonesJson: zonesJson !== undefined ? zonesJson : existing.zonesJson,
        notes: notes !== undefined ? notes : existing.notes,
        updatedAt: new Date(),
      })
      .where(eq(furnitureTable.id, req.params.furnitureId))
      .returning();

    const [{ itemCount }] = await db
      .select({ itemCount: count(itemsTable.id) })
      .from(itemsTable)
      .where(eq(itemsTable.furnitureId, furniture.id));

    res.json({
      ...furniture,
      itemCount: Number(itemCount),
      createdAt: furniture.createdAt.toISOString(),
      updatedAt: furniture.updatedAt.toISOString(),
    });
  } catch (err) {
    req.log.error({ err }, "Failed to update furniture");
    res.status(500).json({ error: "Failed to update furniture" });
  }
});

router.delete("/furniture/:furnitureId", async (req, res) => {
  try {
    await db.delete(furnitureTable).where(eq(furnitureTable.id, req.params.furnitureId));
    res.status(204).send();
  } catch (err) {
    req.log.error({ err }, "Failed to delete furniture");
    res.status(500).json({ error: "Failed to delete furniture" });
  }
});

export default router;
