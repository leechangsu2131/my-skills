// 화면 설정(T110) 순수 함수 시험:  node tests/test_layout.js  (teacherlesson-assistant 폴더에서)
const assert = require('assert');
const { normalizeLayout, panelKeys, toggleHidden, setFolded, nextTheme } = require('../web/layout.js');

let pass = 0;
function t(name, fn) { fn(); pass++; console.log('ok -', name); }

t('비어 있거나 깨진 저장값은 기본값', () => {
  const base = { theme: 'light', hidden: [], folded: {} };
  for (const raw of [null, undefined, '', '{깨짐', '[]', '5', 'null', []]) assert.deepStrictEqual(normalizeLayout(raw), base);
});
t('글로 저장된 값도 읽음', () => {
  const v = normalizeLayout(JSON.stringify({ theme: 'dark', hidden: ['#subBox'], folded: { '#aiBox': true } }));
  assert.deepStrictEqual(v, { theme: 'dark', hidden: ['#subBox'], folded: { '#aiBox': true } });
});
t('알 수 없는 테마는 light', () => assert.strictEqual(normalizeLayout({ theme: 'neon' }).theme, 'light'));
t('hidden 은 글자만·중복 없이', () => assert.deepStrictEqual(normalizeLayout({ hidden: ['a', 'a', 3, '', null, 'b'] }).hidden, ['a', 'b']));
t('folded 는 true/false 값만', () => assert.deepStrictEqual(normalizeLayout({ folded: { a: true, b: 'yes', c: false } }).folded, { a: true, c: false }));
t('hidden 이 배열이 아니면 빈 배열', () => assert.deepStrictEqual(normalizeLayout({ hidden: 'a' }).hidden, []));

t('칸 키: id 우선', () => assert.deepStrictEqual(panelKeys([{ id: 'aiBox', title: 'x' }]), ['#aiBox']));
t('칸 키: id 없으면 제목(공백 정리·24자)', () => {
  assert.deepStrictEqual(panelKeys([{ title: '  📢  알림장·숙제 ' }]), ['t:📢 알림장·숙제']);
  assert.strictEqual(panelKeys([{ title: 'a'.repeat(40) }])[0], 't:' + 'a'.repeat(24));
});
t('같은 키는 -2, -3', () => assert.deepStrictEqual(panelKeys([{ title: '가' }, { title: '가' }, { title: '가' }]), ['t:가', 't:가-2', 't:가-3']));

t('숨기기 토글(원본 안 바뀜)', () => {
  const a = normalizeLayout(null);
  const b = toggleHidden(a, 'k');
  assert.deepStrictEqual(b.hidden, ['k']);
  assert.deepStrictEqual(a.hidden, []);
  assert.deepStrictEqual(toggleHidden(b, 'k').hidden, []);
});
t('접기 기록(원본 안 바뀜)', () => {
  const a = normalizeLayout(null);
  const b = setFolded(a, 'k', true);
  assert.deepStrictEqual(b.folded, { k: true });
  assert.deepStrictEqual(a.folded, {});
  assert.deepStrictEqual(setFolded(b, 'k', false).folded, { k: false });
});
t('테마 바꾸기', () => { assert.strictEqual(nextTheme('light'), 'dark'); assert.strictEqual(nextTheme('dark'), 'light'); assert.strictEqual(nextTheme('x'), 'dark'); });
t('저장→읽기 왕복', () => {
  let v = normalizeLayout(null);
  v = setFolded(toggleHidden({ ...v, theme: nextTheme(v.theme) }, '#hero'), '#aiBox', true);
  assert.deepStrictEqual(normalizeLayout(JSON.stringify(v)), v);
});

console.log(`${pass} passed`);
