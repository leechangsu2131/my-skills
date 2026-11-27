/**
 * tests/test_overdue.js — web/overdue.js (지난 미완료 차시 알림) 순수 함수 시험
 * 실행: node tests/test_overdue.js   (Node 내장만 사용)
 */
'use strict';
const assert = require('assert');
const path = require('path');
const { daysBetween, overdueLine, overdueSummary, sortOverdue, bringMode } =
  require(path.join(__dirname, '..', 'web', 'overdue.js'));

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log(`  ✓ ${name}`); }
  catch (e) { failed++; console.log(`  ✗ ${name}\n      ${e.message}`); }
}

const item = { period: 3, subject: '국어', lesson: '5', title: '실천하기', planned_date: '2026-11-24', record_key: 'lesson-0410' };

console.log('daysBetween');
test('하루 차이', () => assert.strictEqual(daysBetween('2026-11-24', '2026-11-25'), 1));
test('같은 날은 0', () => assert.strictEqual(daysBetween('2026-11-25', '2026-11-25'), 0));
test('달·해를 넘겨도 맞다', () => { assert.strictEqual(daysBetween('2026-10-31', '2026-11-02'), 2); assert.strictEqual(daysBetween('2025-12-31', '2026-01-01'), 1); });
test('앞이 더 늦으면 음수', () => assert.strictEqual(daysBetween('2026-11-26', '2026-11-25'), -1));
test('형식이 틀리면 null', () => { assert.strictEqual(daysBetween('', '2026-11-25'), null); assert.strictEqual(daysBetween(null, undefined), null); assert.strictEqual(daysBetween('11/24', '2026-11-25'), null); });
test('시각이 붙어도 날짜만 본다', () => assert.strictEqual(daysBetween('2026-11-24T09:00:00', '2026-11-25 00:00:00'), 1));

console.log('overdueLine');
test('날짜·교시·과목·차시·제목·며칠 전', () => assert.strictEqual(overdueLine(item, '2026-11-25'), '11/24 3교시 · 국어 5차시 실천하기 (1일 전)'));
test('제목이 "N차시" 와 같으면 반복하지 않는다', () => assert.strictEqual(overdueLine({ ...item, title: '5차시' }, '2026-11-25'), '11/24 3교시 · 국어 5차시 (1일 전)'));
test('교시가 없으면 교시를 빼고, 날짜가 없으면 "날짜 없음"', () => {
  assert.strictEqual(overdueLine({ ...item, period: null }, '2026-11-25'), '11/24 · 국어 5차시 실천하기 (1일 전)');
  assert.strictEqual(overdueLine({ ...item, planned_date: '' }, '2026-11-25'), '날짜 없음 3교시 · 국어 5차시 실천하기');
});
test('오늘 날짜면 "며칠 전"을 붙이지 않는다', () => assert.ok(!overdueLine({ ...item, planned_date: '2026-11-25' }, '2026-11-25').includes('전')));
test('빈 값도 죽지 않는다', () => assert.strictEqual(typeof overdueLine({}, '2026-11-25'), 'string'));

console.log('overdueSummary / sortOverdue');
test('개수 글', () => { assert.strictEqual(overdueSummary([item, item]), '지난 미완료 2개'); assert.strictEqual(overdueSummary([]), ''); assert.strictEqual(overdueSummary(null), ''); });
test('오래된 날짜가 위, 같은 날은 교시 순, 원본은 그대로', () => {
  const a = { ...item, planned_date: '2026-11-24', period: 4 }, b = { ...item, planned_date: '2026-11-23', period: 5 }, c = { ...item, planned_date: '2026-11-24', period: 2 };
  const src = [a, b, c];
  assert.deepStrictEqual(sortOverdue(src), [b, c, a]);
  assert.deepStrictEqual(src, [a, b, c]);
  assert.deepStrictEqual(sortOverdue(undefined), []);
});

console.log('bringMode');
const cur = { subject: '국어', record_key: 'lesson-0411', slot_id: 's1', status: 'planned' };
test('같은 과목이면 catch-up', () => assert.strictEqual(bringMode(item, cur), 'catch-up'));
test('다른 과목이면 replace', () => assert.strictEqual(bringMode(item, { ...cur, subject: '수학' }), 'replace'));
test('지금 교시가 없거나 예정이 아니거나 슬롯이 없으면 null', () => {
  assert.strictEqual(bringMode(item, null), null);
  assert.strictEqual(bringMode(item, { ...cur, status: 'completed' }), null);
  assert.strictEqual(bringMode(item, { ...cur, slot_id: '' }), null);
  assert.strictEqual(bringMode(item, { ...cur, record_key: '' }), null);
  assert.strictEqual(bringMode(null, cur), null);
});

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
