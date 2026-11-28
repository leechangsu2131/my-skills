// 로그인 자동 연장 (T122, ISSUE-009)
// 나이스 화면의 "남은 시간"이 5분 이하가 되면 '연장' 단추**만** 누르고, 화면 구석 작은 표시로 상태를 보여 준다.
// - 누르는 것은 글자가 '연장'(예: '로그인 연장')인 단추 딱 하나뿐이다. 못 찾거나 둘 이상이면 누르지 않고 표시만 한다.
// - 아이디·비밀번호·쿠키·화면 내용은 읽거나 저장하지 않는다(읽는 것은 남은 시간 글자뿐). 저장하는 것은 켜짐/멈춤 한 가지(chrome.storage.local).
// - content.js 와 같은 격리 공간을 쓰므로 전체를 함수로 감싸 이름이 겹치지 않게 한다.
// - 순수 함수는 Node 로 시험한다(tests/session_keeper.test.js).
(function () {
  'use strict';

  const THRESHOLD_SECONDS = 300;      // 5분 이하가 되면 누른다
  const CHECK_INTERVAL_MS = 15000;    // 15초마다 본다
  const RETRY_GAP_MS = 60000;         // 눌렀는데도 시간이 안 늘면 1분 뒤에 다시
  const MAX_ATTEMPTS = 3;             // 한 번 낮아진 동안 최대 3번까지만
  const STORAGE_KEY = 'sessionKeeperEnabled';
  const KEYWORDS = /남은|잔여|로그아웃|세션|로그인\s*시간|접속\s*시간/;
  const BUTTON_TEXT = /^(로그인|세션|시간|자동)?연장(하기)?$/;

  // "47:12" · "1:02:03" · "12분 30초" · "5분" · "45초" → 초. 못 읽으면 null.
  function parseRemainingSeconds(text) {
    const s = String(text == null ? '' : text);
    let m = s.match(/(?<!\d)(\d{1,2}):(\d{2}):(\d{2})(?!\d)/);
    if (m) return Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3]);
    m = s.match(/(?<!\d)(\d{1,3}):(\d{2})(?!\d)/);
    if (m && Number(m[2]) < 60) return Number(m[1]) * 60 + Number(m[2]);
    m = s.match(/(?:(\d{1,3})\s*시간)?\s*(?:(\d{1,3})\s*분)?\s*(?:(\d{1,3})\s*초)?/);
    if (m && (m[1] || m[2] || m[3])) return Number(m[1] || 0) * 3600 + Number(m[2] || 0) * 60 + Number(m[3] || 0);
    return null;
  }

  // 글자 조각들(화면의 짧은 글)에서 남은 시간을 고른다. "남은 시간" 같은 말이 든 조각만 보고,
  // 서로 다른 값이 둘 이상이면(어느 것이 맞는지 모르므로) null.
  function findRemainingSeconds(texts) {
    const values = new Set();
    for (const raw of texts || []) {
      const t = String(raw == null ? '' : raw).replace(/\s+/g, ' ').trim();
      if (!t || t.length > 40 || !KEYWORDS.test(t)) continue;
      const v = parseRemainingSeconds(t);
      if (v !== null) values.add(v);
    }
    return values.size === 1 ? [...values][0] : null;
  }

  // 단추 후보 [{text, disabled, visible}] 에서 연장 단추를 고른다. 딱 하나일 때만 {index}.
  function pickExtendButton(candidates) {
    const hits = [];
    (candidates || []).forEach((c, i) => {
      if (!c || c.disabled || c.visible === false) return;
      if (BUTTON_TEXT.test(String(c.text || '').replace(/\s+/g, ''))) hits.push(i);
    });
    if (hits.length === 1) return { index: hits[0] };
    return { index: -1, reason: hits.length ? 'many' : 'none' };
  }

  // 한 번 살펴본 뒤 할 일. state = {attempts, lastClickAt, lastExtendedAt}. 돌려줌: {action:'click'|'none', status, state}
  // status: unknown(시간 못 읽음) · waiting(5분 넘게 남음) · no-button · many-buttons · clicked · stuck(눌러도 안 늘어남)
  function nextStep(state, now, remaining, pick) {
    const st = { attempts: 0, lastClickAt: 0, lastExtendedAt: 0, ...state };
    if (remaining === null || remaining === undefined) return { action: 'none', status: 'unknown', state: st };
    if (remaining > THRESHOLD_SECONDS) {
      // 눌렀던 뒤 시간이 다시 늘었으면 연장이 된 것: 그때 누른 시각을 '마지막 연장'으로 남기고 다음 번을 위해 되돌린다
      return { action: 'none', status: 'waiting', state: { attempts: 0, lastClickAt: 0, lastExtendedAt: st.lastClickAt || st.lastExtendedAt } };
    }
    if (!pick || pick.index < 0) {
      return { action: 'none', status: pick && pick.reason === 'many' ? 'many-buttons' : 'no-button', state: st };
    }
    if (st.attempts >= MAX_ATTEMPTS) return { action: 'none', status: 'stuck', state: st };
    if (st.lastClickAt && now - st.lastClickAt < RETRY_GAP_MS) return { action: 'none', status: 'clicked', state: st };
    return { action: 'click', status: 'clicked', state: { ...st, attempts: st.attempts + 1, lastClickAt: now } };
  }

  const STATUS_TEXT = {
    off: '연장 멈춤',
    unknown: '남은 시간을 못 읽음',
    waiting: '지켜보는 중',
    'no-button': '연장 단추를 못 찾음',
    'many-buttons': '연장 단추가 여러 개라 안 누름',
    clicked: '연장 눌렀어요',
    stuck: '눌렀는데 안 늘어남',
  };

  function pad(n) { return String(n).padStart(2, '0'); }
  function clock(ms) { const d = new Date(ms); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; }
  function badgeText(enabled, status, lastExtendedAt) {
    if (!enabled) return '🔒 ' + STATUS_TEXT.off;
    const base = (status === 'waiting' ? '🟢 ' : '🟡 ') + (STATUS_TEXT[status] || STATUS_TEXT.waiting);
    return lastExtendedAt ? `${base} · 마지막 연장 ${clock(lastExtendedAt)}` : base;
  }

  // ──────── 화면(브라우저에서만) ────────
  function realVisible(el) {
    return Boolean(el && (el.offsetParent !== null || (el.getClientRects && el.getClientRects().length)));
  }

  function shortTexts(doc) {
    return Array.from(doc.querySelectorAll('span,div,strong,em,b,p,label,li,td,th,a'))
      .map(el => el.textContent || '').filter(t => t.length > 0 && t.length <= 40);
  }

  function buttonCandidates(doc, isVisible = realVisible) {
    const els = Array.from(doc.querySelectorAll('button,a,input[type=button],input[type=submit],[role=button]'));
    return {
      els,
      list: els.map(el => ({
        text: el.tagName === 'INPUT' ? (el.value || '') : (el.textContent || ''),
        disabled: Boolean(el.disabled) || (el.getAttribute && el.getAttribute('aria-disabled') === 'true'),
        visible: isVisible(el),
      })),
    };
  }

  function start() {
    let enabled = true;
    let state = { attempts: 0, lastClickAt: 0, lastExtendedAt: 0 };
    let status = 'waiting';
    const badge = document.createElement('div');
    badge.id = 'neis-session-keeper';
    badge.style.cssText = 'position:fixed;left:8px;bottom:8px;z-index:2147483000;padding:3px 8px;border-radius:10px;background:rgba(0,0,0,.65);color:#fff;font:12px/1.4 sans-serif;cursor:pointer;user-select:none';
    badge.title = '누르면 자동 연장을 끄고 켭니다';
    const paint = () => { badge.textContent = badgeText(enabled, status, state.lastExtendedAt); };
    const tick = () => {
      if (!enabled) { status = 'off'; paint(); return; }
      const remaining = findRemainingSeconds(shortTexts(document));
      const { els, list } = buttonCandidates(document);
      const pick = remaining !== null && remaining <= THRESHOLD_SECONDS ? pickExtendButton(list) : null;
      const step = nextStep(state, Date.now(), remaining, pick);
      state = step.state;
      status = step.status;
      if (step.action === 'click') els[pick.index].click();   // 연장 단추 말고는 아무것도 누르지 않는다
      paint();
    };
    badge.addEventListener('click', () => {
      enabled = !enabled;
      try { chrome.storage.local.set({ [STORAGE_KEY]: enabled }); } catch (e) { /* 저장 못 해도 이번 화면은 바뀜 */ }
      tick();
    });
    try {
      chrome.storage.local.get(STORAGE_KEY, v => { if (v && v[STORAGE_KEY] === false) enabled = false; tick(); });
    } catch (e) { /* 저장소가 없으면 기본(켜짐) */ }
    document.documentElement.appendChild(badge);
    paint();
    setInterval(tick, CHECK_INTERVAL_MS);
  }

  const api = { parseRemainingSeconds, findRemainingSeconds, pickExtendButton, nextStep, badgeText, shortTexts, buttonCandidates, THRESHOLD_SECONDS, RETRY_GAP_MS, MAX_ATTEMPTS };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else if (typeof document !== 'undefined' && window.top === window) start();   // 맨 위 화면에서만(안쪽 틀은 확인 필요)
})();
