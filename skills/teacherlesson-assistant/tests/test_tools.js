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
  compressStages, COMPRESS_FACTOR,
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

/* ── compressStages (모자랄 때 뒤 단계 한 번에 줄이기, ISSUE-009) ─────── */
console.log('\n[compressStages]');
const sum = (a) => a.reduce((x, y) => x + y, 0);
const plain = (n, flag) => Array.from({ length: n }, () => ({ flag: flag || '' }));

test('모자란 분만큼 줄이고, 합이 정확히 맞는다', () => {
  const steps = plain(4);
  const r = compressStages(steps, [5, 10, 20, 5], 1, 6);
  assert.strictEqual(r.cut, 6);
  assert.strictEqual(r.left, 0);
  assert.strictEqual(-sum(r.deltas), 6);
});
test('지금 단계(fromIdx 앞)는 절대 안 줄인다', () => {
  const r = compressStages(plain(4), [10, 10, 10, 10], 2, 8);
  assert.strictEqual(r.deltas[0], 0);
  assert.strictEqual(r.deltas[1], 0);
  assert.strictEqual(-sum(r.deltas), 8);
});
test('줄이는 몫은 단계의 분에 비례한다(긴 단계를 더 줄임)', () => {
  const r = compressStages(plain(3), [5, 10, 25], 0, 8);
  // 비례 몫 1 : 2 : 5
  assert.deepStrictEqual(r.deltas, [-1, -2, -5]);
});
test("'꼭 해야 함'(keep)은 덜 줄이고 '줄여도 됨'(cut)은 더 줄인다", () => {
  const steps = [{ flag: 'keep' }, { flag: '' }, { flag: 'cut' }];
  const r = compressStages(steps, [10, 10, 10], 0, 9);
  assert.ok(-r.deltas[0] < -r.deltas[1], `keep ${r.deltas[0]} < 보통 ${r.deltas[1]}`);
  assert.ok(-r.deltas[1] < -r.deltas[2], `보통 ${r.deltas[1]} < cut ${r.deltas[2]}`);
  assert.strictEqual(-sum(r.deltas), 9);
});
test('keep 단계도 다른 단계가 1분뿐이면 줄인다(꼭 해야 함이라도 1분까지는 양보)', () => {
  const steps = [{ flag: 'keep' }, { flag: '' }];
  const r = compressStages(steps, [10, 1], 0, 5);
  assert.deepStrictEqual(r.deltas, [-5, 0]);
});
test('한 단계는 1분 밑으로 내려가지 않는다', () => {
  const r = compressStages(plain(2), [3, 2], 0, 100);
  assert.deepStrictEqual(r.deltas, [-2, -1]);
  assert.strictEqual(r.cut, 3);
  assert.strictEqual(r.left, 97);
});
test('분이 1 이하·0·없는 단계는 건드리지 않는다', () => {
  const r = compressStages(plain(4), [1, 0, undefined, 6], 0, 4);
  assert.deepStrictEqual(r.deltas, [0, 0, 0, -4]);
});
test('줄일 단계가 하나도 없으면 아무것도 안 줄이고 모자란 분을 그대로 돌려준다', () => {
  const r = compressStages(plain(2), [1, 1], 0, 7);
  assert.deepStrictEqual(r, { deltas: [0, 0], cut: 0, left: 7 });
  const last = compressStages(plain(3), [5, 5, 5], 3, 4);   // 지금이 마지막 단계
  assert.deepStrictEqual(last, { deltas: [0, 0, 0], cut: 0, left: 4 });
});
test('모자란 분이 0·음수·숫자 아님이면 안 줄인다', () => {
  for (const bad of [0, -3, 0.4, NaN, undefined, null, '가']) {
    const r = compressStages(plain(2), [10, 10], 0, bad);
    assert.deepStrictEqual(r.deltas, [0, 0], `short=${bad}`);
    assert.strictEqual(r.cut, 0, `short=${bad}`);
  }
});
test('소수로 모자라면 반올림해서 줄인다', () => {
  const r = compressStages(plain(2), [10, 10], 0, 2.6);
  assert.strictEqual(r.cut, 3);
});
test('같은 몫이면 더 뒤쪽 단계를 먼저 줄인다', () => {
  const r = compressStages(plain(3), [10, 10, 10], 0, 1);
  assert.deepStrictEqual(r.deltas, [0, 0, -1]);
});
test('입력 배열을 바꾸지 않고, deltas 는 항상 steps 와 같은 길이의 0 이하 정수', () => {
  const steps = [{ flag: 'cut' }, {}, { flag: 'keep' }, { flag: 'cut' }];
  const mins = [4, 7, 12, 3];
  const before = JSON.stringify([steps, mins]);
  const r = compressStages(steps, mins, 1, 5);
  assert.strictEqual(JSON.stringify([steps, mins]), before);
  assert.strictEqual(r.deltas.length, steps.length);
  r.deltas.forEach((d, i) => {
    assert.ok(Number.isInteger(d) && d <= 0, `deltas[${i}]=${d}`);
    assert.ok(mins[i] + d >= 1 || mins[i] < 1, `줄인 뒤 ${mins[i] + d}분`);
  });
});
test('fromIdx 가 범위를 벗어나거나 steps 가 비어도 오류 없이 처리', () => {
  assert.deepStrictEqual(compressStages([], [], 0, 3), { deltas: [], cut: 0, left: 3 });
  assert.deepStrictEqual(compressStages(plain(2), [9, 9], 99, 3).deltas, [0, 0]);
  assert.strictEqual(-sum(compressStages(plain(2), [9, 9], -5, 3).deltas), 3);   // 음수 → 처음부터
  assert.deepStrictEqual(compressStages(null, null, 0, 3), { deltas: [], cut: 0, left: 3 });
});
test('가중치 상수가 시험 의도와 맞다(cut > 보통(1) > keep)', () => {
  assert.ok(COMPRESS_FACTOR.cut > 1 && COMPRESS_FACTOR.keep > 0 && COMPRESS_FACTOR.keep < 1);
});

/* ── 결과 ─────────────────────────────── */
console.log(`\n결과: ${passed} 통과 / ${failed} 실패\n`);
if (failed > 0) process.exit(1);
