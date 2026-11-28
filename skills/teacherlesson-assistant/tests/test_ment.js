/**
 * tests/test_ment.js — 💬 학생 대응 멘트 도우미(web/ment.js) 순수 함수 시험 (T106)
 * 실행: node tests/test_ment.js   (Node 내장만 사용)
 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const {
  MENT_FOCUS_KEY, mentMonday, mentFocusActive, mentAnswers, mentButtonLabel, mentSummaryText, mentEsc,
} = require(path.join(__dirname, '..', 'web', 'ment.js'));

let passed = 0;
function test(name, fn) {
  try { fn(); passed += 1; } catch (e) { console.error(`✗ ${name}\n  ${e.message}`); process.exitCode = 1; }
}

const S = [{ id: 'noisy', icon: '🔊', label: '떠들기' }, { id: 'cry', icon: '😢', label: '울음' }];

test('mentMonday: 주 중간·월요일·일요일은 같은 월요일', () => {
  assert.strictEqual(mentMonday('2026-11-23'), '2026-11-23');  // 월
  assert.strictEqual(mentMonday('2026-11-26'), '2026-11-23');  // 목
  assert.strictEqual(mentMonday('2026-11-29'), '2026-11-23');  // 일
  assert.strictEqual(mentMonday('2026-11-30'), '2026-11-30');  // 다음 월
});
test('mentMonday: 달·해 경계', () => {
  assert.strictEqual(mentMonday('2026-12-02'), '2026-11-30');
  assert.strictEqual(mentMonday('2027-01-01'), '2026-12-28');
});
test('mentMonday: 모양이 틀리거나 없는 날짜는 null', () => {
  for (const bad of ['', null, undefined, '어제', '2026-13-01', '2026-02-30', '2026-1-1', 20261123]) {
    assert.strictEqual(mentMonday(bad), null, String(bad));
  }
});

test('mentFocusActive: 같은 주 + 목록에 있는 상황이면 돌려준다', () => {
  assert.strictEqual(mentFocusActive({ id: 'noisy', day: '2026-11-23' }, S, '2026-11-27').label, '떠들기');
  assert.strictEqual(mentFocusActive({ id: 'cry', day: '2026-11-29' }, S, '2026-11-23').label, '울음');
});
test('mentFocusActive: 지난 주 / 다음 주에 둔 것은 풀린다', () => {
  assert.strictEqual(mentFocusActive({ id: 'noisy', day: '2026-11-22' }, S, '2026-11-23'), null);
  assert.strictEqual(mentFocusActive({ id: 'noisy', day: '2026-11-30' }, S, '2026-11-29'), null);
});
test('mentFocusActive: 없어진 상황·깨진 저장값은 null', () => {
  assert.strictEqual(mentFocusActive({ id: 'gone', day: '2026-11-23' }, S, '2026-11-23'), null);
  for (const bad of [null, undefined, 'x', 5, {}, { id: 'noisy' }, { id: 'noisy', day: '어제' }]) {
    assert.strictEqual(mentFocusActive(bad, S, '2026-11-23'), null, JSON.stringify(bad));
  }
  assert.strictEqual(mentFocusActive({ id: 'noisy', day: '2026-11-23' }, S, '날짜아님'), null);
  assert.strictEqual(mentFocusActive({ id: 'noisy', day: '2026-11-23' }, null, '2026-11-23'), null);
});

test('mentAnswers: 기본 문장 먼저, 교사 대답은 뒤에 custom 표시와 번호', () => {
  const got = mentAnswers({ answers: ['가', '나'], custom: ['내것1', '내것2'] });
  assert.deepStrictEqual(got.map(a => a.text), ['가', '나', '내것1', '내것2']);
  assert.deepStrictEqual(got.map(a => a.custom), [false, false, true, true]);
  assert.deepStrictEqual(got.filter(a => a.custom).map(a => a.index), [0, 1]);
});
test('mentAnswers: custom 이 없거나 상황이 없어도 안 깨진다', () => {
  assert.strictEqual(mentAnswers({ answers: ['가'] }).length, 1);
  assert.deepStrictEqual(mentAnswers(null), []);
  assert.deepStrictEqual(mentAnswers({}), []);
});

test('mentButtonLabel: 집중 상황에만 ⭐', () => {
  assert.strictEqual(mentButtonLabel(S[0], 'noisy'), '🔊 떠들기 ⭐');
  assert.strictEqual(mentButtonLabel(S[1], 'noisy'), '😢 울음');
  assert.strictEqual(mentButtonLabel({ id: 'x', label: '이름만' }, ''), '이름만');
});
test('mentSummaryText: 집중 상황이 있으면 접힌 줄에도 이름이 보인다', () => {
  assert.strictEqual(mentSummaryText(null), '💬 학생 대응 멘트');
  assert.ok(mentSummaryText({ label: '떠들기' }).includes('떠들기'));
});

test('mentEsc: 화면에 넣는 글의 태그·따옴표를 막는다', () => {
  assert.strictEqual(mentEsc('<b onclick="x">&\'</b>'), '&lt;b onclick=&quot;x&quot;&gt;&amp;&#39;&lt;/b&gt;');
  assert.strictEqual(mentEsc(null), '');
  assert.strictEqual(mentEsc(0), '0');
});

test('저장 키 이름이 정해진 값', () => { assert.strictEqual(MENT_FOCUS_KEY, 'ment.focus'); });

test('web/ment.json 의 모든 글이 화면용 이스케이프를 거쳐도 읽을 수 있다(태그 글자 없음)', () => {
  const data = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'web', 'ment.json'), 'utf8'));
  for (const s of data.situations) for (const a of s.answers) assert.ok(!/[<>]/.test(a), a);
});

console.log(`ment.js: ${passed}개 통과`);
