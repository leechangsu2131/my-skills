// 제출 확인표(T108) 화면 순수 함수 시험:  node tests/test_submissions.js  (teacherlesson-assistant 폴더에서)
const assert = require('assert');
const { submissionCells, submissionSummary, submissionMissingText } = require('../web/submissions.js');

let pass = 0;
function t(name, fn) { fn(); pass++; console.log('ok -', name); }

const rec = { title: '동의서', total: 5, marks: { 2: '2026-11-28', 5: '2026-11-28' } };

t('칸은 1~total 번호 순서', () => assert.deepStrictEqual(submissionCells(rec).map(c => c.no), [1, 2, 3, 4, 5]));
t('낸 번호만 done', () => assert.deepStrictEqual(submissionCells(rec).filter(c => c.done).map(c => c.no), [2, 5]));
t('낸 날짜가 칸에 붙음', () => assert.strictEqual(submissionCells(rec)[1].date, '2026-11-28'));
t('명단이 있으면 이름, 없으면 빈 글', () => {
  assert.strictEqual(submissionCells(rec, { 3: '학생A' })[2].name, '학생A');
  assert.strictEqual(submissionCells(rec, null)[2].name, '');
  assert.strictEqual(submissionCells(rec)[0].name, '');
});
t('빈·이상한 기록은 빈 목록', () => {
  assert.deepStrictEqual(submissionCells(null), []);
  assert.deepStrictEqual(submissionCells({ title: 'x' }), []);
});
t('요약', () => assert.strictEqual(submissionSummary(rec), '5명 중 2명 냈어요'));
t('다 내면 모두 냈어요', () => assert.strictEqual(submissionSummary({ title: 'x', total: 2, marks: { 1: 'd', 2: 'd' } }), '모두 냈어요'));
t('0명은 모두 냈어요가 아님', () => assert.strictEqual(submissionSummary({ title: 'x', total: 0, marks: {} }), '0명 중 0명 냈어요'));
t('안 낸 번호 글은 번호만', () => assert.strictEqual(submissionMissingText(rec), '동의서 아직 안 낸 번호: 1, 3, 4번'));
t('안 낸 번호 글에 이름이 안 들어감', () => assert.ok(!submissionMissingText(rec).includes('학생')));
t('모두 냈을 때 글', () => assert.strictEqual(submissionMissingText({ title: 'x', total: 1, marks: { 1: 'd' } }), 'x: 모두 냈어요.'));

console.log(`${pass} passed`);
