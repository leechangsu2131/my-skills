const APP_ID = "edu/sw/els/edc/tm/els_edctm06_m00";
const monthInput = document.querySelector("#monthInput");
const weekButton = document.querySelector("#weekButton");
const monthButton = document.querySelector("#monthButton");
const studentButton = document.querySelector("#studentButton");
const statusNode = document.querySelector("#status");
const viewerButton = document.querySelector("#viewerButton");

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

async function collectStudentStatusOnNeis({ today, monthStart, monthEnd }) {
    const platform = window.cpr?.core?.Platform?.INSTANCE;
    if (!platform) return { ok: false, error: "NEIS 업무 화면이 열려 있지 않습니다." };

    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const text = (value, limit = 50) => String(value ?? "").trim().slice(0, limit);
    const date = (value) => {
        const digits = String(value ?? "").replace(/\D/g, "").slice(0, 8);
        return digits.length === 8 ? `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6, 8)}` : "";
    };
    const numeric = (value) => {
        const number = Number(String(value ?? "").replace(/,/g, "").trim());
        return Number.isFinite(number) ? number : 0;
    };
    const valueAt = (dataset, row, column) => {
        try { return dataset.getValue(row, column) ?? ""; } catch (_) { return ""; }
    };
    function hasCompletedRequest(endpoint, since) {
        return performance.getEntriesByType("resource").some((entry) => {
            if (entry.startTime < since || entry.responseEnd <= 0) return false;
            try { return new URL(entry.name, location.href).pathname.endsWith(endpoint); } catch (_) { return false; }
        });
    }
    async function waitForRequest(endpoint, since) {
        for (let attempt = 0; attempt < 40; attempt += 1) {
            if (hasCompletedRequest(endpoint, since)) return true;
            await sleep(150);
        }
        return false;
    }
    const appFor = (appId) => platform.getAllRunningAppInstances().find((instance) => instance?.app?.id === appId) || null;
    async function openApp(menuId, appId) {
        if (typeof window.openMdiMenu === "function") window.openMdiMenu(menuId);
        else {
            const index = appFor("app/com/main/Index");
            if (typeof index?.callAppMethod === "function") index.callAppMethod("doOpenMenuToMdi", [menuId]);
        }
        for (let attempt = 0; attempt < 36; attempt += 1) {
            const instance = appFor(appId);
            if (instance) return instance;
            await sleep(250);
        }
        throw new Error("NEIS 조회 화면을 열지 못했습니다.");
    }
    function setControlValue(instance, controlId, value) {
        const control = instance.lookup(controlId);
        if (!control) return false;
        control.value = value;
        try { control.dispatchEvent(new cpr.events.CUIEvent("value-change")); } catch (_) { }
        return true;
    }
    async function searchWithButton(instance, endpoint) {
        const button = instance.lookup("btnSearch");
        if (!button?.click) throw new Error("조회 버튼을 찾지 못했습니다.");
        const started = performance.now();
        button.click();
        if (!await waitForRequest(endpoint, started)) throw new Error("NEIS 조회 응답을 확인하지 못했습니다.");
    }
    function classLabel(dataset, row) {
        const namedClass = text(valueAt(dataset, row, "clsNm"), 24);
        if (namedClass) return namedClass;
        const grade = text(valueAt(dataset, row, "grd"), 8);
        const classNo = text(valueAt(dataset, row, "clsNo"), 8);
        return [grade, classNo && `${classNo}반`].filter(Boolean).join(" ");
    }
    function readApplications(instance, datasetId, type) {
        const dataset = instance.lookup(datasetId);
        if (!dataset?.getRowCount) throw new Error(`${type} 신청자료를 찾지 못했습니다.`);
        const rows = [];
        for (let row = 0; row < dataset.getRowCount() && rows.length < 500; row += 1) {
            const startDate = date(valueAt(dataset, row, type === "결석" ? "abeBgngDt" : "experLrnBgngDt"));
            const endDate = date(valueAt(dataset, row, type === "결석" ? "abeEndDt" : "experLrnEndDt")) || startDate;
            const student = text(valueAt(dataset, row, "stuFlnm"));
            if (!startDate || !endDate || startDate > endDate || !student) continue;
            rows.push({
                start_date: startDate,
                end_date: endDate,
                student,
                class_name: classLabel(dataset, row),
                kind: text(valueAt(dataset, row, type === "결석" ? "abeDclrScNm" : "experLrnScNm"), 40) || `${type} 신청`,
                status: text(valueAt(dataset, row, "eduActPrcsStsNm"), 30),
                approval_status: text(valueAt(dataset, row, "atrzStsNm"), 30),
            });
        }
        return rows;
    }

    const payload = { as_of: today, attendance: [], absence_applications: [], experiential_applications: [] };
    const errors = [];

    try {
        const attendanceApp = await openApp("AMELS40197", "edu/sw/els/srg/aa/els_srgaa02_m06");
        if (!setControlValue(attendanceApp, "dtiBgngDd", today.replace(/-/g, ""))
            || !setControlValue(attendanceApp, "dtiEndDd", today.replace(/-/g, ""))) {
            throw new Error("출결 조회 날짜를 설정하지 못했습니다.");
        }
        const query = attendanceApp.lookup("subListAbeYmdAbeStu");
        if (typeof query?.send !== "function") throw new Error("일일 출결 조회를 찾지 못했습니다.");
        const attendanceQueryStarted = performance.now();
        await query.send();
        if (!await waitForRequest("/els_srg_aa02_010.do", attendanceQueryStarted)) throw new Error("일일 출결 조회 응답을 확인하지 못했습니다.");
        const dataset = attendanceApp.lookup("dsListAbeYmdAbeStu");
        if (!dataset?.getRowCount) throw new Error("일일 출결 결과를 찾지 못했습니다.");
        const categories = [
            ["gyulsukIllIlsu", "질병 결석"], ["gyulsukSagoIlsu", "사고 결석"], ["gyulsukEtcIlsu", "기타 결석"], ["chulsukInjungIlsu", "출석인정"],
            ["lateIllIlsu", "질병 지각"], ["lateSagoIlsu", "사고 지각"], ["lateEtcIlsu", "기타 지각"], ["lateInjungIlsu", "출석인정 지각"],
            ["chotoeIllIlsu", "질병 조퇴"], ["chotoeSagoIlsu", "사고 조퇴"], ["chotoeEtcIlsu", "기타 조퇴"], ["chotoeInjungIlsu", "출석인정 조퇴"],
            ["gyulgwaIllIlsu", "질병 결과"], ["gyulgwaSagoIlsu", "사고 결과"], ["gyulgwaEtcIlsu", "기타 결과"], ["gyulgwaInjungIlsu", "출석인정 결과"],
        ];
        for (let row = 0; row < dataset.getRowCount() && payload.attendance.length < 1000; row += 1) {
            const student = text(valueAt(dataset, row, "stuFlnm"));
            if (!student) continue;
            let hasDetailedAbsence = false;
            for (const [column, kind] of categories) {
                const count = numeric(valueAt(dataset, row, column));
                if (count <= 0) continue;
                hasDetailedAbsence ||= column.startsWith("gyulsuk");
                payload.attendance.push({ date: today, end_date: today, student, class_name: classLabel(dataset, row), kind, count });
            }
            const totalAbsent = numeric(valueAt(dataset, row, "absentDays"));
            if (totalAbsent > 0 && !hasDetailedAbsence) {
                payload.attendance.push({ date: today, end_date: today, student, class_name: classLabel(dataset, row), kind: "결석", count: totalAbsent });
            }
        }
    } catch (error) { errors.push(`일일 출결: ${error.message || "조회 실패"}`); }

    try {
        const absenceApp = await openApp("AMEDS40531", "edu/sa/eds/eaa/ae/eds_eaaae03_m01");
        if (!setControlValue(absenceApp, "dtAbeBgngYmd", monthStart.replace(/-/g, ""))
            || !setControlValue(absenceApp, "dtAbeEndYmd", monthEnd.replace(/-/g, ""))) {
            throw new Error("결석신고서 조회 기간을 설정하지 못했습니다.");
        }
        await searchWithButton(absenceApp, "/eds_eaa_ae03_002.do");
        payload.absence_applications = readApplications(absenceApp, "dsStdntListForAbe", "결석");
    } catch (error) { errors.push(`결석 신청: ${error.message || "조회 실패"}`); }

    try {
        const fieldTripApp = await openApp("AMEDS40501", "edu/sa/eds/eaa/ae/eds_eaaae01_m01");
        await searchWithButton(fieldTripApp, "/eds_eaa_ae01_002.do");
        payload.experiential_applications = readApplications(fieldTripApp, "dsStdntListForAply", "체험학습");
    } catch (error) { errors.push(`체험학습 신청: ${error.message || "조회 실패"}`); }

    if (errors.length) return { ok: false, error: `일부 조회가 실패해 이번 결과는 저장하지 않았습니다. ${errors.join(" · ")}` };
    return { ok: true, payload };
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
        setStatus(`${result.range_start} ~ ${result.range_end} · ${result.imported}개 수업을 Chrome에 저장했습니다.`);
    } catch (error) {
        setStatus(error.message || "수업을 가져오지 못했습니다.", true);
    } finally {
        weekButton.disabled = false;
        monthButton.disabled = false;
    }
}

