export function compareSlotOrder(a, b) {
    if (a.slot_date !== b.slot_date) return a.slot_date.localeCompare(b.slot_date);
    if (a.slot_period !== b.slot_period) return (a.slot_period ?? 0) - (b.slot_period ?? 0);
    if (a.slot_order !== b.slot_order) return (a.slot_order ?? 0) - (b.slot_order ?? 0);
    return String(a.id).localeCompare(String(b.id));
}

function nextSlotOrderInGroup(rows) {
    const values = rows
        .map((row) => Number(row.slot_order))
        .filter((value) => Number.isFinite(value));
    if (values.length === 0) return rows.length + 1;
    return Math.max(...values) + 1;
}

export function buildFutureTemplate(subjectRows) {
    const sorted = [...subjectRows].sort(compareSlotOrder);
    const last = sorted[sorted.length - 1];
    if (!last) return null;

    const dates = sorted.map((row) => row.slot_date).filter(Boolean);
    let gapDays = 7;
    for (let i = 1; i < dates.length; i += 1) {
        const prev = new Date(`${dates[i - 1]}T00:00:00`);
        const cur = new Date(`${dates[i]}T00:00:00`);
        const diff = Math.round((cur - prev) / (1000 * 60 * 60 * 24));
        if (diff > 0) gapDays = diff;
    }

    const nextDate = new Date(`${last.slot_date}T00:00:00`);
    nextDate.setDate(nextDate.getDate() + gapDays);
    const yyyy = nextDate.getFullYear();
    const mm = String(nextDate.getMonth() + 1).padStart(2, "0");
    const dd = String(nextDate.getDate()).padStart(2, "0");

    return {
        slot_date: `${yyyy}-${mm}-${dd}`,
        slot_period: last.slot_period,
        slot_order: last.slot_order,
    };
}

export function buildPullNextPlan({ currentSlot, subjectSlots }) {
    const targetSlotKey = {
        slot_date: currentSlot.slot_date,
        slot_period: currentSlot.slot_period,
    };
    if (!targetSlotKey.slot_date) {
        throw new Error("target slot has no date");
    }

    const sortedSubjectSlots = [...subjectSlots].sort(compareSlotOrder);
    const targetGroupRows = sortedSubjectSlots.filter(
        (row) => row.slot_date === targetSlotKey.slot_date
            && Number(row.slot_period) === Number(targetSlotKey.slot_period)
    );
    if (targetGroupRows.length === 0) {
        throw new Error("target slot group not found");
    }

    const targetGroupIds = new Set(targetGroupRows.map((row) => row.id));
    const targetGroupEndIndex = sortedSubjectSlots.reduce((acc, row, idx) => (
        targetGroupIds.has(row.id) ? idx : acc
    ), -1);

    const nextPlannedRow = sortedSubjectSlots
        .slice(targetGroupEndIndex + 1)
        .find((row) => row.status === "planned");
    if (!nextPlannedRow) {
        throw new Error("there is no later lesson to pull forward");
    }

    const plannedSubjectRows = sortedSubjectSlots.filter((row) => row.status === "planned");
    const sourceIndex = plannedSubjectRows.findIndex((row) => row.id === nextPlannedRow.id);
    if (sourceIndex < 0) {
        throw new Error("next planned row not found in subject flow");
    }

    const shiftRows = plannedSubjectRows.slice(sourceIndex + 1);
    const shiftTemplates = plannedSubjectRows
        .slice(sourceIndex)
        .map((row) => ({
            slot_date: row.slot_date,
            slot_period: row.slot_period,
            slot_order: row.slot_order,
        }));

    const updates = [
        {
            id: nextPlannedRow.id,
            slot_date: targetSlotKey.slot_date,
            slot_period: targetSlotKey.slot_period,
            slot_order: nextSlotOrderInGroup(targetGroupRows),
        },
    ];

    for (let i = 0; i < shiftRows.length; i += 1) {
        const row = shiftRows[i];
        const tpl = shiftTemplates[i];
        if (!tpl) continue;

        const changed = (
            row.slot_date !== tpl.slot_date
            || Number(row.slot_period) !== Number(tpl.slot_period)
            || Number(row.slot_order) !== Number(tpl.slot_order)
        );
        if (!changed) continue;

        updates.push({
            id: row.id,
            slot_date: tpl.slot_date,
            slot_period: tpl.slot_period,
            slot_order: tpl.slot_order,
        });
    }

    return { updates };
}
