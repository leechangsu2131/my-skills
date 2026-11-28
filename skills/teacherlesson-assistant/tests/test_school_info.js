/** web/school_info.js 순수 함수 시험.  실행: node tests/test_school_info.js */
'use strict';
const assert = require('assert');
const path = require('path');
const { schoolInfoText, stripAllergy, renderSchoolInfo } = require(path.join(__dirname, '..', 'web', 'school_info.js'));
let n = 0;
function t(name, fn) { fn(); n += 1; }

t('급식과 날씨를 한 줄로', () => {
  assert.strictEqual(schoolInfoText({ status: 'success', meal: '쌀밥, 된장국', weather: { temp: 12, icon: '☀' } }), '🍱 쌀밥, 된장국 · ☀ 12°');
});
t('알레르기 번호는 지운다', () => {
  assert.strictEqual(stripAllergy('된장국 (5.6.13)'), '된장국');
  assert.ok(!schoolInfoText({ status: 'success', meal: '우유 (2)', weather: null }).includes('('));
});
t('한쪽만 있어도 보인다', () => {
  assert.strictEqual(schoolInfoText({ status: 'success', meal: '', weather: { temp: -3, icon: '❄' } }), '❄ -3°');
  assert.strictEqual(schoolInfoText({ status: 'success', meal: '쌀밥', weather: null }), '🍱 쌀밥');
});
t('0도는 보인다', () => {
  assert.strictEqual(schoolInfoText({ status: 'success', meal: '', weather: { temp: 0, icon: '☁' } }), '☁ 0°');
});
t('없거나 이상하면 빈 글', () => {
  for (const bad of [null, undefined, {}, { status: 'error' }, { status: 'success', meal: '', weather: null },
    { status: 'success', meal: '', weather: { temp: null } }, { status: 'success', meal: '', weather: { temp: 'x' } }]) {
    assert.strictEqual(schoolInfoText(bad), '', JSON.stringify(bad));
  }
});
t('보여 줄 게 없으면 칸을 숨긴다', () => {
  const box = { hidden: false, textContent: 'x', title: '' };
  global.document = { getElementById: id => (id === 'schoolInfo' ? box : null) };
  renderSchoolInfo(null);
  assert.strictEqual(box.hidden, true);
  assert.strictEqual(box.textContent, '');
  renderSchoolInfo({ status: 'success', meal: '쌀밥', weather: null });
  assert.strictEqual(box.hidden, false);
  assert.strictEqual(box.textContent, '🍱 쌀밥');
  delete global.document;
});
console.log(`school_info.js: ${n} passed`);