async function runStudentImport() {
    studentButton.disabled = true;
    setStatus("NEIS에서 오늘 출결과 신청 현황을 조회하고 있습니다…");
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab?.id || !/^https:\/\/.+\.neis\.go\.kr\//.test(tab.url || "")) {
            throw new Error("NEIS 탭을 활성화한 뒤 확장 프로그램을 열어 주세요.");
        }
        const now = new Date();
        const toIso = (value) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
        const today = toIso(now);
        const monthStart = toIso(new Date(now.getFullYear(), now.getMonth(), 1));
        const monthEnd = toIso(new Date(now.getFullYear(), now.getMonth() + 1, 0));
        const [{ result }] = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            world: "MAIN",
            func: collectStudentStatusOnNeis,
            args: [{ today, monthStart, monthEnd }],
        });
        if (!result?.ok) throw new Error(result?.error || "NEIS 학생 현황을 읽지 못했습니다.");
        const stored = await chrome.runtime.sendMessage({ type: "STORE_STUDENT_STATUS", payload: result.payload });
        if (!stored?.ok) throw new Error(stored?.error || "학생 현황을 Chrome에 저장하지 못했습니다.");
        setStatus(`${today} · 출결 ${stored.attendance}건, 결석신고 ${stored.absence_applications}건, 체험학습 ${stored.experiential_applications}건을 Chrome에 저장했습니다.`);
    } catch (error) {
        setStatus(error.message || "학생 현황을 가져오지 못했습니다.", true);
    } finally {
        studentButton.disabled = false;
    }
}

monthInput.value = localMonth();
weekButton.addEventListener("click", () => runImport("week"));
monthButton.addEventListener("click", () => runImport("month"));
studentButton.addEventListener("click", runStudentImport);
viewerButton.addEventListener("click", () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("viewer.html") });
});
