import test from "node:test";
import assert from "node:assert/strict";

import { buildPullNextPlan } from "../src/utils/slotPacing.mjs";

test("buildPullNextPlan shifts every following planned lesson forward by one slot", () => {
    const plan = buildPullNextPlan({
        currentSlot: {
            id: "current",
            slot_date: "2026-04-20",
            slot_period: 2,
            slot_order: 1,
            status: "done",
        },
        subjectSlots: [
            {
                id: "done-before",
                slot_date: "2026-04-19",
                slot_period: 2,
                slot_order: 1,
                status: "done",
            },
            {
                id: "current",
                slot_date: "2026-04-20",
                slot_period: 2,
                slot_order: 1,
                status: "done",
            },
            {
                id: "next",
                slot_date: "2026-04-21",
                slot_period: 3,
                slot_order: 1,
                status: "planned",
            },
            {
                id: "later-1",
                slot_date: "2026-04-22",
                slot_period: 4,
                slot_order: 1,
                status: "planned",
            },
            {
                id: "later-2",
                slot_date: "2026-04-23",
                slot_period: 5,
                slot_order: 1,
                status: "planned",
            },
        ],
    });

    assert.deepStrictEqual(plan.updates, [
        {
            id: "next",
            slot_date: "2026-04-20",
            slot_period: 2,
            slot_order: 2,
        },
        {
            id: "later-1",
            slot_date: "2026-04-21",
            slot_period: 3,
            slot_order: 1,
        },
        {
            id: "later-2",
            slot_date: "2026-04-22",
            slot_period: 4,
            slot_order: 1,
        },
    ]);
});
