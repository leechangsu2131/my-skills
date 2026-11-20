importScripts("absence-workflow.js");

/* 팝업은 다른 곳을 클릭하거나 NEIS 확인창이 뜨면 닫힌다. 결과를 아이콘 배지로도 보여준다. */
function showAbsenceBadge(status, submittedCount) {
    const text = status === "running" ? "…" : status === "complete" ? String(submittedCount || "✓") : "!";
    const color = status === "running" ? "#6b7280" : status === "complete" ? "#16a34a" : "#dc2626";
    try {
        chrome.action.setBadgeBackgroundColor({ color });
        chrome.action.setBadgeText({ text });
        chrome.action.setTitle({ title: status === "running" ? "NEIS 신청서 접수·상신 처리 중…" : status === "complete" ? `신청서 승인요청 ${submittedCount || 0}건 완료` : "신청서 처리 확인 필요 — 팝업을 열어 확인하세요" });
    } catch (_) { }
}


const STORAGE_KEY = "teacherlessonNeisCache";
const STUDENT_STATUS_KEY = "teacherlessonNeisStudentStatus";
const LAST_ABSENCE_ACTION_KEY = "teacherlessonNeisLastAbsenceAction";
const ABSENCE_EXECUTION_LOCK_KEY = "teacherlessonNeisAbsenceExecutionLock";
const MAX_RECORDS = 2500;
const WEEK_CACHE_TTL_MS = 12 * 60 * 60 * 1000;
let absenceExecutionInFlight = false;

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

async function storePayload(payload) {
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

    return {
        ok: true,
        imported: normalized.records.length,
        range_start: normalized.start,
        range_end: normalized.end,
        stored_locally: true,
    };
}

function normalizeStudentRecords(rows, { attendance = false } = {}) {
    if (!Array.isArray(rows)) return [];
    return rows.slice(0, 1000).flatMap((item) => {
        const startDate = normalizeDate(item?.date || item?.start_date || item?.startDate);
        const endDate = normalizeDate(item?.end_date || item?.endDate) || startDate;
        const student = normalizeText(item?.student || item?.student_name, 50);
        const kind = normalizeText(item?.kind || item?.category, 40);
        if (!startDate || !endDate || startDate > endDate || !student || !kind) return [];
        const row = {
            date: startDate,
            end_date: endDate,
            student,
            class_name: normalizeText(item?.class_name || item?.className, 30),
            kind,
        };
        if (attendance) {
            const count = Number(item?.count);
            if (!Number.isFinite(count) || count <= 0 || count > 100) return [];
            row.count = count;
        } else {
            row.status = normalizeText(item?.status, 30);
            row.approval_status = normalizeText(item?.approval_status || item?.approvalStatus, 30);
        }
        return [row];
    });
}

async function storeStudentStatus(payload) {
    const asOf = normalizeDate(payload?.as_of);
    if (!asOf) throw new Error("출결 기준 날짜를 확인할 수 없습니다.");
    const previousStorage = await chrome.storage.local.get(STUDENT_STATUS_KEY);
    const previous = previousStorage[STUDENT_STATUS_KEY] || {};
    const failedSections = Array.isArray(payload?.failed_sections)
        ? [...new Set(payload.failed_sections.filter((key) => ["attendance", "absence_applications", "experiential_applications"].includes(key)))]
        : [];
    const preserveOrNormalize = (key, previousKey, rows, options) => failedSections.includes(key)
        ? (Array.isArray(previous[previousKey]) ? previous[previousKey] : [])
        : normalizeStudentRecords(rows, options);
    const cache = {
        asOf,
        updatedAt: new Date().toISOString(),
        attendance: preserveOrNormalize("attendance", "attendance", payload.attendance, { attendance: true }),
        absenceApplications: preserveOrNormalize("absence_applications", "absenceApplications", payload.absence_applications),
        experientialApplications: preserveOrNormalize("experiential_applications", "experientialApplications", payload.experiential_applications),
        failedSections,
        errors: Array.isArray(payload?.errors) ? payload.errors.map((item) => normalizeText(item, 180)).filter(Boolean) : [],
    };
    await chrome.storage.local.set({ [STUDENT_STATUS_KEY]: cache });
    return {
        ok: true,
        as_of: cache.asOf,
        attendance: cache.attendance.length,
        absence_applications: cache.absenceApplications.length,
        experiential_applications: cache.experientialApplications.length,
    };
}

