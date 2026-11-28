// ✅ 제출 확인표 (T108). 순수 함수(위)는 Node 로 시험하고, 화면 코드(아래)는 index.html 의 esc·post·toast 를 쓴다.
// 이름은 서버가 이 PC 에 roster.txt 가 있을 때만 보내며, 화면에만 쓰고 복사 글에는 번호만 넣는다.

// 번호 칸 하나의 모양: 냈으면 '✓', 아니면 번호. 명단이 있으면 이름을 title 로.
function submissionCells(rec, roster) {
  const total = Number(rec && rec.total) || 0;
  const marks = (rec && rec.marks) || {};
  const names = roster || {};
  const cells = [];
  for (let no = 1; no <= total; no++) {
    const date = marks[String(no)] || '';
    cells.push({ no, done: Boolean(date), date, name: names[String(no)] || '' });
  }
  return cells;
}

// "12명 중 9명 냈어요" / 다 냈으면 "모두 냈어요"
function submissionSummary(rec) {
  const total = Number(rec && rec.total) || 0;
  const done = submissionCells(rec, null).filter(c => c.done).length;
  if (total > 0 && done === total) return '모두 냈어요';
  return `${total}명 중 ${done}명 냈어요`;
}

// 알림장에 붙일 글(서버 missing_text 와 같은 모양, 이름 없이 번호만)
function submissionMissingText(rec) {
  const left = submissionCells(rec, null).filter(c => !c.done).map(c => c.no);
  if (!left.length) return `${rec.title}: 모두 냈어요.`;
  return `${rec.title} 아직 안 낸 번호: ${left.join(', ')}번`;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { submissionCells, submissionSummary, submissionMissingText };
}

// ──────── 화면 (브라우저에서만) ────────
if (typeof document !== 'undefined' && document.getElementById('subBox')) {
  let subOpen = '';
  const subApi = async (query) => (await fetch('/api/submissions' + query)).json().catch(() => ({ status: 'error' }));

  async function subRenderList() {
    const j = await subApi('');
    const box = document.getElementById('subBody');
    if (j.status !== 'success') { box.textContent = '확인표를 불러오지 못했어요.'; return; }
    box.innerHTML = `<div class="row"><input id="subTitle" type="text" placeholder="새 확인표 제목 (예: 현장학습 동의서)" style="flex:1;min-width:140px">
      <input id="subTotal" type="number" min="1" max="60" value="${esc(j.class_size || 25)}" style="width:64px" title="반 인원"><button type="button" id="subNew">만들기</button></div>
      <div id="subItems">${j.items.map(it => `<button type="button" class="sub-item" data-title="${esc(it.title)}">${esc(it.title)} · ${it.done}/${it.total}</button>`).join('') || '<p class="muted">아직 확인표가 없어요.</p>'}</div>`;
    document.getElementById('subNew').onclick = async () => {
      const title = document.getElementById('subTitle').value.trim();
      const r = await post('/api/submissions', { action: 'create', title, total: Number(document.getElementById('subTotal').value) });
      if (r.status === 'success') { subOpen = title; subRenderOne(); }
    };
    box.querySelectorAll('.sub-item').forEach(b => { b.onclick = () => { subOpen = b.dataset.title; subRenderOne(); }; });
  }

  async function subRenderOne() {
    const j = await subApi('?title=' + encodeURIComponent(subOpen));
    const box = document.getElementById('subBody');
    if (j.status !== 'success') { subOpen = ''; return subRenderList(); }
    const rec = j.record;
    box.innerHTML = `<div class="row"><b>${esc(rec.title)}</b><span class="muted">${esc(submissionSummary(rec))}</span><button type="button" id="subBack">← 목록</button><button type="button" id="subCopy">📋 안 낸 번호 복사</button></div>
      <div class="sub-grid">${submissionCells(rec, j.roster).map(c => `<button type="button" class="sub-cell${c.done ? ' on' : ''}" data-no="${c.no}" title="${esc(c.name)}">${c.done ? '✓' : ''}${c.no}${c.name ? `<small>${esc(c.name)}</small>` : ''}</button>`).join('')}</div>`;
    document.getElementById('subBack').onclick = () => { subOpen = ''; subRenderList(); };
    document.getElementById('subCopy').onclick = async () => {
      try { await navigator.clipboard.writeText(submissionMissingText(rec)); toast('안 낸 번호를 복사했어요'); } catch (e) { toast('복사하지 못했어요'); }
    };
    box.querySelectorAll('.sub-cell').forEach(b => {
      b.onclick = async () => {
        const done = !b.classList.contains('on');
        const r = await post('/api/submissions', { action: 'mark', title: rec.title, no: Number(b.dataset.no), done });
        if (r.status === 'success') subRenderOne();
      };
    });
  }

  document.getElementById('subBox').addEventListener('toggle', e => { if (e.target.open) (subOpen ? subRenderOne() : subRenderList()); });
}
