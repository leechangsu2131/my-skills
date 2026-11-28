// extension/session-keeper.js(나이스 로그인 자동 연장, T122) 시험
//
// 남은 시간 읽기·연장 단추 고르기·"언제 누를지" 판단은 순수 함수라 그대로 시험한다.
// 화면 쪽 도우미(shortTexts·buttonCandidates)는 가짜 document 로 시험한다.
// 실제 나이스·크롬·네트워크는 쓰지 않는다. 실제 나이스에서 남은 시간·단추 모양은 교사 PC 확인(점검표).
//
// 실행: skills/teacherlesson-from-neis 폴더에서  node --test tests/session_keeper.test.js
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const K = require(path.join(__dirname, '..', 'extension', 'session-keeper.js'));
const { parseRemainingSeconds: parse, findRemainingSeconds: find, pickExtendButton: pick, nextStep, badgeText } = K;

test('남은 시간 읽기: mm:ss · hh:mm:ss · 분 초', () => {
  assert.equal(parse('남은 시간 47:12'), 47 * 60 + 12);
  assert.equal(parse('04:59'), 299);
  assert.equal(parse('1:02:03'), 3723);
  assert.equal(parse('12분 30초'), 750);
  assert.equal(parse('5분'), 300);
  assert.equal(parse('45초'), 45);
  assert.equal(parse('1시간 5분'), 3900);
});

test('남은 시간 읽기: 못 읽는 글은 null', () => {
  for (const s of ['', null, undefined, '남은 시간', '연장', '99:99', '시각 12:75', 'abc']) assert.equal(parse(s), null, String(s));
});

test('남은 시간 찾기: 남은 시간 말이 든 짧은 글만 본다(시계 글자는 무시)', () => {
  assert.equal(find(['14:32', '남은 시간 04:10', '메뉴']), 250);
});

test('남은 시간 찾기: 같은 값이 겹쳐 보여도(바깥 상자·안쪽 글) 하나로 본다', () => {
  assert.equal(find(['남은 시간 04:10', '남은 시간 04:10', ' 남은 시간   04:10 ']), 250);
});

test('남은 시간 찾기: 서로 다른 값이 둘이면 null(어느 것이 맞는지 모름)', () => {
  assert.equal(find(['남은 시간 04:10', '세션 남은 시간 30:00']), null);
});

test('남은 시간 찾기: 없거나 긴 글만 있으면 null', () => {
  assert.equal(find([]), null);
  assert.equal(find(null), null);
  assert.equal(find(['남은 시간 ' + 'x'.repeat(50) + ' 04:10']), null);
  assert.equal(find(['04:10']), null);
});

test('단추 고르기: 글자가 연장인 것 하나', () => {
  assert.deepEqual(pick([{ text: '저장' }, { text: '로그인 연장' }, { text: '닫기' }]), { index: 1 });
  for (const t of ['연장', ' 연 장 ', '세션연장', '시간 연장', '자동연장', '연장하기']) assert.deepEqual(pick([{ text: t }]), { index: 0 }, t);
});

test('단추 고르기: 연장이 들어갔어도 다른 글이면 안 누름', () => {
  for (const t of ['연장근무 신청', '출장 연장 신청서', '연장 취소', '기간연장신청', '연장하지 않음']) {
    assert.deepEqual(pick([{ text: t }]), { index: -1, reason: 'none' }, t);
  }
});

test('단추 고르기: 없음·둘 이상·숨김·비활성', () => {
  assert.deepEqual(pick([]), { index: -1, reason: 'none' });
  assert.deepEqual(pick(null), { index: -1, reason: 'none' });
  assert.deepEqual(pick([{ text: '연장' }, { text: '로그인 연장' }]), { index: -1, reason: 'many' });
  assert.deepEqual(pick([{ text: '연장', visible: false }]), { index: -1, reason: 'none' });
  assert.deepEqual(pick([{ text: '연장', disabled: true }]), { index: -1, reason: 'none' });
  assert.deepEqual(pick([{ text: '연장', visible: false }, { text: '로그인 연장' }]), { index: 1 });
});

const BTN = { index: 0 };
const T0 = 1_000_000;

test('판단: 시간을 못 읽으면 아무것도 안 함', () => {
  assert.equal(nextStep({}, T0, null, null).action, 'none');
  assert.equal(nextStep({}, T0, null, null).status, 'unknown');
  assert.equal(nextStep({}, T0, undefined, BTN).action, 'none');
});

test('판단: 5분을 넘게 남았으면 기다림, 정확히 5분이면 누름', () => {
  assert.deepEqual([nextStep({}, T0, 301, BTN).action, nextStep({}, T0, 301, BTN).status], ['none', 'waiting']);
  assert.equal(nextStep({}, T0, 300, BTN).action, 'click');
  assert.equal(nextStep({}, T0, 299, BTN).action, 'click');
});

