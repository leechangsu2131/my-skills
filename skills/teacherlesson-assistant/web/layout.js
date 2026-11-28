/**
 * layout.js — 어두운 화면, 칸 접기·숨기기 (T110). 설정은 이 브라우저의 localStorage 에만 둔다.
 *
 * 칸을 직접 고치지 않고 <style> 한 덩어리로만 접고 숨긴다. 그래서 다른 스크립트가 나중에 넣는 칸에도 그대로 걸리고,
 * 🎯 수업 진행 화면(body.focus-mode)에는 아무 규칙도 걸리지 않는다.
 * 새 칸을 목록에 넣으려면 PANELS 에 한 줄 더하거나, 그 칸에 data-panel="영문id" data-panel-title="이름" 을 단다.
 * Node 시험: tests/test_layout.js
 */
'use strict';

(function () {
  const KEY = 'ta.layout.v1';
  const MODES = ['open', 'fold', 'hide'];
  const PANELS = [
    { id: 'hero', title: '지금 할 일', sel: '#hero' },
    { id: 'sites', title: '수업 사이트 단추', sel: '#siteBtns' },
    { id: 'record', title: '수업 기록·메모', sel: 'main > section.card:has(#recbar)' },
    { id: 'agenda', title: '일정·할 일', sel: '#agendaBox' },
    { id: 'ment', title: '대응 멘트', sel: '#ment' },
    { id: 'caution', title: '주의할 점', sel: '#cautionBox' },
    { id: 'flow', title: '수업 흐름 전체', sel: '#flowBox' },
    { id: 'unit', title: '단원 개관', sel: '#unitBox' },
    { id: 'ai', title: 'AI와 수업 준비', sel: '#aiBox' },
    { id: 'submissions', title: '제출 확인표', sel: '#subBox' },
    { id: 'notice', title: '알림장·숙제', sel: 'main > details.fold:has(#notice)' },
    { id: 'progress', title: '진도 조정', sel: 'main > details.fold:has(#catchBtn)' },
    { id: 'links', title: '바로가기', sel: 'main > details.fold:has(#links)' },
    { id: 'tools', title: '교실 도구', sel: '#classToolsBox' },
  ];

  /** 저장된 글 → 설정. 깨졌거나 모르는 값은 기본(밝은 화면, 모두 보이기). */
  function parsePrefs(text) {
    let raw = null;
    try { raw = JSON.parse(text); } catch (e) { /* 아래에서 기본값 */ }
    const prefs = { theme: raw && raw.theme === 'dark' ? 'dark' : 'light', panels: {} };
    const panels = raw && typeof raw.panels === 'object' && raw.panels ? raw.panels : {};
    for (const [id, mode] of Object.entries(panels)) {
      if (/^[a-z0-9_-]+$/i.test(id) && (mode === 'fold' || mode === 'hide')) prefs.panels[id] = mode;
    }
    return prefs;
  }

  function setMode(prefs, id, mode) {
    const panels = { ...prefs.panels };
    if (mode === 'fold' || mode === 'hide') panels[id] = mode; else delete panels[id];
    return { theme: prefs.theme, panels };
  }

  /** 접기·숨기기 설정 → CSS. 선택자마다 규칙을 따로 써서 하나가 안 먹혀도 나머지는 걸린다. */
  function buildCss(prefs, panels) {
    const out = [];
    for (const p of panels) {
      const mode = prefs.panels[p.id];
      const sel = `body:not(.focus-mode) ${p.sel}`;
      if (mode === 'hide') out.push(`${sel}{display:none!important}`);
      if (mode === 'fold') {
        const label = `▸ ${p.title} — 눌러서 펼치기`.replace(/["\\\n\r]/g, ' ');
        out.push(`${sel}{cursor:pointer;padding:0!important;min-height:0!important}`);
        out.push(`${sel}>*{display:none!important}`);
        out.push(`${sel}::before{content:"${label}";display:block;padding:12px 16px;font-size:14px;font-weight:600;color:var(--sub)}`);
      }
    }
    return out.join('\n');
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PANELS, MODES, parsePrefs, setMode, buildCss };
  }
  if (typeof document === 'undefined') return;

  function load() {
    try { return parsePrefs(localStorage.getItem(KEY)); } catch (e) { return parsePrefs(null); }
  }
  let prefs = load();

  function allPanels() {
    const extra = [...document.querySelectorAll('[data-panel]')]
      .filter(el => /^[a-z0-9_-]+$/i.test(el.dataset.panel) && !PANELS.some(p => p.id === el.dataset.panel))
      .map(el => ({ id: el.dataset.panel, title: el.dataset.panelTitle || el.dataset.panel, sel: `[data-panel="${el.dataset.panel}"]` }));
    return PANELS.concat(extra);
  }

  const style = document.createElement('style');
  style.id = 'layoutStyle';

  function apply() {
    document.documentElement.dataset.theme = prefs.theme;
    style.textContent = buildCss(prefs, allPanels());
    const btn = document.getElementById('themeBtn');
    if (btn) btn.textContent = prefs.theme === 'dark' ? '☀ 밝은 화면으로' : '🌙 어두운 화면으로';
  }

  function save(next) {
    prefs = next;
    try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch (e) { /* 저장이 안 되면 이번 창에서만 */ }
    apply();
  }

  const exists = sel => { try { return !!document.querySelector(sel); } catch (e) { return false; } };

  function drawRows(list) {
    list.textContent = '';
    for (const p of allPanels().filter(p => exists(p.sel))) {
      const row = document.createElement('label');
      row.className = 'layout-row';
      const name = document.createElement('span');
      name.textContent = p.title;
      const pick = document.createElement('select');
      for (const [value, text] of [['open', '보이기'], ['fold', '접기'], ['hide', '숨기기']]) {
        pick.add(new Option(text, value));
      }
      pick.value = prefs.panels[p.id] || 'open';
      pick.onchange = () => save(setMode(prefs, p.id, pick.value));
      row.append(name, pick);
      list.append(row);
    }
  }

  function buildBox() {
    const main = document.querySelector('main');
    if (!main) return;
    const box = document.createElement('details');
    box.className = 'fold';
    box.id = 'layoutBox';
    box.innerHTML = '<summary>🎨 화면 설정 <span class="muted">(이 컴퓨터·브라우저에만 저장)</span></summary>' +
      '<div class="fold-body"><div class="row"><button type="button" id="themeBtn"></button>' +
      '<button type="button" id="layoutReset">모두 보이기</button></div><div id="layoutList"></div></div>';
    main.append(box);
    const list = box.querySelector('#layoutList');
    box.addEventListener('toggle', () => { if (box.open) drawRows(list); });
    box.querySelector('#themeBtn').onclick = () => save({ ...prefs, theme: prefs.theme === 'dark' ? 'light' : 'dark' });
    box.querySelector('#layoutReset').onclick = () => { save({ theme: prefs.theme, panels: {} }); drawRows(list); };
  }

  // 접힌 칸을 누르면 펼친다(칸 안의 것은 숨겨져 있어 누른 곳은 칸 자체다)
  document.addEventListener('click', e => {
    if (document.body.classList.contains('focus-mode')) return;
    const hit = allPanels().find(p => {
      if (prefs.panels[p.id] !== 'fold') return false;
      try { return !!e.target.closest(p.sel); } catch (err) { return false; }
    });
    if (!hit) return;
    e.preventDefault();
    save(setMode(prefs, hit.id, 'open'));
    const list = document.getElementById('layoutList');
    if (list && list.childElementCount) drawRows(list);
  }, true);

  document.documentElement.dataset.theme = prefs.theme;   // 그리기 전에 먼저(번쩍임 방지)
  function start() {
    document.head.append(style);
    buildBox();
    apply();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
