/**
 * ment.js — 💬 학생 대응 멘트 도우미 (T106). AI 를 부르지 않고 web/ment.json 의 문장만 보여 준다.
 *
 * 위쪽은 화면 없이 시험되는 순수 함수(브라우저·Node 공용), 아래쪽(initMent)은 화면 연결이다.
 * Node 시험: tests/test_ment.js   ·   서버: assistant_server.py 의 /api/ment*
 */

const MENT_FOCUS_KEY = 'ment.focus';

/** 'YYYY-MM-DD' → 그 주 월요일 'YYYY-MM-DD' (시간대와 상관없이 날짜만 계산). 모양이 틀리면 null. */
function mentMonday(dayText) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(dayText || ''));
  if (!m) return null;
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  if (d.getUTCFullYear() !== +m[1] || d.getUTCMonth() !== +m[2] - 1 || d.getUTCDate() !== +m[3]) return null;
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
}

/**
 * 저장해 둔 '이번 주 집중 하나' 가 지금도 유효한지 본다.
 * 같은 주(월~일)이고 그 상황이 아직 목록에 있을 때만 상황을 돌려주고, 아니면 null.
 * @param {{id:string, day:string}|null} stored
 * @param {Array<{id:string}>} situations
 * @param {string} today  'YYYY-MM-DD'
 */
function mentFocusActive(stored, situations, today) {
  if (!stored || typeof stored !== 'object') return null;
  const week = mentMonday(today);
  if (!week || mentMonday(stored.day) !== week) return null;
  return (situations || []).find(s => s.id === stored.id) || null;
}

/** 한 상황의 대답을 화면 순서(기본 문장 → 교사가 덧붙인 것)로 [{text, custom, index}] 로 만든다. index 는 custom 안의 번호. */
function mentAnswers(situation) {
  const base = ((situation && situation.answers) || []).map(text => ({ text, custom: false, index: -1 }));
  const mine = ((situation && situation.custom) || []).map((text, index) => ({ text, custom: true, index }));
  return base.concat(mine);
}

/** 상황 단추 눈에 보이는 글 — 집중 상황은 ⭐ 를 붙인다. */
function mentButtonLabel(situation, focusId) {
  return `${situation.icon || ''} ${situation.label}${situation.id === focusId ? ' ⭐' : ''}`.trim();
}

/** 접었을 때 한 줄 — 집중 상황이 있으면 그 이름을 늘 보여 준다. */
function mentSummaryText(focus) {
  return focus ? `💬 학생 대응 멘트 · 이번 주 집중: ${focus.label}` : '💬 학생 대응 멘트';
}

