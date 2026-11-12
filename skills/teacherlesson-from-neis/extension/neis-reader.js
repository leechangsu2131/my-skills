(() => {
    "use strict";

    const APP_ID = "edu/sw/els/edc/tm/els_edctm06_m00";
    const SOURCE = "teacherlesson-from-neis-v1";
    const DAYS = ["mon", "tue", "wed", "thu", "fri"];
    const MAX_AUTO_WEEKS = 40;
    const CACHE_WAIT_MS = 4000;
    if (window.__teacherlessonFromNeisReader) return;
    window.__teacherlessonFromNeisReader = true;

    let lastSignature = "";
    let lastPayload = null;
    let captureGeneration = 0;
    let lastBlockedSignature = "";
    let autoSyncRunning = false;
    let cacheRequestId = 0;
    const cacheWaiters = new Map();
    const internalEntryKeys = new Set();

    function post(type, payload = {}) {
        window.postMessage({ source: SOURCE, type, payload }, location.origin);
    }

    function dateValue(value) {
        const digits = String(value ?? "").replace(/\D/g, "");
        if (digits.length !== 8) return "";
        return `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6, 8)}`;
    }

    function textValue(value, limit = 2000) {
        return String(value ?? "").trim().slice(0, limit);
    }

    function getApp() {
        const platform = window.cpr?.core?.Platform?.INSTANCE;
        if (!platform) return null;
        try {
            return platform.getAllRunningAppInstances().find((instance) => instance?.app?.id === APP_ID) || null;
        } catch (_) {
            return null;
        }
    }

    function getValue(dataset, row, column) {
        try { return dataset.getValue(row, column) ?? ""; } catch (_) { return ""; }
    }

    function readWeekRows(dataset) {
        const rows = [];
        if (!dataset?.getRowCount) return rows;
        for (let row = 0; row < dataset.getRowCount(); row += 1) {
            rows.push({
                index: row,
                begin: dateValue(getValue(dataset, row, "weekBgngYmd")),
                end: dateValue(getValue(dataset, row, "weekEndYmd")),
                rawBegin: getValue(dataset, row, "weekBgngYmd"),
                rawEnd: getValue(dataset, row, "weekEndYmd"),
                week: String(getValue(dataset, row, "weekCnt") ?? ""),
                rawWeek: getValue(dataset, row, "weekCnt"),
            });
        }
        return rows.filter((row) => row.begin && row.end && row.begin <= row.end);
    }

    function currentRange(app, weekRows, dates) {
        const search = app.lookup("dmSearch");
        let begin = "";
        let end = "";
        try {
            begin = dateValue(search?.getValue?.("weekBgngYmd"));
            end = dateValue(search?.getValue?.("weekEndYmd"));
        } catch (_) { }
        if (begin && end) {
            const matching = weekRows.find((row) => row.begin === begin && row.end === end);
            if (matching) return { start: matching.begin, end: matching.end };
        }
        if (dates.length) {
            const matching = weekRows.find((row) => dates.some((date) => row.begin <= date && date <= row.end));
            if (matching) return { start: matching.begin, end: matching.end };
            const first = [...dates].sort()[0];
            const weekday = new Date(`${first}T12:00:00`).getDay();
            const monday = new Date(`${first}T12:00:00`);
            monday.setDate(monday.getDate() - ((weekday + 6) % 7));
            const friday = new Date(monday);
            friday.setDate(friday.getDate() + 4);
            const format = (value) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
            return { start: format(monday), end: format(friday) };
        }
        return null;
    }

    function isLessonDataModified(dataset) {
        try {
            return typeof dataset?.isModified === "function" && dataset.isModified();
        } catch (_) {
            return true;
        }
    }

    function readPayload(app, range) {
        const lessonData = app.lookup("dsWikLrn");
        if (!lessonData?.getRowCount) return { ready: false };
        if (isLessonDataModified(lessonData)) {
            return { ready: false, blocked: true, reason: "수업내용에 저장되지 않은 변경이 있어 자동 동기화를 건너뛰었습니다." };
        }

        const records = [];
        for (let row = 0; row < lessonData.getRowCount(); row += 1) {
            const period = textValue(getValue(lessonData, row, "pirNm") || getValue(lessonData, row, "pir"), 12)
                .replace(/교시/g, "")
                .replace(/\s/g, "");
            if (!/^\d{1,2}$/.test(period)) continue;
            for (const day of DAYS) {
                const date = dateValue(getValue(lessonData, row, `${day}AllTiYmd`));
                if (!date || date < range.start || date > range.end) continue;
                const record = {
                    date,
                    period: String(Number(period)),
                    subject: textValue(getValue(lessonData, row, `${day}EtbSbjtNm`), 100),
                    unit: textValue(getValue(lessonData, row, `${day}WikLrnUitNm`), 300),
                    content: textValue(getValue(lessonData, row, `${day}WikLrnCn`)),
                    lessonNumber: textValue(getValue(lessonData, row, `${day}WikLrnRlvtTmsValue`), 20),
                    totalLessons: textValue(getValue(lessonData, row, `${day}WikLrnAllTmsValue`), 20),
                    textbookPage: textValue(getValue(lessonData, row, `${day}WikLrnPgeValue`), 100),
                    additionalPage: textValue(getValue(lessonData, row, `${day}WikLrnAtaPgeValue`), 100),
                };
                if (record.subject || record.unit || record.content || record.lessonNumber || record.textbookPage || record.additionalPage) {
                    records.push(record);
                }
            }
        }

        const unique = new Map();
        for (const record of records) unique.set(`${record.date}|${record.period}|${record.subject}`, record);
        return {
            ready: true,
            payload: {
                source: "NEIS 주간학습안내 자동 동기화",
                range_start: range.start,
                range_end: range.end,
                complete_weeks: [{ start: range.start, end: range.end }],
                records: [...unique.values()],
            },
        };
    }

    function readCurrentWeek() {
        const app = getApp();
        if (!app) return { ready: false };
        const lessonData = app.lookup("dsWikLrn");
        if (!lessonData?.getRowCount) return { ready: false };
        if (isLessonDataModified(lessonData)) {
            return { ready: false, blocked: true, reason: "수업내용에 저장되지 않은 변경이 있어 자동 동기화를 건너뛰었습니다." };
        }
        const dates = [];
        for (let row = 0; row < lessonData.getRowCount(); row += 1) {
            for (const day of DAYS) {
                const date = dateValue(getValue(lessonData, row, `${day}AllTiYmd`));
                if (date) dates.push(date);
            }
        }
        const range = currentRange(app, readWeekRows(app.lookup("dsWeekList")), dates);
        if (!range || dates.some((date) => date < range.start || date > range.end)) return { ready: false };
        return readPayload(app, range);
    }

    function attemptCapture(generation, attempt = 0) {
        if (generation !== captureGeneration || attempt > 40) return;
        const result = readCurrentWeek();
        if (result.blocked) {
            const signature = `${result.reason}|${location.pathname}`;
            if (signature !== lastBlockedSignature) post("blocked", { message: result.reason });
            lastBlockedSignature = signature;
            return;
        }
        if (!result.ready) {
            setTimeout(() => attemptCapture(generation, attempt + 1), 350);
            return;
        }
        const signature = JSON.stringify(result.payload);
        lastSignature = signature;
        lastPayload = result.payload;
        lastBlockedSignature = "";
        // Every completed user query refreshes this week's cache timestamp, even if the data is unchanged.
        post("lessons", result.payload);
        if (!autoSyncRunning) void autoFillListedWeeks(result.payload);
    }

    function noteSuccessfulQuery() {
        captureGeneration += 1;
        const generation = captureGeneration;
        post("progress", { message: "NEIS 조회를 감지했습니다. 주별 자료를 확인 중입니다." });
        setTimeout(() => attemptCapture(generation), 600);
    }

    function entryKey(entry) {
        return `${entry.name}|${entry.startTime}`;
    }

    function isLessonQuery(entry) {
        try {
            return new URL(entry.name, location.href).pathname.endsWith("/els_edc_tm06_003.do") && entry.responseEnd > 0;
        } catch (_) { return false; }
    }

    function askWhichWeeksAreFresh(weeks) {
        const requestId = `w${Date.now()}-${++cacheRequestId}`;
        return new Promise((resolve) => {
            const timer = setTimeout(() => {
                cacheWaiters.delete(requestId);
                resolve({ ok: false, fresh: {} });
            }, CACHE_WAIT_MS);
            cacheWaiters.set(requestId, (result) => {
                clearTimeout(timer);
                cacheWaiters.delete(requestId);
                resolve(result);
            });
            post("week-cache-check", { requestId, weeks });
        });
    }

    window.addEventListener("message", (event) => {
        const message = event.data;
        if (event.source !== window || message?.source !== SOURCE) return;
        if (message.type === "week-cache-result") {
            cacheWaiters.get(message.payload?.requestId)?.(message.payload);
            return;
        }
        if (message.type === "reader-ready" && lastPayload) post("lessons", lastPayload);
    });

    function sameWeekInSearch(search, week) {
        try {
            return dateValue(search.getValue("weekBgngYmd")) === week.begin
                && dateValue(search.getValue("weekEndYmd")) === week.end;
        } catch (_) { return false; }
    }

    function rememberInternalRequests(fromTime, toTime) {
        for (const entry of performance.getEntriesByType("resource")) {
            if (isLessonQuery(entry) && entry.startTime >= fromTime - 5 && entry.startTime <= toTime + 5) {
                internalEntryKeys.add(entryKey(entry));
            }
        }
        if (internalEntryKeys.size > 500) {
            const keep = [...internalEntryKeys].slice(-250);
            internalEntryKeys.clear();
            keep.forEach((key) => internalEntryKeys.add(key));
        }
    }

    async function submitWeek(app, week, search, weekControl, submission, expectedWeek) {
        const lessonData = app.lookup("dsWikLrn");
        if (isLessonDataModified(lessonData)) throw new Error("수업내용에 저장되지 않은 변경이 생겨 주차 동기화를 멈췄습니다.");
        if (expectedWeek && !sameWeekInSearch(search, expectedWeek)) {
            throw new Error("NEIS 화면에서 주차 선택이 바뀌어 자동 동기화를 멈췄습니다.");
        }
        const started = performance.now();
        weekControl.selectItem(week.index, true);
        search.setValue("weekCnt", week.rawWeek);
        search.setValue("weekBgngYmd", week.rawBegin);
        search.setValue("weekEndYmd", week.rawEnd);
        try {
            await submission.send();
            await new Promise((resolve) => setTimeout(resolve, 140));
        } finally {
            rememberInternalRequests(started, performance.now());
        }
        if (!sameWeekInSearch(search, week)) throw new Error("조회 중 선택한 주차가 달라져 자동 동기화를 멈췄습니다.");
        if (isLessonDataModified(lessonData)) throw new Error("조회 중 수업내용 수정 상태가 감지되어 자동 동기화를 멈췄습니다.");
    }

    async function autoFillListedWeeks(currentPayload) {
        if (autoSyncRunning) return;
        const app = getApp();
        if (!app) return;
        const weekRows = readWeekRows(app.lookup("dsWeekList"));
        if (!weekRows.length) return;
        const currentWeek = weekRows.find((week) => week.begin === currentPayload.range_start && week.end === currentPayload.range_end);
        if (!currentWeek) return;
        if (weekRows.length > MAX_AUTO_WEEKS) {
            post("progress", { message: `주차가 ${MAX_AUTO_WEEKS}개를 넘어 자동 동기화를 건너뛰었습니다. 팝업에서 필요한 달을 가져와 주세요.` });
            return;
        }

        autoSyncRunning = true;
        const weeksToCheck = weekRows.filter((week) => week.begin !== currentWeek.begin || week.end !== currentWeek.end);
        const cache = await askWhichWeeksAreFresh(weeksToCheck.map(({ begin, end }) => ({ start: begin, end })));
        const staleWeeks = weeksToCheck.filter((week) => !cache.ok || cache.fresh?.[`${week.begin}|${week.end}`] !== true);
        if (!staleWeeks.length) {
            post("progress", { message: `NEIS 등록 ${weekRows.length}주 자료가 최신 상태입니다.` });
            autoSyncRunning = false;
            return;
        }

        const search = app.lookup("dmSearch");
        const weekControl = app.lookup("cmbWeek");
        const submission = app.lookup("subSelectWikInfo");
        const lessonData = app.lookup("dsWikLrn");
        if (!search?.setValue || !search?.getValue || !weekControl?.selectItem || typeof submission?.send !== "function") {
            post("progress", { message: "현재 주는 저장했지만 자동 주차 조회 기능을 찾지 못했습니다." });
            autoSyncRunning = false;
            return;
        }
        if (isLessonDataModified(lessonData)) {
            post("blocked", { message: "미저장 수업내용 변경이 있어 나머지 주차 자동 조회를 건너뛰었습니다." });
            autoSyncRunning = false;
            return;
        }

        let originalWeek = currentWeek;
        try {
            const originalBegin = dateValue(search.getValue("weekBgngYmd"));
            const originalEnd = dateValue(search.getValue("weekEndYmd"));
            originalWeek = weekRows.find((week) => week.begin === originalBegin && week.end === originalEnd) || currentWeek;
        } catch (_) { }

        const previousInternalFlag = window.__teacherlessonFromNeisInternalQuery;
        window.__teacherlessonFromNeisInternalQuery = true;
        let expectedWeek = originalWeek;
        let shouldRestore = true;
        let restored = false;
        let completed = 0;
        post("progress", { message: `NEIS 등록 주차 확인 중 · 0/${staleWeeks.length}` });
        try {
            for (const week of staleWeeks) {
                const previousExpectedWeek = expectedWeek;
                expectedWeek = week;
                await submitWeek(app, week, search, weekControl, submission, previousExpectedWeek);
                completed += 1;
                const result = readPayload(app, { start: week.begin, end: week.end });
                if (!result.ready) {
                    if (result.blocked) throw new Error(result.reason);
                    throw new Error(`${week.begin} 주차 수업 데이터를 읽지 못했습니다.`);
                }
                post("lessons", result.payload);
                post("progress", { message: `NEIS 등록 주차 가져오는 중 · ${completed}/${staleWeeks.length}` });
            }
        } catch (error) {
            shouldRestore = sameWeekInSearch(search, expectedWeek) && !isLessonDataModified(lessonData);
            post("progress", { message: error.message || "일부 주차를 가져오지 못했습니다." });
        } finally {
            if (shouldRestore && sameWeekInSearch(search, expectedWeek) && !isLessonDataModified(lessonData)) {
                try {
                    await submitWeek(app, originalWeek, search, weekControl, submission, expectedWeek);
                    restored = true;
                    const currentResult = readPayload(app, { start: originalWeek.begin, end: originalWeek.end });
                    if (currentResult.ready) post("lessons", currentResult.payload);
                } catch (error) {
                    post("progress", { message: `주차 자료는 가져왔지만 원래 주차 복원에 실패했습니다: ${error.message || "조회 오류"}` });
                }
            }
            rememberInternalRequests(0, performance.now());
            window.__teacherlessonFromNeisInternalQuery = previousInternalFlag;
            autoSyncRunning = false;
        }
        if (completed === staleWeeks.length && restored) {
            post("progress", { message: `NEIS 등록 ${weekRows.length}주 수업자료 자동 동기화 완료` });
        } else if (completed < staleWeeks.length) {
            post("progress", { message: `${completed}/${staleWeeks.length}주를 가져왔습니다. 다시 조회하면 이어서 동기화합니다.` });
        }
    }

    try {
        const observer = new PerformanceObserver((list) => {
            const entries = list.getEntries().filter(isLessonQuery);
            if (!entries.length) return;
            if (autoSyncRunning || window.__teacherlessonFromNeisInternalQuery) {
                entries.forEach((entry) => internalEntryKeys.add(entryKey(entry)));
                return;
            }
            const externalEntries = entries.filter((entry) => !internalEntryKeys.has(entryKey(entry)));
            if (externalEntries.length) noteSuccessfulQuery();
        });
        observer.observe({ type: "resource", buffered: true });
    } catch (_) { }

    const priorQuery = performance.getEntriesByType("resource").some(isLessonQuery);
    if (priorQuery) noteSuccessfulQuery();
})();
