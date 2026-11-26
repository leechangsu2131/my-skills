/**
 * tools.js — 교실 도구 묶음 순수 함수 (브라우저/Node 공용)
 *
 * 타이머, 발표자 뽑기, 소음 측정 UI 의 핵심 로직.
 * DOM/MediaStream 에 의존하지 않는 함수만 여기에 둔다.
 * index.html 의 <script src="/tools.js"> 로 불러온다.
 *
 * Node 시험: tests/test_tools.js
 */

/* ── 타이머 ─────────────────────────────────────────── */

/**
 * 초(seconds)를 'MM:SS' 문자열로 바꾼다.
 * @param {number} totalSec  0 이상 정수
 * @returns {string}  예) 90 → "1:30", 5 → "0:05"
 */
function timerFormat(totalSec) {
  const s = Math.max(0, Math.floor(totalSec));
  const m = Math.floor(s / 60);
  const ss = s % 60;
  return `${m}:${String(ss).padStart(2, '0')}`;
}

/**
 * 'MM:SS' 또는 'M:SS' 문자열을 초(number)로 바꾼다.
 * 형식이 맞지 않으면 null 을 돌려준다.
 * @param {string} str
 * @returns {number|null}
 */
function timerParse(str) {
  if (typeof str !== 'string') return null;
  const m = str.trim().match(/^(\d+):(\d{2})$/);
  if (!m) return null;
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
}

/**
 * 타이머 단계(남은 초)를 받아 화면에 보여 줄 상태를 돌려준다.
 * @param {number} remainSec   남은 초 (0 이상)
 * @param {number} totalSec    처음 설정한 초 (양수)
 * @returns {{ text: string, phase: 'normal'|'warn'|'done' }}
 *   phase: 'done' 은 remainSec ≤ 0, 'warn' 은 나머지 10 % 이하, 'normal' 은 그 외
 */
function timerState(remainSec, totalSec) {
  const s = Math.max(0, remainSec);
  const phase =
    s <= 0 ? 'done' :
    s <= Math.max(1, totalSec * 0.1) ? 'warn' : 'normal';
  return { text: timerFormat(s), phase };
}

/* ── 발표자 뽑기 ──────────────────────────────────────── */

/**
 * [start, end] 범위(포함)의 번호를 순서 없이 섞어 돌려준다.
 * start 와 end 는 정수여야 한다. start > end 면 빈 배열.
 * @param {number} start
 * @param {number} end
 * @param {function} [rng]  Math.random 대신 쓸 함수(시험용)
 * @returns {number[]}
 */
