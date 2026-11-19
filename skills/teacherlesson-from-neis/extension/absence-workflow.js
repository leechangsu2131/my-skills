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
    const appId = "edu/sa/eds/eaa/ae/eds_eaaae03_m01";
    const detailAppId = "edu/sa/eds/eaa/ae/eds_eaaae03_p01";
    const draftAppId = "edu/cm/wam/woa/pm/wam_woapm07_p00";
    const approverAppId = "edu/cm/wam/woa/pm/wam_woapm07_p04";
    const menuId = "AMEDS40531";
    const appsFor = (targetId) => platform.getAllRunningAppInstances().filter((instance) => instance?.app?.id === targetId);
    const appFor = (targetId) => appsFor(targetId)[0] || null;
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
            throw new Error("결석신고서 목록 화면이 여러 개 열려 있습니다. 목록 창을 하나만 남긴 뒤 다시 처리대상을 조회해 주세요.");
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
        if (typeof window.openMdiMenu === "function") {
            window.openMdiMenu(menuId);
            const opened = await waitForVisibleList(10000);
            if (opened) return opened;
        }
        throw new Error("결석신고서 목록 화면을 활성화하지 못했습니다. NEIS에서 목록 탭을 연 뒤 다시 시도해 주세요.");
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
        if (!button?.click) throw new Error("결석신고서 조회 버튼을 찾지 못했습니다.");
        const started = performance.now();
        button.click();
        for (let attempt = 0; attempt < 50; attempt += 1) {
            const completed = performance.getEntriesByType("resource").some((entry) => {
                if (entry.startTime < started || entry.responseEnd <= 0) return false;
                try { return new URL(entry.name, location.href).pathname.endsWith("/eds_eaa_ae03_002.do"); } catch (_) { return false; }
            });
            if (completed) return;
            await sleep(150);
        }
        throw new Error("결석신고서 조회 응답을 확인하지 못했습니다.");
    }
    function getRows(instance) {
        const dataset = instance.lookup("dsStdntListForAbe");
        if (!dataset?.getRowCount) throw new Error("결석신고서 데이터셋을 찾지 못했습니다.");
        const rows = [];
        for (let row = 0; row < dataset.getRowCount() && rows.length < 1000; row += 1) {
            const applicationId = text(valueAt(dataset, row, "abeDclrId"), 80);
            if (!applicationId) continue;
            const startDate = date(valueAt(dataset, row, "abeBgngDt"));
            const endDate = date(valueAt(dataset, row, "abeEndDt")) || startDate;
            const status = text(valueAt(dataset, row, "eduActPrcsStsNm"), 30);
            const approvalStatus = text(valueAt(dataset, row, "atrzStsNm"), 30);
            const namedClass = text(valueAt(dataset, row, "clsNm"), 24);
            const grade = text(valueAt(dataset, row, "grd"), 8);
            const classNo = text(valueAt(dataset, row, "clsNo"), 8);
            rows.push({
                row,
                application_id: applicationId,
                start_date: startDate,
                end_date: endDate,
                student: text(valueAt(dataset, row, "stuFlnm"), 50),
                class_name: namedClass || [grade && `${grade}학년`, classNo && `${classNo}반`].filter(Boolean).join(" "),
                kind: "결석신고",
                absence_category_code: text(valueAt(dataset, row, "abeDclrScCd"), 2),
                absence_category: text(valueAt(dataset, row, "abeDclrScNm"), 40),
                reason: text(valueAt(dataset, row, "abeRsnCn"), 500),
                teacher_reason: exactText(valueAt(dataset, row, "shlOpiCn")),
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
    const selectedIds = approvalBatches.flatMap((batch) => batch.applicationIds);
    const selectedIdSet = new Set(selectedIds);
    if (!selectedIds.length) return { ok: false, error: "처리할 신청을 선택해 주세요." };
    if (approvalBatches.some((batch) => !batch.kind || !batch.applicationIds.length || !batch.approvers.length)
        || selectedIdSet.size !== selectedIds.length
        || new Set(approvalBatches.map((batch) => batch.kind)).size !== approvalBatches.length) {
        return { ok: false, error: "신청 유형별 처리 대상과 저장 결재선이 올바르지 않습니다." };
    }
    const expectedKindById = new Map(approvalBatches.flatMap((batch) => batch.applicationIds.map((id) => [id, batch.kind])));
    const expectedCategoryCodeById = new Map(approvalBatches.flatMap((batch) => batch.applicationIds.map((id) => [id, batch.absenceCategoryCodes[id] || ""])));
    const expectedTeacherReasonById = new Map(approvalBatches.flatMap((batch) => batch.applicationIds.map((id) => [id, exactText(batch.teacherReasons[id] ?? "")])));

    const report = { ok: true, receiptIds: [], submittedIds: [], errors: [], absence_applications: [] };
    let instance = null;
    try {
        instance = await openListApp();
        if (appsFor(appId).length !== 1) throw new Error("결석신고서 목록 화면이 하나인지 확인하지 못해 처리를 중단했습니다.");
        if (appsFor(detailAppId).length || appsFor(draftAppId).length || appsFor(approverAppId).length) {
            throw new Error("결석신고서 상세창 또는 결재창이 이미 열려 있습니다. 창을 정리한 뒤 처리대상을 다시 조회해 주세요.");
        }
        if (!setControlValue(instance, "dtAbeBgngYmd", monthStart.replace(/-/g, ""))
            || !setControlValue(instance, "dtAbeEndYmd", monthEnd.replace(/-/g, ""))) {
            throw new Error("결석신고서 조회기간을 설정하지 못했습니다.");
        }
        await search(instance);
        let { rows } = getRows(instance);
        const rowCounts = new Map();
        for (const row of rows) rowCounts.set(row.application_id, (rowCounts.get(row.application_id) || 0) + 1);
        const selectedRows = selectedIds.map((id) => rows.find((row) => row.application_id === id));
        if (selectedRows.some((row, index) => !row || rowCounts.get(selectedIds[index]) !== 1)) {
            throw new Error("조회 후 신청 목록이 달라졌거나 식별값이 중복되어 실행을 중단했습니다. 처리 대상을 다시 확인해 주세요.");
        }
        if (selectedRows.some((row) => row.kind !== expectedKindById.get(row.application_id))) {
            throw new Error("NEIS 신청 유형이 저장 결재선에 연결된 유형과 달라 처리를 중단했습니다.");
        }
        if (selectedRows.some((row) => !(row.status === "접수대기" || (row.status === "접수" && row.approval_status === "미상신")))) {
            throw new Error("선택한 신청의 처리 상태가 바뀌었습니다. 최신 목록을 다시 확인해 주세요.");
        }

        if (selectedRows.some((row) => !["01", "02", "03", "04"].includes(expectedCategoryCodeById.get(row.application_id)))) {
            throw new Error("선택한 신청의 결석 구분을 확인해 주세요. 기본값은 질병결석이며 행별로 바꿀 수 있습니다.");
        }
            if (selectedRows.some((row) => typeof expectedTeacherReasonById.get(row.application_id) !== "string")) {
                throw new Error("선택한 신청의 담임/교사 결석 사유를 확인해 주세요.");
            }

        function detailRecord(detail) {
            const dataset = detail?.lookup("dsStdntListForAbe");
            if (!dataset?.getRowCount?.()) return null;
            return {
                application_id: text(valueAt(dataset, 0, "abeDclrId"), 80),
                student: text(valueAt(dataset, 0, "stuFlnm"), 50),
                start_date: date(valueAt(dataset, 0, "abeBgngDt")),
                end_date: date(valueAt(dataset, 0, "abeEndDt")) || date(valueAt(dataset, 0, "abeBgngDt")),
                status: text(valueAt(dataset, 0, "eduActPrcsStsNm"), 30),
                absence_category_code: text(valueAt(dataset, 0, "abeDclrScCd"), 2),
                reason: text(valueAt(dataset, 0, "abeRsnCn"), 500),
                teacher_reason: exactText(valueAt(dataset, 0, "shlOpiCn")),
            };
        }

        async function openDetailForSelected(selected, row) {
            const existing = appsFor(detailAppId);
            if (existing.length > 1) throw new Error("결석신고서 상세창이 여러 개 열려 있습니다. 창을 하나만 남긴 뒤 다시 조회해 주세요.");
            if (existing.length === 1) {
                if (detailRecord(existing[0])?.application_id !== selected.application_id) {
                    throw new Error("다른 신청의 상세창이 열려 있어 선택 건을 처리하지 않았습니다. 상세창을 닫은 뒤 다시 시도해 주세요.");
                }
                return existing[0];
            }

            const grid = instance.lookup("grdMain");
            if (!grid?.selectRows || typeof cpr.events?.CGridMouseEvent !== "function") {
                throw new Error("결석신고서 목록에서 상세창을 안전하게 열 수 없습니다.");
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
                if (opened.length > 1) throw new Error("결석신고서 상세창이 중복으로 열려 처리를 멈췄습니다.");
                if (opened.length === 1) {
                    if (detailRecord(opened[0])?.application_id !== selected.application_id) {
                        throw new Error("NEIS에서 다른 신청의 상세창이 열려 선택 건을 처리하지 않았습니다.");
                    }
                    return opened[0];
                }
                await sleep(150);
            }
            throw new Error("선택한 결석신고서 상세 화면을 열지 못했습니다.");
        }

        for (const selected of selectedRows.filter((row) => row.status === "접수대기")) {
            if (appsFor(appId).length !== 1 || appsFor(detailAppId).length) {
                throw new Error("처리 도중 결석신고서 목록/상세 창이 바뀌거나 중복되어 나머지 처리를 멈췄습니다.");
            }
            const current = getRows(instance);
            const row = current.rows.find((item) => item.application_id === selected.application_id);
            if (!row || row.status !== "접수대기") throw new Error("접수 전 대상 상태가 바뀌어 나머지 처리를 중단했습니다.");
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
            const saveButton = detail.lookup("btnUpdateSave");
            if (!statusControl || !saveButton?.click) throw new Error("접수 상태 저장 컨트롤을 찾지 못했습니다.");
            if (!setControlValue(detail, "cmbEduActPrcsStsCd", "02")) throw new Error("접수 상태를 설정하지 못했습니다.");
            saveButton.click();
            await sleep(1200);
            if (appFor("app/cmn/confirm") || appFor("app/cmn/alert")) {
                throw new Error("NEIS 확인 창이 열렸습니다. 화면에서 확인한 뒤 처리대상을 다시 조회해 주세요.");
            }
            const closeButton = detail.lookup("btnCancel");
            if (closeButton?.click && appFor(detailAppId)) closeButton.click();
            await waitForApp(detailAppId, 5000, false);
            if (appFor(detailAppId)) throw new Error("결석신고서 상세 화면이 닫히지 않아 나머지 처리를 중단했습니다.");
            await search(instance);
            const refreshed = getRows(instance).rows.find((item) => item.application_id === selected.application_id);
            if (!refreshed || refreshed.status !== "접수"
                || refreshed.absence_category_code !== expectedCategoryCode
                || refreshed.teacher_reason !== expectedTeacherReasonById.get(selected.application_id)) {
                throw new Error("접수 저장 후 상태·결석 구분·담임/교사 사유를 확인하지 못했습니다. 승인요청은 보내지 않고 중단했습니다.");
            }
            report.receiptIds.push(selected.application_id);
        }

        for (const batch of approvalBatches) {
            if (appsFor(appId).length !== 1 || appsFor(detailAppId).length
                || appsFor(draftAppId).length || appsFor(approverAppId).length) {
                throw new Error("상신 전 결석신고서 목록이나 결재 창이 중복/변경되어 처리를 멈췄습니다.");
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
                const rowId = text(valueAt(currentData.dataset, selected.row, "abeDclrId"), 80);
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
                    const applicationId = text(valueAt(currentData.dataset, row, "abeDclrId"), 80);
                    if (!expectedIds.has(applicationId)) throw new Error("선택하지 않은 신청이 승인요청 대상으로 체크되어 처리를 중단했습니다.");
                    checkedIds.add(applicationId);
                }
                if (checkedIds.size === expectedIds.size && [...expectedRows].every((row) => checkedRows.has(row))) break;
                await sleep(100);
            }
            if (checkedIds.size !== expectedIds.size || [...expectedRows].some((row) => !grid.getCheckRowIndices().includes(row))) {
                throw new Error("그리드에서 선택한 승인요청 대상을 확인하지 못해 상신하지 않았습니다.");
            }
            if (appsFor(draftAppId).length || appsFor(approverAppId).length) {
                throw new Error("기존 결재창이 열려 있어 중복 상신을 막았습니다. 창의 상태를 확인한 뒤 다시 조회해 주세요.");
            }
            const submitButton = instance.lookup("btnUpdateCancel3");
            if (!submitButton?.click) throw new Error("승인요청 버튼을 찾지 못했습니다.");
            submitButton.click();
            const draft = await waitForApp(draftAppId, 10000);
            if (!draft || appsFor(draftAppId).length !== 1) throw new Error("승인요청 결재선 화면이 하나인지 확인하지 못했습니다. NEIS에서 처리 상태를 확인해 주세요.");
            const selectApproversButton = draft.lookup("btnSelectSancr");
            if (!selectApproversButton?.click) throw new Error("결재자 지정 화면을 열지 못했습니다.");
            selectApproversButton.click();
            const approverPopup = await waitForApp(approverAppId, 10000);
            if (!approverPopup || appsFor(approverAppId).length !== 1) throw new Error("결재자 선택 창이 하나인지 확인하지 못했습니다.");
            const approverDataset = approverPopup.lookup("dsMain");
            const selectedApproverDataset = approverPopup.lookup("dsParam");
            const approverGrid = approverPopup.lookup("grdUserListFrom");
            const selectedApproverGrid = approverPopup.lookup("grdUserListTo");
            const addButton = approverPopup.lookup("btn1");
            const removeButton = approverPopup.lookup("btn15");
            if (!approverDataset?.getRowCount || !selectedApproverDataset?.getRowCount
                || !approverGrid?.selectRows || !selectedApproverGrid?.setCheckRowIndex
                || !selectedApproverGrid?.getCheckRowIndices || !addButton?.click || !removeButton?.click) {
                throw new Error("결재자 목록, 현재 결재선 또는 추가·삭제 컨트롤을 찾지 못했습니다.");
            }
            const isDraftRow = (dataset, row) => {
                const roleName = text(valueAt(dataset, row, "atrzScNm"), 20);
                const roleCode = text(valueAt(dataset, row, "atrzScCd"), 4);
                const sequence = Number(valueAt(dataset, row, "atrzSeqSn"));
                return roleName === "기안" || (roleCode === "1" && sequence === 0);
            };
            const readSelectedApprovers = () => {
                const names = [];
                for (let row = 0; row < selectedApproverDataset.getRowCount(); row += 1) {
                    if (isDraftRow(selectedApproverDataset, row)) continue;
                    names.push(text(valueAt(selectedApproverDataset, row, "userNm"), 40));
                }
                return names;
            };
            const currentApprovers = readSelectedApprovers();
            const alreadyExact = currentApprovers.length === batch.approvers.length
                && currentApprovers.every((name, index) => name === batch.approvers[index]);
            if (currentApprovers.length && !alreadyExact) {
                const rowsToRemove = [];
                for (let row = 0; row < selectedApproverDataset.getRowCount(); row += 1) {
                    if (!isDraftRow(selectedApproverDataset, row)) rowsToRemove.push(row);
                }
                selectedApproverGrid.clearAllCheck?.();
                for (const row of rowsToRemove) selectedApproverGrid.setCheckRowIndex(row, true);
                const checkedRows = new Set(selectedApproverGrid.getCheckRowIndices());
                if (rowsToRemove.some((row) => !checkedRows.has(row))
                    || checkedRows.size !== rowsToRemove.length
                    || [...checkedRows].some((row) => !rowsToRemove.includes(row))) {
                    throw new Error("기안자 행을 보존하면서 기존 결재자만 선택하지 못해 상신을 중단했습니다.");
                }
                removeButton.click();
                await sleep(300);
                if (readSelectedApprovers().length) {
                    throw new Error("기존 결재자를 지우지 못해 저장된 결재선을 추가하지 않았습니다.");
                }
            }
            if (!alreadyExact) {
                for (const name of batch.approvers) {
                    const matches = [];
                    for (let row = 0; row < approverDataset.getRowCount(); row += 1) {
                        if (text(valueAt(approverDataset, row, "userNm"), 40) === name) matches.push(row);
                    }
                    if (matches.length !== 1) throw new Error("저장된 결재자를 정확히 하나 찾지 못했습니다. 결재선 설정을 확인해 주세요.");
                    const row = matches[0];
                    const listElement = document.getElementById(`uuid-${approverGrid.uuid}`);
                    const rowElement = listElement?.querySelector(`[data-rowindex="${row}"]`);
                    const nameElement = [...(rowElement?.querySelectorAll("span,div,td,a") || [])].find((element) => text(element.innerText || element.textContent, 40) === name);
                    if (!nameElement) throw new Error("저장된 결재자 행을 선택하지 못했습니다.");
                    approverGrid.selectRows([row]);
                    nameElement.click();
                    nameElement.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true, view: window }));
                    addButton.click();
                    await sleep(500);
                }
            }
            const actualApprovers = readSelectedApprovers();
            if (actualApprovers.length !== batch.approvers.length
                || actualApprovers.some((name, index) => name !== batch.approvers[index])) {
                throw new Error("NEIS 결재자 창에 저장된 결재자가 순서대로 지정되지 않아 상신하지 않았습니다.");
            }
            const saveApproverButton = approverPopup.lookup("btn4");
            if (!saveApproverButton?.click) throw new Error("결재선을 지정할 수 없습니다.");
            saveApproverButton.click();
            await waitForApp(approverAppId, 5000, false);
            if (appFor(approverAppId)) throw new Error("결재자 선택 창이 닫히지 않아 상신을 중단했습니다.");
            const currentDraft = appFor(draftAppId);
            const draftApproverDataset = currentDraft?.lookup("dsSancr");
            if (!draftApproverDataset?.getRowCount) throw new Error("결재자 지정 후 기안 화면의 결재선 데이터를 확인하지 못했습니다.");
            const draftApprovers = [];
            for (let row = 0; row < draftApproverDataset.getRowCount(); row += 1) {
                const roleName = text(valueAt(draftApproverDataset, row, "atrzScNm"), 20);
                const roleCode = text(valueAt(draftApproverDataset, row, "atrzScCd"), 4);
                const sequence = Number(valueAt(draftApproverDataset, row, "atrzSeqSn"));
                if (roleName === "기안" || (roleCode === "1" && sequence === 0)) continue;
                draftApprovers.push(text(valueAt(draftApproverDataset, row, "sancrUserNm"), 40));
            }
            if (draftApprovers.length !== batch.approvers.length
                || draftApprovers.some((name, index) => name !== batch.approvers[index])) {
                throw new Error("NEIS 기안 화면에 저장된 결재선이 정확히 반영되지 않아 상신하지 않았습니다.");
            }
            const draftButton = currentDraft?.lookup("btnDrft");
            if (!draftButton?.click) throw new Error("상신 버튼을 찾지 못했습니다.");
            draftButton.click();
            await sleep(1800);
            if (appFor("app/cmn/confirm") || appFor("app/cmn/alert")) {
                throw new Error("NEIS 확인 창이 열려 있습니다. 화면에서 확인한 뒤 상태를 다시 조회해 주세요.");
            }
            await waitForApp(draftAppId, 6000, false);
            if (appFor(draftAppId)) throw new Error("상신 화면이 닫히지 않아 완료 여부를 확인하지 못했습니다.");
            await search(instance);
            const verifiedRows = getRows(instance).rows;
            const submittedForBatch = eligibleForSubmission
                .map((row) => verifiedRows.find((candidate) => candidate.application_id === row.application_id))
                .filter((row) => row && row.kind === batch.kind && row.status === "접수" && row.approval_status && row.approval_status !== "미상신")
                .map((row) => row.application_id);
            report.submittedIds.push(...submittedForBatch);
            if (submittedForBatch.length !== eligibleForSubmission.length) {
                throw new Error("일부 승인요청 상태를 NEIS 목록에서 확인하지 못했습니다. 재실행하지 말고 현재 상태를 확인해 주세요.");
            }
        }
    } catch (error) {
        report.errors.push(error.message || "선택 건 처리 중 오류가 발생했습니다.");
    }

    try {
        instance = instance || appFor(appId);
        if (instance) {
            await search(instance);
            report.absence_applications = getRows(instance).rows;
        }
    } catch (error) {
        report.errors.push("처리 후 상태를 다시 조회하지 못했습니다.");
    }
    return report;
}
