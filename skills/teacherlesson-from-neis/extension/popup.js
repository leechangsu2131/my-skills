const APP_ID = "edu/sw/els/edc/tm/els_edctm06_m00";
const LAST_ABSENCE_ACTION_KEY = "teacherlessonNeisLastAbsenceAction";
const APPROVAL_PROFILES_KEY = "teacherlessonNeisApprovalProfiles";
const ABSENCE_CATEGORY_OPTIONS = [
    { code: "01", name: "질병결석" },
    { code: "02", name: "인정결석" },
    { code: "03", name: "미인정결석" },
    { code: "04", name: "기타결석" },
];
const monthInput = document.querySelector("#monthInput");
const weekButton = document.querySelector("#weekButton");
const monthButton = document.querySelector("#monthButton");
const studentButton = document.querySelector("#studentButton");
const reviewAbsenceButton = document.querySelector("#reviewAbsenceButton");
const actionPanel = document.querySelector("#actionPanel");
const actionStatus = document.querySelector("#actionStatus");
const actionCandidatesNode = document.querySelector("#actionCandidates");
const actionPreview = document.querySelector("#actionPreview");
const actionPreviewText = document.querySelector("#actionPreviewText");
const actionSelectionSummary = document.querySelector("#actionSelectionSummary");
const selectAllAbsenceButton = document.querySelector("#selectAllAbsenceButton");
const clearAbsenceSelectionButton = document.querySelector("#clearAbsenceSelectionButton");
const approvalSettings = document.querySelector("#approvalSettings");
const approvalProfilesNode = document.querySelector("#approvalProfiles");
const addApprovalProfileButton = document.querySelector("#addApprovalProfileButton");
const actionExecuteButton = document.querySelector("#actionExecuteButton");
const statusNode = document.querySelector("#status");
const viewerButton = document.querySelector("#viewerButton");
let absenceWorkCandidates = [];
let selectedWorkApplicationIds = new Set();
let approvalProfiles = {};
let approvalProfilesReady = Promise.resolve();
let absenceUiExecutionInFlight = false;

function normalizeProfileKind(value) {
    return String(value || "").trim().replace(/\s+/g, " ").slice(0, 40);
}

function normalizeApproverNames(value) {
    return [...new Set(String(value || "").split(/\r?\n/).map((name) => name.trim().slice(0, 40)).filter(Boolean))];
}

function sanitizeApprovalProfiles(value) {
    const profiles = {};
    if (!value || typeof value !== "object" || Array.isArray(value)) return profiles;
    for (const [rawKind, rawNames] of Object.entries(value)) {
        const kind = normalizeProfileKind(rawKind);
        const names = normalizeApproverNames(Array.isArray(rawNames) ? rawNames.join("\n") : "");
        if (kind && names.length) profiles[kind] = names;
    }
    return profiles;
}

function createApprovalProfileRow(kind = "", names = [], saved = false) {
    const row = document.createElement("div");
    row.className = "approval-profile";
    row.dataset.originalKind = saved ? kind : "";

    const kindLabel = document.createElement("label");
    kindLabel.textContent = "NEIS 신청 유형";
    const kindInput = document.createElement("input");
    kindInput.type = "text";
    kindInput.maxLength = 40;
    kindInput.value = kind;
    kindInput.placeholder = "예: 결석신고서에 표시되는 신청 유형";
    kindLabel.append(kindInput);

    const namesLabel = document.createElement("label");
    namesLabel.textContent = "결재자 이름 · 순서대로 한 줄에 한 명씩";
    const namesInput = document.createElement("textarea");
    namesInput.rows = 2;
    namesInput.value = names.join("\n");
    namesInput.placeholder = "예: 결재자 이름";
    namesLabel.append(namesInput);

    const buttons = document.createElement("div");
    buttons.className = "approval-profile-buttons";
    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.className = "button secondary";
    saveButton.textContent = "결재선 저장";
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "button secondary";
    deleteButton.textContent = "삭제";
    buttons.append(saveButton, deleteButton);

    const status = document.createElement("div");
    status.className = `approval-profile-status${saved ? "" : " missing"}`;
    status.textContent = saved ? "이 신청 유형에 저장된 결재선입니다." : "아직 저장되지 않았습니다. 저장 전에는 이 유형을 상신할 수 없습니다.";
    row.append(kindLabel, namesLabel, buttons, status);

    saveButton.addEventListener("click", async () => {
        const nextKind = normalizeProfileKind(kindInput.value);
        const nextNames = normalizeApproverNames(namesInput.value);
        if (!nextKind || !nextNames.length) {
            status.textContent = "신청 유형과 결재자를 모두 입력해 주세요.";
            status.classList.add("missing");
            return;
        }
        const duplicate = [...approvalProfilesNode.querySelectorAll(".approval-profile")]
            .find((other) => other !== row && normalizeProfileKind(other.querySelector('input[type="text"]')?.value) === nextKind);
        if (duplicate) {
            status.textContent = "같은 신청 유형이 이미 있습니다. 한 유형에는 결재선 하나만 저장할 수 있습니다.";
            status.classList.add("missing");
            return;
        }
        const nextProfiles = { ...approvalProfiles };
        const previousKind = row.dataset.originalKind;
        if (previousKind && previousKind !== nextKind) delete nextProfiles[previousKind];
        nextProfiles[nextKind] = nextNames;
        try {
            await chrome.storage.local.set({ [APPROVAL_PROFILES_KEY]: nextProfiles });
            approvalProfiles = nextProfiles;
            row.dataset.originalKind = nextKind;
            kindInput.value = nextKind;
            namesInput.value = nextNames.join("\n");
            status.textContent = "결재선을 이 PC의 Chrome 로컬 저장소에 저장했습니다.";
            status.classList.remove("missing");
            updateCandidateProfileLabels();
        } catch (_) {
            status.textContent = "결재선을 저장하지 못했습니다.";
            status.classList.add("missing");
        }
    });

    deleteButton.addEventListener("click", async () => {
        const previousKind = row.dataset.originalKind;
        if (previousKind) {
            const nextProfiles = { ...approvalProfiles };
            delete nextProfiles[previousKind];
            try {
                await chrome.storage.local.set({ [APPROVAL_PROFILES_KEY]: nextProfiles });
                approvalProfiles = nextProfiles;
            } catch (_) {
                status.textContent = "저장된 결재선을 삭제하지 못했습니다.";
                status.classList.add("missing");
                return;
            }
        }
        row.remove();
        updateCandidateProfileLabels();
    });
    return row;
}

