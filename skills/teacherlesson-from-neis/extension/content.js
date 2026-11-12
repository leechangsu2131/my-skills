(() => {
    "use strict";
    const SOURCE = "teacherlesson-from-neis-v1";
    const STORAGE_KEY = "teacherlessonNeisCache";
    const ROOT_ID = "teacherlesson-from-neis-root";
    if (document.getElementById(ROOT_ID)) return;

    const host = document.createElement("div");
    host.id = ROOT_ID;
    host.style.cssText = "all:initial; position:fixed; left:18px; bottom:18px; z-index:2147483647;";
    document.documentElement.appendChild(host);
    const shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = `
      <style>
        :host { all: initial; }
        * { box-sizing: border-box; }
        .card { width: 318px; max-height: 54vh; overflow: hidden; border: 1px solid #d8e4ef; border-radius: 16px; background: #fff; color: #18324d; box-shadow: 0 14px 40px #17314e30; font: 13px/1.45 "Malgun Gothic", "Segoe UI", sans-serif; }
        .head { display:flex; align-items:center; gap:9px; padding:11px 12px; background:linear-gradient(110deg,#f2f8ff,#fff); border-bottom:1px solid #edf1f5; }
        .mark { width:28px;height:28px;display:grid;place-items:center;border-radius:9px;background:#075bb4;color:#fff;font-weight:900; }
        .titlebox { flex:1; min-width:0; }
        .title { font-size:13px;font-weight:900;color:#142f4d; }
        .status { margin-top:2px;color:#72849a;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
        .icon { border:0;background:transparent;color:#74859a;font-size:17px;line-height:1;cursor:pointer;padding:4px; }
        .body { max-height:calc(54vh - 54px); overflow:auto; padding:9px 10px 10px; }
        .empty { padding:12px 4px;color:#77899e;font-size:11px; }
        .lesson { display:grid;grid-template-columns:44px 1fr;gap:9px;padding:8px 4px;border-bottom:1px solid #eef2f6; }
        .lesson:last-child { border-bottom:0; }
        .period { align-self:start;text-align:center;padding:4px 3px;border-radius:7px;background:#eef6ff;color:#075bb4;font-size:10px;font-weight:900; }
        .subject { color:#264563;font-weight:900;font-size:11px; }
        .unit { margin-top:3px;color:#55708c;font-size:10px;font-weight:700; }
        .content { margin-top:3px;color:#344d67;font-size:11px;white-space:pre-wrap;overflow-wrap:anywhere; }
        .foot { display:flex;justify-content:space-between;align-items:center;padding:7px 2px 1px;color:#8a9bad;font-size:9px; }
        .foot a { color:#075bb4;text-decoration:none;font-weight:800; }
        .collapsed .body { display:none; }
      </style>
      <section class="card" aria-label="오늘의 수업">
        <header class="head">
          <div class="mark">N</div>
          <div class="titlebox"><div class="title">오늘의 수업</div><div class="status" id="status">주간학습 조회 결과를 기다리는 중</div></div>
          <button class="icon" id="collapse" type="button" title="접기" aria-label="접기">−</button>
        </header>
        <div class="body">
          <div id="lessons" class="empty">주간학습안내작성 화면에서 조회하면 수업내용이 자동으로 동기화됩니다.</div>
          <div class="foot"><span id="updated">로컬 저장</span><a href="http://127.0.0.1:5101" target="_blank" rel="noreferrer">전체 보기 ↗</a></div>
        </div>
      </section>`;

    const card = shadow.querySelector(".card");
    const status = shadow.querySelector("#status");
    const lessonHost = shadow.querySelector("#lessons");
    const updated = shadow.querySelector("#updated");
    let progressStatus = "";

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

    shadow.querySelector("#collapse").addEventListener("click", (event) => {
        card.classList.toggle("collapsed");
        event.currentTarget.textContent = card.classList.contains("collapsed") ? "+" : "−";
        event.currentTarget.title = card.classList.contains("collapsed") ? "펼치기" : "접기";
    });

    chrome.storage.local.get(STORAGE_KEY).then((data) => render(data[STORAGE_KEY]));
    chrome.storage.onChanged.addListener((changes, area) => {
        if (area === "local" && changes[STORAGE_KEY]) render(changes[STORAGE_KEY].newValue);
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
                    if (!progressStatus) status.textContent = result.viewer_updated
                        ? `오늘 수업 ${result.imported}개 · 자동 동기화 완료`
                        : `오늘 수업 ${result.imported}개 · 브라우저에 저장됨 (뷰어 연결 확인 필요)`;
                } else {
                    progressStatus = result?.error || "자동 동기화에 실패했습니다.";
                    status.textContent = progressStatus;
                }
            })
            .catch(() => { status.textContent = "자동 동기화 연결에 실패했습니다."; });
    });

    window.postMessage({ source: SOURCE, type: "reader-ready" }, location.origin);
})();
