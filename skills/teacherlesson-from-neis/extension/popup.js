const APP_ID = "edu/sw/els/edc/tm/els_edctm06_m00";
const monthInput = document.querySelector("#monthInput");
const weekButton = document.querySelector("#weekButton");
const monthButton = document.querySelector("#monthButton");
const statusNode = document.querySelector("#status");

function localMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function setStatus(message, isError = false) {
    statusNode.textContent = message;
    statusNode.style.color = isError ? "#a33333" : "#718399";
}

async function collectOnNeisPage({ mode, month }) {
    const weekdayPrefix = ["mon", "tue", "wed", "thu", "fri"];
    function isoFromNeis(value) {
        const digits = String(value ?? "").replace(/\D/g, "");
        if (digits.length !== 8) return "";
        return `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6, 8)}`;
    }
    const platform = window.cpr?.core?.Platform?.INSTANCE;
    if (!platform) return { ok: false, error: "NEIS 학습 화면을 찾지 못했습니다. NEIS 업무 화면을 열어 주세요." };
    const app = platform.getAllRunningAppInstances().find((instance) => instance?.app?.id === "edu/sw/els/edc/tm/els_edctm06_m00");
    if (!app) return { ok: false, error: "주간학습안내작성 화면이 아닙니다. 해당 화면을 연 뒤 다시 시도해 주세요." };

    const lessonData = app.lookup("dsWikLrn");
    const weekData = app.lookup("dsWeekList");
    if (!lessonData?.getRowCount) return { ok: false, error: "주간학습 데이터를 찾지 못했습니다. NEIS 화면에서 먼저 조회해 주세요." };

    try {
        if (typeof lessonData.isModified === "function" && lessonData.isModified()) {
            return { ok: false, error: "수업내용에 저장되지 않은 변경이 있어 가져오기를 중단했습니다. 수업내용을 저장하거나 되돌린 뒤 다시 시도해 주세요." };
        }
    } catch (_) {
        return { ok: false, error: "수업내용 수정 상태를 확인하지 못해 안전을 위해 중단했습니다." };
    }

    function getValue(dataset, row, column) {
        try { return dataset.getValue(row, column) ?? ""; } catch (_) { return ""; }
    }

    function readLessons(startDate, endDate) {
        const output = [];
        const columns = [
            ["subject", "EtbSbjtNm"], ["unit", "WikLrnUitNm"], ["content", "WikLrnCn"],
            ["lessonNumber", "WikLrnRlvtTmsValue"], ["totalLessons", "WikLrnAllTmsValue"],
            ["textbookPage", "WikLrnPgeValue"], ["additionalPage", "WikLrnAtaPgeValue"],
        ];
        for (let row = 0; row < lessonData.getRowCount(); row += 1) {
            const period = String(getValue(lessonData, row, "pirNm") || getValue(lessonData, row, "pir") || "").trim().replace(/교시/g, "").replace(/\s/g, "");
            if (!/^\d{1,2}$/.test(period)) continue;
            for (const day of ["mon", "tue", "wed", "thu", "fri"]) {
                const date = isoFromNeis(getValue(lessonData, row, `${day}AllTiYmd`));
                if (!date || date < startDate || date > endDate) continue;
                const record = { date, period };
                for (const [key, suffix] of columns) record[key] = String(getValue(lessonData, row, `${day}${suffix}`) ?? "").trim();
                if (![record.subject, record.unit, record.content, record.textbookPage, record.additionalPage, record.lessonNumber].some(Boolean)) continue;
                output.push(record);
            }
        }
        return output;
    }

    function readRows(dataset) {
        const rows = [];
        for (let row = 0; row < (dataset?.getRowCount?.() || 0); row += 1) {
            rows.push({
                index: row,
                begin: isoFromNeis(getValue(dataset, row, "weekBgngYmd")),
                end: isoFromNeis(getValue(dataset, row, "weekEndYmd")),
                week: String(getValue(dataset, row, "weekCnt") ?? ""),
                rawBegin: getValue(dataset, row, "weekBgngYmd"),
                rawEnd: getValue(dataset, row, "weekEndYmd"),
                rawWeek: getValue(dataset, row, "weekCnt"),
            });
        }
        return rows;
    }

    if (mode === "week") {
        const rows = readRows(weekData);
        const search = app.lookup("dmSearch");
        let selected = null;
        if (search?.getValue) {
            const currentBegin = isoFromNeis(search.getValue("weekBgngYmd"));
            const currentEnd = isoFromNeis(search.getValue("weekEndYmd"));
            selected = rows.find((row) => row.begin === currentBegin && row.end === currentEnd) || null;
        }
        const visibleDates = [];
        for (let row = 0; row < lessonData.getRowCount(); row += 1) {
            for (const day of weekdayPrefix) {
                const value = isoFromNeis(getValue(lessonData, row, `${day}AllTiYmd`));
                if (value) visibleDates.push(value);
            }
        }
        if (!selected && visibleDates.length) {
            selected = rows.find((row) => visibleDates.some((value) => row.begin <= value && value <= row.end)) || null;
        }
        const lessonRows = readLessons(selected?.begin || "0000-00-00", selected?.end || "9999-99-99");
        if (!selected && !lessonRows.length) return { ok: false, error: "현재 주차 정보를 찾지 못했습니다. NEIS에서 주차를 선택하고 조회해 주세요." };
        if (!lessonRows.length) return { ok: false, error: "현재 주차의 수업내용이 비어 있습니다." };
        const rangeStart = selected?.begin || lessonRows[0].date;
        const rangeEnd = selected?.end || lessonRows.at(-1).date;
        return {
            ok: true,
            range_start: rangeStart,
            range_end: rangeEnd,
            complete_weeks: [{ start: rangeStart, end: rangeEnd }],
            records: lessonRows,
        };
    }

    if (!weekData?.getRowCount) return { ok: false, error: "월간 주차 목록을 찾지 못했습니다." };
    const monthMatch = /^(\d{4})-(\d{2})$/.exec(month || "");
    if (!monthMatch) return { ok: false, error: "가져올 달을 선택해 주세요." };
    const year = Number(monthMatch[1]);
    const monthNumber = Number(monthMatch[2]);
    const startDate = `${monthMatch[1]}-${monthMatch[2]}-01`;
    const lastDay = new Date(year, monthNumber, 0).getDate();
    const endDate = `${monthMatch[1]}-${monthMatch[2]}-${String(lastDay).padStart(2, "0")}`;
    const weeks = readRows(weekData).filter((row) => row.begin && row.end && row.begin <= endDate && row.end >= startDate);
    if (!weeks.length) return { ok: false, error: "선택한 달과 겹치는 주차가 NEIS에 없습니다." };
    if (weeks.length > 8) return { ok: false, error: "주차 수가 예상 범위를 넘어 안전을 위해 중단했습니다." };

    const search = app.lookup("dmSearch");
    const weekControl = app.lookup("cmbWeek");
    const submission = app.lookup("subSelectWikInfo");
    const allWeeks = readRows(weekData);
    if (!search?.setValue || !weekControl?.selectItem || typeof submission?.send !== "function") {
        return { ok: false, error: "NEIS 주간 조회 제출을 찾지 못했습니다. 주간학습안내작성 화면을 다시 열어 주세요." };
    }
    let originalBegin = "";
    let originalEnd = "";
    let originalWeekValue = "";
    try {
        originalBegin = isoFromNeis(search.getValue("weekBgngYmd"));
        originalEnd = isoFromNeis(search.getValue("weekEndYmd"));
        originalWeekValue = String(search.getValue("weekCnt") ?? "");
    } catch (_) { }
    const originalWeek = allWeeks.find((row) => row.begin === originalBegin && row.end === originalEnd)
        || allWeeks.find((row) => row.week === originalWeekValue);
    if (!originalWeek) return { ok: false, error: "현재 표시 중인 주차를 보존할 수 없어 월간 조회를 시작하지 않았습니다." };

    async function queryWeek(week) {
        if (typeof lessonData.isModified === "function" && lessonData.isModified()) {
            throw new Error("수업내용에 저장되지 않은 변경이 생겨 조회를 멈췄습니다.");
        }
        weekControl.selectItem(week.index, true);
        search.setValue("weekCnt", week.rawWeek);
        search.setValue("weekBgngYmd", week.rawBegin);
        search.setValue("weekEndYmd", week.rawEnd);
        await submission.send();
        await new Promise((resolve) => setTimeout(resolve, 120));
    }

    const records = [];
    let failure = null;
    const previousInternalQuery = window.__teacherlessonFromNeisInternalQuery;
    window.__teacherlessonFromNeisInternalQuery = true;
    try {
        for (const week of weeks) {
            await queryWeek(week);
            records.push(...readLessons(startDate, endDate));
        }
    } catch (error) {
        failure = error.message || "월간 수업을 조회하지 못했습니다.";
    } finally {
        try {
            await queryWeek(originalWeek);
        } catch (_) {
            failure = failure || "가져오기는 끝났지만 NEIS 화면의 원래 주차를 복원하지 못했습니다.";
        } finally {
            window.__teacherlessonFromNeisInternalQuery = previousInternalQuery;
        }
    }
    if (failure) return { ok: false, error: failure };
    const unique = new Map();
    records.forEach((record) => unique.set(`${record.date}|${record.period}|${record.subject}`, record));
    return {
        ok: true,
        range_start: startDate,
        range_end: endDate,
        complete_month: month,
        complete_weeks: weeks.map((week) => ({ start: week.begin, end: week.end })),
        records: [...unique.values()],
    };
}