function renderApprovalProfiles(candidateKinds = []) {
    const kinds = [...new Set([
        ...Object.keys(approvalProfiles),
        ...candidateKinds.map(normalizeProfileKind).filter(Boolean),
    ])];
    approvalProfilesNode.replaceChildren();
    if (!kinds.length) {
        const empty = document.createElement("div");
        empty.className = "approval-profile-status";
        empty.textContent = "저장된 결재선이 없습니다. 신청 유형을 추가해 결재자를 저장하세요.";
        approvalProfilesNode.append(empty);
    }
    for (const kind of kinds) {
        const names = approvalProfiles[kind] || [];
        approvalProfilesNode.append(createApprovalProfileRow(kind, names, names.length > 0));
    }
}

async function loadApprovalProfiles() {
    try {
        const stored = await chrome.storage.local.get(APPROVAL_PROFILES_KEY);
        approvalProfiles = sanitizeApprovalProfiles(stored[APPROVAL_PROFILES_KEY]);
    } catch (_) {
        approvalProfiles = {};
    }
    renderApprovalProfiles();
}

function updateCandidateProfileLabels() {
    actionCandidatesNode.querySelectorAll(".action-candidate").forEach((label) => {
        const candidate = absenceWorkCandidates.find((item) => item.application_id === label.dataset.applicationId);
        const profileLabel = label.querySelector(".profile-status");
        if (!candidate || !profileLabel) return;
        const configured = (approvalProfiles[normalizeProfileKind(candidate.kind)] || []).length > 0;
        profileLabel.textContent = configured ? "신청 유형 결재선 저장됨" : "신청 유형 결재선 미등록";
        profileLabel.classList.toggle("missing", !configured);
    });
}