test('판단: 눌렀으면 1분 안에는 다시 안 누름(한 번만)', () => {
  const first = nextStep({}, T0, 290, BTN);
  assert.equal(first.action, 'click');
  const again = nextStep(first.state, T0 + 15000, 275, BTN);
  assert.equal(again.action, 'none');
  assert.equal(again.status, 'clicked');
  assert.equal(nextStep(first.state, T0 + 59999, 200, BTN).action, 'none');
});

test('판단: 눌렀는데도 1분 뒤 그대로면 다시 누르되 3번까지만', () => {
  let s = nextStep({}, T0, 290, BTN);
  let clicks = 1;
  for (let i = 1; i <= 6; i++) {
    s = nextStep(s.state, T0 + i * 60000, 250, BTN);
    if (s.action === 'click') clicks++;
  }
  assert.equal(clicks, 3);
  assert.equal(s.status, 'stuck');
});

test('판단: 시간이 다시 늘면 연장된 것 — 마지막 연장 시각을 남기고 다음 번을 위해 되돌림', () => {
  const first = nextStep({}, T0, 290, BTN);
  const done = nextStep(first.state, T0 + 20000, 3600, BTN);
  assert.equal(done.status, 'waiting');
  assert.deepEqual(done.state, { attempts: 0, lastClickAt: 0, lastExtendedAt: T0 });
  assert.equal(nextStep(done.state, T0 + 3_500_000, 280, BTN).action, 'click');   // 다음 번에 또 누름
  assert.equal(nextStep(done.state, T0 + 3_500_000, 700, BTN).state.lastExtendedAt, T0);  // 기다리는 동안 값 유지
});

test('판단: 단추가 없거나 여러 개면 누르지 않고 알림만', () => {
  assert.deepEqual([nextStep({}, T0, 100, null).action, nextStep({}, T0, 100, null).status], ['none', 'no-button']);
  assert.equal(nextStep({}, T0, 100, { index: -1, reason: 'none' }).status, 'no-button');
  assert.equal(nextStep({}, T0, 100, { index: -1, reason: 'many' }).status, 'many-buttons');
  assert.equal(nextStep({}, T0, 100, { index: -1, reason: 'many' }).action, 'none');
});

test('판단: 받은 상태 객체는 바꾸지 않음', () => {
  const st = { attempts: 0, lastClickAt: 0, lastExtendedAt: 0 };
  nextStep(st, T0, 100, BTN);
  assert.deepEqual(st, { attempts: 0, lastClickAt: 0, lastExtendedAt: 0 });
});

test('표시 글: 멈춤·상태·마지막 연장 시각', () => {
  assert.equal(badgeText(false, 'waiting', 0), '🔒 연장 멈춤');
  assert.equal(badgeText(true, 'waiting', 0), '🟢 지켜보는 중');
  assert.equal(badgeText(true, 'unknown', 0), '🟡 남은 시간을 못 읽음');
  assert.equal(badgeText(true, 'no-button', 0), '🟡 연장 단추를 못 찾음');
  const ms = new Date(2026, 10, 28, 9, 5).getTime();
  assert.equal(badgeText(true, 'waiting', ms), '🟢 지켜보는 중 · 마지막 연장 09:05');
});

// ── 가짜 화면 ──
function el(tag, text, extra = {}) {
  return { tagName: tag, textContent: text, value: extra.value, disabled: extra.disabled, getAttribute: n => (extra.attrs || {})[n] ?? null };
}
const fakeDoc = (els) => ({ querySelectorAll: () => els });

test('화면 도우미: 짧은 글만 모은다', () => {
  const doc = fakeDoc([el('SPAN', '남은 시간 04:10'), el('DIV', ''), el('DIV', 'x'.repeat(41))]);
  assert.deepEqual(K.shortTexts(doc), ['남은 시간 04:10']);
});

test('화면 도우미: 단추 후보(input 은 value, 비활성·숨김 표시)', () => {
  const doc = fakeDoc([el('BUTTON', ' 로그인 연장 '), el('INPUT', '', { value: '연장' }), el('A', '연장', { attrs: { 'aria-disabled': 'true' } }), el('BUTTON', '숨김')]);
  const { els, list } = K.buttonCandidates(doc, e => e.textContent !== '숨김');
  assert.equal(els.length, 4);
  assert.deepEqual(list.map(c => c.text.trim()), ['로그인 연장', '연장', '연장', '숨김']);
  assert.deepEqual(list.map(c => c.disabled), [false, false, true, false]);
  assert.deepEqual(list.map(c => c.visible), [true, true, true, false]);
  assert.deepEqual(pick(list), { index: -1, reason: 'many' });   // 로그인 연장 + input 연장 → 둘 → 안 누름
});

test('화면 도우미: 단추가 정확히 하나면 그 위치를 돌려줌', () => {
  const doc = fakeDoc([el('BUTTON', '저장'), el('BUTTON', '로그인 연장'), el('A', '닫기')]);
  const { list } = K.buttonCandidates(doc, () => true);
  assert.deepEqual(pick(list), { index: 1 });
});
