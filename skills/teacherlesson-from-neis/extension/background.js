const STORAGE_KEY = "teacherlessonNeisCache";
const API_URL = "http://127.0.0.1:5101/api/import";
const MAX_RECORDS = 2500;
const WEEK_CACHE_TTL_MS = 12 * 60 * 60 * 1000;

function normalizeDate(value) {
    const text = String(value || "").trim();
    return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : "";
}

function normalizeText(value, maxLength) {
    return String(value ?? "").trim().slice(0, maxLength);
}

function normalizePayload(payload) {
    const start = normalizeDate(payload?.range_start);
    const end = normalizeDate(payload?.range_end);
    if (!start || !end || start > end || !Array.isArray(payload?.records) || payload.records.length > 1200) {
        throw new Error("가져온 날짜 범위 또는 수업 목록이 올바르지 않습니다.");
    }

    const byKey = new Map();
    for (const item of payload.records) {
        const date = normalizeDate(item?.date);
        const periodText = normalizeText(item?.period, 3);
        const subject = normalizeText(item?.subject, 100);
        if (!date || date < start || date > end || !/^\d{1,2}$/.test(periodText) || !subject) continue;
        const record = {
            date,
            period: String(Number(periodText)),
            subject,
            unit: normalizeText(item?.unit, 300),
            content: normalizeText(item?.content, 2000),
            lesson_number: normalizeText(item?.lessonNumber ?? item?.lesson_number, 20),
            total_lessons: normalizeText(item?.totalLessons ?? item?.total_lessons, 20),
            textbook_page: normalizeText(item?.textbookPage ?? item?.textbook_page, 100),
            additional_page: normalizeText(item?.additionalPage ?? item?.additional_page, 100),
        };
        byKey.set(`${record.date}|${record.period}|${record.subject}`, record);
    }
    const completeWeeks = Array.isArray(payload.complete_weeks)
        ? payload.complete_weeks.map((week) => ({ start: normalizeDate(week?.start), end: normalizeDate(week?.end) }))
            .filter((week) => week.start && week.end && week.start <= week.end && week.start >= start && week.end <= end)
        : [];
    const completeMonth = /^\d{4}-\d{2}$/.test(String(payload.complete_month || "")) ? String(payload.complete_month) : "";
    return {
        start,
        end,
        records: [...byKey.values()],
        source: normalizeText(payload.source, 50) || "NEIS 주간학습안내",
        completeWeeks,
        completeMonth,
    };
}

async function storeAndForward(payload) {
    const normalized = normalizePayload(payload);
    const stored = await chrome.storage.local.get(STORAGE_KEY);
    const previous = stored[STORAGE_KEY] || {};
    const retained = (Array.isArray(previous.records) ? previous.records : []).filter(
        (record) => record.date < normalized.start || record.date > normalized.end,
    );
    const records = [...retained, ...normalized.records]
        .sort((a, b) => a.date.localeCompare(b.date) || Number(a.period) - Number(b.period) || a.subject.localeCompare(b.subject))
        .slice(-MAX_RECORDS);
    const fetchedWeeks = { ...(previous.fetchedWeeks || {}) };
    for (const week of normalized.completeWeeks) fetchedWeeks[`${week.start}|${week.end}`] = Date.now();
    const completeMonths = { ...(previous.completeMonths || {}) };
    if (normalized.completeMonth) completeMonths[normalized.completeMonth] = Date.now();
    const cache = {
        records,
        updatedAt: new Date().toISOString(),
        rangeStart: normalized.start,
        rangeEnd: normalized.end,
        source: normalized.source,
        fetchedWeeks,
        completeMonths,
    };
    await chrome.storage.local.set({ [STORAGE_KEY]: cache });

    let viewerUpdated = false;
    let viewerError = "";
    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source: normalized.source,
                range_start: normalized.start,
                range_end: normalized.end,
                records: normalized.records.map((record) => ({
                    ...record,
                    lessonNumber: record.lesson_number,
                    totalLessons: record.total_lessons,
                    textbookPage: record.textbook_page,
                    additionalPage: record.additional_page,
                })),
            }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(result.error || "로컬 뷰어가 자료를 받지 못했습니다.");
        viewerUpdated = true;
    } catch (error) {
        viewerError = error.message || "로컬 뷰어에 연결하지 못했습니다.";
    }

    return {
        ok: true,
        imported: normalized.records.length,
        range_start: normalized.start,
        range_end: normalized.end,
        stored_locally: true,
        viewer_updated: viewerUpdated,
        viewer_error: viewerError,
    };
}

function isNeisPage(sender) {
    return /^https:\/\/.+\.neis\.go\.kr\//.test(sender.tab?.url || sender.url || "");
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message) return false;
    if (message.type === "CHECK_WEEK_CACHE") {
        if (!isNeisPage(sender)) {
            sendResponse({ ok: false, error: "NEIS 페이지에서 온 요청이 아닙니다." });
            return false;
        }
        chrome.storage.local.get(STORAGE_KEY).then((stored) => {
            const fetchedWeeks = stored[STORAGE_KEY]?.fetchedWeeks || {};
            const now = Date.now();
            const fresh = {};
            for (const week of Array.isArray(message.weeks) ? message.weeks : []) {
                const start = normalizeDate(week?.start);
                const end = normalizeDate(week?.end);
                const key = start && end ? `${start}|${end}` : "";
                fresh[key] = Boolean(key && fetchedWeeks[key] && now - fetchedWeeks[key] < WEEK_CACHE_TTL_MS);
            }
            sendResponse({ ok: true, fresh });
        }).catch(() => sendResponse({ ok: false, error: "로컬 수업 캐시를 읽지 못했습니다." }));
        return true;
    }
    if (!["AUTO_SYNC_LESSONS", "MANUAL_IMPORT_LESSONS"].includes(message.type)) return false;
    if (message.type === "AUTO_SYNC_LESSONS") {
        if (!isNeisPage(sender)) {
            sendResponse({ ok: false, error: "NEIS 페이지에서 온 자료가 아닙니다." });
            return false;
        }
    } else if (sender.id !== chrome.runtime.id) {
        sendResponse({ ok: false, error: "확장 프로그램 팝업에서 보낸 요청만 처리합니다." });
        return false;
    }

    storeAndForward(message.payload)
        .then(sendResponse)
        .catch((error) => sendResponse({ ok: false, error: error.message || "수업내용을 저장하지 못했습니다." }));
    return true;
});