function buildApprovalBatches(selected) {
    const byKind = new Map();
    for (const item of selected) {
        const kind = "결석신고";
        if (!byKind.has(kind)) byKind.set(kind, { kind, applicationIds: [], approvers: approvalProfiles[kind] || [], absenceCategoryCodes: {}, teacherReasons: {} });
        const batch = byKind.get(kind);
        batch.applicationIds.push(item.application_id);
        batch.absenceCategoryCodes[item.application_id] = item.selected_absence_category_code || item.absence_category_code || "01";
        batch.teacherReasons[item.application_id] = item.selected_teacher_reason ?? item.teacher_reason ?? "";
    }
    return [...byKind.values()];
}

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
    async function waitForApp(appId, timeoutMs) {
        const until = Date.now() + timeoutMs;
        while (Date.now() < until) {
            const instance = appFor(appId);
            if (instance) return instance;
            await sleep(250);
        }
        return null;
    }
    function visibleMenuLabels(label) {
        const candidates = [...document.querySelectorAll("span, div, a, td")].filter((element) => {
            const value = String(element.innerText || element.textContent || "").trim();
            if (value !== label) return false;
            const rect = element.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        });
        return candidates;
    }
    function clickMenuLabel(label) {
        const candidates = visibleMenuLabels(label);
        const target = candidates.find((element) => element.children.length <= 1) || candidates[0];
        if (!target) return false;
        target.click();
        return true;
    }
    async function openApp(menuId, appId, menuPath = []) {
        const existing = appFor(appId);
        if (existing) return existing;

        const index = appFor("app/com/main/Index");
        if (typeof index?.callAppMethod === "function") {
            try {
                const result = index.callAppMethod("doOpenMenuToMdi", [menuId]);
                if (result && typeof result.catch === "function") result.catch(() => { });
                const opened = await waitForApp(appId, 10000);
                if (opened) return opened;
            } catch (_) { }
        }

        if (typeof window.openMdiMenu === "function") {
            try {
                window.openMdiMenu(menuId);
                const opened = await waitForApp(appId, 10000);
                if (opened) return opened;
            } catch (_) { }
        }

        for (let index = 0; index < menuPath.length; index += 1) {
            if (appFor(appId)) return appFor(appId);
            const label = menuPath[index];
            const nextLabel = menuPath[index + 1];
            if (nextLabel && visibleMenuLabels(nextLabel).length) continue;
            if (!clickMenuLabel(label)) break;
            await sleep(800);
        }
        const openedFromTree = await waitForApp(appId, menuPath.length ? 8000 : 0);
        if (openedFromTree) return openedFromTree;

        throw new Error(`NEIS 조회 화면을 열지 못했습니다. 메뉴 ${menuId} / 화면 ${appId}`);
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
        for (let row = 0; row < dataset.getRowCount() && rows.length < 1000; row += 1) {
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
    const failedSections = [];

    try {
        const attendanceApp = await openApp(
            "AMELS40197",
            "edu/sw/els/srg/aa/els_srgaa02_m06",
            ["학급담임", "출결관리", "결석자및개인별출결현황"],
        );
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
    } catch (error) {
        errors.push(`일일 출결: ${error.message || "조회 실패"}`);
        failedSections.push("attendance");
    }

    try {
        const absenceApp = await openApp("AMEDS40531", "edu/sa/eds/eaa/ae/eds_eaaae03_m01");
        if (!setControlValue(absenceApp, "dtAbeBgngYmd", monthStart.replace(/-/g, ""))
            || !setControlValue(absenceApp, "dtAbeEndYmd", monthEnd.replace(/-/g, ""))) {
            throw new Error("결석신고서 조회 기간을 설정하지 못했습니다.");
        }
        await searchWithButton(absenceApp, "/eds_eaa_ae03_002.do");
        payload.absence_applications = readApplications(absenceApp, "dsStdntListForAbe", "결석");
    } catch (error) {
        errors.push(`결석 신청: ${error.message || "조회 실패"}`);
        failedSections.push("absence_applications");
    }

    try {
        const fieldTripApp = await openApp(
            "AMEDS40501",
            "edu/sa/eds/eaa/ae/eds_eaaae01_m01",
            ["학급담임", "교육활동신청관리", "교외체험학습관리", "교외체험학습신청서관리"],
        );
        await searchWithButton(fieldTripApp, "/eds_eaa_ae01_002.do");
        payload.experiential_applications = readApplications(fieldTripApp, "dsStdntListForAply", "체험학습");
    } catch (error) {
        errors.push(`체험학습 신청: ${error.message || "조회 실패"}`);
        failedSections.push("experiential_applications");
    }

    payload.failed_sections = failedSections;
    payload.errors = errors;
    return { ok: true, payload, errors };
}

async function scanAbsenceWorkQueueOnNeis({ monthStart, monthEnd }) {
    const platform = window.cpr?.core?.Platform?.INSTANCE;
    if (!platform) return { ok: false, error: "NEIS 업무 화면이 열려 있지 않습니다." };
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const text = (value, limit = 80) => String(value ?? "").trim().slice(0, limit);
    const exactText = (value, limit = 3000) => String(value ?? "").slice(0, limit);
    const date = (value) => {
        const digits = String(value ?? "").replace(/\D/g, "").slice(0, 8);
        return digits.length === 8 ? `${digits.slice(0, 4)}-${digits.slice(4, 6)}-${digits.slice(6, 8)}` : "";
    };
    const valueAt = (dataset, row, column) => {
        try { return dataset.getValue(row, column) ?? ""; } catch (_) { return ""; }
    };
    const appId = "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
    const menuId = "AMEDS40531";
    const appsFor = () => platform.getAllRunningAppInstances().filter((instance) => instance?.app?.id === appId);
    const appFor = () => appsFor()[0] || null;
    async function waitForApp(timeoutMs) {
        const until = Date.now() + timeoutMs;
        while (Date.now() < until) {
            const instance = appFor();
            if (instance) return instance;
            await sleep(250);
        }
        return null;
    }
    async function openApp() {
        const existingApps = appsFor();
        if (existingApps.length > 1) {
            throw new Error("결석신고서 목록 화면이 여러 개 열려 있습니다. 목록 창을 하나만 남긴 뒤 다시 조회해 주세요.");
        }
        const existing = existingApps[0] || null;
        if (existing) return existing;
        const index = platform.getAllRunningAppInstances().find((instance) => instance?.app?.id === "app/com/main/Index");
        if (typeof index?.callAppMethod === "function") {
            try {
                const result = index.callAppMethod("doOpenMenuToMdi", [menuId]);
                if (result && typeof result.catch === "function") result.catch(() => { });
                const opened = await waitForApp(10000);
                if (opened) return opened;
            } catch (_) { }
        }
        if (typeof window.openMdiMenu === "function") {
            try {
                window.openMdiMenu(menuId);
                const opened = await waitForApp(10000);
                if (opened) return opened;
            } catch (_) { }
        }
        throw new Error("결석신고서 목록 화면을 열지 못했습니다.");
    }
    function setControlValue(instance, controlId, value) {
        const control = instance.lookup(controlId);
        if (!control) return false;
        control.value = value;
        try { control.dispatchEvent(new cpr.events.CUIEvent("value-change")); } catch (_) { }
        return true;
    }
    async function search(instance) {
        const button = instance.lookup("btnSearch");
        if (!button?.click) throw new Error("결석신고서 조회 버튼을 찾지 못했습니다.");
        const started = performance.now();
        button.click();
        for (let attempt = 0; attempt < 40; attempt += 1) {
            const completed = performance.getEntriesByType("resource").some((entry) => {
                if (entry.startTime < started || entry.responseEnd <= 0) return false;
                try { return new URL(entry.name, location.href).pathname.endsWith("/eds_eaa_ae03_002.do"); } catch (_) { return false; }
            });
            if (completed) return;
            await sleep(150);
        }
        throw new Error("결석신고서 조회 응답을 확인하지 못했습니다.");
    }

    const instance = await openApp();
    if (!setControlValue(instance, "dtAbeBgngYmd", monthStart.replace(/-/g, ""))
        || !setControlValue(instance, "dtAbeEndYmd", monthEnd.replace(/-/g, ""))) {
        return { ok: false, error: "결석신고서 조회기간을 설정하지 못했습니다." };
    }
    await search(instance);
    const dataset = instance.lookup("dsStdntListForAbe");
    if (!dataset?.getRowCount) return { ok: false, error: "결석신고서 목록을 읽지 못했습니다." };

    const candidates = [];
    const seenIds = new Map();
    let skippedMissingId = 0;
    for (let row = 0; row < dataset.getRowCount() && candidates.length < 1000; row += 1) {
        const status = text(valueAt(dataset, row, "eduActPrcsStsNm"), 30);
        const approvalStatus = text(valueAt(dataset, row, "atrzStsNm"), 30);
        if (status !== "접수대기" && !(status === "접수" && approvalStatus === "미상신")) continue;
        const applicationId = text(valueAt(dataset, row, "abeDclrId"), 80);
        if (!applicationId) {
            skippedMissingId += 1;
            continue;
        }
        const startDate = date(valueAt(dataset, row, "abeBgngDt"));
        const endDate = date(valueAt(dataset, row, "abeEndDt")) || startDate;
        const student = text(valueAt(dataset, row, "stuFlnm"), 50);
        if (!startDate || !endDate || !student) continue;
        seenIds.set(applicationId, (seenIds.get(applicationId) || 0) + 1);
        const namedClass = text(valueAt(dataset, row, "clsNm"), 24);
        const grade = text(valueAt(dataset, row, "grd"), 8);
        const classNo = text(valueAt(dataset, row, "clsNo"), 8);
        candidates.push({
            application_id: applicationId,
            student,
            class_name: namedClass || [grade && `${grade}학년`, classNo && `${classNo}반`].filter(Boolean).join(" "),
            start_date: startDate,
            end_date: endDate,
            kind: "결석신고",
            absence_category_code: text(valueAt(dataset, row, "abeDclrScCd"), 2),
            absence_category: text(valueAt(dataset, row, "abeDclrScNm"), 40),
            reason: text(valueAt(dataset, row, "abeRsnCn"), 500),
            teacher_reason: exactText(valueAt(dataset, row, "shlOpiCn")),
            status,
            approval_status: approvalStatus,
        });
    }
    for (const candidate of candidates) candidate.selectable = seenIds.get(candidate.application_id) === 1;
    return {
        ok: true,
        month_start: monthStart,
        month_end: monthEnd,
        candidates,
        duplicates: [...seenIds.values()].filter((count) => count > 1).length,
        skipped_missing_id: skippedMissingId,
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
        const partial = result.errors?.length
            ? ` 일부 조회 실패(실패 구역은 이전 자료 유지): ${result.errors.join(" · ")}`
            : "";
        setStatus(`${today} · 저장 자료: 출결 ${stored.attendance}건, 결석신고 ${stored.absence_applications}건, 체험학습 ${stored.experiential_applications}건.${partial}`, Boolean(result.errors?.length));
    } catch (error) {
        setStatus(error.message || "학생 현황을 가져오지 못했습니다.", true);
    } finally {
        studentButton.disabled = false;
    }
}

function selectedAbsenceCandidates() {
    const selectedIds = new Set(
        [...actionCandidatesNode.querySelectorAll('input[type="checkbox"]:checked')]
            .map((input) => input.dataset.applicationId)
            .filter(Boolean),
    );
    selectedWorkApplicationIds = selectedIds;
    return absenceWorkCandidates.filter((item) => selectedIds.has(item.application_id));
}

function updateAbsenceSelection() {
    const selected = selectedAbsenceCandidates();
    const receiptCount = selected.filter((item) => item.status === "접수대기").length;
    const submissionCount = selected.length;
    actionPreviewText.textContent = `${selected.length}건 선택 · 새 접수 ${receiptCount}건 · 승인요청 ${submissionCount}건`;
    actionSelectionSummary.textContent = selected.map((item) => {
        const period = item.start_date === item.end_date ? item.start_date : `${item.start_date} ~ ${item.end_date}`;
        const code = item.selected_absence_category_code || item.absence_category_code || "01";
        const category = ABSENCE_CATEGORY_OPTIONS.find((option) => option.code === code)?.name || "구분 확인 필요";
        const approvers = approvalProfiles[normalizeProfileKind(item.kind)] || [];
        const approvalLine = approvers.length ? approvers.join(" → ") : "결재선 미등록";
        const teacherReason = item.selected_teacher_reason ?? item.teacher_reason ?? "";
        return `${item.class_name} ${item.student} · ${period} · ${category}\n신청 내용 · ${item.reason || "기재 없음"}\n담임/교사 추가 내용 · ${teacherReason || "없음"}\n결재선 · ${approvalLine}`.trim();
    }).join("\n");
    actionExecuteButton.disabled = selected.length === 0 || absenceUiExecutionInFlight;
}

function renderAbsenceWorkCandidates(items) {
    absenceWorkCandidates = items;
    selectedWorkApplicationIds = new Set();
    actionCandidatesNode.replaceChildren();
    renderApprovalProfiles(items.map((item) => item.kind));
    actionPreview.hidden = true;
    selectAllAbsenceButton.disabled = !items.some((item) => item.selectable);
    clearAbsenceSelectionButton.disabled = !items.some((item) => item.selectable);

    if (!items.length) {
        actionStatus.textContent = "이 달에 접수대기 또는 접수 후 미상신 상태인 결석신고서가 없습니다.";
        return;
    }

    const bulkCategory = document.createElement("div");
    bulkCategory.className = "absence-bulk-category";
    const bulkLabel = document.createElement("label");
    bulkLabel.textContent = "선택한 접수대기 건의 결석 구분 · 기본 질병결석";
    const bulkSelect = document.createElement("select");
    bulkSelect.className = "absence-bulk-select";
    for (const option of ABSENCE_CATEGORY_OPTIONS) {
        const element = document.createElement("option");
        element.value = option.code;
        element.textContent = option.name;
        bulkSelect.append(element);
    }
    bulkSelect.value = "01";
    bulkLabel.append(bulkSelect);
    bulkSelect.addEventListener("change", () => {
        let applied = 0;
        for (const item of selectedAbsenceCandidates()) {
            if (item.status !== "접수대기") continue;
            item.selected_absence_category_code = bulkSelect.value;
            const row = actionCandidatesNode.querySelector(`[data-application-id="${CSS.escape(item.application_id)}"]`);
            const select = row?.querySelector("select.absence-category-select");
            if (select) select.value = bulkSelect.value;
            applied += 1;
        }
        if (!applied) actionStatus.textContent = "결석 구분을 적용할 접수대기 건을 먼저 선택해 주세요.";
        updateAbsenceSelection();
    });
    bulkCategory.append(bulkLabel);
    actionCandidatesNode.append(bulkCategory);

    const groups = [
        ["접수대기 · 접수 후 승인요청까지", items.filter((item) => item.status === "접수대기")],
        ["접수 · 미상신 · 승인요청 대상", items.filter((item) => item.status === "접수" && item.approval_status === "미상신")],
    ];
    for (const [title, rows] of groups) {
        if (!rows.length) continue;
        const heading = document.createElement("div");
        heading.className = "action-group-title";
        heading.textContent = `${title} (${rows.length}건)`;
        actionCandidatesNode.append(heading);
        for (const item of rows) {
            const label = document.createElement("div");
            label.className = `action-candidate${item.selectable ? "" : " disabled"}`;
            label.dataset.applicationId = item.application_id;
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.dataset.applicationId = item.application_id;
            checkbox.disabled = !item.selectable;
            checkbox.addEventListener("change", updateAbsenceSelection);
            const body = document.createElement("div");
            const period = item.start_date === item.end_date ? item.start_date : `${item.start_date} ~ ${item.end_date}`;
            const name = document.createElement("strong");
            name.textContent = `${item.class_name} ${item.student}`.trim();
            body.append(name);
            const detail = document.createElement("small");
            detail.textContent = `${item.kind} · ${period} · ${item.status}${item.approval_status ? ` / ${item.approval_status}` : ""}`;
            body.append(detail);
            const reason = document.createElement("small");
            reason.textContent = `신청 내용 · ${item.reason || "기재 없음"}`;
            body.append(reason);
            const teacherReasonLabel = document.createElement("label");
            teacherReasonLabel.className = "teacher-reason-label";
            teacherReasonLabel.textContent = "담임/교사 결석 사유 · 필요할 때만 추가";
            const teacherReasonInput = document.createElement("textarea");
            teacherReasonInput.className = "teacher-reason-input";
            teacherReasonInput.rows = 2;
            teacherReasonInput.maxLength = 3000;
            teacherReasonInput.value = item.teacher_reason || "";
            teacherReasonInput.placeholder = "접수 시 NEIS의 교사 결석 사유 칸에 저장됩니다";
            teacherReasonInput.disabled = item.status !== "접수대기";
            item.selected_teacher_reason = teacherReasonInput.value;
            teacherReasonInput.addEventListener("input", () => {
                item.selected_teacher_reason = teacherReasonInput.value.slice(0, 3000);
                updateAbsenceSelection();
            });
            body.append(teacherReasonLabel, teacherReasonInput);
            const categoryLabel = document.createElement("label");
            categoryLabel.className = "absence-category-label";
            categoryLabel.textContent = "결석 구분";
            const categorySelect = document.createElement("select");
            categorySelect.className = "absence-category-select";
            for (const option of ABSENCE_CATEGORY_OPTIONS) {
                const element = document.createElement("option");
                element.value = option.code;
                element.textContent = option.name;
                categorySelect.append(element);
            }
            const currentCategoryCode = ABSENCE_CATEGORY_OPTIONS.some((option) => option.code === item.absence_category_code)
                ? item.absence_category_code
                : "01";
            item.selected_absence_category_code = currentCategoryCode;
            categorySelect.value = currentCategoryCode;
            categorySelect.disabled = item.status !== "접수대기";
            categorySelect.addEventListener("change", () => {
                item.selected_absence_category_code = categorySelect.value;
                updateAbsenceSelection();
            });
            categoryLabel.append(categorySelect);
            body.append(categoryLabel);
            const profileStatus = document.createElement("small");
            profileStatus.className = "profile-status";
            profileStatus.textContent = (approvalProfiles[normalizeProfileKind(item.kind)] || []).length
                ? "신청 유형 결재선 저장됨"
                : "신청 유형 결재선 미등록";
            if (!approvalProfiles[normalizeProfileKind(item.kind)]?.length) profileStatus.classList.add("missing");
            body.append(profileStatus);
            if (!item.selectable) {
                const duplicate = document.createElement("small");
                duplicate.textContent = "중복 신청 ID라 안전을 위해 선택할 수 없습니다.";
                body.append(duplicate);
            }
            label.append(checkbox, body);
            actionCandidatesNode.append(label);
        }
    }
    actionStatus.textContent = `학생·날짜·신청 내용과 결석 구분을 확인하고 처리할 건을 선택하세요. 선택 건 접수와 결재 상신은 아래 버튼 한 번으로 시작합니다.${items.some((item) => !item.selectable) ? " 중복 식별값은 처리 대상에서 제외했습니다." : ""}`;
    actionPreview.hidden = false;
    updateAbsenceSelection();
}

async function reviewAbsenceWorkQueue() {
    await approvalProfilesReady;
    actionPanel.hidden = false;
    reviewAbsenceButton.disabled = true;
    actionStatus.textContent = "NEIS에서 이번 달 결석신고 처리대상을 다시 확인하고 있습니다…";
    actionCandidatesNode.replaceChildren();
    actionPreview.hidden = true;
    absenceWorkCandidates = [];
    selectedWorkApplicationIds = new Set();
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab?.id || !/^https:\/\/.+\.neis\.go\.kr\//.test(tab.url || "")) {
            throw new Error("NEIS 탭을 활성화한 뒤 확장 프로그램을 열어 주세요.");
        }
        const [year, month] = monthInput.value.split("-").map(Number);
        if (!year || !month) throw new Error("가져올 달을 선택해 주세요.");
        const monthStart = `${year}-${String(month).padStart(2, "0")}-01`;
        const monthEnd = `${year}-${String(month).padStart(2, "0")}-${String(new Date(year, month, 0).getDate()).padStart(2, "0")}`;
        const [{ result }] = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            world: "MAIN",
            func: scanAbsenceWorkQueueOnNeis,
            args: [{ monthStart, monthEnd }],
        });
        if (!result?.ok) throw new Error(result?.error || "결석신고 처리대상을 읽지 못했습니다.");
        await chrome.storage.local.remove("teacherlessonNeisAbsenceExecutionLock");
        const previous = await chrome.storage.local.get(LAST_ABSENCE_ACTION_KEY);
        if (previous[LAST_ABSENCE_ACTION_KEY]?.status === "unknown") {
            await chrome.storage.local.set({
                [LAST_ABSENCE_ACTION_KEY]: {
                    status: "reviewed",
                    updatedAt: new Date().toISOString(),
                    receiptCount: null,
                    submittedCount: null,
                    errors: [],
                },
            });
        }
        renderAbsenceWorkCandidates(result.candidates || []);
        if (result.duplicates) actionStatus.textContent += ` 중복 신청 ID ${result.duplicates}개는 선택할 수 없습니다.`;
        if (result.skipped_missing_id) actionStatus.textContent += ` 신청 ID를 확인할 수 없는 ${result.skipped_missing_id}건은 제외했습니다.`;
    } catch (error) {
        actionStatus.textContent = error.message || "처리대상을 확인하지 못했습니다.";
    } finally {
        reviewAbsenceButton.disabled = false;
    }
}

