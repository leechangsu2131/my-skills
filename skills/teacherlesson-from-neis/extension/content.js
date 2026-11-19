(() => {
    "use strict";
    const SOURCE = "teacherlesson-from-neis-v1";
    const STORAGE_KEY = "teacherlessonNeisCache";
    const STUDENT_STATUS_KEY = "teacherlessonNeisStudentStatus";
    const POSITION_KEY = "teacherlessonNeisPanelPosition";
    const ROOT_ID = "teacherlesson-from-neis-root";
    if (document.getElementById(ROOT_ID)) return;

    const host = document.createElement("div");
    host.id = ROOT_ID;
    host.style.cssText = "all:initial; position:fixed; right:18px; bottom:18px; z-index:2147483647;";
    document.documentElement.appendChild(host);
    const shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = `
      <style>
        :host { all: initial; }
        * { box-sizing: border-box; }
        .card { width: 318px; max-height: 54vh; overflow: hidden; border: 1px solid #c9dedb; border-radius: 16px; background: #fff; color: #183b3c; box-shadow: 0 14px 40px #154b4a30; font: 13px/1.45 "Malgun Gothic", "Segoe UI", sans-serif; }
        .head { display:flex; align-items:center; gap:9px; padding:11px 12px; background:linear-gradient(110deg,#e7f8f4,#f5efff 78%,#fff); border-bottom:1px solid #e3eeea; cursor:grab; touch-action:none; user-select:none; }
        .head:active { cursor:grabbing; }
        .mark { width:28px;height:28px;display:grid;place-items:center;border-radius:9px;background:linear-gradient(145deg,#0b9f91,#7456c8);color:#fff;font-weight:900; box-shadow:0 4px 10px #167d7850; }
        .titlebox { flex:1; min-width:0; }
        .title { font-size:13px;font-weight:900;color:#183b3c; }
        .status { margin-top:2px;color:#72849a;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
        .icon { border:0;background:transparent;color:#667e82;font-size:17px;line-height:1;cursor:pointer;padding:4px; }
        .body { max-height:calc(54vh - 54px); overflow:auto; padding:9px 10px 10px; }
        .tabs { display:flex; gap:6px; margin-bottom:7px; }
        .tab { flex:1; border:1px solid #dbe8e6; border-radius:8px; padding:6px; background:#fff; color:#66807f; font-family:inherit; font-size:10px; font-weight:700; line-height:1.2; cursor:pointer; }
        .tab.active { border-color:#8ccfc5; background:#e8f8f4; color:#087e73; }
        .panel[hidden] { display:none; }
        .empty { padding:12px 4px;color:#77899e;font-size:11px; }
        .lesson { display:grid;grid-template-columns:44px 1fr;gap:9px;padding:8px 4px;border-bottom:1px solid #eef2f6; }
        .lesson:last-child { border-bottom:0; }
        .period { align-self:start;text-align:center;padding:4px 3px;border-radius:7px;background:#e7f8f4;color:#087e73;font-size:10px;font-weight:900; }
        .subject { color:#264a4b;font-weight:900;font-size:11px; }
        .unit { margin-top:3px;color:#55708c;font-size:10px;font-weight:700; }
        .content { margin-top:3px;color:#344d67;font-size:11px;white-space:pre-wrap;overflow-wrap:anywhere; }
        .foot { display:flex;justify-content:space-between;align-items:center;padding:7px 2px 1px;color:#8a9bad;font-size:9px; }
        .foot a { color:#6a4db6;text-decoration:none;font-weight:800; }
        .student-group { margin:7px 0 10px; }
        .student-list { min-height:32px; }
        .student-heading { display:flex;justify-content:space-between;align-items:center;margin:0 1px 4px;color:#355c60;font-size:10px;font-weight:900; }
        .student-heading span { color:#809496;font-weight:700; }
        .student-row { display:grid;grid-template-columns:minmax(55px,auto) 1fr;gap:6px;align-items:center;padding:5px 6px;margin:3px 0;border-radius:7px;background:#f4f8fb;font-size:10px; }
        .student-name { color:#264a4b;font-weight:900; }
        .student-meta { color:#607b83;overflow-wrap:anywhere; }
        .student-empty { padding:10px 4px;color:#77899e;font-size:10px; }
        .collapsed .body { display:none; }
      </style>
      <section class="card" aria-label="오늘의 수업">
        <header class="head">
          <div class="mark">N</div>
          <div class="titlebox"><div class="title">오늘의 수업</div><div class="status" id="status">주간학습 조회 결과를 기다리는 중</div></div>
          <button class="icon" id="collapse" type="button" title="접기" aria-label="접기">−</button>
        </header>
        <div class="body">
          <div class="tabs" role="tablist" aria-label="오늘 확인할 내용">
            <button class="tab active" id="lessonsTab" type="button" role="tab" aria-selected="true">오늘의 수업</button>
            <button class="tab" id="studentsTab" type="button" role="tab" aria-selected="false">학생 현황</button>
          </div>
          <div id="lessonsPanel" class="panel" role="tabpanel">
            <div id="lessons" class="empty">주간학습안내작성 화면에서 조회하면 수업내용이 자동으로 동기화됩니다.</div>
          </div>
          <div id="studentsPanel" class="panel" role="tabpanel" hidden>
            <div id="students" class="student-empty">학생 현황을 보려면 확장 팝업에서 ‘오늘 출결·결석·체험학습 현황 조회’를 실행하세요.</div>
          </div>
          <div class="foot"><span id="updated">Chrome 로컬 저장</span><a href="#" id="openViewer">전체 보기 ↗</a></div>
        </div>
      </section>`;

    const card = shadow.querySelector(".card");
    const status = shadow.querySelector("#status");
    const lessonHost = shadow.querySelector("#lessons");
    const updated = shadow.querySelector("#updated");
    const dragHandle = shadow.querySelector(".head");
    const studentsHost = shadow.querySelector("#students");
    const lessonsTab = shadow.querySelector("#lessonsTab");
    const studentsTab = shadow.querySelector("#studentsTab");
    const lessonsPanel = shadow.querySelector("#lessonsPanel");
    const studentsPanel = shadow.querySelector("#studentsPanel");
    let progressStatus = "";

    function setPanelView(view) {
        const showStudents = view === "students";
        lessonsTab.classList.toggle("active", !showStudents);
        lessonsTab.setAttribute("aria-selected", String(!showStudents));
        studentsTab.classList.toggle("active", showStudents);
        studentsTab.setAttribute("aria-selected", String(showStudents));
        lessonsPanel.hidden = showStudents;
        studentsPanel.hidden = !showStudents;
    }
    lessonsTab.addEventListener("click", () => setPanelView("lessons"));
    studentsTab.addEventListener("click", () => setPanelView("students"));

    function clampPanelPosition(left, top) {
        const rect = host.getBoundingClientRect();
        return {
            left: Math.max(0, Math.min(Number(left) || 0, window.innerWidth - rect.width)),
            top: Math.max(0, Math.min(Number(top) || 0, window.innerHeight - rect.height)),
        };
    }

    chrome.storage.local.get(POSITION_KEY).then((data) => {
        const position = data[POSITION_KEY];
        if (!Number.isFinite(position?.left) || !Number.isFinite(position?.top)) return;
        const bounded = clampPanelPosition(position.left, position.top);
        host.style.left = `${bounded.left}px`;
        host.style.top = `${bounded.top}px`;
        host.style.right = "auto";
        host.style.bottom = "auto";
    });

    let dragState = null;
    dragHandle.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || event.target.closest("button, a")) return;
        const rect = host.getBoundingClientRect();
        dragState = { pointerId: event.pointerId, offsetX: event.clientX - rect.left, offsetY: event.clientY - rect.top };
        host.style.left = `${rect.left}px`;
        host.style.top = `${rect.top}px`;
        host.style.right = "auto";
        host.style.bottom = "auto";
        dragHandle.setPointerCapture(event.pointerId);
        event.preventDefault();
    });
    dragHandle.addEventListener("pointermove", (event) => {
        if (!dragState || event.pointerId !== dragState.pointerId) return;
        const bounded = clampPanelPosition(event.clientX - dragState.offsetX, event.clientY - dragState.offsetY);
        host.style.left = `${bounded.left}px`;
        host.style.top = `${bounded.top}px`;
    });
    const finishDrag = (event) => {
        if (!dragState || event.pointerId !== dragState.pointerId) return;
        dragState = null;
        const rect = host.getBoundingClientRect();
        const position = clampPanelPosition(rect.left, rect.top);
        chrome.storage.local.set({ [POSITION_KEY]: position });
    };
    dragHandle.addEventListener("pointerup", finishDrag);
    dragHandle.addEventListener("pointercancel", finishDrag);
    window.addEventListener("resize", () => {
        if (!host.style.left || !host.style.top) return;
        const rect = host.getBoundingClientRect();
        const bounded = clampPanelPosition(rect.left, rect.top);
        host.style.left = `${bounded.left}px`;
        host.style.top = `${bounded.top}px`;
        chrome.storage.local.set({ [POSITION_KEY]: bounded });
    });

    shadow.querySelector("#openViewer").addEventListener("click", (event) => {
        event.preventDefault();
        chrome.runtime.sendMessage({ type: "OPEN_VIEWER" });
    });

    function todayIso() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    }

    function el(tag, className, text) {
        const node = document.createElement(tag);
        node.className = className;
        node.textContent = text || "";
        return node;
    }

    function render(cache, overrideStatus = "") {
        const records = (cache?.records || []).filter((record) => record.date === todayIso());
        lessonHost.replaceChildren();
        if (!records.length) {
            lessonHost.className = "empty";
            lessonHost.textContent = "오늘 수업 자료가 없습니다. 주간학습안내에서 조회하면 자동으로 불러옵니다.";
        } else {
            lessonHost.className = "lessons";
            for (const record of records) {
                const row = el("article", "lesson", "");
                row.append(el("div", "period", `${record.period}교시`));
                const detail = el("div", "detail", "");
                detail.append(el("div", "subject", record.subject));
                if (record.unit) detail.append(el("div", "unit", record.unit));
                if (record.content) detail.append(el("div", "content", record.content));
                row.append(detail);
                lessonHost.append(row);
            }
        }
        if (!overrideStatus && !progressStatus) status.textContent = records.length
            ? `오늘 ${records.length}개 수업 · NEIS에서 자동 동기화`
            : "주간학습 조회 결과를 기다리는 중";
        else if (overrideStatus) status.textContent = overrideStatus;
        updated.textContent = cache?.updatedAt
            ? `갱신 ${new Intl.DateTimeFormat("ko-KR", { hour: "2-digit", minute: "2-digit" }).format(new Date(cache.updatedAt))}`
            : "로컬 저장";
    }

    function renderStudents(cache) {
        const today = todayIso();
        const attendance = (cache?.attendance || []).filter((row) => row.date === today);
        const absence = (cache?.absenceApplications || []).filter((row) => row.date <= today && row.end_date >= today);
        const fieldtrip = (cache?.experientialApplications || []).filter((row) => row.date <= today && row.end_date >= today);
        studentsHost.replaceChildren();

        if (!cache) {
            studentsHost.className = "student-empty";
            studentsHost.textContent = "학생 현황을 보려면 확장 팝업에서 ‘오늘 출결·결석·체험학습 현황 조회’를 실행하세요.";
            return;
        }
        studentsHost.className = "student-list";

        const groups = [
            ["오늘 출결", attendance],
            ["결석 신고서", absence],
            ["체험학습", fieldtrip],
        ];
        for (const [title, rows] of groups) {
            const section = document.createElement("section");
            section.className = "student-group";
            const heading = document.createElement("div");
            heading.className = "student-heading";
            heading.append(el("strong", "", title), el("span", "", `${rows.length}건`));
            section.append(heading);
            if (!rows.length) {
                section.append(el("div", "student-empty", "해당 학생 없음"));
            } else {
                for (const row of rows.slice(0, 80)) {
                    const item = document.createElement("div");
                    item.className = "student-row";
                    const name = el("span", "student-name", row.student);
                    const details = [row.class_name, row.kind];
                    if (title !== "오늘 출결") {
                        const range = row.date === row.end_date ? row.date : `${row.date} ~ ${row.end_date}`;
                        details.push(range, row.status, row.approval_status);
                    } else if (row.count > 1) details.push(`${row.count}일`);
                    item.append(name, el("span", "student-meta", details.filter(Boolean).join(" · ")));
                    section.append(item);
                }
                if (rows.length > 80) section.append(el("div", "student-empty", `외 ${rows.length - 80}명 · 전체 보기에서 확인`));
            }
            studentsHost.append(section);
        }
        const importedAt = cache.updatedAt
            ? new Intl.DateTimeFormat("ko-KR", { hour: "2-digit", minute: "2-digit" }).format(new Date(cache.updatedAt))
            : "시간 미상";
        studentsHost.append(el("div", "student-empty", `마지막 조회 ${importedAt} · 다시 가져오기로 갱신`));
    }

    shadow.querySelector("#collapse").addEventListener("click", (event) => {
        card.classList.toggle("collapsed");
        event.currentTarget.textContent = card.classList.contains("collapsed") ? "+" : "−";
        event.currentTarget.title = card.classList.contains("collapsed") ? "펼치기" : "접기";
    });

    chrome.storage.local.get([STORAGE_KEY, STUDENT_STATUS_KEY]).then((data) => {
        render(data[STORAGE_KEY]);
        renderStudents(data[STUDENT_STATUS_KEY]);
    });
    chrome.storage.onChanged.addListener((changes, area) => {
        if (area === "local" && changes[STORAGE_KEY]) render(changes[STORAGE_KEY].newValue);
        if (area === "local" && changes[STUDENT_STATUS_KEY]) renderStudents(changes[STUDENT_STATUS_KEY].newValue);
    });

    window.addEventListener("message", (event) => {
        const message = event.data;
        if (event.source !== window || message?.source !== SOURCE) return;
        if (message.type === "blocked") {
            progressStatus = message.payload?.message || "미저장 수업 변경 때문에 자동 동기화를 건너뛰었습니다.";
            status.textContent = progressStatus;
            return;
        }
        if (message.type === "progress") {
            progressStatus = message.payload?.message || "주간 수업자료를 동기화하고 있습니다…";
            status.textContent = progressStatus;
            return;
        }
        if (message.type === "week-cache-check") {
            chrome.runtime.sendMessage({ type: "CHECK_WEEK_CACHE", weeks: message.payload?.weeks || [] })
                .then((result) => window.postMessage({
                    source: SOURCE,
                    type: "week-cache-result",
                    payload: { requestId: message.payload?.requestId, ...(result || {}) },
                }, location.origin))
                .catch(() => window.postMessage({
                    source: SOURCE,
                    type: "week-cache-result",
                    payload: { requestId: message.payload?.requestId, ok: false, fresh: {} },
                }, location.origin));
            return;
        }
        if (message.type !== "lessons") return;
        status.textContent = "수업내용을 로컬에 저장하는 중…";
        chrome.runtime.sendMessage({ type: "AUTO_SYNC_LESSONS", payload: message.payload })
            .then((result) => {
                if (result?.ok) {
                    if (!progressStatus) status.textContent = `오늘 수업 ${result.imported}개 · Chrome에 저장됨`;
                } else {
                    progressStatus = result?.error || "자동 동기화에 실패했습니다.";
                    status.textContent = progressStatus;
                }
            })
            .catch(() => { status.textContent = "자동 동기화 연결에 실패했습니다."; });
    });

    window.postMessage({ source: SOURCE, type: "reader-ready" }, location.origin);
})();
