(function () {
  "use strict";

  const STORAGE_KEYS = {
    template: "jbeDutyApiTemplate",
    endpoint: "jbeDutyApiEndpoint",
    origin: "jbeDutyApiOrigin",
    capturedAt: "jbeDutyApiCapturedAt",
    autoLoad: "jbeDutyAutoLoad",
    targetNames: "jbeDutyTargetNames",
    includePending: "jbeDutyIncludePending",
    panelPosition: "jbeDutyPanelPosition",
    displayMode: "jbeDutyDisplayMode",
    cachePrefix: "jbeDutyCacheV15:"
  };

  const APPROVED = "승인완료";
  const PENDING_LABEL = "결재중";
  const DEFAULT_ENDPOINT = "/srv_mym_mm01_001.do";
  const CACHE_TTL_MS = 10 * 60 * 1000;
  const MAX_CELL_LINES = 4;
  const DISPLAY_MODES = {
    academic: "academic",
    duty: "duty"
  };

  // v1.3부터 전북 전용 기본 조회값을 사용하지 않는다.
  // 전체 시도교육청에서 동작하도록 사용자가 접속한 나이스에서 일일근무상황조회를 한 번 실행하면
  // 해당 시도교육청/사용자/부서 기준 조회정보를 현재 접속 도메인별로 저장한다.
  const HOOK_SOURCE = "NEIS_DUTY_HOOK";
  const LEGACY_HOOK_SOURCE = "JBE_NEIS_DUTY_HOOK";
  const LEGACY_JBE_ORIGIN = "https://jbe.neis.go.kr";

  const state = {
    initialized: false,
    loading: false,
    currentMonthKey: "",
    autoLoad: true,
    targetNames: [],
    includePending: false,
    duplicateNames: new Set(),
    panelPosition: null,
    panelDragging: false,
    displayMode: null,
    lastRowsByDate: null,
    detailRowsByDate: new Map(),
    observer: null,
    renderTimer: null,
    internalDomUpdate: false
  };

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function storageGet(keys) {
    return new Promise((resolve) => chrome.storage.local.get(keys, resolve));
  }

  function storageSet(obj) {
    return new Promise((resolve) => chrome.storage.local.set(obj, resolve));
  }

  function storageRemove(keys) {
    return new Promise((resolve) => chrome.storage.local.remove(keys, resolve));
  }

  async function clearDutyCaches() {
    const all = await storageGet(null);
    const cacheKeys = Object.keys(all || {}).filter((key) => key.startsWith(STORAGE_KEYS.cachePrefix) || key.startsWith("jbeDutyCache:"));
    if (cacheKeys.length) await storageRemove(cacheKeys);
  }

  function withOwnDomUpdate(fn) {
    state.internalDomUpdate = true;
    try {
      return fn();
    } finally {
      setTimeout(() => {
        state.internalDomUpdate = false;
      }, 0);
    }
  }

  function safeJsonParse(text) {
    try {
      return JSON.parse(text);
    } catch (_) {
      return null;
    }
  }

  function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  function normalizeEndpoint(url) {
    if (!url) return DEFAULT_ENDPOINT;
    try {
      return new URL(url, location.origin).pathname;
    } catch (_) {
      return DEFAULT_ENDPOINT;
    }
  }

  function isDutyPayload(obj) {
    return !!(
      obj &&
      obj.data &&
      obj.data.dmSearch &&
      Object.prototype.hasOwnProperty.call(obj.data.dmSearch, "workYmd")
    );
  }

  async function saveCapturedTemplate(detail) {
    const parsed = safeJsonParse(detail && detail.body);
    if (!isDutyPayload(parsed)) return;

    await storageSet({
      [STORAGE_KEYS.template]: parsed,
      [STORAGE_KEYS.endpoint]: normalizeEndpoint(detail.url),
      [STORAGE_KEYS.origin]: location.origin,
      [STORAGE_KEYS.capturedAt]: Date.now()
    });
    await clearDutyCaches();

    showToast("현재 나이스 기준 복무 조회정보가 저장되었습니다.");
    updatePanelStatus();
  }

  window.addEventListener("message", (event) => {
    if (event.source !== window) return;
    const data = event.data;
    if (!data || (data.source !== HOOK_SOURCE && data.source !== LEGACY_HOOK_SOURCE)) return;
    if (!data.payload || data.payload.kind !== "duty-api") return;
    saveCapturedTemplate(data.payload);
  });

  async function getActiveTemplate() {
    const stored = await storageGet([
      STORAGE_KEYS.template,
      STORAGE_KEYS.endpoint,
      STORAGE_KEYS.origin,
      STORAGE_KEYS.capturedAt
    ]);

    if (stored[STORAGE_KEYS.template]) {
      const savedOrigin = stored[STORAGE_KEYS.origin] || "";

      // v1.2까지 저장된 조회정보에는 origin이 없었고, 당시 확장은 jbe.neis.go.kr에서만 실행됐다.
      // 다른 시도교육청에서 전북 조회정보를 잘못 재사용하지 않도록 legacy 값은 전북 도메인에서만 인정한다.
      if (!savedOrigin && location.origin === LEGACY_JBE_ORIGIN) {
        await storageSet({ [STORAGE_KEYS.origin]: location.origin });
      } else if (!savedOrigin || savedOrigin !== location.origin) {
        return {
          template: null,
          endpoint: DEFAULT_ENDPOINT,
          capturedAt: 0,
          source: "missingForOrigin"
        };
      }

      return {
        template: stored[STORAGE_KEYS.template],
        endpoint: stored[STORAGE_KEYS.endpoint] || DEFAULT_ENDPOINT,
        capturedAt: stored[STORAGE_KEYS.capturedAt] || 0,
        source: "captured"
      };
    }

    return {
      template: null,
      endpoint: DEFAULT_ENDPOINT,
      capturedAt: 0,
      source: "none"
    };
  }

  function normalizeTargetNames(value) {
    if (Array.isArray(value)) {
      return value.map((v) => String(v || "").trim()).filter(Boolean);
    }
    return String(value || "")
      .split(/[\n,，;；]+/)
      .map((v) => v.trim())
      .filter(Boolean);
  }

  function cleanText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function getRoleValues(row) {
    return [...new Set([row && row.jbpsNm, row && row.rksNm, row && row.jbgdNm]
      .map(cleanText)
      .filter(Boolean))];
  }

  function getRoleLabel(row) {
    return cleanText(row && row.rksNm)
      || cleanText(row && row.jbgdNm)
      || cleanText(row && row.jbpsNm);
  }

  function parseTargetRule(value) {
    const text = cleanText(value);
    const match = text.match(/^(.+?)\s*[\(（](.+)[\)）]\s*$/);
    if (!match) return { name: text, role: "" };
    return { name: cleanText(match[1]), role: cleanText(match[2]) };
  }

  async function getTargetNames() {
    const stored = await storageGet([STORAGE_KEYS.targetNames]);
    return normalizeTargetNames(stored[STORAGE_KEYS.targetNames]);
  }

  async function setTargetNames(names) {
    const normalized = [...new Set(normalizeTargetNames(names))];
    await storageSet({ [STORAGE_KEYS.targetNames]: normalized });
    state.targetNames = normalized;
    return normalized;
  }

  function filterTargetRows(rows, names) {
    const targets = names || state.targetNames || [];
    if (!targets.length) return rows || [];
    const rules = targets.map(parseTargetRule).filter((rule) => rule.name);
    return (rows || []).filter((row) => {
      const name = cleanText(row.invlFlnm);
      const roles = getRoleValues(row);
      return rules.some((rule) => rule.name === name && (!rule.role || roles.includes(rule.role)));
    });
  }

  function targetLabel(names) {
    return names && names.length ? `대상 ${names.length}명` : "부서 전체";
  }

  function getApprovalStatus(row) {
    return cleanText(row && row.atrzStsNm);
  }

  function isApprovedRow(row) {
    return getApprovalStatus(row) === APPROVED;
  }

  function isPendingRow(row) {
    const status = getApprovalStatus(row).replace(/\s+/g, "");
    return status === "상신(진행)" || status === "상신진행" || status === "결재중";
  }

  function isDisplayableStatus(row) {
    return isApprovedRow(row) || isPendingRow(row);
  }

  function filterApprovalRows(rows) {
    return (rows || []).filter((row) => isApprovedRow(row) || (state.includePending && isPendingRow(row)));
  }

  function updateDuplicateNames(rowsByDate) {
    const rolesByName = new Map();
    for (const rows of (rowsByDate || new Map()).values()) {
      for (const row of rows || []) {
        const name = cleanText(row.invlFlnm);
        if (!name) continue;
        if (!rolesByName.has(name)) rolesByName.set(name, new Set());
        rolesByName.get(name).add(getRoleLabel(row));
      }
    }
    state.duplicateNames = new Set([...rolesByName.entries()]
      .filter(([, roles]) => roles.size > 1)
      .map(([name]) => name));
  }

  function getDisplayName(row) {
    const name = cleanText(row && row.invlFlnm);
    const role = getRoleLabel(row);
    const roleValues = getRoleValues(row);
    const qualifiedRule = (state.targetNames || [])
      .map(parseTargetRule)
      .find((rule) => rule.name === name && rule.role && roleValues.includes(rule.role));
    if (qualifiedRule) return `${name}(${qualifiedRule.role})`;
    return state.duplicateNames.has(name) && role ? `${name}(${role})` : name;
  }

  function isVisible(el) {
    if (!el || !(el instanceof Element)) return false;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function viewportIntersectionArea(rect) {
    const width = Math.max(0, Math.min(rect.right, window.innerWidth) - Math.max(rect.left, 0));
    const height = Math.max(0, Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0));
    return width * height;
  }

  function getCalendarRoot(options = {}) {
    const allowHidden = !!options.allowHidden;
    const all = [...document.querySelectorAll(".calendar2.form-table")];
    const candidates = all.filter((root) => allowHidden || isVisible(root));
    if (!candidates.length) return null;

    return candidates
      .map((root) => {
        const rect = root.getBoundingClientRect();
        const section = getCalendarSectionRoot(root);
        const sectionText = section ? (section.textContent || "") : "";
        const titleBonus = sectionText.includes("월간일정") ? 100000000 : 0;
        const visibleBonus = isVisible(root) ? 1000000 : 0;
        const area = allowHidden ? Math.max(1, rect.width * rect.height) : viewportIntersectionArea(rect);
        return { root, score: titleBonus + visibleBonus + area };
      })
      .sort((a, b) => b.score - a.score)[0].root;
  }

  function getCalendarSectionRoot(root) {
    if (!root) return null;
    return root.closest(".item-rate3") ||
      root.closest(".lay-flex-content") ||
      root.closest(".neis-emb-base") ||
      root.closest(".cl-embeddedapp") ||
      document;
  }

  function parseMonthText(text) {
    const match = String(text || "").trim().match(/^(\d{4})년\s*(\d{1,2})월$/);
    if (!match) return null;
    const year = Number(match[1]);
    const month = Number(match[2]);
    if (!year || !month || month < 1 || month > 12) return null;
    return {
      year,
      month,
      monthKey: `${year}-${String(month).padStart(2, "0")}`
    };
  }

  function getMonthInfoFromNav(calendarRoot = getCalendarRoot()) {
    const section = getCalendarSectionRoot(calendarRoot) || document;
    const buttons = [...section.querySelectorAll('[aria-label="지난달"], [aria-label="다음달"]')].filter(isVisible);
    const candidates = [];

    for (const button of buttons) {
      let node = button.parentElement;
      for (let depth = 0; node && depth < 9 && node !== document; depth++, node = node.parentElement) {
        const hasPrev = [...node.querySelectorAll('[aria-label="지난달"]')].some(isVisible);
        const hasNext = [...node.querySelectorAll('[aria-label="다음달"]')].some(isVisible);
        if (!hasPrev || !hasNext) continue;

        const texts = [...node.querySelectorAll(".cl-text")]
          .filter(isVisible)
          .map((el) => (el.textContent || "").trim())
          .filter((text) => /^\d{4}년\s*\d{1,2}월$/.test(text));

        if (!texts.length) continue;
        const rect = node.getBoundingClientRect();
        const rootRect = calendarRoot ? calendarRoot.getBoundingClientRect() : null;
        const gap = rootRect ? Math.abs(rect.bottom - rootRect.top) : 0;
        const area = Math.max(1, rect.width * rect.height);
        for (const text of texts) {
          candidates.push({ text, score: gap + depth * 10 + area / 1000000 });
        }
      }
    }

    candidates.sort((a, b) => a.score - b.score);
    return parseMonthText(candidates[0]?.text || "");
  }

  function getVisibleMonthText(calendarRoot = getCalendarRoot()) {
    const navInfo = getMonthInfoFromNav(calendarRoot);
    if (navInfo) return `${navInfo.year}년 ${String(navInfo.month).padStart(2, "0")}월`;

    const section = getCalendarSectionRoot(calendarRoot) || document;
    const calRect = calendarRoot ? calendarRoot.getBoundingClientRect() : null;
    const matches = [];

    for (const el of [...section.querySelectorAll(".cl-text")]) {
      if (!isVisible(el)) continue;
      const text = (el.textContent || "").trim();
      if (!/^\d{4}년\s*\d{1,2}월$/.test(text)) continue;
      const rect = el.getBoundingClientRect();
      let score = matches.length;
      if (calRect) {
        const centerGap = Math.abs(((rect.left + rect.right) / 2) - ((calRect.left + calRect.right) / 2));
        const verticalGap = Math.abs(rect.bottom - calRect.top);
        const aboveBonus = rect.bottom <= calRect.top + 160 ? 0 : 100000;
        score = aboveBonus + verticalGap + centerGap / 1000;
      }
      matches.push({ text, score });
    }

    matches.sort((a, b) => a.score - b.score);
    return matches[0]?.text || "";
  }

  function getCurrentMonthInfo(calendarRoot = getCalendarRoot()) {
    return parseMonthText(getVisibleMonthText(calendarRoot));
  }

  function getDaysInMonth(year, month) {
    return new Date(year, month, 0).getDate();
  }

  function ymdCompact(year, month, day) {
    return `${year}${String(month).padStart(2, "0")}${String(day).padStart(2, "0")}`;
  }

  function ymdDashed(year, month, day) {
    return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  function cellDayNumber(cell) {
    const dateOutput = [...cell.querySelectorAll("[aria-label]")].find((el) => {
      const label = (el.getAttribute("aria-label") || "").trim();
      return /^\d{1,2}\s+[월화수목금토일]\s+/.test(label);
    });
    const label = dateOutput ? dateOutput.getAttribute("aria-label") || "" : "";
    const fromLabel = label.match(/^(\d{1,2})\s+/);
    if (fromLabel) return Number(fromLabel[1]);

    const span = cell.querySelector("span");
    const day = Number((span && span.textContent || "").trim());
    return Number.isFinite(day) ? day : null;
  }

  function isDateCellCandidate(cell) {
    if (!cell || !(cell instanceof Element)) return false;
    if (!cell.querySelector('[data-role="content-pane"]')) return false;
    if (!cell.querySelector("[aria-label]")) return false;
    return [...cell.querySelectorAll("[aria-label]")].some((el) => {
      const label = (el.getAttribute("aria-label") || "").trim();
      return /^\d{1,2}\s+[월화수목금토일]\s+/.test(label);
    });
  }

  function getCalendarDateSlots(calendarRoot) {
    if (!calendarRoot) return [];
    const rootRect = calendarRoot.getBoundingClientRect();
    return [...calendarRoot.querySelectorAll(".cl-control.cl-container")]
      .filter(isVisible)
      .filter(isDateCellCandidate)
      .map((cell) => {
        const rect = cell.getBoundingClientRect();
        return {
          cell,
          rect,
          day: cellDayNumber(cell),
          isOutside: cell.classList.contains("bg-gray-100"),
          top: Math.round(rect.top - rootRect.top),
          left: Math.round(rect.left - rootRect.left)
        };
      })
      .filter((slot) => slot.day)
      .sort((a, b) => (a.top - b.top) || (a.left - b.left));
  }

  function getCurrentMonthSlots(calendarRoot, monthInfo) {
    if (!calendarRoot || !monthInfo) return [];
    return getCalendarDateSlots(calendarRoot)
      .filter((slot) => !slot.isOutside)
      .map((slot) => ({
        ...slot,
        ymd: ymdDashed(monthInfo.year, monthInfo.month, slot.day)
      }));
  }

  function detectSchoolCalendar() {
    const topbarText = [...document.querySelectorAll(".topbar [title], .topbar .cl-text, .topbar")].map((el) => {
      return `${el.getAttribute?.("title") || ""} ${el.textContent || ""}`;
    }).join(" ");
    if (/학교|유치원|초등학교|중학교|고등학교/.test(topbarText)) return true;

    const root = getCalendarRoot();
    const calendarAreaText = root ? (root.closest(".lay-flex-content")?.textContent || root.textContent || "") : "";
    return /학사일정|재량휴업|개교기념|방학|개학|종업|체험학습/.test(calendarAreaText);
  }

  function isMonthlyCalendarScreen() {
    const root = getCalendarRoot({ allowHidden: true });
    if (!root) return false;

    const section = getCalendarSectionRoot(root) || root;
    const sectionText = String(section.textContent || "");
    if (sectionText.includes("월간일정")) return true;

    const titleCandidates = [...document.querySelectorAll(".app-tit .cl-text, .neis-main-tit .cl-text, .h3 .cl-text, .cl-text")];
    return titleCandidates.some((el) => {
      if (!isVisible(el)) return false;
      return String(el.textContent || "").trim() === "월간일정";
    });
  }

  function isValidDisplayMode(mode) {
    return mode === DISPLAY_MODES.academic || mode === DISPLAY_MODES.duty;
  }

  async function getDisplayMode() {
    const stored = await storageGet([STORAGE_KEYS.displayMode]);
    const mode = stored[STORAGE_KEYS.displayMode];
    if (isValidDisplayMode(mode)) return mode;
    return detectSchoolCalendar() ? DISPLAY_MODES.academic : DISPLAY_MODES.duty;
  }

  async function saveDisplayMode(mode) {
    const normalized = isValidDisplayMode(mode) ? mode : DISPLAY_MODES.duty;
    await storageSet({ [STORAGE_KEYS.displayMode]: normalized });
    state.displayMode = normalized;
    return normalized;
  }

  function getCalendarWrap(calendarRoot = getCalendarRoot({ allowHidden: true })) {
    if (!calendarRoot) return null;
    return calendarRoot.closest(".cl-layout-wrap") || calendarRoot.parentElement;
  }

  function normalizePanelPosition(value) {
    if (!value || !Number.isFinite(Number(value.left)) || !Number.isFinite(Number(value.top))) return null;
    return { left: Number(value.left), top: Number(value.top) };
  }

  function applyPanelPosition(panel, position = state.panelPosition) {
    if (!panel || !position) return;
    const rect = panel.getBoundingClientRect();
    const width = rect.width || Math.min(420, window.innerWidth - 24);
    const height = rect.height || 150;
    const bounded = {
      left: Math.max(0, Math.min(position.left, Math.max(0, window.innerWidth - width))),
      top: Math.max(0, Math.min(position.top, Math.max(0, window.innerHeight - height)))
    };
    panel.style.setProperty("left", `${bounded.left}px`, "important");
    panel.style.setProperty("top", `${bounded.top}px`, "important");
    panel.style.setProperty("right", "auto", "important");
    panel.style.setProperty("bottom", "auto", "important");
    state.panelPosition = bounded;
  }

  async function resetPanelPosition() {
    state.panelPosition = null;
    await storageRemove([STORAGE_KEYS.panelPosition]);
    const panel = document.getElementById("jbe-duty-panel");
    if (!panel) return;
    for (const property of ["left", "top", "right", "bottom"]) panel.style.removeProperty(property);
    showToast("제어판 위치를 초기화했습니다.");
  }

  function enablePanelDragging(panel) {
    const handle = panel && panel.querySelector(".jbe-duty-drag-handle");
    if (!handle || handle.dataset.dragReady === "true") return;
    handle.dataset.dragReady = "true";
    handle.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || event.target.closest("button")) return;
      const rect = panel.getBoundingClientRect();
      const start = { x: event.clientX, y: event.clientY, left: rect.left, top: rect.top };
      state.panelDragging = true;
      panel.classList.add("dragging");
      handle.setPointerCapture(event.pointerId);
      event.preventDefault();

      const move = (moveEvent) => applyPanelPosition(panel, {
        left: start.left + moveEvent.clientX - start.x,
        top: start.top + moveEvent.clientY - start.y
      });
      const end = async () => {
        state.panelDragging = false;
        panel.classList.remove("dragging");
        handle.removeEventListener("pointermove", move);
        handle.removeEventListener("pointerup", end);
        handle.removeEventListener("pointercancel", end);
        if (state.panelPosition) await storageSet({ [STORAGE_KEYS.panelPosition]: state.panelPosition });
      };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", end);
      handle.addEventListener("pointercancel", end);
    });
  }

  function ensureModeSwitch() {
    let panel = document.getElementById("jbe-duty-panel");
    if (!panel) {
      panel = document.createElement("div");
      panel.id = "jbe-duty-panel";
      panel.className = "jbe-duty-floating-panel";
      panel.innerHTML = `
        <div class="jbe-duty-drag-handle" title="잡고 끌어서 제어판을 이동하세요.">
          <span>복무 달력 제어판 · 끌어서 이동</span>
          <button type="button" class="jbe-duty-position-reset">위치 초기화</button>
        </div>
        <div class="jbe-duty-mode-group" aria-label="월간일정 표시 선택">
          <button type="button" id="jbe-duty-mode-academic" class="jbe-duty-mode-btn">학사일정</button>
          <button type="button" id="jbe-duty-mode-duty" class="jbe-duty-mode-btn">부서 복무</button>
        </div>
        <div class="jbe-duty-panel-status" id="jbe-duty-status">복무 조회정보 확인 중...</div>
        <div class="jbe-duty-panel-actions">
          <button type="button" id="jbe-duty-load">부서 복무 다시 불러오기</button>
          <button type="button" id="jbe-duty-target">대상자 설정</button>
          <button type="button" id="jbe-duty-pending">상신(진행) 숨김</button>
          <button type="button" id="jbe-duty-auto">자동 켬</button>
        </div>
      `;

      panel.querySelector("#jbe-duty-mode-academic").addEventListener("click", () => changeDisplayMode(DISPLAY_MODES.academic));
      panel.querySelector("#jbe-duty-mode-duty").addEventListener("click", () => changeDisplayMode(DISPLAY_MODES.duty));
      panel.querySelector("#jbe-duty-load").addEventListener("click", async () => {
        if (state.displayMode !== DISPLAY_MODES.duty) {
          await changeDisplayMode(DISPLAY_MODES.duty, { skipLoad: true });
        }
        loadAndRenderMonth({ force: true });
      });
      panel.querySelector("#jbe-duty-target").addEventListener("click", openTargetSettingsModal);
      panel.querySelector("#jbe-duty-pending").addEventListener("click", togglePendingRows);
      panel.querySelector("#jbe-duty-auto").addEventListener("click", toggleAutoLoad);
      panel.querySelector(".jbe-duty-position-reset").addEventListener("click", resetPanelPosition);

      const oldSwitch = document.getElementById("jbe-duty-floating-mode-switch");
      withOwnDomUpdate(() => {
        if (oldSwitch) oldSwitch.remove();
        document.body.appendChild(panel);
      });
    }
    enablePanelDragging(panel);
    applyPanelPosition(panel);
    updateFloatingModeSwitch();
    return panel;
  }

  function updateFloatingModeSwitch() {
    const panel = document.getElementById("jbe-duty-panel");
    if (!panel) return;

    if (!isMonthlyCalendarScreen()) {
      setStyleIfChanged(panel, "display", "none", "important");
      return;
    }

    setStyleIfChanged(panel, "display", "flex", "important");

    const academicBtn = panel.querySelector("#jbe-duty-mode-academic");
    const dutyBtn = panel.querySelector("#jbe-duty-mode-duty");
    toggleClassIfChanged(academicBtn, "active", state.displayMode === DISPLAY_MODES.academic);
    toggleClassIfChanged(dutyBtn, "active", state.displayMode === DISPLAY_MODES.duty);

    // 컨트롤은 월간일정 화면에서만 우측 하단에 유지한다.
    // 나이스 월간일정 DOM 내부에는 삽입하지 않는다.
    const actions = panel.querySelector(".jbe-duty-panel-actions");
    const status = panel.querySelector(".jbe-duty-panel-status");
    setStyleIfChanged(actions, "display", "flex");
    setStyleIfChanged(status, "display", "block");
  }

  function setStyleIfChanged(element, property, value, priority = "") {
    if (!element) return;
    if (element.style.getPropertyValue(property) === value && element.style.getPropertyPriority(property) === priority) return;
    element.style.setProperty(property, value, priority);
  }

  function toggleClassIfChanged(element, className, active) {
    if (!element || element.classList.contains(className) === active) return;
    element.classList.toggle(className, active);
  }

  function restoreOriginalCalendarDisplay() {
    for (const root of [...document.querySelectorAll(".calendar2.form-table")]) {
      const original = root.dataset.jbeDutyOriginalDisplay;
      if (original !== undefined) {
        root.style.display = original === "__empty__" ? "" : original;
        delete root.dataset.jbeDutyOriginalDisplay;
      }
    }
  }

  function teardownEmbeddedRoot() {
    restoreOriginalCalendarDisplay();
    const ownCalendar = document.getElementById("jbe-duty-own-calendar");
    withOwnDomUpdate(() => {
      if (ownCalendar) ownCalendar.remove();
    });
    state.detailRowsByDate = new Map();
  }

  function stopDomObserver() {
    if (state.observer) {
      state.observer.disconnect();
      state.observer = null;
    }
    clearTimeout(state.renderTimer);
  }

  function startDomObserver() {
    if (state.observer) return;
    const observer = new MutationObserver((records) => {
      if (state.internalDomUpdate || state.displayMode !== DISPLAY_MODES.duty) return;
      if (records.every(isExtensionMutation)) return;
      debounceRender();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["style", "class", "aria-label"] });
    state.observer = observer;
  }

  function isExtensionElement(node) {
    const element = node instanceof Element ? node : node && node.parentElement;
    if (!element) return false;
    const selector = "#jbe-duty-panel, #jbe-duty-own-calendar, #jbe-duty-modal, #jbe-duty-target-modal, #jbe-duty-toast";
    return element.matches(selector) || !!element.closest(selector);
  }

  function isExtensionMutation(record) {
    if (isExtensionElement(record.target)) return true;
    if (record.type !== "childList") return false;
    const changedNodes = [...record.addedNodes, ...record.removedNodes];
    return changedNodes.length > 0 && changedNodes.every(isExtensionElement);
  }

  function ensureEmbeddedRoot() {
    const calendarRoot = getCalendarRoot({ allowHidden: true });
    if (!calendarRoot) return null;

    const wrap = getCalendarWrap(calendarRoot);
    const parent = wrap && wrap.parentElement;
    if (!wrap || !parent) return null;

    let ownCalendar = document.getElementById("jbe-duty-own-calendar");
    if (!ownCalendar) {
      ownCalendar = document.createElement("div");
      ownCalendar.id = "jbe-duty-own-calendar";
      ownCalendar.setAttribute("aria-label", "부서 복무 달력");
    }

    if (ownCalendar.parentElement !== wrap) {
      withOwnDomUpdate(() => wrap.appendChild(ownCalendar));
    }

    return { ownCalendar, calendarRoot, wrap, parent };
  }

  function ensurePanel() {
    const panel = ensureModeSwitch();
    updateModeButtons();
    return panel;
  }

  function positionPanel() {
    const panel = document.getElementById("jbe-duty-panel");
    if (panel && state.panelPosition && !state.panelDragging) applyPanelPosition(panel);
  }

  async function updatePanelStatus(extraText) {
    ensurePanel();
    const panel = document.getElementById("jbe-duty-panel");
    if (!panel) return;

    const [{ jbeDutyAutoLoad, jbeDutyIncludePending }, active, targetNames] = await Promise.all([
      storageGet([STORAGE_KEYS.autoLoad, STORAGE_KEYS.includePending]),
      getActiveTemplate(),
      getTargetNames()
    ]);
    state.autoLoad = typeof jbeDutyAutoLoad === "boolean" ? jbeDutyAutoLoad : true;
    state.includePending = jbeDutyIncludePending === true;
    state.targetNames = targetNames;

    const status = panel.querySelector("#jbe-duty-status");
    const loadBtn = panel.querySelector("#jbe-duty-load");
    const autoBtn = panel.querySelector("#jbe-duty-auto");
    const pendingBtn = panel.querySelector("#jbe-duty-pending");

    if (autoBtn) autoBtn.textContent = state.autoLoad ? "자동 켬" : "자동 끔";
    if (pendingBtn) {
      pendingBtn.textContent = state.includePending ? "상신(진행) 표시 중" : "상신(진행) 숨김";
      toggleClassIfChanged(pendingBtn, "active", state.includePending);
      pendingBtn.setAttribute("aria-pressed", String(state.includePending));
    }

    if (!active.template) {
      if (status) status.textContent = "복무 조회정보 없음 · 일일근무상황조회에서 조회를 한 번 실행하세요.";
      if (loadBtn) loadBtn.disabled = true;
      return;
    }

    if (loadBtn) loadBtn.disabled = false;

    const sourceText = `조회정보 저장: ${active.capturedAt ? new Date(active.capturedAt).toLocaleString("ko-KR", { hour12: false }) : "저장됨"}`;

    const approvalText = state.includePending ? "승인완료+결재중" : "승인완료만";
    if (status) status.textContent = extraText || `${targetLabel(targetNames)} · ${approvalText} · ${sourceText}`;
    updateModeButtons();
  }

  function updateModeButtons() {
    const academicBtn = document.getElementById("jbe-duty-mode-academic");
    const dutyBtn = document.getElementById("jbe-duty-mode-duty");
    toggleClassIfChanged(academicBtn, "active", state.displayMode === DISPLAY_MODES.academic);
    toggleClassIfChanged(dutyBtn, "active", state.displayMode === DISPLAY_MODES.duty);
    updateFloatingModeSwitch();
  }

  function applyDisplayMode() {
    ensurePanel();

    if (state.displayMode === DISPLAY_MODES.academic) {
      teardownEmbeddedRoot();
      updateModeButtons();
      return;
    }

    const env = ensureEmbeddedRoot();
    if (!env) return;

    const { calendarRoot, ownCalendar } = env;

    if (!calendarRoot.dataset.jbeDutyOriginalDisplay) {
      calendarRoot.dataset.jbeDutyOriginalDisplay = calendarRoot.style.display || "__empty__";
    }

    setStyleIfChanged(calendarRoot, "display", "none");
    setStyleIfChanged(ownCalendar, "display", "block");
    renderDutyCalendar();
    updateModeButtons();
  }

  async function changeDisplayMode(mode, options = {}) {
    const saved = await saveDisplayMode(mode);

    if (saved === DISPLAY_MODES.academic) {
      stopDomObserver();
      state.lastRowsByDate = null;
      state.detailRowsByDate = new Map();
      applyDisplayMode();
      return;
    }

    applyDisplayMode();
    startDomObserver();
    await updatePanelStatus();
    renderDutyCalendar();

    if (!options.skipLoad && state.autoLoad && !state.lastRowsByDate) {
      loadAndRenderMonth({ force: false });
    } else if (state.lastRowsByDate) {
      renderMonth(state.lastRowsByDate);
    }
  }

  async function toggleAutoLoad() {
    state.autoLoad = !state.autoLoad;
    await storageSet({ [STORAGE_KEYS.autoLoad]: state.autoLoad });
    await updatePanelStatus();
    if (state.autoLoad && state.displayMode === DISPLAY_MODES.duty) loadAndRenderMonth({ force: false });
  }

  async function togglePendingRows() {
    state.includePending = !state.includePending;
    await storageSet({ [STORAGE_KEYS.includePending]: state.includePending });
    if (state.lastRowsByDate) renderMonth(state.lastRowsByDate);
    const total = state.lastRowsByDate ? filteredTotalCount(state.lastRowsByDate) : 0;
    await updatePanelStatus(`${state.includePending ? "승인완료와 상신(진행)" : "승인완료"} 표시 · 현재 ${total}건`);
    showToast(state.includePending ? "상신(진행) 건을 (결재중)으로 함께 표시합니다." : "승인완료 건만 표시합니다.");
  }

  async function fetchDay(template, endpoint, ymd) {
    const payload = deepClone(template);
    payload.data.dmSearch.workYmd = ymd;

    const response = await fetch(endpoint, {
      method: "POST",
      credentials: "include",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "ui": "eXbuilder"
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) throw new Error(`복무 조회 실패 ${response.status}`);
    const data = await response.json();
    return Array.isArray(data.dsMain) ? data.dsMain : [];
  }

  async function mapLimit(items, limit, worker, onProgress) {
    const results = new Array(items.length);
    let index = 0;
    let done = 0;

    async function runner() {
      while (index < items.length) {
        const current = index++;
        results[current] = await worker(items[current], current);
        done++;
        if (onProgress) onProgress(done, items.length);
        await sleep(30);
      }
    }

    await Promise.all(Array.from({ length: Math.min(limit, items.length) }, runner));
    return results.flat();
  }

  function dedupeRows(rows) {
    const seen = new Set();
    const result = [];
    for (const row of rows || []) {
      const key = [row.invlFlnm, row.jbpsNm, row.rksNm, row.jbgdNm, row.workSittnNm, row.workSittnPrd, row.destiNm, row.atrzStsNm].join("|");
      if (seen.has(key)) continue;
      seen.add(key);
      result.push(row);
    }
    return result;
  }

  function normalizeRowsByDate(rawRowsByDate) {
    const rowsByDate = new Map();
    for (const [ymd, rows] of rawRowsByDate.entries()) {
      const displayable = dedupeRows(rows).filter(isDisplayableStatus);
      if (displayable.length > 0) rowsByDate.set(ymd, displayable);
    }
    return rowsByDate;
  }

  function getCacheKey(monthKey) {
    return `${STORAGE_KEYS.cachePrefix}${location.host}:${monthKey}`;
  }

  async function getCachedMonth(monthKey) {
    const cacheKey = getCacheKey(monthKey);
    const result = await storageGet(cacheKey);
    const cached = result[cacheKey];
    if (!cached || !cached.savedAt || !cached.rowsByDate) return null;
    if (Date.now() - cached.savedAt > CACHE_TTL_MS) return null;
    return cached;
  }

  async function setCachedMonth(monthKey, rowsByDateObject, savedAt = Date.now()) {
    const cacheKey = getCacheKey(monthKey);
    await storageSet({
      [cacheKey]: {
        origin: location.origin,
        savedAt,
        rowsByDate: rowsByDateObject
      }
    });
    return savedAt;
  }

  function rowsByDateMapToObject(map) {
    const obj = {};
    for (const [key, rows] of map.entries()) obj[key] = rows;
    return obj;
  }

  function rowsByDateObjectToMap(obj) {
    const map = new Map();
    for (const [key, rows] of Object.entries(obj || {})) {
      if (Array.isArray(rows)) map.set(key, rows);
    }
    return map;
  }

  function filteredTotalCount(rowsByDate) {
    return [...(rowsByDate || new Map()).values()].reduce((sum, rows) => sum + filterApprovalRows(filterTargetRows(rows)).length, 0);
  }

  function formatInfoTime(timestamp) {
    if (!timestamp) return "조회시각 없음";
    const d = new Date(timestamp);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}. ${d.getMonth() + 1}. ${d.getDate()}. ${pad(d.getHours())}:${pad(d.getMinutes())} 기준`;
  }

  function buildDisplayStatus(monthKey, count, savedAt) {
    const approvalText = state.includePending ? "승인완료+결재중" : "승인완료만";
    return `${targetLabel(state.targetNames)} · ${approvalText} · ${monthKey} ${count}건 · ${formatInfoTime(savedAt)}`;
  }

  async function loadAndRenderMonth(options = {}) {
    if (state.displayMode !== DISPLAY_MODES.duty) {
      await changeDisplayMode(DISPLAY_MODES.duty, { skipLoad: true });
    }
    if (state.loading) return;
    const calendarRoot = getCalendarRoot({ allowHidden: true });
    const monthInfo = getCurrentMonthInfo(calendarRoot);
    if (!calendarRoot || !monthInfo) return;

    const active = await getActiveTemplate();
    if (!active.template) {
      await updatePanelStatus("복무 조회정보 없음 · 일일근무상황조회에서 조회를 한 번 실행하세요.");
      return;
    }

    state.loading = true;
    state.targetNames = await getTargetNames();
    const endpoint = normalizeEndpoint(active.endpoint || DEFAULT_ENDPOINT);
    const monthKey = monthInfo.monthKey;

    try {
      if (!options.force) {
        const cached = await getCachedMonth(monthKey);
        if (cached) {
          const map = rowsByDateObjectToMap(cached.rowsByDate);
          renderMonth(map);
          await updatePanelStatus(buildDisplayStatus(monthKey, filteredTotalCount(map), cached.savedAt));
          return;
        }
      }

      const days = getDaysInMonth(monthInfo.year, monthInfo.month);
      const dayList = Array.from({ length: days }, (_, i) => i + 1);
      const rawRowsByDate = new Map();
      await updatePanelStatus(`${monthKey} 복무현황 조회 중... 0/${days}`);

      await mapLimit(dayList, 4, async (day) => {
        const compact = ymdCompact(monthInfo.year, monthInfo.month, day);
        const dashed = ymdDashed(monthInfo.year, monthInfo.month, day);
        const rows = await fetchDay(active.template, endpoint, compact);
        rawRowsByDate.set(dashed, rows);
        return rows;
      }, (done, total) => {
        updatePanelStatus(`${monthKey} 복무현황 조회 중... ${done}/${total}`);
      });

      const rowsByDate = normalizeRowsByDate(rawRowsByDate);
      renderMonth(rowsByDate);
      const savedAt = await setCachedMonth(monthKey, rowsByDateMapToObject(rowsByDate));
      await updatePanelStatus(buildDisplayStatus(monthKey, filteredTotalCount(rowsByDate), savedAt));
    } catch (error) {
      console.error("[NEIS Duty Calendar]", error);
      await updatePanelStatus(`복무현황 조회 실패 · ${error.message || error}`);
      showToast("복무현황 조회에 실패했습니다. 나이스 로그인 상태와 조회 권한을 확인하세요.", true);
    } finally {
      state.loading = false;
    }
  }

  function simplifyWorkType(type) {
    const text = String(type || "").trim();
    if (!text) return "복무";
    if (text.includes("출장")) return "출장";
    if (text.includes("가족돌봄")) return "돌봄";
    if (text.includes("특별휴가")) return "특별휴가";
    if (text.includes("학습휴가")) return "학습휴가";
    if (text.includes("육아")) return "육아시간";
    if (text.includes("병")) return text;
    return text.replace(/\(.*?\)/g, "").trim() || text;
  }

  function dutyClass(type) {
    const text = String(type || "");
    if (text.includes("출장")) return "jbe-duty-blue";
    if (text.includes("연가") || text.includes("학습")) return "jbe-duty-green";
    if (text.includes("병")) return "jbe-duty-red";
    if (text.includes("육아") || text.includes("돌봄") || text.includes("특별")) return "jbe-duty-purple";
    if (text.includes("지각") || text.includes("조퇴") || text.includes("외출")) return "jbe-duty-orange";
    return "jbe-duty-gray";
  }

  function buildCellLines(rows) {
    const hasMore = rows.length > MAX_CELL_LINES;
    const shown = hasMore ? rows.slice(0, MAX_CELL_LINES - 1) : rows.slice(0, MAX_CELL_LINES);
    const lines = shown.map((row) => ({
      text: `${getDisplayName(row)} ${simplifyWorkType(row.workSittnNm)}${isPendingRow(row) ? ` (${PENDING_LABEL})` : ""}`.trim(),
      cls: `${dutyClass(row.workSittnNm)}${isPendingRow(row) ? " jbe-duty-pending" : ""}`
    }));
    if (hasMore) lines.push({ text: `+${rows.length - (MAX_CELL_LINES - 1)}건 더보기`, cls: "jbe-duty-more" });
    return lines;
  }

  function clearDutyOverlay() {
    const ownCalendar = document.getElementById("jbe-duty-own-calendar");
    if (ownCalendar) withOwnDomUpdate(() => {
      ownCalendar.textContent = "";
      ownCalendar.__jbeDutyRenderKey = "";
    });
    state.detailRowsByDate = new Map();
    state.duplicateNames = new Set();
  }

  function createDutyCalendarCell({ ymd, day, isCurrentMonth, rows }) {
    const cell = document.createElement("div");
    cell.className = isCurrentMonth ? "jbe-duty-own-cell" : "jbe-duty-own-cell outside-month";
    if (ymd) cell.dataset.ymd = ymd;

    const dayEl = document.createElement("div");
    dayEl.className = "jbe-duty-own-day";
    dayEl.textContent = String(day);
    cell.appendChild(dayEl);

    if (!isCurrentMonth) return cell;

    const list = document.createElement("div");
    list.className = "jbe-duty-own-list";
    const filteredRows = rows || [];

    if (filteredRows.length) {
      cell.classList.add("has-duty");
      const lines = buildCellLines(filteredRows);
      for (const line of lines) {
        const item = document.createElement("div");
        item.className = `jbe-duty-own-item ${line.cls}`;
        item.textContent = line.text;
        list.appendChild(item);
      }
      cell.title = `${formatKoreanDate(ymd)} 복무현황 ${filteredRows.length}건`;
      cell.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        showDetailModal(ymd, filteredRows);
      });
    }

    cell.appendChild(list);
    return cell;
  }

  function buildCalendarRenderKey(monthInfo, rowsByDate) {
    const visibleRows = [];
    const dates = [...(rowsByDate || new Map()).keys()].sort();
    for (const ymd of dates) {
      const rows = filterApprovalRows(filterTargetRows(rowsByDate.get(ymd) || []));
      for (const row of rows) {
        visibleRows.push([
          ymd,
          getDisplayName(row),
          cleanText(row.workSittnNm),
          cleanPeriod(row.workSittnPrd),
          cleanText(row.destiNm),
          getApprovalStatus(row)
        ]);
      }
    }
    return JSON.stringify([
      monthInfo.monthKey,
      state.targetNames,
      state.includePending,
      visibleRows
    ]);
  }

  function renderDutyCalendar() {
    if (state.displayMode !== DISPLAY_MODES.duty) {
      const ownCalendar = document.getElementById("jbe-duty-own-calendar");
      if (ownCalendar) withOwnDomUpdate(() => {
        ownCalendar.textContent = "";
        ownCalendar.__jbeDutyRenderKey = "";
      });
      return;
    }

    const env = ensureEmbeddedRoot();
    if (!env) return;

    const { ownCalendar, calendarRoot } = env;
    const monthInfo = getCurrentMonthInfo(calendarRoot);

    if (!ownCalendar || !monthInfo) {
      if (ownCalendar) withOwnDomUpdate(() => {
        ownCalendar.textContent = "";
        ownCalendar.__jbeDutyRenderKey = "";
      });
      return;
    }

    const weekNames = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"];
    const firstWeekday = new Date(monthInfo.year, monthInfo.month - 1, 1).getDay();
    const daysInThisMonth = getDaysInMonth(monthInfo.year, monthInfo.month);
    const prevMonth = monthInfo.month === 1 ? 12 : monthInfo.month - 1;
    const prevYear = monthInfo.month === 1 ? monthInfo.year - 1 : monthInfo.year;
    const daysInPrevMonth = getDaysInMonth(prevYear, prevMonth);

    const rowsByDate = state.lastRowsByDate || new Map();
    const renderKey = buildCalendarRenderKey(monthInfo, rowsByDate);
    if (ownCalendar.__jbeDutyRenderKey === renderKey && ownCalendar.firstElementChild) return;
    state.detailRowsByDate = new Map();

    withOwnDomUpdate(() => {
      ownCalendar.textContent = "";
      const grid = document.createElement("div");
      grid.className = "jbe-duty-own-grid";

      for (let i = 0; i < 7; i++) {
        const head = document.createElement("div");
        head.className = `jbe-duty-own-head day-${i}`;
        head.textContent = weekNames[i];
        grid.appendChild(head);
      }

      for (let i = 0; i < 42; i++) {
        const index = i - firstWeekday + 1;
        let day;
        let ymd = "";
        let isCurrentMonth = index >= 1 && index <= daysInThisMonth;

        if (isCurrentMonth) {
          day = index;
          ymd = ymdDashed(monthInfo.year, monthInfo.month, day);
        } else if (index < 1) {
          day = daysInPrevMonth + index;
        } else {
          day = index - daysInThisMonth;
        }

        const rows = isCurrentMonth ? filterApprovalRows(filterTargetRows(rowsByDate.get(ymd) || [])) : [];
        if (rows.length) state.detailRowsByDate.set(ymd, rows);
        const cell = createDutyCalendarCell({ ymd, day, isCurrentMonth, rows });
        if (i % 7 === 0) cell.classList.add("sunday");
        if (i % 7 === 6) cell.classList.add("saturday");
        grid.appendChild(cell);
      }

      ownCalendar.appendChild(grid);
      ownCalendar.__jbeDutyRenderKey = renderKey;
    });
  }

  function renderMonth(rowsByDate) {
    state.lastRowsByDate = rowsByDate;
    updateDuplicateNames(rowsByDate);
    state.detailRowsByDate = new Map();
    for (const [ymd, rows] of (rowsByDate || new Map()).entries()) {
      const filtered = filterApprovalRows(filterTargetRows(rows));
      if (filtered.length) state.detailRowsByDate.set(ymd, filtered);
    }
    renderDutyCalendar();
  }

  function cleanPeriod(period) {
    return String(period || "").replace(/\s+/g, " ").trim();
  }

  function sortRows(a, b) {
    const aName = getDisplayName(a);
    const bName = getDisplayName(b);
    const aType = String(a.workSittnNm || "");
    const bType = String(b.workSittnNm || "");
    return aName.localeCompare(bName, "ko") || aType.localeCompare(bType, "ko");
  }

  function countRowsByWorkType(rows) {
    const map = new Map();
    for (const row of rows || []) {
      const type = String(row.workSittnNm || "복무").trim() || "복무";
      map.set(type, (map.get(type) || 0) + 1);
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0], "ko"));
  }

  function formatKoreanDate(ymd) {
    const match = String(ymd).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return ymd;
    const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    const week = ["일", "월", "화", "수", "목", "금", "토"][date.getDay()];
    return `${match[1]}. ${Number(match[2])}. ${Number(match[3])}.(${week})`;
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function appendMetaLine(parent, label, value) {
    const text = String(value || "").trim();
    if (!text) return;

    const line = document.createElement("div");
    line.className = "jbe-duty-detail-line";

    const labelEl = document.createElement("span");
    labelEl.className = "jbe-duty-detail-label";
    labelEl.textContent = `${label}: `;

    const valueEl = document.createElement("span");
    valueEl.className = "jbe-duty-detail-value";
    valueEl.textContent = text;

    line.append(labelEl, valueEl);
    parent.appendChild(line);
  }

  function renderDetailRows(container, rows) {
    container.textContent = "";
    if (!rows.length) {
      const empty = document.createElement("div");
      empty.className = "jbe-duty-detail-empty";
      empty.textContent = "표시할 복무현황이 없습니다.";
      container.appendChild(empty);
      return;
    }

    rows.forEach((row) => {
      const rowEl = document.createElement("div");
      rowEl.className = "jbe-duty-detail-row";

      const name = document.createElement("div");
      name.className = "jbe-duty-detail-name";
      name.textContent = getDisplayName(row);

      const type = document.createElement("div");
      type.className = `jbe-duty-detail-type ${dutyClass(row.workSittnNm)}`;
      type.textContent = `${row.workSittnNm || "복무"}${isPendingRow(row) ? ` (${PENDING_LABEL})` : ""}`;
      if (isPendingRow(row)) type.classList.add("jbe-duty-pending");

      const meta = document.createElement("div");
      meta.className = "jbe-duty-detail-meta";
      appendMetaLine(meta, "직급/직위/직종", getRoleLabel(row));
      appendMetaLine(meta, "복무시간", cleanPeriod(row.workSittnPrd));
      appendMetaLine(meta, "목적지", row.destiNm);
      appendMetaLine(meta, "결재상태", isPendingRow(row) ? `${getApprovalStatus(row)} (${PENDING_LABEL})` : getApprovalStatus(row));

      rowEl.append(name, type, meta);
      container.appendChild(rowEl);
    });
  }

  function showDetailModal(ymd, rows) {
    document.getElementById("jbe-duty-modal")?.remove();

    const sortedRows = rows.slice().sort(sortRows);
    const typeCounts = countRowsByWorkType(sortedRows);

    const overlay = document.createElement("div");
    overlay.id = "jbe-duty-modal";
    overlay.innerHTML = `
      <div class="jbe-duty-modal-backdrop"></div>
      <div class="jbe-duty-modal-card" role="dialog" aria-modal="true">
        <div class="jbe-duty-modal-head">
          <div class="jbe-duty-modal-heading">
            <div class="jbe-duty-modal-title">${escapeHtml(formatKoreanDate(ymd))} 복무현황</div>
            <div class="jbe-duty-modal-sub" id="jbe-duty-detail-count">전체 ${rows.length}건</div>
          </div>
          <div class="jbe-duty-type-filter" id="jbe-duty-type-filter" aria-label="복무 종류 필터"></div>
          <button type="button" class="jbe-duty-modal-close" aria-label="닫기">×</button>
        </div>
        <div class="jbe-duty-modal-body"></div>
      </div>
    `;

    const body = overlay.querySelector(".jbe-duty-modal-body");
    const countEl = overlay.querySelector("#jbe-duty-detail-count");
    const filterEl = overlay.querySelector("#jbe-duty-type-filter");

    function makeFilterButton(type, count, active) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = active ? "jbe-duty-type-chip active" : "jbe-duty-type-chip";
      btn.dataset.type = type;
      btn.textContent = type === "__all__" ? `전체 ${count}건` : `${type} ${count}건`;
      btn.addEventListener("click", () => applyFilter(type));
      return btn;
    }

    function renderFilterButtons(activeType) {
      filterEl.textContent = "";
      filterEl.appendChild(makeFilterButton("__all__", sortedRows.length, activeType === "__all__"));
      for (const [type, count] of typeCounts) {
        filterEl.appendChild(makeFilterButton(type, count, activeType === type));
      }
    }

    function applyFilter(activeType) {
      renderFilterButtons(activeType);
      const displayRows = activeType === "__all__" ? sortedRows : sortedRows.filter((row) => String(row.workSittnNm || "복무") === activeType);
      if (countEl) {
        countEl.textContent = activeType === "__all__"
          ? `전체 ${displayRows.length}건`
          : `${activeType} ${displayRows.length}건 / 전체 ${sortedRows.length}건`;
      }
      renderDetailRows(body, displayRows);
    }

    applyFilter("__all__");

    overlay.querySelector(".jbe-duty-modal-backdrop").addEventListener("click", () => overlay.remove());
    overlay.querySelector(".jbe-duty-modal-close").addEventListener("click", () => overlay.remove());
    withOwnDomUpdate(() => document.body.appendChild(overlay));
  }

  async function openTargetSettingsModal() {
    document.getElementById("jbe-duty-target-modal")?.remove();

    const names = await getTargetNames();
    const overlay = document.createElement("div");
    overlay.id = "jbe-duty-target-modal";
    overlay.innerHTML = `
      <div class="jbe-duty-modal-backdrop"></div>
      <div class="jbe-duty-target-card" role="dialog" aria-modal="true">
        <div class="jbe-duty-modal-head">
          <div>
            <div class="jbe-duty-modal-title">복무 표시 대상자 설정</div>
            <div class="jbe-duty-modal-sub">이름만 입력하거나, 동명이인은 이름 뒤에 직급·직위·직종을 붙여 구분합니다.</div>
          </div>
          <button type="button" class="jbe-duty-modal-close" aria-label="닫기">×</button>
        </div>
        <div class="jbe-duty-target-body">
          <div class="jbe-duty-target-guide">
            <strong>입력 방법</strong>
            <div><code>홍길동</code> — 직급과 관계없이 같은 이름을 모두 표시</div>
            <div><code>홍길동(7급)</code> — ‘7급’인 홍길동만 표시</div>
            <div><code>김철수(장학관)</code> — ‘장학관’인 김철수만 표시</div>
          </div>
          <textarea id="jbe-duty-target-text" spellcheck="false" placeholder="예)\n홍길동\n홍길동(7급)\n김철수(장학관)"></textarea>
          <div class="jbe-duty-target-help">한 줄에 한 명씩 입력하며 쉼표로 구분해도 됩니다. 동명이인을 구분하려면 나이스 일일근무상황조회 화면의 ‘직급/직위/직종’ 값을 괄호 안에 그대로 입력하세요. 비워두면 부서 전체를 표시합니다.</div>
        </div>
        <div class="jbe-duty-target-actions">
          <button type="button" class="jbe-duty-target-clear">전체 표시</button>
          <button type="button" class="jbe-duty-target-cancel">취소</button>
          <button type="button" class="jbe-duty-target-save">저장</button>
        </div>
      </div>
    `;

    overlay.querySelector("#jbe-duty-target-text").value = names.join("\n");

    const close = () => overlay.remove();
    overlay.querySelector(".jbe-duty-modal-backdrop").addEventListener("click", close);
    overlay.querySelector(".jbe-duty-modal-close").addEventListener("click", close);
    overlay.querySelector(".jbe-duty-target-cancel").addEventListener("click", close);
    overlay.querySelector(".jbe-duty-target-clear").addEventListener("click", async () => {
      await setTargetNames([]);
      if (state.lastRowsByDate) renderMonth(state.lastRowsByDate);
      await updatePanelStatus("대상자 설정을 비웠습니다. 부서 전체를 표시합니다.");
      showToast("부서 전체 표시로 변경했습니다.");
      close();
    });
    overlay.querySelector(".jbe-duty-target-save").addEventListener("click", async () => {
      const text = overlay.querySelector("#jbe-duty-target-text").value;
      const saved = await setTargetNames(text);
      if (state.lastRowsByDate) renderMonth(state.lastRowsByDate);
      const total = state.lastRowsByDate ? filteredTotalCount(state.lastRowsByDate) : 0;
      await updatePanelStatus(`대상자 ${saved.length}명을 저장했습니다. 현재 표시 ${total}건`);
      showToast(saved.length ? `대상자 ${saved.length}명만 표시합니다.` : "부서 전체를 표시합니다.");
      close();
    });

    withOwnDomUpdate(() => document.body.appendChild(overlay));
    setTimeout(() => overlay.querySelector("#jbe-duty-target-text")?.focus(), 50);
  }

  function showToast(message, isError) {
    const old = document.getElementById("jbe-duty-toast");
    if (old) old.remove();

    const toast = document.createElement("div");
    toast.id = "jbe-duty-toast";
    toast.className = isError ? "error" : "";
    toast.textContent = message;
    withOwnDomUpdate(() => document.body.appendChild(toast));
    setTimeout(() => toast.remove(), 3800);
  }

  function debounceRender() {
    if (state.displayMode === DISPLAY_MODES.academic) return;
    if (state.internalDomUpdate) return;
    clearTimeout(state.renderTimer);
    state.renderTimer = setTimeout(async () => {
      if (state.internalDomUpdate) return;

      ensurePanel();
      applyDisplayMode();

      const calendarRoot = getCalendarRoot({ allowHidden: true });
      const monthInfo = getCurrentMonthInfo(calendarRoot);
      if (!calendarRoot || !monthInfo) {
        clearDutyOverlay();
        return;
      }

      positionPanel();

      if (monthInfo.monthKey !== state.currentMonthKey) {
        state.currentMonthKey = monthInfo.monthKey;
        state.lastRowsByDate = null;
        state.detailRowsByDate = new Map();
        clearDutyOverlay();
        await updatePanelStatus();

        const active = await getActiveTemplate();
        if (state.autoLoad && active.template && state.displayMode === DISPLAY_MODES.duty) {
          loadAndRenderMonth({ force: false });
        }
        return;
      }

      if (state.lastRowsByDate) renderMonth(state.lastRowsByDate);
      else renderDutyCalendar();
    }, 500);
  }

  async function init() {
    if (state.initialized) return;
    state.initialized = true;

    const stored = await storageGet([
      STORAGE_KEYS.autoLoad,
      STORAGE_KEYS.includePending,
      STORAGE_KEYS.panelPosition
    ]);
    state.autoLoad = typeof stored[STORAGE_KEYS.autoLoad] === "boolean" ? stored[STORAGE_KEYS.autoLoad] : true;
    state.includePending = stored[STORAGE_KEYS.includePending] === true;
    state.panelPosition = normalizePanelPosition(stored[STORAGE_KEYS.panelPosition]);
    state.targetNames = await getTargetNames();
    state.displayMode = await getDisplayMode();

    ensureModeSwitch();
    ensurePanel();
    applyDisplayMode();
    await updatePanelStatus();

    setInterval(() => {
      updateFloatingModeSwitch();
    }, 1000);

    if (state.displayMode === DISPLAY_MODES.duty) startDomObserver();

    window.addEventListener("resize", () => {
      positionPanel();
    });
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden && state.displayMode === DISPLAY_MODES.duty) debounceRender();
    });

    if (state.displayMode === DISPLAY_MODES.duty) debounceRender();
  }

  init();
})();
