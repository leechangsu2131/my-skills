import { subjectMatches } from "./constants";

function text(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value).trim();
}

function numberText(value) {
    if (value === null || value === undefined || value === "") {
        return "";
    }
    return String(value).trim();
}

function firstValue(item, keys) {
    if (!item || typeof item !== "object") {
        return "";
    }

    for (const key of keys) {
        const value = item[key];
        if (value !== null && value !== undefined && value !== "") {
            return value;
        }
    }

    return "";
}

function formatPeriod(value) {
    const raw = text(value);
    if (!raw) {
        return "";
    }

    if (raw.includes("교시")) {
        return raw;
    }

    const match = raw.match(/\d+/);
    return match ? `${match[0]}교시` : raw;
}

export function getSubject(item) {
    return text(firstValue(item, ["subject", "과목"]));
}

export function getTitle(item) {
    return text(firstValue(item, ["title", "수업내용", "lesson_title"]));
}

export function getLesson(item) {
    return numberText(firstValue(item, ["lesson", "차시"]));
}

export function getUnit(item) {
    return text(firstValue(item, ["unit", "대단원", "단원"]));
}

export function getPdfPath(item) {
    return text(firstValue(item, ["pdf_path", "pdf파일", "pdf_pathname"]));
}

export function getRecordKey(item) {
    return text(firstValue(item, ["record_key", "_record_key", "lesson_id", "row_number", "_row"]));
}

export function getBridgeRow(item) {
    const value = firstValue(item, ["bridge_row", "_bridge_row"]);
    return value === "" ? null : value;
}

export function getPlannedDate(item) {
    return text(firstValue(item, ["planned_date", "slot_date", "plannedDate", "계획일", "date"]));
}

export function getPlannedPeriod(item) {
    return text(firstValue(item, ["planned_period", "slot_period", "plannedPeriod", "계획교시"]));
}

export function isDoneItem(item) {
    if (item?.is_done === true) {
        return true;
    }

    const status = text(firstValue(item, ["status", "실행여부"])).toLowerCase();
    return status === "done" || status === "완료" || status === "y" || status === "yes";
}

export function formatPlacement(item) {
    const plannedDate = getPlannedDate(item);
    const plannedPeriod = formatPeriod(getPlannedPeriod(item));

    if (plannedDate && plannedPeriod) {
        return `${plannedDate} · ${plannedPeriod}`;
    }
    if (plannedDate) {
        return plannedDate;
    }
    if (plannedPeriod) {
        return plannedPeriod;
    }
    return "배치 미정";
}

export function getActionKey(item) {
    return (
        getBridgeRow(item) ||
        getRecordKey(item) ||
        [
            getSubject(item),
            getPlannedDate(item),
            getPlannedPeriod(item),
            getLesson(item),
            getTitle(item),
        ]
            .filter(Boolean)
            .join("::")
    );
}

export function filterItemsBySubject(items, subjectFilter) {
    const normalizedItems = Array.isArray(items) ? items : [];

    if (!subjectFilter) {
        return normalizedItems;
    }

    return normalizedItems.filter((item) => subjectMatches(getSubject(item), subjectFilter));
}