function renderLastAbsenceActionStatus(last) {
    if (!last?.status) return;
    actionPanel.hidden = false;
    actionCandidatesNode.replaceChildren();
    actionPreview.hidden = true;
    if (last.status === "running") {
        const startedAt = new Date(last.startedAt || 0).getTime();
        const stale = !Number.isFinite(startedAt) || Date.now() - startedAt > 10 * 60 * 1000;
        const stillRunning = !stale;
        reviewAbsenceButton.disabled = stillRunning;
        studentButton.disabled = stillRunning;
        weekButton.disabled = stillRunning;
        monthButton.disabled = stillRunning;
        actionStatus.textContent = stale
            ? "이전 처리 응답이 없습니다. 중복 실행하지 말고 대상 목록을 다시 조회해 NEIS 현재 상태를 확인해 주세요."
            : "NEIS 처리 작업이 진행 중입니다. NEIS 화면의 확인 창을 처리한 뒤 결과를 다시 확인해 주세요.";
        return;
    }
    reviewAbsenceButton.disabled = false;
    studentButton.disabled = false;
    weekButton.disabled = false;
    monthButton.disabled = false;
    if (last.status === "unknown") {
        actionStatus.textContent = "이전 실행이 중간에 끝나 NEIS 반영 건수를 확인하지 못했습니다. 재실행하지 말고 대상 목록을 새로 조회해 현재 상태를 확인하세요.";
        return;
    }
    if (last.status === "reviewed") {
        actionStatus.textContent = "이전 실행 뒤 대상 목록을 다시 조회했습니다. 현재 표시된 접수대기·미상신 건만 검토할 수 있습니다.";
        return;
    }
    const summary = `최근 처리 결과 · 접수 ${last.receiptCount || 0}건 · 승인요청 ${last.submittedCount || 0}건`;
    const issues = last.errors?.length ? ` · 확인 필요: ${last.errors.join(" · ")}` : " · NEIS에서 상태를 확인했습니다.";
    actionStatus.textContent = `${summary}${issues}`;
}