async function updateAbsenceApplications(rows) {
    const stored = await chrome.storage.local.get(STUDENT_STATUS_KEY);
    const cache = stored[STUDENT_STATUS_KEY] || {};
    cache.absenceApplications = normalizeStudentRecords(rows);
    cache.updatedAt = new Date().toISOString();
    cache.failedSections = (Array.isArray(cache.failedSections) ? cache.failedSections : [])
        .filter((section) => section !== "absence_applications");
    cache.errors = (Array.isArray(cache.errors) ? cache.errors : [])
        .filter((item) => !String(item).startsWith("결석 신청:"));
    await chrome.storage.local.set({ [STUDENT_STATUS_KEY]: cache });
    return { ok: true, count: cache.absenceApplications.length };
}

function isNeisPage(sender) {
    return /^https:\/\/.+\.neis\.go\.kr\//.test(sender.tab?.url || sender.url || "");
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message) return false;
    if (message.type === "OPEN_VIEWER") {
        if (!isNeisPage(sender)) {
            sendResponse({ ok: false, error: "NEIS 화면에서 온 요청이 아닙니다." });
            return false;
        }
        chrome.tabs.create({ url: chrome.runtime.getURL("viewer.html") }, () => {
            sendResponse(chrome.runtime.lastError
                ? { ok: false, error: "수업 뷰어를 열지 못했습니다." }
                : { ok: true });
        });
        return true;
    }
    if (message.type === "STORE_STUDENT_STATUS") {
        if (sender.id !== chrome.runtime.id) {
            sendResponse({ ok: false, error: "확장 프로그램 팝업에서 보낸 자료만 저장할 수 있습니다." });
            return false;
        }
        storeStudentStatus(message.payload)
            .then(sendResponse)
            .catch((error) => sendResponse({ ok: false, error: error.message || "학생 현황을 저장하지 못했습니다." }));
        return true;
    }
    if (message.type === "PROCESS_SELECTED_ABSENCE_WORK") {
        if (sender.id !== chrome.runtime.id || sender.url !== chrome.runtime.getURL("popup.html")) {
            sendResponse({ ok: false, error: "NEIS 처리 실행은 확장 팝업에서만 시작할 수 있습니다." });
            return false;
        }
        if (absenceExecutionInFlight) {
            sendResponse({ ok: false, error: "신청서 처리가 이미 진행 중입니다. 중복 실행하지 말고 현재 NEIS 상태를 확인해 주세요." });
            return false;
        }
        absenceExecutionInFlight = true;
        let absenceExecutionLockCreated = false;
        let knownExecutionResult = null;
        (async () => {
            const payload = message.payload || {};
            const monthStart = normalizeDate(payload.monthStart);
            const monthEnd = normalizeDate(payload.monthEnd);
            const batches = (Array.isArray(payload.batches) ? payload.batches : []).slice(0, 50).map((batch) => ({
                kind: normalizeText(batch?.kind, 40),
                applicationIds: [...new Set((Array.isArray(batch?.applicationIds) ? batch.applicationIds : [])
                    .map((value) => normalizeText(value, 80)).filter(Boolean))],
                approvers: [...new Set((Array.isArray(batch?.approvers) ? batch.approvers : [])
                    .map((value) => normalizeText(value, 40)).filter(Boolean))],
                absenceCategoryCodes: batch?.absenceCategoryCodes && typeof batch.absenceCategoryCodes === "object"
                    ? Object.fromEntries(Object.entries(batch.absenceCategoryCodes)
                        .map(([id, code]) => [normalizeText(id, 80), normalizeText(code, 2)]).filter(([id]) => id))
                    : {},
                teacherReasons: batch?.teacherReasons && typeof batch.teacherReasons === "object"
                    ? Object.fromEntries(Object.entries(batch.teacherReasons)
                        .map(([id, reason]) => [normalizeText(id, 80), String(reason ?? "").slice(0, 3000)]).filter(([id]) => id))
                    : {},
            }));
            if (!monthStart || !monthEnd || monthStart > monthEnd || !batches.length
                || batches.some((batch) => !batch.kind || !batch.applicationIds.length || !batch.approvers.length)
                || batches.some((batch) => !["결석신고", "체험학습신청서", "체험학습보고서"].includes(batch.kind))
                || batches.some((batch) => batch.kind === "결석신고" && batch.applicationIds.some((id) => !["01", "02", "03", "04"].includes(batch.absenceCategoryCodes[id])))
                || batches.some((batch) => batch.kind === "결석신고" && batch.applicationIds.some((id) => typeof batch.teacherReasons[id] !== "string"))
                || new Set(batches.map((batch) => batch.kind)).size !== batches.length
                || batches.some((batch) => new Set(batch.applicationIds).size !== batch.applicationIds.length)) {
                throw new Error("선택 기간, 신청 유형별 대상, 저장 결재선을 다시 확인해 주세요.");
            }
            const tabId = Number(message.tabId);
            const tab = Number.isInteger(tabId) ? await chrome.tabs.get(tabId) : null;
            if (!tab?.id || !/^https:\/\/.+\.neis\.go\.kr\//.test(tab.url || "")) {
                throw new Error("로그인한 NEIS 탭을 찾지 못했습니다. 목록을 다시 조회해 주세요.");
            }
            const existingLockData = await chrome.storage.local.get(ABSENCE_EXECUTION_LOCK_KEY);
            if (existingLockData[ABSENCE_EXECUTION_LOCK_KEY]) {
                throw new Error("이전 실행의 상태가 아직 확인되지 않았습니다. NEIS 처리대상 목록을 새로 조회한 뒤 다시 선택해 주세요.");
            }
            await chrome.storage.local.set({
                [ABSENCE_EXECUTION_LOCK_KEY]: {
                    status: "running",
                    startedAt: new Date().toISOString(),
                    tabId: tab.id,
                },
            });
            absenceExecutionLockCreated = true;
            showAbsenceBadge("running");
            await chrome.storage.local.set({
                [LAST_ABSENCE_ACTION_KEY]: {
                    status: "running",
                    startedAt: new Date().toISOString(),
                    receiptCount: 0,
                    submittedCount: 0,
                    errors: [],
                },
            });
            const executions = await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                world: "MAIN",
                func: processSelectedAbsenceWorkOnNeis,
                args: [{ monthStart, monthEnd, batches }],
            });
            const result = executions?.[0]?.result;
            if (!result?.ok) {
                await chrome.storage.local.remove(ABSENCE_EXECUTION_LOCK_KEY);
                absenceExecutionLockCreated = false;
                throw new Error(result?.error || "선택 건 처리 결과를 받지 못했습니다.");
            }
            knownExecutionResult = result;
            await chrome.storage.local.remove(ABSENCE_EXECUTION_LOCK_KEY);
            absenceExecutionLockCreated = false;
            if (Array.isArray(result.processedKinds) && result.processedKinds.includes("결석신고") && Array.isArray(result.absence_applications)) await updateAbsenceApplications(result.absence_applications);
            const summary = {
                status: result.errors?.length ? "attention" : "complete",
                updatedAt: new Date().toISOString(),
                receiptCount: Array.isArray(result.receiptIds) ? result.receiptIds.length : 0,
                submittedCount: Array.isArray(result.submittedIds) ? result.submittedIds.length : 0,
                errors: Array.isArray(result.errors) ? result.errors.map((item) => normalizeText(item, 400)).filter(Boolean) : [],
                warnings: Array.isArray(result.warnings) ? result.warnings.map((item) => normalizeText(item, 300)).filter(Boolean) : [],
            };
            await chrome.storage.local.set({ [LAST_ABSENCE_ACTION_KEY]: summary });
            showAbsenceBadge(summary.status, summary.submittedCount);
            sendResponse({ ok: true, ...summary });
        })().catch(async (error) => {
            const uncertain = absenceExecutionLockCreated && !knownExecutionResult;
            const summary = {
                status: uncertain ? "unknown" : "attention",
                updatedAt: new Date().toISOString(),
                receiptCount: uncertain ? null : Array.isArray(knownExecutionResult?.receiptIds) ? knownExecutionResult.receiptIds.length : 0,
                submittedCount: uncertain ? null : Array.isArray(knownExecutionResult?.submittedIds) ? knownExecutionResult.submittedIds.length : 0,
                errors: [normalizeText(uncertain
                    ? "실행 중 NEIS 응답이 끊겨 일부 반영 여부를 확인할 수 없습니다. 재실행하지 말고 대상 목록을 새로 조회해 현재 상태를 확인하세요."
                    : error?.message || "처리 실행이 중단되었습니다.", 180)],
            };
            if (uncertain) {
                await chrome.storage.local.set({
                    [ABSENCE_EXECUTION_LOCK_KEY]: {
                        status: "unknown",
                        updatedAt: summary.updatedAt,
                    },
                });
                await chrome.storage.local.set({ [LAST_ABSENCE_ACTION_KEY]: summary });
            } else if (knownExecutionResult) {
                await chrome.storage.local.set({ [LAST_ABSENCE_ACTION_KEY]: summary });
            }
            showAbsenceBadge(summary.status, summary.submittedCount);
            sendResponse({ ok: false, error: summary.errors[0] });
        }).finally(() => { absenceExecutionInFlight = false; });
        return true;
    }
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

    storePayload(message.payload)
        .then(sendResponse)
        .catch((error) => sendResponse({ ok: false, error: error.message || "수업내용을 저장하지 못했습니다." }));
    return true;
});