function mentEsc(text) {
  return String(text == null ? '' : text).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

if (typeof module !== 'undefined') {
  module.exports = { MENT_FOCUS_KEY, mentMonday, mentFocusActive, mentAnswers, mentButtonLabel, mentSummaryText, mentEsc };
}

/* ── 화면 연결 (브라우저에서만) ───────────────────────────── */

(function () {
  if (typeof document === 'undefined') return;
  const memory = {};
  const store = {
    get(key) { try { return JSON.parse(localStorage.getItem(key)); } catch (e) { return memory[key] || null; } },
    set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { memory[key] = value; } },
    del(key) { try { localStorage.removeItem(key); } catch (e) { delete memory[key]; } },
  };
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
  let situations = [];
  let current = null;
  let note = '';

  const css = `
  #ment{position:fixed;right:12px;bottom:12px;z-index:30;width:min(360px,calc(100vw - 24px))}
  #ment details{background:var(--card,#fff);border:1px solid var(--line,#e5e5ea);border-radius:16px;box-shadow:0 6px 24px rgba(0,0,0,.18)}
  #ment summary{cursor:pointer;padding:10px 14px;font-weight:600;list-style:none}
  #ment summary::-webkit-details-marker{display:none}
  #ment .ment-body{padding:0 12px 12px;max-height:68vh;overflow:auto}
  #ment .ment-grid{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
  #ment .ment-grid button.on{background:var(--ink,#1d1d1f);color:var(--card,#fff)}
  #ment .ment-said{color:var(--sub,#6e6e73);font-size:13px;margin:2px 0 8px}
  #ment .ment-ans{border:1px solid var(--line,#e5e5ea);border-radius:12px;padding:10px 12px;margin-bottom:8px;font-size:17px;line-height:1.5}
  #ment .ment-ans small{display:block;margin-top:6px;color:var(--sub,#6e6e73);font-size:12px}
  #ment .ment-why{font-size:13px;color:var(--sub,#6e6e73);margin:4px 0 8px}
  #ment .ment-add{display:flex;gap:6px;margin-top:8px}
  #ment .ment-add input{flex:1;font:inherit;border:1px solid var(--line,#e5e5ea);border-radius:10px;padding:6px 8px;background:transparent;color:inherit}
  #ment .ment-note{font-size:12px;color:var(--sub,#6e6e73);margin-top:4px}`;

  function mount() {
    const host = document.getElementById('mentMount');
    if (!host) return;
    if (!document.getElementById('mentStyle')) {
      const style = document.createElement('style');
      style.id = 'mentStyle';
      style.textContent = css;
      document.head.appendChild(style);
    }
    host.id = 'ment';
    load();
  }

  async function load() {
    try {
      const r = await fetch('/api/ment');
      situations = (await r.json()).situations || [];
    } catch (e) { situations = []; }
    render();
  }

  function focusSituation() { return mentFocusActive(store.get(MENT_FOCUS_KEY), situations, today()); }

  function render() {
    const host = document.getElementById('ment');
    if (!host) return;
    const open = host.querySelector('details') ? host.querySelector('details').open : false;
    const focus = focusSituation();
    const focusId = focus ? focus.id : '';
    let body = '';
    if (!situations.length) {
      body = '<div class="ment-note">문장 파일(web/ment.json)을 읽지 못했어요.</div>';
    } else {
      body += '<div class="ment-grid">' + situations.map(s => `<button type="button" data-s="${mentEsc(s.id)}" class="${current && current.id === s.id ? 'on' : ''}">${mentEsc(mentButtonLabel(s, focusId))}</button>`).join('') + '</div>';
      if (current) {
        const isFocus = current.id === focusId;
        body += `<div class="ment-said">${mentEsc(current.said)}</div>`;
        body += mentAnswers(current).map(a => `<div class="ment-ans">${mentEsc(a.text)}<small><button type="button" data-copy="${mentEsc(a.text)}">📋 복사</button>${a.custom ? ` <button type="button" data-del="${a.index}">지우기</button> ✎ 내 대답` : ''}</small></div>`).join('');
        body += `<div class="ment-why"><b>${mentEsc(current.principle.name)}</b> — ${mentEsc(current.principle.note)}</div>`;
        body += `<button type="button" data-focus="${isFocus ? 'off' : 'on'}">${isFocus ? '⭐ 이번 주 집중 풀기' : '⭐ 이번 주 집중으로 두기'}</button>`;
        body += `<div class="ment-add"><input id="mentInput" maxlength="200" placeholder="내 대답 덧붙이기"><button type="button" data-add="1">추가</button></div>`;
      }
      if (note) body += `<div class="ment-note">${mentEsc(note)}</div>`;
    }
    host.innerHTML = `<details${open ? ' open' : ''}><summary>${mentEsc(mentSummaryText(focus))}</summary><div class="ment-body">${body}</div></details>`;
    host.querySelector('.ment-body').onclick = onClick;
  }

  async function post(path, body) {
    const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    return r.json();
  }

  async function onClick(event) {
    const t = event.target.closest('button');
    if (!t) return;
    note = '';
    if (t.dataset.s) {
      current = situations.find(s => s.id === t.dataset.s) || null;
      if (current) post('/api/ment-count', { situation: current.id }).catch(() => {});  // 세기만 — 실패해도 화면은 그대로
    } else if (t.dataset.copy !== undefined) {
      await copyText(t.dataset.copy);
      note = '복사했어요.';
    } else if (t.dataset.focus && current) {
      if (t.dataset.focus === 'on') store.set(MENT_FOCUS_KEY, { id: current.id, day: today() }); else store.del(MENT_FOCUS_KEY);
    } else if (t.dataset.add && current) {
      const input = document.getElementById('mentInput');
      const res = await post('/api/ment-custom', { situation: current.id, text: input ? input.value : '' });
      if (res.status === 'success') { current.custom = res.custom; } else { note = res.message || '추가하지 못했어요.'; }
    } else if (t.dataset.del !== undefined && current) {
      const res = await post('/api/ment-custom', { situation: current.id, delete: Number(t.dataset.del) });
      if (res.status === 'success') { current.custom = res.custom; } else { note = res.message || '지우지 못했어요.'; }
    }
    render();
  }

  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); return; } catch (e) { /* 아래 방법으로 */ }
    const area = document.createElement('textarea');
    area.value = text;
    document.body.appendChild(area);
    area.select();
    try { document.execCommand('copy'); } catch (e) { /* 복사 못 함 */ }
    area.remove();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
