/* 📅 오늘·이번 주 일정과 할 일 칸 (T107). 서버(/api/agenda)가 일정DB 시트를 읽어 준다.
 * 위쪽에는 개수만 한 줄로 보이고(화면을 학생들과 함께 볼 수 있음), 누르면 내용이 펼쳐진다.
 * 순수 함수(breakLine·agendaList·quickAdd)는 node 로 시험한다(tests/test_agenda.js). */

const agendaEsc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const agendaMinutes = t => { const [h, m] = String(t).split(':').map(Number); return h * 60 + m; };

/** 쉬는 시간(교시와 교시 사이)이면 '다음 교시 과목 · 오늘 할 일 수' 한 줄, 아니면 ''. due 를 모르면 null. */
function breakLine(periods, lessons, minutes, due) {
  const list = (periods || []).slice().sort((a, b) => agendaMinutes(a.start) - agendaMinutes(b.start));
  for (let i = 1; i < list.length; i++) {
    if (minutes < agendaMinutes(list[i - 1].end) || minutes >= agendaMinutes(list[i].start)) continue;
    const no = list[i].no;
    const names = [...new Set((lessons || []).filter(l => Number(l.period) === Number(no)).map(l => l.subject).filter(Boolean))];
    const todo = due === null || due === undefined ? '' : due ? ` · 오늘까지 할 일 ${due}개` : ' · 오늘까지 할 일 없음';
    return `☕ 쉬는 시간 · 다음 ${no}교시 ${names.join('·') || '수업 없음'}${todo}`;
  }
  return '';
}

/** 펼친 칸의 내용(HTML). */
function agendaList(data) {
  if (data.reason) return `<div class="agenda-reason">${agendaEsc(data.reason)}</div>`;
  const event = (e, withDate) => `<li>${withDate ? `${agendaEsc(e.when)} ` : ''}<span class="agenda-kind">${agendaEsc(e.category)}</span> ${agendaEsc(e.text)}</li>`;
  const task = t => `<li class="${t.left < 0 ? 'late' : t.left === 0 ? 'now' : ''}"><b>${agendaEsc(t.dday)}</b> ${agendaEsc(t.when)} ${agendaEsc(t.text)}</li>`;
  const section = (title, items, none) => `<h4>${agendaEsc(title)}</h4>${items.length ? `<ul>${items.join('')}</ul>` : `<div class="muted">${none}</div>`}`;
  const today = data.today || [], tasks = data.tasks || [], week = data.week || [];
  return section('오늘', today.map(e => event(e, false)), '등록된 행사 없음')
    + section('할 일', tasks.map(task), '30일 안에 할 일 없음')
    + (week.length ? section(data.week_label || '이번 주 남은 일정', week.map(e => event(e, true)), '') : '')
    + (tasks.length ? '<div class="muted">끝낸 할 일은 일정 시트의 상태 칸에 ✔ 를 적으면 사라져요.</div>' : '');
}

/** 빠른 할 일: 먼저 어떻게 읽히는지 받아 확인 창을 띄우고, '확인'일 때만 쓴다. 적었으면 true. */
async function quickAdd(text, send, ask) {
  if (!String(text || '').trim()) return false;
  const preview = await send({ text });
  if (preview.status !== 'success') return false;
  const p = preview.parsed;
  if (!ask(`일정 시트의 '빠른입력' 탭에 적을까요?\n\n${p.when} · ${p.category}\n${p.text}`)) return false;
  const done = await send({ text: preview.line, confirm: true });
  return done.written === true;
}

