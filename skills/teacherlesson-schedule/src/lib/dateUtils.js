function toDate(value) {
    if (value instanceof Date) {
        return new Date(value.getTime());
    }

    if (typeof value === "string") {
        const trimmed = value.trim();
        const match = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (match) {
            const [, year, month, day] = match;
            return new Date(Number(year), Number(month) - 1, Number(day));
        }

        const parsed = new Date(trimmed);
        if (!Number.isNaN(parsed.getTime())) {
            return parsed;
        }
    }

    if (typeof value === "number") {
        const parsed = new Date(value);
        if (!Number.isNaN(parsed.getTime())) {
            return parsed;
        }
    }

    return new Date();
}

export function toIsoDate(value) {
    const date = toDate(value);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

export function shiftDate(value, days) {
    const date = toDate(value);
    date.setDate(date.getDate() + Number(days || 0));
    return toIsoDate(date);
}

export function formatKoreanDate(value, options = {}) {
    const date = toDate(value);
    const formatOptions =
        Object.keys(options).length > 0
            ? options
            : {
                  month: "numeric",
                  day: "numeric",
                  weekday: "short",
              };

    return new Intl.DateTimeFormat("ko-KR", formatOptions).format(date);
}

export function formatWeekday(value) {
    return new Intl.DateTimeFormat("ko-KR", { weekday: "short" }).format(toDate(value));
}

export function getWeekdays(value) {
    const anchor = toDate(value);
    const mondayOffset = (anchor.getDay() + 6) % 7;
    anchor.setDate(anchor.getDate() - mondayOffset);

    return Array.from({ length: 5 }, (_, index) => {
        const current = new Date(anchor.getTime());
        current.setDate(anchor.getDate() + index);
        return current;
    });
}

export function getMonthGrid(value) {
    const anchor = toDate(value);
    const monthStart = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
    const monthEnd = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0);

    const gridStart = new Date(monthStart.getTime());
    gridStart.setDate(monthStart.getDate() - monthStart.getDay());

    const gridEnd = new Date(monthEnd.getTime());
    gridEnd.setDate(monthEnd.getDate() + (6 - monthEnd.getDay()));

    const weeks = [];
    let cursor = new Date(gridStart.getTime());

    while (cursor <= gridEnd) {
        const week = [];

        for (let dayIndex = 0; dayIndex < 7; dayIndex += 1) {
            const current = new Date(cursor.getTime());
            week.push({
                date: current,
                iso: toIsoDate(current),
                inMonth: current.getMonth() === anchor.getMonth(),
            });
            cursor.setDate(cursor.getDate() + 1);
        }

        weeks.push(week);
    }

    return weeks;
}
