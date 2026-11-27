function renderOverdue(items) {
  const box = document.getElementById('overdue');
  if (!box) return;
  box.hidden = !items.length;
  if (!items.length) {
    box.innerHTML = '';
    return;
  }
  box.innerHTML = `<details class="overdue-banner" open><summary>지난 미완료 ${items.length}개</summary>${items.map((item, index) => {
    const lesson = item.lesson ? `${esc(item.lesson)}차시 · ` : '';
    const period = item.original_period ? `${esc(item.original_period)}교시` : '교시 없음';
    return `<div class="overdue-item"><span><b>${esc(item.subject)} ${lesson}${esc(item.title)}</b><br>${esc(item.original_date)} · ${period}</span><button type="button" data-overdue="${index}">이 교시로 가져오기</button></div>`;
  }).join('')}</details>`;
  box.onclick = event => {
    const button = event.target.closest('button[data-overdue]');
    if (!button) return;
    const item = items[Number(button.dataset.overdue)];
    if (item) replaceWithLesson(item, item.subject);
  };
}