async function restoreLastAbsenceActionStatus() {
    try {
        const stored = await chrome.storage.local.get(LAST_ABSENCE_ACTION_KEY);
        renderLastAbsenceActionStatus(stored[LAST_ABSENCE_ACTION_KEY]);
    } catch (_) { }
}

async function executeSelectedAbsenceWork() {
    if (absenceUiExecutionInFlight) return;
    absenceUiExecutionInFlight = true;
    setNeisButtonsDisabled(true);
    actionExecuteButton.disabled = true;
    const selected = selectedAbsenceCandidates();
    if (!selected.length) {
        actionStatus.textContent = "먼저 처리할 신청을 선택해 주세요.";
        absenceUiExecutionInFlight = false;
        setNeisButtonsDisabled(false);
        updateAbsenceSelection();
        return;
    }
    try {
        await approvalProfilesReady;
        const batches = buildApprovalBatches(selected);
        const missingProfiles = batches.filter((batch) => !batch.approvers.length).map((batch) => batch.kind);
        if (missingProfiles.length) {
            actionStatus.textContent = `신청 유형별 결재선을 먼저 저장해 주세요: ${missingProfiles.join(" · ")}`;
            approvalSettings.open = true;
            return;
        }
        actionStatus.textContent = `선택한 ${selected.length}건을 접수·결재 상신합니다. 처리 중에는 확장 팝업이나 NEIS 창을 다시 실행하지 마세요…`;
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab?.id || !/^https:\/\/.+\.neis\.go\.kr\//.test(tab.url || "")) {
            throw new Error("NEIS 탭을 활성화한 뒤 확장 프로그램을 다시 열어 주세요.");
        }
        const [year, month] = monthInput.value.split("-").map(Number);
        if (!year || !month) throw new Error("가져올 달을 선택해 주세요.");
        const monthStart = `${year}-${String(month).padStart(2, "0")}-01`;
        const monthEnd = `${year}-${String(month).padStart(2, "0")}-${String(new Date(year, month, 0).getDate()).padStart(2, "0")}`;
        const response = await chrome.runtime.sendMessage({
            type: "PROCESS_SELECTED_ABSENCE_WORK",
            tabId: tab.id,
            payload: {
                monthStart,
                monthEnd,
                batches,
            },
        });
        if (!response?.ok) throw new Error(response?.error || "선택한 결석신고서를 처리하지 못했습니다.");
        const summary = `접수 ${response.receiptCount || 0}건 · 승인요청 ${response.submittedCount || 0}건`;
        const issues = response.errors?.length ? ` · 확인 필요: ${response.errors.join(" · ")}` : " · NEIS 목록에서 상태를 확인했습니다.";
        actionStatus.textContent = `${summary}${issues}`;
        actionCandidatesNode.replaceChildren();
        actionPreview.hidden = true;
        absenceWorkCandidates = [];
        selectedWorkApplicationIds = new Set();
    } catch (error) {
        actionStatus.textContent = error.message || "선택한 결석신고서를 처리하지 못했습니다. NEIS 화면의 상태를 확인해 주세요.";
        actionCandidatesNode.replaceChildren();
        actionPreview.hidden = true;
        absenceWorkCandidates = [];
        selectedWorkApplicationIds = new Set();
    } finally {
        absenceUiExecutionInFlight = false;
        setNeisButtonsDisabled(false);
        updateAbsenceSelection();
    }
}

