// 🌙 화면 설정 (T110): 밝은/어두운 화면, 칸 접기·숨기기. 설정은 이 브라우저(localStorage)에만 저장한다.
// 위쪽은 순수 함수(Node 로 시험), 아래는 브라우저에서만 도는 화면 코드. 수업 진행(🎯) 화면은 건드리지 않는다.
const LAYOUT_KEY = 'lessonAssistantLayout';
const LAYOUT_THEMES = ['light', 'dark'];

// 저장된 글/객체 → {theme, hidden:[키], folded:{키:true|false}}. 이상한 값은 기본값으로.
function normalizeLayout(raw) {
  let v = raw;
  if (typeof raw === 'string') {
    try { v = JSON.parse(raw); } catch (e) { v = null; }
  }
  if (!v || typeof v !== 'object' || Array.isArray(v)) v = {};
  const folded = {};
  if (v.folded && typeof v.folded === 'object' && !Array.isArray(v.folded)) {
    for (const k of Object.keys(v.folded)) if (typeof v.folded[k] === 'boolean') folded[k] = v.folded[k];
  }
  return {
    theme: LAYOUT_THEMES.includes(v.theme) ? v.theme : 'light',
    hidden: Array.isArray(v.hidden) ? [...new Set(v.hidden.filter(k => typeof k === 'string' && k))] : [],
    folded,
  };
}

// 칸 키: id 가 있으면 id, 없으면 제목 글(앞 24자). 같은 키가 겹치면 뒤에 -2, -3.
function panelKeys(items) {
  const seen = {};
  return items.map(({ id, title }) => {
    const base = id ? `#${id}` : `t:${String(title || '').replace(/\s+/g, ' ').trim().slice(0, 24)}`;
    seen[base] = (seen[base] || 0) + 1;
    return seen[base] === 1 ? base : `${base}-${seen[base]}`;
  });
}

function toggleHidden(layout, key) {
  const hidden = layout.hidden.includes(key) ? layout.hidden.filter(k => k !== key) : [...layout.hidden, key];
  return { ...layout, hidden };
}

function setFolded(layout, key, folded) {
  return { ...layout, folded: { ...layout.folded, [key]: Boolean(folded) } };
}

function nextTheme(theme) {
  return theme === 'dark' ? 'light' : 'dark';
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { normalizeLayout, panelKeys, toggleHidden, setFolded, nextTheme, LAYOUT_KEY };
}

// ──────── 화면 (브라우저에서만) ────────
if (typeof document !== 'undefined') {
  let layout = normalizeLayout(null);
  const readStore = () => { try { return localStorage.getItem(LAYOUT_KEY); } catch (e) { return null; } };
  const save = () => { try { localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout)); } catch (e) { /* 저장 못 해도 화면은 계속 */ } };
  const applyTheme = () => { document.documentElement.dataset.theme = layout.theme; };

  layout = normalizeLayout(readStore());
  applyTheme(); // 깜박임 없게 head 에서 바로

  document.addEventListener('DOMContentLoaded', () => {
    const main = document.querySelector('main');
    if (!main) return;
    const panels = [...main.children].filter(el => el.id === 'hero' || el.matches('section.card, details.fold'));
    const titleOf = el => {
      if (el.id === 'hero') return '지금 할 일';
      const t = el.querySelector(':scope > h2, :scope > summary');
      return t ? t.textContent.replace(/\(.*?\)/g, '') : '';
    };
    const keys = panelKeys(panels.map(el => ({ id: el.id, title: titleOf(el) })));
    const render = () => {
      panels.forEach((el, i) => {
        // class 가 아니라 속성으로 표시한다 — index.html 이 hero.className 을 통째로 다시 써도 지워지지 않게
        el.toggleAttribute('data-layout-hidden', layout.hidden.includes(keys[i]));
        if (keys[i] in layout.folded && el.id !== 'hero') {
          if (el.tagName === 'DETAILS') el.open = !layout.folded[keys[i]];
          else el.toggleAttribute('data-layout-collapsed', layout.folded[keys[i]]);
        }
      });
      const list = document.getElementById('layoutList');
      if (list) {
        list.innerHTML = panels.map((el, i) => `<label><input type="checkbox" data-i="${i}" ${layout.hidden.includes(keys[i]) ? '' : 'checked'}> ${titleOf(el).trim() || keys[i]}</label>`).join('');
      }
      const tb = document.getElementById('themeBtn');
      if (tb) tb.textContent = layout.theme === 'dark' ? '☀ 밝은 화면으로' : '🌙 어두운 화면으로';
    };
    panels.forEach((el, i) => {
      if (el.tagName === 'DETAILS') {
        el.addEventListener('toggle', () => { layout = setFolded(layout, keys[i], !el.open); save(); });
      } else if (el.id !== 'hero') {
        const h = el.querySelector(':scope > h2');
        if (h) {
          h.classList.add('layout-fold-head');
          h.title = '눌러서 접기·펴기';
          h.addEventListener('click', () => { layout = setFolded(layout, keys[i], !el.hasAttribute('data-layout-collapsed')); save(); render(); });
        }
      }
    });
    const btn = document.getElementById('layoutBtn');
    const pop = document.getElementById('layoutPanel');
    if (btn && pop) {
      btn.addEventListener('click', () => { pop.hidden = !pop.hidden; });
      pop.addEventListener('change', e => {
        const box = e.target.closest('input[data-i]');
        if (box) { layout = toggleHidden(layout, keys[Number(box.dataset.i)]); save(); render(); }
      });
      document.getElementById('themeBtn').addEventListener('click', () => { layout = { ...layout, theme: nextTheme(layout.theme) }; save(); applyTheme(); render(); });
      document.getElementById('layoutReset').addEventListener('click', () => { layout = normalizeLayout(null); save(); applyTheme(); panels.forEach(el => { el.removeAttribute('data-layout-collapsed'); if (el.tagName === 'DETAILS') el.open = el.id === 'cautionBox'; }); render(); });
    }
    render();
  });
}
