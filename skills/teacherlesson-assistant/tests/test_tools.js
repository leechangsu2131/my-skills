/**
 * tests/test_tools.js
 * 교실 도구 묶음(web/tools.js) 순수 함수 단위 시험
 *
 * 실행: node tests/test_tools.js
 * 의존: Node.js 내장만 사용 (npm 불필요)
 */

'use strict';

const assert = require('assert');
const path = require('path');
const {
  timerFormat, timerParse, timerState,
  shuffleRange, pickNext,
  calcNoiseLevel, noiseLabel,
} = require(path.join(__dirname, '..', 'web', 'tools.js'));

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✅ ${name}`);
    passed++;
  } catch (e) {
    console.error(`  ❌ ${name}`);
    console.error(`     ${e.message}`);
    failed++;
  }
}

/* ── timerFormat ─────────────────────────── */
console.log('\n[timerFormat]');
test('90초 → 1:30', () => assert.strictEqual(timerFormat(90), '1:30'));
test('5초 → 0:05', () => assert.strictEqual(timerFormat(5), '0:05'));
test('0초 → 0:00', () => assert.strictEqual(timerFormat(0), '0:00'));
test('3600초 → 60:00', () => assert.strictEqual(timerFormat(3600), '60:00'));
test('음수는 0:00', () => assert.strictEqual(timerFormat(-10), '0:00'));
test('소수점은 버림', () => assert.strictEqual(timerFormat(61.9), '1:01'));

/* ── timerParse ─────────────────────────── */
console.log('\n[timerParse]');
test('"1:30" → 90', () => assert.strictEqual(timerParse('1:30'), 90));
test('"0:05" → 5', () => assert.strictEqual(timerParse('0:05'), 5));
test('"60:00" → 3600', () => assert.strictEqual(timerParse('60:00'), 3600));
test('잘못된 형식 → null', () => assert.strictEqual(timerParse('90'), null));
test('빈 문자열 → null', () => assert.strictEqual(timerParse(''), null));
test('null 입력 → null', () => assert.strictEqual(timerParse(null), null));
test('공백 포함 처리', () => assert.strictEqual(timerParse('  2:30  '), 150));

/* ── timerState ─────────────────────────── */
console.log('\n[timerState]');
test('정상 구간 phase=normal', () => {
  const s = timerState(50, 100);
  assert.strictEqual(s.phase, 'normal');
  assert.strictEqual(s.text, '0:50');
});
test('10% 이하 phase=warn', () => {
  const s = timerState(9, 100);
  assert.strictEqual(s.phase, 'warn');
});
test('0초 phase=done', () => {
  const s = timerState(0, 100);
  assert.strictEqual(s.phase, 'done');
  assert.strictEqual(s.text, '0:00');
});
test('음수도 done', () => {
  assert.strictEqual(timerState(-1, 100).phase, 'done');
});

/* ── shuffleRange ─────────────────────────── */
console.log('\n[shuffleRange]');
test('1~5 범위: 길이 5, 모든 번호 포함', () => {
  const arr = shuffleRange(1, 5);
  assert.strictEqual(arr.length, 5);
  for (let i = 1; i <= 5; i++) assert.ok(arr.includes(i), `${i} 없음`);
});
test('start > end → 빈 배열', () => {
  assert.deepStrictEqual(shuffleRange(5, 1), []);
});
test('start === end → 한 원소', () => {
  assert.deepStrictEqual(shuffleRange(3, 3), [3]);
});
test('순서가 섞임(결정적 rng로 확인)', () => {
  // rng 가 항상 0 을 돌려주면 arr[0] 이 계속 뒤로 쌓임
  let call = 0;
  const rng = () => [0.9, 0.1, 0.8, 0.0][call++ % 4];
  const a = shuffleRange(1, 4, rng);
  // 길이와 집합이 맞으면 충분
  assert.strictEqual(a.length, 4);
  assert.ok(a.includes(1) && a.includes(2) && a.includes(3) && a.includes(4));
});

/* ── pickNext ─────────────────────────── */
console.log('\n[pickNext]');
test('빈 대기열에서 첫 뽑기: start~end 범위', () => {
  const q = [];
  const n = pickNext(q, 1, 5);
  assert.ok(n >= 1 && n <= 5, `${n} 범위 밖`);
  assert.strictEqual(q.length, 4);  // 4개가 대기열에 남아야 함
});
test('대기열이 있으면 거기서 꺼냄', () => {
  const q = [3, 7];
  assert.strictEqual(pickNext(q, 1, 10), 3);
  assert.strictEqual(pickNext(q, 1, 10), 7);
  assert.strictEqual(q.length, 0);
});
test('대기열 소진 후 자동 재보충', () => {
  const q = [1];
  pickNext(q, 1, 3);  // 1 꺼냄 → q 비어 있음
  const n = pickNext(q, 1, 3);  // 재보충 후 꺼냄
  assert.ok(n >= 1 && n <= 3);
});

/* ── calcNoiseLevel ─────────────────────────── */
console.log('\n[calcNoiseLevel]');
test('모두 0 → 0', () => {
  assert.strictEqual(calcNoiseLevel(new Uint8Array([0, 0, 0])), 0);
});
test('모두 255 → 100', () => {
  assert.strictEqual(calcNoiseLevel(new Uint8Array([255, 255])), 100);
});
test('중간값 → 약 50', () => {
  const level = calcNoiseLevel(new Uint8Array([128, 127]));
  assert.ok(level > 49 && level < 51, `${level} 이 50 근처가 아님`);
});
test('빈 배열 → 0', () => {
  assert.strictEqual(calcNoiseLevel(new Uint8Array(0)), 0);
});

/* ── noiseLabel ─────────────────────────── */
console.log('\n[noiseLabel]');
test('70 이상 → 빨간색', () => {
  const r = noiseLabel(75);
  assert.strictEqual(r.color, '#d92d20');
});
test('45~69 → 노란색', () => {
  const r = noiseLabel(50);
  assert.strictEqual(r.color, '#c77700');
});
test('45 미만 → 초록색', () => {
  const r = noiseLabel(30);
  assert.strictEqual(r.color, '#1d8a4a');
});
test('경계값 70 → 빨간색', () => {
  assert.strictEqual(noiseLabel(70).color, '#d92d20');
});
test('경계값 45 → 노란색', () => {
  assert.strictEqual(noiseLabel(45).color, '#c77700');
});

/* ── 결과 ─────────────────────────────── */
console.log(`\n결과: ${passed} 통과 / ${failed} 실패\n`);
if (failed > 0) process.exit(1);
