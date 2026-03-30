import { Router, type IRouter } from "express";
import { db, spacesTable, furnitureTable } from "@workspace/db";
import { eq, count } from "drizzle-orm";

const router: IRouter = Router();

router.get("/spaces", async (req, res) => {
  try {
    const spaces = await db.select().from(spacesTable).orderBy(spacesTable.createdAt);
    res.json(spaces.map(s => ({
      ...s,
      createdAt: s.createdAt.toISOString(),
      updatedAt: s.updatedAt.toISOString(),
    })));
  } catch (err) {
    req.log.error({ err }, "Failed to list spaces");
    res.status(500).json({ error: "Failed to list spaces" });
  }
});

router.post("/spaces", async (req, res) => {
  try {
    const { name, description, context } = req.body;
    if (!name) return res.status(400).json({ error: "name is required" });
    const [space] = await db.insert(spacesTable).values({
      name,
      description: description ?? null,
      context: context ?? null,
    }).returning();
    res.status(201).json({
      ...space,
      createdAt: space.createdAt.toISOString(),
      updatedAt: space.updatedAt.toISOString(),
    });
  } catch (err) {
    req.log.error({ err }, "Failed to create space");
    res.status(500).json({ error: "Failed to create space" });
  }
});

router.get("/spaces/:spaceId", async (req, res) => {
  try {
    const [space] = await db.select().from(spacesTable).where(eq(spacesTable.id, req.params.spaceId));
    if (!space) return res.status(404).json({ error: "Space not found" });
    res.json({
      ...space,
      createdAt: space.createdAt.toISOString(),
      updatedAt: space.updatedAt.toISOString(),
    });
  } catch (err) {
    req.log.error({ err }, "Failed to get space");
    res.status(500).json({ error: "Failed to get space" });
  }
});

router.put("/spaces/:spaceId", async (req, res) => {
  try {
    const { name, description, context } = req.body;
    const [space] = await db.update(spacesTable)
      .set({ name, description: description ?? null, context: context ?? null, updatedAt: new Date() })
      .where(eq(spacesTable.id, req.params.spaceId))
      .returning();
    if (!space) return res.status(404).json({ error: "Space not found" });
    res.json({
      ...space,
      createdAt: space.createdAt.toISOString(),
      updatedAt: space.updatedAt.toISOString(),
    });
  } catch (err) {
    req.log.error({ err }, "Failed to update space");
    res.status(500).json({ error: "Failed to update space" });
  }
});

router.delete("/spaces/:spaceId", async (req, res) => {
  try {
    await db.delete(spacesTable).where(eq(spacesTable.id, req.params.spaceId));
    res.status(204).send();
  } catch (err) {
    req.log.error({ err }, "Failed to delete space");
    res.status(500).json({ error: "Failed to delete space" });
  }
});

export default router;