function setAbsenceSelection(selected) {
    actionCandidatesNode.querySelectorAll('input[type="checkbox"]').forEach((input) => {
        if (!input.disabled) input.checked = selected;
    });
    updateAbsenceSelection();
}

function setNeisButtonsDisabled(disabled) {
    for (const button of [weekButton, monthButton, studentButton, reviewAbsenceButton]) button.disabled = disabled;
    const selectable = absenceWorkCandidates.some((item) => item.selectable);
    selectAllAbsenceButton.disabled = disabled || !selectable;
    clearAbsenceSelectionButton.disabled = disabled || !selectable;
    actionCandidatesNode.querySelectorAll('input[type="checkbox"], select, textarea').forEach((control) => {
        if (control.classList.contains("absence-bulk-select")) {
            control.disabled = disabled;
            return;
        }
        const applicationId = control.dataset.applicationId || control.closest(".action-candidate")?.dataset.applicationId;
        const item = absenceWorkCandidates.find((candidate) => candidate.application_id === applicationId);
        const canEdit = control.matches('input[type="checkbox"]') ? item?.selectable : item?.status === "접수대기";
        control.disabled = disabled || !canEdit;
    });
}

monthInput.value = localMonth();
approvalProfilesReady = loadApprovalProfiles();
restoreLastAbsenceActionStatus();
chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes[LAST_ABSENCE_ACTION_KEY]) {
        if (changes[LAST_ABSENCE_ACTION_KEY].newValue?.status === "reviewed" && absenceWorkCandidates.length) return;
        renderLastAbsenceActionStatus(changes[LAST_ABSENCE_ACTION_KEY].newValue);
    }
});
weekButton.addEventListener("click", () => runImport("week"));
monthButton.addEventListener("click", () => runImport("month"));
studentButton.addEventListener("click", runStudentImport);
addApprovalProfileButton.addEventListener("click", () => {
    const row = createApprovalProfileRow();
    approvalProfilesNode.append(row);
    approvalSettings.open = true;
    row.querySelector('input[type="text"]')?.focus();
});
reviewAbsenceButton.addEventListener("click", reviewAbsenceWorkQueue);
selectAllAbsenceButton.addEventListener("click", () => setAbsenceSelection(true));
clearAbsenceSelectionButton.addEventListener("click", () => setAbsenceSelection(false));
actionExecuteButton.addEventListener("click", executeSelectedAbsenceWork);
viewerButton.addEventListener("click", () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("viewer.html") });
});
