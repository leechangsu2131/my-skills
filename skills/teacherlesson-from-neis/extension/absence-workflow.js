/* Main-world function injected by the extension service worker. */

async function processSelectedAbsenceWorkOnNeis({ monthStart, monthEnd, batches }) {
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
    /*
     * 신청 종류별 NEIS 화면. 승인요청(btnUpdateCancel3) 이후 기안·결재자지정·상신 창은 셋 다 같다.
     * receipt: "status"는 상세창 상태 콤보를 접수(02)로 바꾸고 저장, "button"은 상세창 [접수](btnUpdate)를 누른다.
     */
    const SCREENS = {
        결석신고: {
            label: "결석신고서", appId: "edu/sa/eds/eaa/ae/eds_eaaae03_m01", detailAppId: "edu/sa/eds/eaa/ae/eds_eaaae03_p01", menuId: "AMEDS40531",
            listDataset: "dsStdntListForAbe", detailDataset: "dsStdntListForAbe", idColumn: "abeDclrId",
            startColumn: "abeBgngDt", endColumn: "abeEndDt", endpoint: "/eds_eaa_ae03_002.do", monthFilter: true, receipt: "status",
        },
        체험학습신청서: {
            label: "교외체험학습 신청서", appId: "edu/sa/eds/eaa/ae/eds_eaaae01_m01", detailAppId: "edu/sa/eds/eaa/ae/eds_eaaae01_p01", menuId: "AMEDS40501",
            listDataset: "dsStdntListForAply", detailDataset: "dsStdntDtlForAply", idColumn: "ousExperLrnAplyId",
            startColumn: "experLrnBgngDt", endColumn: "experLrnEndDt", endpoint: "/eds_eaa_ae01_002.do", monthFilter: false, receipt: "button",
        },
        체험학습보고서: {
            label: "교외체험학습 보고서", appId: "edu/sa/eds/eaa/ae/eds_eaaae02_m01", detailAppId: "edu/sa/eds/eaa/ae/eds_eaaae02_p01", menuId: "AMEDS40511",
            listDataset: "dsStdntListForRlt", detailDataset: "dsStdntDtlForRlt", idColumn: "ousExperLrnRltId",
            startColumn: "experLrnBgngDt", endColumn: "experLrnEndDt", endpoint: "/eds_eaa_ae02_002.do", monthFilter: false, receipt: "button",
        },
    };
    const isAbsence = (kind) => kind === "결석신고";
    let screen = SCREENS.결석신고;
    let appId = screen.appId;
    let detailAppId = screen.detailAppId;
    let menuId = screen.menuId;
    const allDetailAppIds = Object.values(SCREENS).map((item) => item.detailAppId);
    function useScreen(kind) {
        screen = SCREENS[kind];
        appId = screen.appId;
        detailAppId = screen.detailAppId;
        menuId = screen.menuId;
    }
    const draftAppId = "edu/cm/wam/woa/pm/wam_woapm07_p00";
    const approverAppId = "edu/cm/wam/woa/pm/wam_woapm07_p04";
    const appsFor = (targetId) => platform.getAllRunningAppInstances().filter((instance) => instance?.app?.id === targetId);
    const appFor = (targetId) => appsFor(targetId)[0] || null;
    const isRunning = (instance) => platform.getAllRunningAppInstances().includes(instance);
    const safeLookup = (instance, id) => {
        try { return instance && isRunning(instance) ? instance.lookup(id) : null; } catch (_) { return null; }
    };
    let stage = "준비";

    /* NEIS confirm/alert windows (app/cmn/confirm, app/cmn/alert). They often open 5–10 s late. */
    function dialogInstances() {
        return platform.getAllRunningAppInstances().filter((instance) => {
            const id = String(instance?.app?.id || "");
            return /(^|\/)cmn\/(confirm|alert)$/i.test(id) || /(confirm|alert)$/i.test(id);
        });
    }
    function dialogInfo(instance) {
        const id = String(instance?.app?.id || "");
        const messages = [];
        let okButton = null;
        let children = [];
        try { children = instance.getContainer().getAllRecursiveChildren(); } catch (_) { }
        for (const control of children) {
            const value = String(control?.value ?? control?.text ?? "").trim();
            if (["output", "htmlsnippet", "textarea"].includes(control?.type) && value) messages.push(value);
            if (!okButton && typeof control?.click === "function"
                && (["btnOk", "btnConfirm", "btnYes"].includes(control.id) || ["확인", "예", "OK"].includes(value))) {
                okButton = control;
            }
        }
        const message = messages.join(" ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 300);
        return { id, type: /confirm/i.test(id) ? "confirm" : "alert", message, okButton, instance };
    }
    /* 대화상자 앱은 화면에 뜬 뒤 몇 초 늦게 앱 목록에 등록된다. 화면의 확인/알림 상자도 함께 본다. */
    function alertBoxOnScreen() {
        return [...document.querySelectorAll(".cl-dialog-header")].some((header) => {
            if (!/^(확인|알림|경고|오류|안내|에러)$/.test(String(header.innerText || "").trim())) return false;
            const box = header.closest(".cl-dialog-wrapper") || header.parentElement;
            const bounds = box?.getBoundingClientRect();
            return Boolean(bounds?.width && bounds?.height && getComputedStyle(box).visibility !== "hidden" && getComputedStyle(box).display !== "none");
        });
    }
    /* 다른 업무(출장신청 등)의 팝업이나 알림이 떠 있으면 그 창을 잘못 누를 수 있으므로 시작하지 않는다. */
    function foreignWindowsOnScreen() {
        return [...document.querySelectorAll(".cl-dialog-header")]
            .filter((header) => {
                const box = header.closest(".cl-dialog-wrapper") || header.parentElement;
                const bounds = box?.getBoundingClientRect();
                return Boolean(bounds?.width && bounds?.height && getComputedStyle(box).visibility !== "hidden" && getComputedStyle(box).display !== "none");
            })
            .map((header) => String(header.innerText || "").trim().slice(0, 30) || "제목 없음");
    }
    function assertNeisIdle(when) {
        const windows = foreignWindowsOnScreen();
        const messages = dialogInstances().map((instance) => dialogInfo(instance).message).filter(Boolean);
        if (windows.length || messages.length) {
            throw new Error(`${when} NEIS에 다른 창이나 알림이 열려 있어 아무것도 누르지 않고 멈췄습니다. 열린 창: ${[...new Set(windows)].join(", ") || "없음"}${messages.length ? ` / 알림: ${messages.join(" / ")}` : ""}. 해당 창을 정리한 뒤 다시 실행해 주세요.`);
        }
    }
    const asksToProceed = (message) => /(하시겠습니까|하겠습니까|할까요)/.test(message);
    /*
     * Wait until `isDone()` holds with no dialog open for `quietMs`.
     * Each dialog is passed to `decide(info)` which returns true (press 확인) or a string (stop with that error).
     * The 확인 button is pressed once per dialog instance; never re-clicks the original action button.
     */
    async function settleDialogs({ isDone, decide, timeoutMs, quietMs = 800, timeoutError }) {
        const until = Date.now() + timeoutMs;
        let lastActivity = Date.now();
        while (Date.now() < until) {
            const dialog = dialogInstances()[0];
            if (dialog) {
                let info = dialogInfo(dialog);
                // 확인창은 문구(optMsg)가 채워지기 전에 먼저 등록된다. 문구가 보일 때까지 잠시 기다린다.
                const messageUntil = Date.now() + 5000;
                while (!info.message && Date.now() < messageUntil && isRunning(dialog)) {
                    await sleep(150);
                    info = dialogInfo(dialog);
                }
                if (!isRunning(dialog)) continue;
                const decision = decide(info);
                if (decision !== true) {
                    throw new Error(`${typeof decision === "string" ? decision : "예상하지 못한 NEIS 알림이 열려 처리를 멈췄습니다."} (NEIS 메시지: ${info.message || "내용 없음"})`);
                }
                if (!info.okButton) throw new Error(`NEIS 알림의 확인 버튼을 찾지 못했습니다. (NEIS 메시지: ${info.message || "내용 없음"})`);
                report.dialogs.push(info.message || info.id);
                info.okButton.click();
                const closeUntil = Date.now() + 4000;
                while (isRunning(dialog) && Date.now() < closeUntil) await sleep(100);
                if (isRunning(dialog)) throw new Error(`NEIS 알림이 닫히지 않았습니다. (NEIS 메시지: ${info.message || "내용 없음"})`);
                lastActivity = Date.now();
                continue;
            }
            if (alertBoxOnScreen()) {
                lastActivity = Date.now();
            } else if (isDone() && Date.now() - lastActivity >= quietMs) {
                return;
            }
            await sleep(200);
        }
        if (!dialogInstances().length && !alertBoxOnScreen() && isDone()) return;
        throw new Error(timeoutError);
    }

    /* "이름", "이름 검토", "이름(결재)", "이름/협조" → { name, roleName, roleCode } */
    const approverRoles = { 결재: "2", 검토: "7", 협조: "4", 공람: "5" };
    function parseApprover(entry, isLast) {
        const raw = text(entry, 40).replace(/\s+/g, " ");
        const match = raw.match(/^(.+?)\s*[(（/:,]?\s*(결재|검토|협조|공람)\s*[)）]?$/);
        const name = text(match ? match[1] : raw, 40);
        const roleName = match ? match[2] : (isLast ? "결재" : "검토");
        return { name, roleName, roleCode: approverRoles[roleName], explicit: Boolean(match) };
    }
    function datasetRowText(dataset, row) {
        try {
            const data = dataset.getRowData?.(row);
            if (data && typeof data === "object") return Object.values(data).map((value) => String(value ?? "")).join(" ");
        } catch (_) { }
        return "";
    }
    function approverPickerCandidates() {
        return platform.getAllRunningAppInstances().filter((instance) => {
            if (instance?.app?.id === approverAppId) return true;
            return Boolean(instance?.lookup("dsParam")?.getRowCount
                && instance?.lookup("dsMain")?.getRowCount
                && instance?.lookup("grdUserListFrom")?.selectRows
                && instance?.lookup("grdUserListTo")?.setCheckRowIndex
                && instance?.lookup("btn15")?.click);
        });
    }
    function isApproverPickerVisible(instance) {
        const grid = instance?.lookup("grdUserListFrom");
        const element = grid?.uuid ? document.getElementById(`uuid-${grid.uuid}`) : null;
        const bounds = element?.getBoundingClientRect();
        return Boolean(bounds?.width && bounds?.height && getComputedStyle(element).visibility !== "hidden");
    }
    async function waitForApproverPicker(timeoutMs) {
        const until = Date.now() + timeoutMs;
        let candidateCount = 0;
        let visibleCount = 0;
        while (Date.now() < until) {
            const candidates = approverPickerCandidates();
            const visible = candidates.filter(isApproverPickerVisible);
            candidateCount = candidates.length;
            visibleCount = visible.length;
            if (visible.length === 1) return { instance: visible[0], candidateCount, visibleCount };
            await sleep(150);
        }
        return { instance: null, candidateCount, visibleCount };
    }
    function isListVisible(instance) {
        const grid = instance?.lookup("grdMain");
        const element = grid?.uuid ? document.getElementById(`uuid-${grid.uuid}`) : null;
        const bounds = element?.getBoundingClientRect();
        return Boolean(bounds?.width && bounds?.height);
    }
    async function waitForVisibleList(timeoutMs) {
        const until = Date.now() + timeoutMs;
        while (Date.now() < until) {
            const instance = appFor(appId);
            if (instance && isListVisible(instance)) return instance;
            await sleep(150);
        }
        return null;
    }
    async function waitForApp(targetId, timeoutMs, shouldExist = true) {
        const until = Date.now() + timeoutMs;
        while (Date.now() < until) {
            const instance = appFor(targetId);
            if (Boolean(instance) === shouldExist) return instance;
            await sleep(200);
        }
        return null;
    }
    async function openListApp() {
        const existingApps = appsFor(appId);
        if (existingApps.length > 1) {
            throw new Error(`${screen.label} 목록 화면이 여러 개 열려 있습니다. 목록 창을 하나만 남긴 뒤 다시 처리대상을 조회해 주세요.`);
        }
        const existing = existingApps[0] || null;
        if (existing && isListVisible(existing)) return existing;
        const index = appFor("app/com/main/Index");
        if (typeof index?.callAppMethod === "function") {
            try {
                const result = index.callAppMethod("doOpenMenuToMdi", [menuId]);
                if (result && typeof result.catch === "function") result.catch(() => { });
                const opened = await waitForVisibleList(10000);
                if (opened) return opened;
            } catch (_) { }
        }
        // NEIS 탭이 다른 창에 가려져 있으면 MDI 전환이 화면에 그려지지 않는다.
        // 목록 앱이 하나 열려 있으면 그리드 API(행 선택·cell-click·버튼 click)는 숨은 상태에서도 동작하므로 그대로 쓴다.
        const createdUntil = Date.now() + 8000;
        while (!appsFor(appId).length && Date.now() < createdUntil) await sleep(250);
        if (appsFor(appId).length === 1 && appFor(appId).lookup("grdMain")) {
            await sleep(1000);
            return appFor(appId);
        }
        if (typeof window.openMdiMenu === "function") {
            window.openMdiMenu(menuId);
            const opened = await waitForVisibleList(10000);
            if (opened) return opened;
        }
        // NEIS 탭이 다른 탭 뒤에 숨어 있으면 화면 전환이 그려지지 않는다.
        throw new Error(document.visibilityState === "hidden"
            ? `NEIS 탭이 화면에 보이지 않아 ${screen.label} 목록으로 전환하지 못했습니다. NEIS 탭을 앞에 둔 채 다시 실행해 주세요.`
            : `${screen.label} 목록 화면을 활성화하지 못했습니다. NEIS에서 목록 탭을 연 뒤 다시 시도해 주세요.`);
    }
    function setControlValue(instance, controlId, value) {
        const control = instance.lookup(controlId);
        if (!control) return false;
        control.value = value;
        try { control.dispatchEvent(new cpr.events.CValueChangeEvent("value-change", { newValue: value })); } catch (_) { }
        try { control.redraw(); } catch (_) { }
        return true;
    }
    async function search(instance) {
        const button = instance.lookup("btnSearch");
        if (!button?.click) throw new Error(`${screen.label} 조회 버튼을 찾지 못했습니다.`);
        // 막 연 화면은 [조회]가 무시될 수 있다. 응답이 없으면 한 번 더 누른다(조회는 읽기 전용).
        for (let tryCount = 0; tryCount < 2; tryCount += 1) {
            // 리소스 타이밍 버퍼(기본 250개)가 차면 새 조회 응답이 기록되지 않는다(NEIS를 오래 켜 둔 경우).
            try { performance.setResourceTimingBufferSize(5000); performance.clearResourceTimings(); } catch (_) { }
            const started = performance.now();
            button.click();
            for (let attempt = 0; attempt < 50; attempt += 1) {
                const completed = performance.getEntriesByType("resource").some((entry) => {
                    if (entry.startTime < started || entry.responseEnd <= 0) return false;
                    try { return new URL(entry.name, location.href).pathname.endsWith(screen.endpoint); } catch (_) { return false; }
                });
                if (completed) {
                    await sleep(200);
                    return;
                }
                await sleep(150);
            }
        }
        throw new Error(`${screen.label} 조회 응답을 확인하지 못했습니다.`);
    }
    function getRows(instance) {
        const dataset = instance.lookup(screen.listDataset);
        if (!dataset?.getRowCount) throw new Error(`${screen.label} 데이터셋을 찾지 못했습니다.`);
        const rows = [];
        for (let row = 0; row < dataset.getRowCount() && rows.length < 1000; row += 1) {
            const applicationId = text(valueAt(dataset, row, screen.idColumn), 80);
            if (!applicationId) continue;
            const startDate = date(valueAt(dataset, row, screen.startColumn));
            const endDate = date(valueAt(dataset, row, screen.endColumn)) || startDate;
            const status = text(valueAt(dataset, row, "eduActPrcsStsNm"), 30);
            const approvalStatus = text(valueAt(dataset, row, "atrzStsNm"), 30);
            const namedClass = text(valueAt(dataset, row, "clsNm"), 24);
            const grade = text(valueAt(dataset, row, "grd"), 8);
            const classNo = text(valueAt(dataset, row, "clsNo"), 8);
            const absence = screen === SCREENS.결석신고;
            rows.push({
                row,
                application_id: applicationId,
                start_date: startDate,
                end_date: endDate,
                student: text(valueAt(dataset, row, "stuFlnm"), 50),
                class_name: namedClass || [grade && `${grade}학년`, classNo && `${classNo}반`].filter(Boolean).join(" "),
                kind: Object.keys(SCREENS).find((kind) => SCREENS[kind] === screen),
                absence_category_code: absence ? text(valueAt(dataset, row, "abeDclrScCd"), 2) : "",
                absence_category: text(valueAt(dataset, row, absence ? "abeDclrScNm" : "experLrnScNm"), 40),
                reason: text(valueAt(dataset, row, absence ? "abeRsnCn" : "experLrnPlaceNm"), 500),
                teacher_reason: absence ? exactText(valueAt(dataset, row, "shlOpiCn")) : "",
                status,
                approval_status: approvalStatus,
            });
        }
        return { dataset, rows };
    }
    const approvalBatches = (Array.isArray(batches) ? batches : []).map((batch) => ({
        kind: text(batch?.kind, 40).replace(/\s+/g, " "),
        applicationIds: [...new Set((Array.isArray(batch?.applicationIds) ? batch.applicationIds : []).map((id) => text(id, 80)).filter(Boolean))],
        approvers: [...new Set((Array.isArray(batch?.approvers) ? batch.approvers : []).map((name) => text(name, 40)).filter(Boolean))],
        absenceCategoryCodes: batch?.absenceCategoryCodes && typeof batch.absenceCategoryCodes === "object"
            ? Object.fromEntries(Object.entries(batch.absenceCategoryCodes).map(([id, code]) => [text(id, 80), text(code, 2)]).filter(([id]) => id))
            : {},
        teacherReasons: batch?.teacherReasons && typeof batch.teacherReasons === "object"
            ? Object.fromEntries(Object.entries(batch.teacherReasons).map(([id, reason]) => [text(id, 80), exactText(reason)]).filter(([id]) => id))
            : {},
    }));
    const allSelected = approvalBatches.flatMap((batch) => batch.applicationIds.map((id) => `${batch.kind}:${id}`));
    if (!allSelected.length) return { ok: false, error: "처리할 신청을 선택해 주세요." };
    if (approvalBatches.some((batch) => !SCREENS[batch.kind] || !batch.applicationIds.length || !batch.approvers.length)
        || new Set(allSelected).size !== allSelected.length
        || new Set(approvalBatches.map((batch) => batch.kind)).size !== approvalBatches.length) {
        return { ok: false, error: "신청 유형별 처리 대상과 저장 결재선이 올바르지 않습니다." };
    }
    // 결석신고 → 체험학습 신청서 → 체험학습 보고서 순서로 처리한다.
    const orderedBatches = Object.keys(SCREENS).map((kind) => approvalBatches.find((batch) => batch.kind === kind)).filter(Boolean);

    const report = { ok: true, receiptIds: [], submittedIds: [], errors: [], warnings: [], dialogs: [], absence_applications: [], processedKinds: [] };
    let instance = null;
    let absenceInstance = null;
    try {
      for (const batch of orderedBatches) {
        useScreen(batch.kind);
        const absence = isAbsence(batch.kind);
        const selectedIds = batch.applicationIds;
        const expectedCategoryCodeById = new Map(selectedIds.map((id) => [id, absence ? (batch.absenceCategoryCodes[id] || "") : ""]));
        const expectedTeacherReasonById = new Map(selectedIds.map((id) => [id, absence ? exactText(batch.teacherReasons[id] ?? "") : ""]));
        stage = `${screen.label} 목록`;
        assertNeisIdle(`${screen.label} 처리 시작 전`);
        for (const otherDetail of allDetailAppIds) {
            if (appsFor(otherDetail).length) throw new Error("신청서 상세창이 이미 열려 있습니다. 창을 정리한 뒤 처리대상을 다시 조회해 주세요.");
        }
        instance = await openListApp();
        if (absence) absenceInstance = instance;
        report.processedKinds.push(batch.kind);
        // 목록을 처음 열 때 안내 알림이 뜰 수 있다. 오류가 아닌 안내만 확인한다.
        await settleDialogs({
            isDone: () => true,
            quietMs: absence ? 0 : 1200,
            timeoutMs: 8000,
            decide: (info) => (info.type === "alert" && !/(오류|실패|불가|권한)/.test(info.message)) || `${screen.label} 목록을 여는 중 NEIS 알림이 열려 멈췄습니다.`,
            timeoutError: `${screen.label} 목록의 안내 알림을 처리하지 못했습니다.`,
        });
        if (appsFor(appId).length !== 1) throw new Error(`${screen.label} 목록 화면이 하나인지 확인하지 못해 처리를 중단했습니다.`);
        if (appsFor(detailAppId).length || appsFor(draftAppId).length || approverPickerCandidates().length) {
            throw new Error(`${screen.label} 상세창 또는 결재창이 이미 열려 있습니다. 창을 정리한 뒤 처리대상을 다시 조회해 주세요.`);
        }
        if (screen.monthFilter && (!setControlValue(instance, "dtAbeBgngYmd", monthStart.replace(/-/g, ""))
            || !setControlValue(instance, "dtAbeEndYmd", monthEnd.replace(/-/g, "")))) {
            throw new Error(`${screen.label} 조회기간을 설정하지 못했습니다.`);
        }
        await search(instance);
        let { rows } = getRows(instance);
        const rowCounts = new Map();
        for (const row of rows) rowCounts.set(row.application_id, (rowCounts.get(row.application_id) || 0) + 1);
        const selectedRows = selectedIds.map((id) => rows.find((row) => row.application_id === id));
        if (selectedRows.some((row, index) => !row || rowCounts.get(selectedIds[index]) !== 1)) {
            throw new Error(`${screen.label}: 조회 후 신청 목록이 달라졌거나 식별값이 중복되어 실행을 중단했습니다. 처리 대상을 다시 확인해 주세요.`);
        }
        if (selectedRows.some((row) => row.kind !== batch.kind)) {
            throw new Error("NEIS 신청 유형이 저장 결재선에 연결된 유형과 달라 처리를 중단했습니다.");
        }
        if (selectedRows.some((row) => !(row.status === "접수대기" || (row.status === "접수" && row.approval_status === "미상신")))) {
            throw new Error(`${screen.label}: 선택한 신청의 처리 상태가 바뀌었습니다. 최신 목록을 다시 확인해 주세요.`);
        }
        if (absence && selectedRows.some((row) => !["01", "02", "03", "04"].includes(expectedCategoryCodeById.get(row.application_id)))) {
            throw new Error("선택한 신청의 결석 구분을 확인해 주세요. 기본값은 질병결석이며 행별로 바꿀 수 있습니다.");
        }

        function detailRecord(detail) {
            const dataset = safeLookup(detail, screen.detailDataset);
            if (!dataset?.getRowCount?.()) return null;
            return {
                application_id: text(valueAt(dataset, 0, screen.idColumn), 80),
                student: text(valueAt(dataset, 0, "stuFlnm"), 50),
                start_date: date(valueAt(dataset, 0, screen.startColumn)),
                end_date: date(valueAt(dataset, 0, screen.endColumn)) || date(valueAt(dataset, 0, screen.startColumn)),
                status: text(valueAt(dataset, 0, "eduActPrcsStsNm"), 30),
                absence_category_code: absence ? text(valueAt(dataset, 0, "abeDclrScCd"), 2) : "",
                reason: text(valueAt(dataset, 0, absence ? "abeRsnCn" : "experLrnPlaceNm"), 500),
                teacher_reason: absence ? exactText(valueAt(dataset, 0, "shlOpiCn")) : "",
            };
        }

        async function openDetailForSelected(selected, row) {
            const existing = appsFor(detailAppId);
            if (existing.length > 1) throw new Error(`${screen.label} 상세창이 여러 개 열려 있습니다. 창을 하나만 남긴 뒤 다시 조회해 주세요.`);
            if (existing.length === 1) {
                if (detailRecord(existing[0])?.application_id !== selected.application_id) {
                    throw new Error("다른 신청의 상세창이 열려 있어 선택 건을 처리하지 않았습니다. 상세창을 닫은 뒤 다시 시도해 주세요.");
                }
                return existing[0];
            }

            const grid = instance.lookup("grdMain");
            if (!grid?.selectRows || typeof cpr.events?.CGridMouseEvent !== "function") {
                throw new Error(`${screen.label} 목록에서 상세창을 안전하게 열 수 없습니다.`);
            }
            grid.selectRows([row.row]);
            grid.dispatchEvent(new cpr.events.CGridMouseEvent("cell-click", {
                rowIndex: row.row,
                viewRowIndex: row.row,
                cellIndex: 8,
                columnName: "stuFlnm",
                control: grid,
            }));

            const until = Date.now() + 10000;
            while (Date.now() < until) {
                const opened = appsFor(detailAppId);
                if (opened.length > 1) throw new Error(`${screen.label} 상세창이 중복으로 열려 처리를 멈췄습니다.`);
                if (opened.length === 1) {
                    // 체험학습 상세창은 열린 직후 "신청일수/누적일수 … 상이할 수 있습니다" 안내가 뜬다. 안내만 확인한다.
                    await settleDialogs({
                        isDone: () => Boolean(detailRecord(opened[0])),
                        quietMs: absence ? 300 : 1500,
                        timeoutMs: 10000,
                        decide: (info) => (info.type === "alert" && !/(오류|실패|불가|권한|없습니다)/.test(info.message)) || `${screen.label} 상세창을 여는 중 NEIS 알림이 열려 멈췄습니다.`,
                        timeoutError: `${screen.label} 상세 내용을 불러오지 못했습니다.`,
                    });
                    if (detailRecord(opened[0])?.application_id !== selected.application_id) {
                        throw new Error("NEIS에서 다른 신청의 상세창이 열려 선택 건을 처리하지 않았습니다.");
                    }
                    return opened[0];
                }
                await sleep(150);
            }
            throw new Error(`선택한 ${screen.label} 상세 화면을 열지 못했습니다.`);
        }

        for (const selected of selectedRows.filter((row) => row.status === "접수대기")) {
            if (appsFor(appId).length !== 1 || appsFor(detailAppId).length) {
                throw new Error(`처리 도중 ${screen.label} 목록/상세 창이 바뀌거나 중복되어 나머지 처리를 멈췄습니다.`);
            }
            const current = getRows(instance);
            const row = current.rows.find((item) => item.application_id === selected.application_id);
            if (!row || row.status !== "접수대기") throw new Error("접수 전 대상 상태가 바뀌어 나머지 처리를 중단했습니다.");
            assertNeisIdle("접수 전");
            stage = `${screen.label} 접수(${selected.start_date})`;
            const detail = await openDetailForSelected(selected, row);
            const detailRow = detailRecord(detail);
            if (!detailRow
                || detailRow.student !== selected.student
                || detailRow.start_date !== selected.start_date
                || detailRow.end_date !== selected.end_date
                || detailRow.status !== "접수대기"
                || detailRow.reason !== selected.reason) {
                throw new Error("상세창의 학생·날짜·내용이 선택 목록과 달라 접수를 중단했습니다.");
            }
            const expectedCategoryCode = expectedCategoryCodeById.get(selected.application_id);
            let receiptButton = null;
            if (screen.receipt === "status") {
                if (detailRow.absence_category_code !== expectedCategoryCode
                    && !setControlValue(detail, "cmbAbeDclrScCd", expectedCategoryCode)) {
                    throw new Error("선택한 결석 구분을 상세창에 설정하지 못했습니다.");
                }
                if (detailRow.teacher_reason !== selected.teacher_reason) {
                    throw new Error("목록 조회 후 담임/교사 결석 사유가 바뀌어 저장을 중단했습니다.");
                }
                if (detailRow.teacher_reason !== expectedTeacherReasonById.get(selected.application_id)
                    && !setControlValue(detail, "txaShlOpiCn", expectedTeacherReasonById.get(selected.application_id))) {
                    throw new Error("담임/교사 결석 내용을 상세창에 설정하지 못했습니다.");
                }
                const statusControl = detail.lookup("cmbEduActPrcsStsCd");
                receiptButton = detail.lookup("btnUpdateSave");
                if (!statusControl || !receiptButton?.click) throw new Error("접수 상태 저장 컨트롤을 찾지 못했습니다.");
                if (!setControlValue(detail, "cmbEduActPrcsStsCd", "02")) throw new Error("접수 상태를 설정하지 못했습니다.");
            } else {
                // 체험학습 신청서·보고서: 상세창 아래 [접수] 버튼. 내용은 바꾸지 않는다.
                // 신청서는 [저장] 없이 [접수]를 누르면 "저장 후 접수 하시기 바랍니다." 알림만 뜬다. 저장 버튼이 있으면 먼저 저장한다.
                const saveFirst = safeLookup(detail, "btnSave");
                // 체험학습 기간 상세(dsReqsDtl): NEIS는 전일(halfScCd=1)인 날의 교시를 "99"(종일)로 채운다.
                // 학부모가 올린 신청서 중에 전일인데 교시가 비어 있는 줄이 있으면 저장 검증이
                // "반일은 교시 선택이 필요합니다"로 막는다. 전일 줄만 NEIS 기본값 99로 채우고, 반일인데 교시가 없으면 멈춘다.
                const periodRows = safeLookup(detail, "dsReqsDtl");
                for (let index = 0; index < (periodRows?.getRowCount?.() || 0); index += 1) {
                    const half = String(valueAt(periodRows, index, "halfScCd"));
                    const begin = String(valueAt(periodRows, index, "ousExperLrnBgngPir"));
                    const end = String(valueAt(periodRows, index, "ousExperLrnEndPir"));
                    if (begin && end) continue;
                    if (half !== "1") {
                        throw new Error(`${screen.label}: ${date(valueAt(periodRows, index, "experBgngYmd"))}이(가) 반일인데 교시가 비어 있습니다. NEIS 상세창에서 교시를 고른 뒤 다시 실행해 주세요.`);
                    }
                    if (!begin) periodRows.setValue(index, "ousExperLrnBgngPir", "99");
                    if (!end) periodRows.setValue(index, "ousExperLrnEndPir", "99");
                    report.warnings.push(`${screen.label} ${selected.student}: 전일인데 교시가 비어 있던 ${date(valueAt(periodRows, index, "experBgngYmd"))}을(를) 종일(99)로 채워 저장했습니다.`);
                }
                try { safeLookup(detail, "grdDetail")?.redraw?.(); } catch (_) { }
                if (saveFirst?.click && saveFirst.visible !== false && saveFirst.enabled !== false) {
                    stage = `${screen.label} 저장(${selected.start_date})`;
                    saveFirst.click();
                    await sleep(500);
                    await settleDialogs({
                        isDone: () => true,
                        quietMs: 3000,
                        timeoutMs: 20000,
                        decide: (info) => {
                            if (info.type === "confirm" && asksToProceed(info.message) && /저장/.test(info.message)) return true;
                            if (info.type === "alert" && /(저장|완료|되었습니다|하였습니다)/.test(info.message) && !/(오류|실패|없습니다|불가|입력|선택|바랍니다|하십시오)/.test(info.message)) return true;
                            return `${screen.label} 저장 중 예상하지 못한 NEIS 알림이 열려 접수하지 않았습니다.`;
                        },
                        timeoutError: `${screen.label} 저장 확인창을 처리하지 못했습니다.`,
                    });
                    if (!isRunning(detail)) throw new Error(`${screen.label} 저장 후 상세창이 닫혀 접수하지 않았습니다. 목록에서 상태를 확인한 뒤 다시 실행해 주세요.`);
                    stage = `${screen.label} 접수(${selected.start_date})`;
                }
                receiptButton = detail.lookup("btnUpdate");
                if (!receiptButton?.click || String(receiptButton.value ?? "").trim() !== "접수" || receiptButton.visible === false || receiptButton.enabled === false) {
                    throw new Error(`${screen.label} 상세창의 [접수] 버튼을 찾지 못했습니다.`);
                }
            }
            receiptButton.click();
            await sleep(500);
            await settleDialogs({
                isDone: () => true,
                quietMs: 4000,
                timeoutMs: 20000,
                decide: (info) => {
                    if (info.type === "confirm" && asksToProceed(info.message) && /(저장|접수)/.test(info.message)) return true;
                    // "저장 후 접수 하시기 바랍니다." 같은 안내는 성공이 아니다.
                    if (info.type === "alert" && /(저장|접수|완료|되었습니다|하였습니다)/.test(info.message) && !/(오류|실패|없습니다|불가|입력|선택|바랍니다|하십시오|후 접수)/.test(info.message)) return true;
                    return "접수 저장 중 예상하지 못한 NEIS 알림이 열려 멈췄습니다.";
                },
                timeoutError: "접수 저장 확인창을 처리하지 못했습니다.",
            });
            // NEIS가 저장 후 상세창을 스스로 닫는 경우가 있다. 닫힌 창의 lookup은 null 오류를 낸다.
            const closeButton = safeLookup(detail, "btnCancel");
            if (closeButton?.click) closeButton.click();
            await waitForApp(detailAppId, 5000, false);
            if (appFor(detailAppId)) throw new Error(`${screen.label} 상세 화면이 닫히지 않아 나머지 처리를 중단했습니다.`);
            await search(instance);
            const refreshed = getRows(instance).rows.find((item) => item.application_id === selected.application_id);
            if (!refreshed || refreshed.status !== "접수"
                || refreshed.absence_category_code !== (absence ? expectedCategoryCode : "")
                || refreshed.teacher_reason !== expectedTeacherReasonById.get(selected.application_id)) {
                throw new Error("접수 저장 후 상태(결석신고는 결석 구분·담임/교사 사유 포함)를 확인하지 못했습니다. 승인요청은 보내지 않고 중단했습니다.");
            }
            report.receiptIds.push(`${batch.kind}:${selected.application_id}`);
        }

        {
            if (appsFor(appId).length !== 1 || appsFor(detailAppId).length
                || appsFor(draftAppId).length || approverPickerCandidates().length) {
                throw new Error(`상신 전 ${screen.label} 목록이나 결재 창이 중복/변경되어 처리를 멈췄습니다.`);
            }
            await search(instance);
            rows = getRows(instance).rows;
            const eligibleForSubmission = batch.applicationIds
                .map((id) => rows.find((row) => row.application_id === id))
                .filter((row) => row
                    && row.kind === batch.kind
                    && row.absence_category_code === expectedCategoryCodeById.get(row.application_id)
                    && row.teacher_reason === expectedTeacherReasonById.get(row.application_id)
                    && row.status === "접수"
                    && row.approval_status === "미상신");
            if (eligibleForSubmission.length !== batch.applicationIds.length) {
                throw new Error(`신청 유형 '${batch.kind}'의 선택 건이 모두 접수·미상신 상태가 아니어서 승인요청을 보내지 않았습니다.`);
            }

            const grid = instance.lookup("grdMain");
            const currentData = getRows(instance);
            if (!grid?.redraw || !grid?.setCheckRowIndex || !grid?.getCheckRowIndices || !currentData.dataset) throw new Error("승인요청 대상 행을 선택할 수 없습니다.");
            for (let row = 0; row < currentData.dataset.getRowCount(); row += 1) {
                try { currentData.dataset.setValue(row, "chk", "0"); }
                catch (_) { throw new Error("승인요청 대상 체크를 초기화하지 못했습니다."); }
            }
            grid.clearAllCheck?.();
            grid.redraw();
            for (const selected of eligibleForSubmission) {
                const rowId = text(valueAt(currentData.dataset, selected.row, screen.idColumn), 80);
                if (rowId !== selected.application_id) throw new Error("승인요청 행 위치가 바뀌어 대상 선택을 중단했습니다.");
                grid.setCheckRowIndex(selected.row, true);
                try { currentData.dataset.setValue(selected.row, "chk", "1"); }
                catch (_) { throw new Error("선택한 승인요청 대상을 설정하지 못했습니다."); }
            }
            grid.redraw();
            const expectedIds = new Set(eligibleForSubmission.map((row) => row.application_id));
            const expectedRows = new Set(eligibleForSubmission.map((row) => row.row));
            let checkedIds = new Set();
            for (let attempt = 0; attempt < 12; attempt += 1) {
                checkedIds = new Set();
                const checkedRows = new Set(grid.getCheckRowIndices());
                for (const row of checkedRows) {
                    const applicationId = text(valueAt(currentData.dataset, row, screen.idColumn), 80);
                    if (!expectedIds.has(applicationId)) throw new Error("선택하지 않은 신청이 승인요청 대상으로 체크되어 처리를 중단했습니다.");
                    checkedIds.add(applicationId);
                }
                if (checkedIds.size === expectedIds.size && [...expectedRows].every((row) => checkedRows.has(row))) break;
                await sleep(100);
            }
            if (checkedIds.size !== expectedIds.size || [...expectedRows].some((row) => !grid.getCheckRowIndices().includes(row))) {
                throw new Error("그리드에서 선택한 승인요청 대상을 확인하지 못해 상신하지 않았습니다.");
            }
            if (appsFor(draftAppId).length || approverPickerCandidates().length) {
                throw new Error("기존 결재창이 열려 있어 중복 상신을 막았습니다. 창의 상태를 확인한 뒤 다시 조회해 주세요.");
            }
            const submitButton = instance.lookup("btnUpdateCancel3");
            if (!submitButton?.click) throw new Error("승인요청 버튼을 찾지 못했습니다.");
            const approverPlan = batch.approvers.map((entry, index) => parseApprover(entry, index === batch.approvers.length - 1));
            if (approverPlan.some((item) => !item.name || !item.roleCode)
                || new Set(approverPlan.map((item) => item.name)).size !== approverPlan.length) {
                throw new Error(`신청 유형 '${batch.kind}'의 결재선 형식을 확인해 주세요. 한 줄에 '이름' 또는 '이름 검토/결재/협조/공람'으로 적습니다.`);
            }

            // 1) 승인요청 → (확인창) → 기안문서상신 창. 버튼은 한 번만 누르고 늦게 뜨는 창을 기다린다.
            assertNeisIdle("승인요청 전");
            stage = `승인요청(${batch.kind})`;
            submitButton.click();
            await settleDialogs({
                isDone: () => appsFor(draftAppId).length >= 1,
                quietMs: 800,
                timeoutMs: 60000,
                decide: (info) => (info.type === "confirm" && asksToProceed(info.message)) || "승인요청 중 NEIS 알림이 열려 상신하지 않았습니다.",
                timeoutError: "60초 안에 기안문서상신 창이 열리지 않았습니다. 승인요청 버튼을 다시 누르지 말고 NEIS 화면을 확인해 주세요.",
            });
            if (appsFor(draftAppId).length !== 1) throw new Error("기안문서상신 창이 여러 개 열려 상신하지 않았습니다. 창을 정리한 뒤 다시 조회해 주세요.");
            const draft = appFor(draftAppId);

            // 2) 결재자지정 창(p04) 열기
            // 기안창은 앱 목록에 먼저 잡히고 내용(결재문서명·기안자 행)은 나중에 채워진다. 다 채워진 뒤에 누른다.
            const draftReadyUntil = Date.now() + 30000;
            while (Date.now() < draftReadyUntil) {
                const title = String(safeLookup(draft, "ipbDoctNm")?.value ?? "").trim();
                const draftLine = safeLookup(draft, "dsSancr");
                const button = safeLookup(draft, "btnSelectSancr");
                if (title && draftLine?.getRowCount?.() >= 1 && button?.click && button.enabled !== false) break;
                await sleep(300);
            }
            await sleep(800);
            const selectApproversButton = safeLookup(draft, "btnSelectSancr");
            if (!selectApproversButton?.click || selectApproversButton.enabled === false) throw new Error("NEIS 기안 화면의 결재자 지정 버튼이 비활성 상태입니다.");
            stage = `결재자지정(${batch.kind})`;
            selectApproversButton.click();
            let pickerState = { instance: null, candidateCount: 0, visibleCount: 0 };
            const pickerStarted = Date.now();
            let pickerRetried = false;
            while (Date.now() - pickerStarted < 40000) {
                if (dialogInstances().length) {
                    const info = dialogInfo(dialogInstances()[0]);
                    throw new Error(`결재자 지정 창을 여는 중 NEIS 알림이 열려 멈췄습니다. (NEIS 메시지: ${info.message || "내용 없음"})`);
                }
                pickerState = await waitForApproverPicker(500);
                if (pickerState.instance) break;
                // 10초가 지나도 창 후보조차 없으면 클릭이 무시된 것이므로 한 번만 다시 누른다.
                if (!pickerRetried && Date.now() - pickerStarted > 10000 && !pickerState.candidateCount && !alertBoxOnScreen()
                    && !foreignWindowsOnScreen().includes("결재자지정")) {
                    pickerRetried = true;
                    safeLookup(draft, "btnSelectSancr")?.click?.();
                }
            }
            const approverPopup = pickerState.instance;
            if (!approverPopup) {
                throw new Error(`NEIS 결재자 선택 창을 확인하지 못했습니다 (창 후보 ${pickerState.candidateCount}개, 화면에 보이는 창 ${pickerState.visibleCount}개). 상신하지 않았습니다.`);
            }
            const approverDataset = approverPopup.lookup("dsMain");
            const selectedApproverDataset = approverPopup.lookup("dsParam");
            const approverGrid = approverPopup.lookup("grdUserListFrom");
            const selectedApproverGrid = approverPopup.lookup("grdUserListTo");
            const addButton = approverPopup.lookup("btn1");
            const removeButton = approverPopup.lookup("btn15");
            const roleRadio = approverPopup.lookup("rdbCn");
            const searchNameInput = approverPopup.lookup("userNm");
            const searchButton = approverPopup.lookup("btnSearch");
            if (!approverDataset?.getRowCount || !selectedApproverDataset?.getRowCount
                || !approverGrid?.selectRows || !selectedApproverGrid?.setCheckRowIndex
                || !selectedApproverGrid?.getCheckRowIndices || !addButton?.click || !removeButton?.click) {
                throw new Error("결재자 목록, 현재 결재선 또는 추가·삭제 컨트롤을 찾지 못했습니다.");
            }
            if (!roleRadio) throw new Error("결재자 지정 창에서 구분(결재/검토) 선택 버튼을 찾지 못했습니다.");
            const isDraftRow = (dataset, row) => {
                const roleName = text(valueAt(dataset, row, "atrzScNm"), 20);
                const roleCode = text(valueAt(dataset, row, "atrzScCd"), 4);
                const sequence = Number(valueAt(dataset, row, "atrzSeqSn"));
                return roleName === "기안" || (roleCode === "1" && sequence === 0);
            };
            const readSelectedApprovers = () => {
                const items = [];
                for (let row = 0; row < selectedApproverDataset.getRowCount(); row += 1) {
                    if (isDraftRow(selectedApproverDataset, row)) continue;
                    items.push({
                        name: text(valueAt(selectedApproverDataset, row, "userNm"), 40),
                        roleName: text(valueAt(selectedApproverDataset, row, "atrzScNm"), 20),
                    });
                }
                return items;
            };
            const matchesPlan = (items, count = approverPlan.length) => items.length === count
                && items.every((item, index) => item.name === approverPlan[index].name
                    && (!item.roleName || item.roleName === approverPlan[index].roleName));
            const describe = (items) => items.map((item) => `${item.name}${item.roleName ? `(${item.roleName})` : ""}`).join(" → ") || "없음";

            // 2-1) 미리 들어 있는 결재자가 저장 결재선과 다르면 기안자 행만 남기고 지운다.
            const currentApprovers = readSelectedApprovers();
            const alreadyExact = matchesPlan(currentApprovers);
            if (currentApprovers.length && !alreadyExact) {
                const rowsToRemove = [];
                for (let row = 0; row < selectedApproverDataset.getRowCount(); row += 1) {
                    if (!isDraftRow(selectedApproverDataset, row)) rowsToRemove.push(row);
                }
                selectedApproverGrid.clearAllCheck?.();
                for (const row of rowsToRemove) selectedApproverGrid.setCheckRowIndex(row, true);
                const checkedRows = new Set(selectedApproverGrid.getCheckRowIndices());
                if (checkedRows.size !== rowsToRemove.length || rowsToRemove.some((row) => !checkedRows.has(row))) {
                    throw new Error("기안자 행을 보존하면서 기존 결재자만 선택하지 못해 상신을 중단했습니다.");
                }
                removeButton.click();
                const removeUntil = Date.now() + 3000;
                while (readSelectedApprovers().length && Date.now() < removeUntil) await sleep(150);
                if (readSelectedApprovers().length) throw new Error("기존 결재자를 지우지 못해 저장된 결재선을 추가하지 않았습니다.");
            }

            // 2-2) 사람마다: 구분(rdbCn)을 먼저 고르고 → 행 선택 → [추가]. 추가되지 않았을 때만 더블클릭으로 한 번 더 시도.
            if (!alreadyExact) {
                for (let index = 0; index < approverPlan.length; index += 1) {
                    const plan = approverPlan[index];
                    // 사용자 목록은 [조회] 전에는 비어 있다(Total 0). 이름으로 조회한 뒤 결과를 기다린다.
                    const findMatches = () => {
                        const found = [];
                        for (let row = 0; row < approverDataset.getRowCount(); row += 1) {
                            if (text(valueAt(approverDataset, row, "userNm"), 40) === plan.name) found.push(row);
                        }
                        return found;
                    };
                    let matches = findMatches();
                    if (matches.length !== 1 && searchNameInput && searchButton?.click) {
                        setControlValue(approverPopup, "userNm", plan.name);
                        searchButton.click();
                        const searchUntil = Date.now() + 20000;
                        await sleep(300);
                        while (Date.now() < searchUntil) {
                            if (dialogInstances().length) {
                                const info = dialogInfo(dialogInstances()[0]);
                                throw new Error(`결재자 '${plan.name}' 조회 중 NEIS 알림이 열려 멈췄습니다. (NEIS 메시지: ${info.message || "내용 없음"})`);
                            }
                            matches = findMatches();
                            if (matches.length) {
                                await sleep(300);
                                matches = findMatches();
                                break;
                            }
                            await sleep(200);
                        }
                    }
                    if (matches.length !== 1) {
                        throw new Error(matches.length
                            ? `결재자 '${plan.name}'이(가) 목록에 ${matches.length}명 있어(동명이인) 상신하지 않았습니다.`
                            : `결재자 '${plan.name}'을(를) NEIS 결재자 목록에서 찾지 못했습니다. 이름을 확인해 주세요.`);
                    }
                    const row = matches[0];
                    if (/부재/.test(datasetRowText(approverDataset, row))
                        && !window.confirm(`결재자 '${plan.name}'님이 NEIS에 부재중으로 표시되어 있습니다.\n그대로 결재선에 넣고 상신할까요?`)) {
                        throw new Error(`결재자 '${plan.name}'님이 부재중이라 상신을 취소했습니다.`);
                    }
                    if (!setControlValue(approverPopup, "rdbCn", plan.roleCode) || String(roleRadio.value) !== plan.roleCode) {
                        throw new Error(`'${plan.name}'의 결재 구분(${plan.roleName})을 선택하지 못했습니다.`);
                    }
                    await sleep(150);
                    approverGrid.selectRows([row]);
                    addButton.click();
                    const added = async () => {
                        const until = Date.now() + 2500;
                        while (Date.now() < until) {
                            if (readSelectedApprovers().length > index) return true;
                            await sleep(150);
                        }
                        return false;
                    };
                    if (!(await added())) {
                        const listElement = document.getElementById(`uuid-${approverGrid.uuid}`);
                        const rowElement = listElement?.querySelector(`[data-rowindex="${row}"]`);
                        const nameElement = [...(rowElement?.querySelectorAll("span,div,td,a") || [])]
                            .find((element) => text(element.innerText || element.textContent, 40) === plan.name);
                        if (!nameElement) throw new Error(`결재자 '${plan.name}' 행을 선택하지 못했습니다.`);
                        nameElement.click();
                        nameElement.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true, view: window }));
                        if (!(await added())) throw new Error(`결재자 '${plan.name}'을(를) 결재선에 추가하지 못했습니다.`);
                    }
                    await sleep(200);
                    const sofar = readSelectedApprovers();
                    if (!matchesPlan(sofar, index + 1)) {
                        throw new Error(`결재선이 예상과 다르게 추가되어 상신하지 않았습니다. (현재: ${describe(sofar)})`);
                    }
                }
            }
            const actualApprovers = readSelectedApprovers();
            if (!matchesPlan(actualApprovers)) {
                throw new Error(`NEIS 결재자 창의 결재선이 저장된 결재선과 달라 상신하지 않았습니다. (현재: ${describe(actualApprovers)})`);
            }

            // 3) 결재선 저장(btn4) → 결재자지정 창 닫힘 확인
            const saveApproverButton = approverPopup.lookup("btn4");
            if (!saveApproverButton?.click) throw new Error("결재선 저장 버튼을 찾지 못했습니다.");
            stage = `결재선 저장(${batch.kind})`;
            saveApproverButton.click();
            await settleDialogs({
                isDone: () => !isRunning(approverPopup),
                quietMs: 600,
                timeoutMs: 15000,
                decide: (info) => {
                    if (info.type === "confirm" && asksToProceed(info.message)) return true;
                    if (info.type === "alert" && /(저장|지정|완료|되었습니다|하였습니다)/.test(info.message) && !/(오류|실패|없습니다|불가)/.test(info.message)) return true;
                    return "결재선 저장 중 NEIS 알림이 열려 상신하지 않았습니다.";
                },
                timeoutError: "결재자 선택 창이 닫히지 않아 상신을 중단했습니다.",
            });
            const currentDraft = appFor(draftAppId);
            if (!currentDraft) throw new Error("결재선 저장 후 기안문서상신 창이 사라져 상신하지 않았습니다. NEIS 목록에서 상태를 확인해 주세요.");
            let draftApprovers = [];
            const draftUntil = Date.now() + 5000;
            while (Date.now() < draftUntil) {
                const draftApproverDataset = safeLookup(currentDraft, "dsSancr");
                draftApprovers = [];
                for (let row = 0; row < (draftApproverDataset?.getRowCount?.() || 0); row += 1) {
                    if (isDraftRow(draftApproverDataset, row)) continue;
                    draftApprovers.push({
                        name: text(valueAt(draftApproverDataset, row, "userNm"), 40),
                        roleName: text(valueAt(draftApproverDataset, row, "atrzScNm"), 20),
                    });
                }
                if (matchesPlan(draftApprovers)) break;
                await sleep(200);
            }
            if (!matchesPlan(draftApprovers)) {
                throw new Error(`NEIS 기안 화면에 저장된 결재선이 정확히 반영되지 않아 상신하지 않았습니다. (기안 화면: ${describe(draftApprovers)})`);
            }

            // 4) [상신] 한 번 → (부재중 경고) → "기안문서상신을 하겠습니까?" → "상신을 완료하였습니다"
            const draftButton = safeLookup(currentDraft, "btnDrft");
            if (!draftButton?.click) throw new Error("상신 버튼을 찾지 못했습니다.");
            let submitConfirmed = false;
            let submitCompleted = false;
            stage = `상신(${batch.kind})`;
            draftButton.click();
            await settleDialogs({
                isDone: () => submitCompleted || (submitConfirmed && !appFor(draftAppId)),
                quietMs: 1500,
                timeoutMs: 45000,
                decide: (info) => {
                    if (/부재/.test(info.message)) {
                        report.warnings.push(`부재중 결재자 안내를 확인하고 상신했습니다: ${info.message}`);
                        return true;
                    }
                    if (info.type === "confirm" && /상신/.test(info.message) && asksToProceed(info.message)) {
                        submitConfirmed = true;
                        return true;
                    }
                    if (info.type === "alert" && /(완료|되었습니다|하였습니다)/.test(info.message) && !/(오류|실패|없습니다|불가)/.test(info.message)) {
                        submitCompleted = true;
                        return true;
                    }
                    return submitConfirmed
                        ? "상신 확인 후 NEIS 알림이 열렸습니다. 다시 실행하지 말고 NEIS 목록에서 결재 상태를 확인해 주세요."
                        : "상신 버튼을 누른 뒤 예상하지 못한 NEIS 알림이 열려 멈췄습니다.";
                },
                timeoutError: "상신 완료를 확인하지 못했습니다. 다시 실행하지 말고 NEIS 목록에서 결재 상태를 확인해 주세요.",
            });
            if (appFor(draftAppId)) {
                const closeButton = ["btnClose", "btnCancel", "btnCls"].map((id) => appFor(draftAppId)?.lookup(id)).find((control) => control?.click);
                if (closeButton) {
                    closeButton.click();
                    await waitForApp(draftAppId, 4000, false);
                }
            }
            await search(instance);
            const verifiedRows = getRows(instance).rows;
            const submittedForBatch = eligibleForSubmission
                .map((row) => verifiedRows.find((candidate) => candidate.application_id === row.application_id))
                .filter((row) => row && row.kind === batch.kind && row.status === "접수" && row.approval_status && row.approval_status !== "미상신")
                .map((row) => row.application_id);
            report.submittedIds.push(...submittedForBatch.map((id) => `${batch.kind}:${id}`));
            if (submittedForBatch.length !== eligibleForSubmission.length) {
                throw new Error("일부 승인요청 상태를 NEIS 목록에서 확인하지 못했습니다. 재실행하지 말고 현재 상태를 확인해 주세요.");
            }
        }
      }
    } catch (error) {
        const internal = error instanceof TypeError || error instanceof ReferenceError;
        report.errors.push(internal
            ? `[${stage}] 단계에서 확장 내부 오류: ${error.message}. 다시 실행하지 말고 NEIS 목록에서 상태를 확인해 주세요.`
            : (error.message || "선택 건 처리 중 오류가 발생했습니다."));
    }

    try {
        // 결석신고를 처리했을 때만 학생 현황의 결석신고 목록을 새로 고친다.
        if (absenceInstance && isRunning(absenceInstance)) {
            useScreen("결석신고");
            await search(absenceInstance);
            report.absence_applications = getRows(absenceInstance).rows;
        }
    } catch (error) {
        report.errors.push("처리 후 상태를 다시 조회하지 못했습니다.");
    }
    return report;
}
