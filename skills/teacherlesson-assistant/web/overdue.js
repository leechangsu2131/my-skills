/**
 * overdue.js — 지난 미완료 차시 알림 (순수 함수, 브라우저/Node 공용) — ISSUE-043
 *
 * `/api/state` 의 `overdue` 목록(과목·차시·원래 날짜·교시)을 화면에 보여 줄 글로 바꾼다.
 * DOM 에 의존하지 않는다. 화면 연결(버튼 누르면 기존 확인 창)은 index.html 에서 한다.
 * Node 시험: tests/test_overdue.js
 */

/** 'YYYY-MM-DD' 두 날짜 사이 일수(앞 날짜 → 뒤 날짜). 형식이 틀리면 null. */
function daysBetween(fromIso, toIso) {
  const re = /^(\d{4})-(\d{2})-(\d{2})/;
  const a = re.exec(String(fromIso || '')), b = re.exec(String(toIso || ''));
  if (!a || !b) return null;
  const ms = (m) => Date.UTC(+m[1], +m[2] - 1, +m[3]);
  return Math.round((ms(b) - ms(a)) / 86400000);
}

/** 한 항목을 한 줄 글로. 예) "11/24 3교시 · 국어 5차시 실천하기 (1일 전)" */
function overdueLine(item, todayIso) {
  const m = /^\d{4}-(\d{2})-(\d{2})/.exec(String((item && item.planned_date) || ''));
  const when = m ? `${m[1]}/${m[2]}` : '날짜 없음';
  const period = item && item.period ? ` ${item.period}교시` : '';
  const ago = daysBetween(item && item.planned_date, todayIso);
  const agoText = ago !== null && ago > 0 ? ` (${ago}일 전)` : '';
  const lesson = item && item.lesson ? ` ${item.lesson}차시` : '';
  const title = item && item.title && item.title !== `${item.lesson}차시` ? ` ${item.title}` : '';
  return `${when}${period} · ${(item && item.subject) || ''}${lesson}${title}${agoText}`;
}

/** 알림 제목. 없으면 ''. */
function overdueSummary(items) {
  const n = Array.isArray(items) ? items.length : 0;
  return n ? `지난 미완료 ${n}개` : '';
}

/** 오래된 날짜가 위로 오게 정렬한 새 배열(원본은 건드리지 않음). */
function sortOverdue(items) {
  return (Array.isArray(items) ? items : []).slice().sort((a, b) =>
    String(a.planned_date || '').localeCompare(String(b.planned_date || '')) || (a.period || 99) - (b.period || 99));
}

/**
 * 가져오기 방식 고르기: 지금 보는 교시(cur)와 같은 과목이면 'catch-up'(같은 과목 차시 고르기),
 * 다른 과목이면 'replace'(과목·차시 바꾸기). 지금 교시가 없거나 예정(planned)이 아니면 null.
 */
function bringMode(item, cur) {
  if (!item || !cur || !cur.record_key || !cur.slot_id || cur.status !== 'planned') return null;
  return item.subject === cur.subject ? 'catch-up' : 'replace';
}

if (typeof module !== 'undefined') {
  module.exports = { daysBetween, overdueLine, overdueSummary, sortOverdue, bringMode };
}
