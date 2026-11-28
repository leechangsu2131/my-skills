/** web/layout.js 순수 함수 시험 (T110). 실행: node tests/test_layout.js — Node 내장만 사용 */
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { PANELS, parsePrefs, setMode, buildCss } = require(path.join(__dirname, '..', 'web', 'layout.js'));

let failed = 0;
function test(name, fn) {
  try { fn(); console.log(`  ✅ ${name}`); }
  catch (e) { failed++; console.error(`  ❌ ${name}\n     ${e.message}`); }
}

test('설정이 없거나 깨지면 밝은 화면·모두 보이기', () => {
  for (const bad of [null, '', '{', '5', '"dark"', '{"theme":"blue","panels":5}']) {
    assert.deepStrictEqual(parsePrefs(bad), { theme: 'light', panels: {} }, String(bad));
  }
});
test('아는 값만 읽는다', () => {
  const p = parsePrefs('{"theme":"dark","panels":{"hero":"fold","ai":"hide","x":"open","a b":"hide","u":"?"}}');
  assert.deepStrictEqual(p, { theme: 'dark', panels: { hero: 'fold', ai: 'hide' } });
});
test('저장했다 다시 읽어도 같다(새로 고쳐도 유지)', () => {
  const p = setMode(setMode({ theme: 'dark', panels: {} }, 'hero', 'fold'), 'links', 'hide');
  assert.deepStrictEqual(parsePrefs(JSON.stringify(p)), p);
});
test('보이기로 바꾸면 설정에서 빠지고 원본은 그대로', () => {
  const a = { theme: 'light', panels: { hero: 'hide' } };
  assert.deepStrictEqual(setMode(a, 'hero', 'open').panels, {});
  assert.deepStrictEqual(a.panels, { hero: 'hide' });
});
test('아무것도 안 고르면 CSS 가 없다', () => {
  assert.strictEqual(buildCss({ theme: 'dark', panels: {} }, PANELS), '');
});
test('접기·숨기기 CSS 는 모두 수업 진행 화면을 비껴 간다', () => {
  const panels = {};
  PANELS.forEach((p, i) => { panels[p.id] = i % 2 ? 'hide' : 'fold'; });
  const lines = buildCss({ theme: 'light', panels }, PANELS).split('\n');
  assert.ok(lines.length >= PANELS.length);
  lines.forEach(l => assert.ok(l.startsWith('body:not(.focus-mode) '), l));
});
test('칸 이름의 따옴표·역슬래시·줄바꿈이 CSS 를 깨지 않는다', () => {
  const css = buildCss({ theme: 'light', panels: { x: 'fold' } }, [{ id: 'x', title: 'a"}b\\c\nd', sel: '#x' }]);
  assert.strictEqual(css.match(/content:"([^"\\\n]*)"/)[1].includes('a }b c d'), true);
});
test('목록의 id 는 겹치지 않고, 지금 있는 칸의 선택자는 index.html 에 짝이 있다', () => {
  assert.strictEqual(new Set(PANELS.map(p => p.id)).size, PANELS.length);
  const html = fs.readFileSync(path.join(__dirname, '..', 'web', 'index.html'), 'utf8');
  const later = ['agenda', 'ment', 'submissions'];   // 다른 브랜치에서 들어올 칸
  for (const p of PANELS.filter(p => !later.includes(p.id))) {
    const ids = p.sel.match(/#[A-Za-z]+/g);
    ids.forEach(id => assert.ok(html.includes(`id="${id.slice(1)}"`), `${p.id}: ${id}`));
  }
});

if (failed) { console.error(`${failed}개 실패`); process.exit(1); }
console.log('모두 통과');