const AGENDA_CSS = `
.agenda{margin-top:8px;border:1px solid var(--line);border-radius:12px;padding:6px 10px;background:var(--card)}
.agenda summary{cursor:pointer;font-weight:700;font-size:14px}
.agenda-body{max-height:38vh;overflow:auto}  /* 입력 칸은 늘 보이게 목록만 굴린다 */
.agenda h4{margin:10px 0 2px;font-size:13px;color:var(--sub)}
.agenda ul{margin:0;padding:0;list-style:none}
.agenda li{padding:3px 0;font-size:14px;word-break:keep-all;overflow-wrap:anywhere}
.agenda li.now b{color:var(--warn)}
.agenda li.late b{color:var(--red)}
.agenda-kind{display:inline-block;font-size:12px;padding:0 7px;border-radius:9px;background:var(--fill)}
.agenda-reason{margin-top:8px;padding:8px 10px;border-radius:10px;background:var(--warn-soft);font-size:13px}
.agenda-add{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 2px}
.agenda-add input{flex:1 1 180px;min-width:0;font:inherit;padding:6px 9px;border:1px solid var(--line);border-radius:10px}
#breakLine{margin:-4px 2px 12px;font-weight:700;color:var(--acc);word-break:keep-all}
body.focus-mode #agendaBox,body.focus-mode #breakLine{display:none}
`;

let agendaData = null;

function tickBreakLine() {
  const line = document.getElementById('breakLine');
  if (!line) return;
  const now = new Date();
  let text = '';
  if (typeof S !== 'undefined' && S && S.date === iso(now)) {
    const due = agendaData && !agendaData.reason && agendaData.date === iso(now) ? agendaData.due_today : null;
    text = breakLine(S.periods, S.lessons, now.getHours() * 60 + now.getMinutes(), due);
  }
  line.textContent = text;
  line.hidden = !text;
}

async function loadAgenda(refresh) {
  try {
    const res = await fetch('/api/agenda' + (refresh ? '?refresh=1' : ''));
    agendaData = await res.json();
    if (!res.ok) agendaData = { reason: agendaData.message || '일정을 읽지 못했어요.' };
  } catch (e) {
    agendaData = { reason: '수업 비서 서버에서 일정을 받지 못했어요.' };
  }
  document.getElementById('agendaSum').textContent = agendaData.reason ? '📅 일정을 불러오지 못했어요 (눌러서 이유 보기)' : `📅 ${agendaData.summary}`;
  document.getElementById('agendaList').innerHTML = agendaList(agendaData);
  tickBreakLine();
}

function setupAgenda() {
  const above = document.getElementById('overdue'), hero = document.getElementById('hero');
  if (!above || !hero) return;
  const style = document.createElement('style');
  style.textContent = AGENDA_CSS;
  document.head.appendChild(style);
  above.insertAdjacentHTML('afterend', `<details id="agendaBox" class="agenda"><summary><span id="agendaSum">📅 일정 불러오는 중…</span></summary>
    <div class="agenda-body" id="agendaList"></div>
      <div class="agenda-add"><input id="agendaText" type="text" maxlength="200" placeholder="빠른 할 일 (예: 금요일 공문 마감)">
        <button type="button" id="agendaAdd">➕ 적기</button><button type="button" id="agendaRefresh" class="ghost">↻ 새로 읽기</button></div></details>`);
  hero.insertAdjacentHTML('afterend', '<div id="breakLine" hidden></div>');
  const input = document.getElementById('agendaText'), button = document.getElementById('agendaAdd');
  const add = async () => {
    if (button.disabled) return;
    button.disabled = true;  // 두 번 눌러 같은 줄이 두 번 적히지 않게
    try {
      if (await quickAdd(input.value, body => post('/api/agenda/add', body), m => window.confirm(m))) input.value = '';
    } catch (e) {
      toast('적지 못했어요. 시트의 빠른입력 탭을 확인한 뒤 다시 해 주세요.');
    } finally {
      button.disabled = false;
    }
  };
  button.onclick = add;
  input.onkeydown = e => { if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); add(); } };
  document.getElementById('agendaRefresh').onclick = () => loadAgenda(true);
  loadAgenda(false);
  setInterval(() => loadAgenda(false), 10 * 60 * 1000);
  setInterval(tickBreakLine, 5000);
}

if (typeof document !== 'undefined') setupAgenda();

if (typeof module !== 'undefined') {
  module.exports = { breakLine, agendaList, quickAdd };
}