async function importFromNeis(mode) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id || !/^https:\/\/.+\.neis\.go\.kr\//.test(tab.url || "")) {
        throw new Error("NEIS 탭을 활성화한 뒤 확장 프로그램을 열어 주세요.");
    }
    const args = mode === "week" ? { mode } : { mode, month: monthInput.value };
    const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        world: "MAIN",
        func: collectOnNeisPage,
        args: [args],
    });
    if (!result?.ok) throw new Error(result?.error || "NEIS 화면에서 수업내용을 읽지 못했습니다.");
    const response = await chrome.runtime.sendMessage({
        type: "MANUAL_IMPORT_LESSONS",
        payload: {
            source: mode === "week" ? "NEIS 주간학습안내" : "NEIS 월간 주간학습안내",
            range_start: result.range_start,
            range_end: result.range_end,
            complete_month: result.complete_month || "",
            complete_weeks: result.complete_weeks || [],
            records: result.records,
        },
    });
    if (!response?.ok) throw new Error(response?.error || "수업내용을 저장하지 못했습니다.");
    return response;
}

async function runImport(mode) {
    weekButton.disabled = true;
    monthButton.disabled = true;
    setStatus(mode === "week" ? "현재 주 수업을 읽는 중입니다…" : "NEIS에서 월별 주차를 순서대로 조회하고 있습니다…");
    try {
        const result = await importFromNeis(mode);
        setStatus(result.viewer_updated
            ? `${result.range_start} ~ ${result.range_end} · ${result.imported}개 수업을 자동 동기화했습니다.`
            : `${result.range_start} ~ ${result.range_end} · 브라우저에 저장했습니다. 뷰어: ${result.viewer_error || "연결되지 않음"}`);
    } catch (error) {
        setStatus(error.message || "수업을 가져오지 못했습니다.", true);
    } finally {
        weekButton.disabled = false;
        monthButton.disabled = false;
    }
}

monthInput.value = localMonth();
weekButton.addEventListener("click", () => runImport("week"));
monthButton.addEventListener("click", () => runImport("month"));