function shuffleRange(start, end, rng) {
  rng = rng || Math.random;
  if (!Number.isInteger(start) || !Number.isInteger(end) || start > end) return [];
  const arr = [];
  for (let i = start; i <= end; i++) arr.push(i);
  // Fisher-Yates
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

/**
 * 뽑기 대기열에서 다음 번호를 꺼낸다.
 * queue 가 비어 있으면 start~end 를 새로 섞어 채운 뒤 꺼낸다.
 * queue 를 직접 수정한다(inout).
 * @param {number[]} queue   남은 번호 배열 (변경됨)
 * @param {number} start
 * @param {number} end
 * @param {function} [rng]
 * @returns {number}  뽑힌 번호
 */
function pickNext(queue, start, end, rng) {
  if (!queue.length) {
    const fresh = shuffleRange(start, end, rng);
    queue.push(...fresh);
  }
  return queue.shift();
}

/* ── 소음 측정 ────────────────────────────────────────── */

/**
 * Web Audio API 의 AnalyserNode 에서 가져온 uint8 배열을 받아
 * 0–100 범위의 평균 소음 수준을 돌려준다.
 * @param {Uint8Array} data  getByteFrequencyData 결과
 * @returns {number}  0–100 (소수점 1자리)
 */
function calcNoiseLevel(data) {
  if (!data || data.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < data.length; i++) sum += data[i];
  return parseFloat(((sum / data.length / 255) * 100).toFixed(1));
}

/**
 * 소음 수준(0–100)을 받아 색상과 설명 문자열을 돌려준다.
 * @param {number} level
 * @returns {{ color: string, label: string }}
 */
function noiseLabel(level) {
  if (level >= 70) return { color: '#d92d20', label: '너무 시끄러워요 🔴' };
  if (level >= 45) return { color: '#c77700', label: '조금 시끄러워요 🟡' };
  return { color: '#1d8a4a', label: '조용해요 🟢' };
}

/* ── 시간이 모자랄 때 뒤 단계 한 번에 줄이기 (ISSUE-009) ──────────────────── */

/** 단계 표시(flag)별로 '얼마나 줄일지'의 무게. 클수록 더 줄인다. 표시가 없으면 1. */
const COMPRESS_FACTOR = { cut: 1.5, keep: 0.4 };

/**
 * 교시 끝까지 shortMin 분이 모자랄 때, fromIdx 번째 단계부터 뒤쪽 단계들의 분을 얼마씩 줄일지 계산한다.
 * - 줄이는 몫은 단계의 분에 비례한다. 단, '줄여도 됨'(cut)은 1.5배, '꼭 해야 함'(keep)은 0.4배로 센다.
 * - 한 단계는 1분 밑으로 내려가지 않는다(분이 0 이하인 단계는 건드리지 않는다).
 * - 줄일 수 있는 분이 모자라면 줄일 수 있는 만큼만 줄이고 나머지는 left 로 돌려준다.
 * - 같은 몫이면 더 뒤쪽 단계를 먼저 줄인다.
 * @param {Array<{flag?: string}>} steps  단계 목록(flag: 'cut' | 'keep' | '')
 * @param {number[]} mins  단계별 지금 적용 중인 분(steps 와 같은 길이)
 * @param {number} fromIdx  줄이기 시작할 첫 단계 번호(보통 지금 단계 + 1)
 * @param {number} shortMin  모자란 분(소수는 반올림)
 * @returns {{deltas: number[], cut: number, left: number}}
 *   deltas: 단계별 바꿀 분(0 이하 정수, steps 와 같은 길이), cut: 실제로 줄인 합계(분), left: 못 줄인 분
 */
function compressStages(steps, mins, fromIdx, shortMin) {
  const n = Array.isArray(steps) ? steps.length : 0;
  const deltas = new Array(n).fill(0);
  const need = Math.round(Number(shortMin));
  if (!n || !Array.isArray(mins) || !(need >= 1)) return { deltas, cut: 0, left: need >= 1 ? need : 0 };
  const start = Math.max(0, Math.floor(Number(fromIdx)) || 0);
  const mm = (i) => { const v = Math.round(Number(mins[i])); return v > 0 ? v : 0; };
  const cap = (i) => Math.max(0, mm(i) - 1);          // 1분 밑으로는 안 줄임
  const weight = (i) => mm(i) * (COMPRESS_FACTOR[(steps[i] || {}).flag] || 1);
  const idxs = [];
  for (let i = start; i < n; i++) if (cap(i) > 0) idxs.push(i);
  let left = need;
  while (left > 0) {
    let best = -1, bestScore = -1;
    for (const i of idxs) {
      if (-deltas[i] >= cap(i)) continue;
      const score = weight(i) / (-deltas[i] + 1);     // 이미 많이 줄인 단계일수록 다음 몫이 줄어듦(비례 배분)
      if (score >= bestScore) { best = i; bestScore = score; }   // 같으면 뒤쪽 단계가 이김(idxs 는 앞→뒤 순)
    }
    if (best < 0) break;
    deltas[best] -= 1;
    left -= 1;
  }
  return { deltas, cut: need - left, left };
}

/* ── 모듈 내보내기(Node 시험용) ──────────────────────── */
if (typeof module !== 'undefined') {
  module.exports = {
    timerFormat, timerParse, timerState,
    shuffleRange, pickNext,
    calcNoiseLevel, noiseLabel,
    compressStages, COMPRESS_FACTOR,
  };
}
