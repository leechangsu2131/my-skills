import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { appRouter } from "./routers";
import type { TrpcContext } from "./_core/context";
import type { User } from "../drizzle/schema";

// Mock context for testing
function createMockContext(): TrpcContext {
  const user: User = {
    id: 1,
    openId: "test-user",
    name: "Test User",
    email: "test@example.com",
    loginMethod: "test",
    role: "user",
    createdAt: new Date(),
    updatedAt: new Date(),
    lastSignedIn: new Date(),
  };

  return {
    user,
    req: {
      protocol: "https",
      headers: {},
    } as any,
    res: {} as any,
  };
}

describe("StorageMap tRPC Routers", () => {
  let caller: ReturnType<typeof appRouter.createCaller>;
  let ctx: TrpcContext;

  beforeAll(() => {
    ctx = createMockContext();
    caller = appRouter.createCaller(ctx);
  });

  describe("Space Router", () => {
    it("should list spaces for user", async () => {
      const spaces = await caller.space.list();
      expect(Array.isArray(spaces)).toBe(true);
    });

    it("should create a new space", async () => {
      const newSpace = await caller.space.create({
        name: "Test Space",
        description: "A test space",
      });
      expect(newSpace).toHaveProperty("spaceId");
      expect(newSpace.name).toBe("Test Space");
    });
  });

  describe("Furniture Router", () => {
    let testSpaceId: string;

    beforeAll(async () => {
      const space = await caller.space.create({
        name: "Furniture Test Space",
      });
      testSpaceId = space.spaceId;
    });

    it("should list furniture by space", async () => {
      const furniture = await caller.furniture.listBySpace({
        spaceId: testSpaceId,
      });
      expect(Array.isArray(furniture)).toBe(true);
    });

    it("should create furniture", async () => {
      const newFurniture = await caller.furniture.create({
        spaceId: testSpaceId,
        name: "Test Cabinet",
        type: "cabinet",
        color: "#ff0000",
      });
      expect(newFurniture).toHaveProperty("furnitureId");
      expect(newFurniture.name).toBe("Test Cabinet");
      expect(newFurniture.color).toBe("#ff0000");
    });

    it("should update furniture position", async () => {
      const furniture = await caller.furniture.create({
        spaceId: testSpaceId,
        name: "Movable Cabinet",
      });

      const updated = await caller.furniture.update({
        furnitureId: furniture.furnitureId,
        posX: 100,
        posY: 200,
        width: 300,
        height: 400,
      });

      expect(updated?.posX).toBe(100);
      expect(updated?.posY).toBe(200);
      expect(updated?.width).toBe(300);
      expect(updated?.height).toBe(400);
    });
  });

  describe("Item Router", () => {
    let testSpaceId: string;
    let testFurnitureId: string;

    beforeAll(async () => {
      const space = await caller.space.create({
        name: "Item Test Space",
      });
      testSpaceId = space.spaceId;

      const furniture = await caller.furniture.create({
        spaceId: testSpaceId,
        name: "Test Drawer",
      });
      testFurnitureId = furniture.furnitureId;
    });

    it("should list items for user", async () => {
      const items = await caller.item.list();
      expect(Array.isArray(items)).toBe(true);
    });

    it("should create an item", async () => {
      const newItem = await caller.item.create({
        name: "Test Item",
        furnitureId: testFurnitureId,
        category: "stationery",
        tags: ["important", "office"],
        memo: "Test memo",
        quantity: 5,
      });

      expect(newItem).toHaveProperty("itemId");
      expect(newItem.name).toBe("Test Item");
      expect(newItem.quantity).toBe(5);
    });

    it("should list items by furniture", async () => {
      await caller.item.create({
        name: "Item 1",
        furnitureId: testFurnitureId,
      });

      const items = await caller.item.listByFurniture({
        furnitureId: testFurnitureId,
      });

      expect(Array.isArray(items)).toBe(true);
      expect(items.length).toBeGreaterThan(0);
    });

    it("should search items with priority", async () => {
      await caller.item.create({
        name: "Scissors",
        furnitureId: testFurnitureId,
        tags: ["sharp", "office"],
      });

      const results = await caller.item.search({
        query: "scissors",
      });

      expect(Array.isArray(results)).toBe(true);
      // Should find the item by name
      const found = results.find((item) => item.name.toLowerCase().includes("scissors"));
      expect(found).toBeDefined();
    });

    it("should update item", async () => {
      const item = await caller.item.create({
        name: "Original Name",
        furnitureId: testFurnitureId,
      });

      const updated = await caller.item.update({
        itemId: item.itemId,
        name: "Updated Name",
        quantity: 10,
      });

      expect(updated?.name).toBe("Updated Name");
      expect(updated?.quantity).toBe(10);
    });

    it("should delete item", async () => {
      const item = await caller.item.create({
        name: "Item to Delete",
        furnitureId: testFurnitureId,
      });

      const result = await caller.item.delete({
        itemId: item.itemId,
      });

      expect(result.success).toBe(true);
    });
  });

  describe("History Router", () => {
    let testSpaceId: string;
    let testFurnitureId: string;
    let testItemId: string;

    beforeAll(async () => {
      const space = await caller.space.create({
        name: "History Test Space",
      });
      testSpaceId = space.spaceId;

      const furniture = await caller.furniture.create({
        spaceId: testSpaceId,
        name: "Test Furniture",
      });
      testFurnitureId = furniture.furnitureId;

      const item = await caller.item.create({
        name: "History Test Item",
        furnitureId: testFurnitureId,
      });
      testItemId = item.itemId;
    });

    it("should list history for item", async () => {
      const history = await caller.history.listByItem({
        itemId: testItemId,
      });

      expect(Array.isArray(history)).toBe(true);
    });
  });

  describe("Metrics Router", () => {
    it("should get data quality metrics", async () => {
      const metrics = await caller.metrics.getQuality();

      expect(metrics).toHaveProperty("requiredFieldsCompleteness");
      expect(metrics).toHaveProperty("furnitureAssignmentRate");
      expect(metrics).toHaveProperty("nameDuplicateRate");
      expect(metrics).toHaveProperty("dataFreshnessRate");

      // All metrics should be between 0 and 100
      expect(metrics.requiredFieldsCompleteness).toBeGreaterThanOrEqual(0);
      expect(metrics.requiredFieldsCompleteness).toBeLessThanOrEqual(100);
    });
  });

  describe("Auth Router", () => {
    it("should get current user", async () => {
      const user = await caller.auth.me();
      expect(user).toBeDefined();
      expect(user?.openId).toBe("test-user");
    });
  });
});
