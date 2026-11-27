// teacherlesson-from-neis extension/viewer.js 의 날짜 계산·색·묶기 함수 시험 (S1)
//
// viewer.js 는 불러오는 순간 document.querySelector 로 화면 요소를 잡고 chrome.storage 를 읽는다.
// 그래서 popup.test.js 와 같게 가짜 document·chrome·Date 를 넣은 node:vm 안에서 파일 전체를 돌린다(소스는 고치지 않음).
// 시험 대상: localIsoDate·parseIsoDate·weekDays·weekBounds·monthBounds·monthCells·dateLabel·shortRange·
//           shiftPeriod·colorForSubject·groupedByDate.
// 대상이 아닌 것: 화면을 그리는 render* 함수(진짜 DOM 이 필요), loadLessons 의 저장소 읽기.
// 실제 NEIS·크롬·네트워크·학생 정보는 쓰지 않는다(예시 날짜는 2026-11 달력).
//
// 실행: skills/teacherlesson-from-neis 폴더에서  node --test tests/viewer.test.js
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(path.join(__dirname, '..', 'extension', 'viewer.js'), 'utf8');
const RealDate = Date;

function fakeElement(overrides = {}) {
  const store = {
    dataset: {},
    children: [],
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    textContent: '',
    value: '',
    checked: false,
    hidden: false,
    style: {},
    ...overrides,
  };
  return new Proxy(store, {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (typeof prop === 'symbol') return undefined;
      if (prop === 'querySelector') return () => fakeElement();   // 처음 불러올 때 emptyState.querySelector('h3') 등을 쓴다
      if (prop === 'closest') return () => null;
      if (prop === 'querySelectorAll') return () => [];
      return () => {};
    },
    set(target, prop, value) { target[prop] = value; return true; },
  });
}

// viewer.js 를 새로 불러온다. now 는 "오늘"(월은 0부터).
function load({ now = [2026, 10, 25, 12, 0, 0] } = {}) {
  const elements = new Map();
  const document = {
    querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, fakeElement());
      return elements.get(selector);
    },
    querySelectorAll() { return []; },
    createElement() { return fakeElement(); },
  };
  const chrome = {
    storage: {
      local: { get: async () => ({}), set: async () => {}, remove: async () => {} },
      onChanged: { addListener() {} },
    },
  };
  class FakeDate extends RealDate {
    constructor(...args) { super(...(args.length ? args : now)); }
  }
  const context = vm.createContext({
    document, chrome, Date: FakeDate, console, Intl, window: { setInterval() {} },
    localStorage: { getItem: () => null, setItem() {} },
  });
  vm.runInContext(SOURCE, context, { filename: 'viewer.js' });
  const get = (code) => vm.runInContext(code, context);
  get('loadLessons = () => {}');   // 달·주를 옮길 때 저장소를 다시 읽지 않게
  return { get, elements };
}

const plain = (value) => JSON.parse(JSON.stringify(value));
const iso = (get, fn, ...args) => plain(get(fn)(...args));

test('localIsoDate: 월·일을 두 자리로 채운다(받은 날짜 그대로, 인자가 없으면 "오늘")', () => {
  const { get } = load();
  assert.equal(get('localIsoDate')(new RealDate(2026, 0, 5, 12)), '2026-01-05');
  assert.equal(get('localIsoDate')(new RealDate(2026, 11, 31, 12)), '2026-12-31');
  assert.equal(get('localIsoDate')(), '2026-11-25');
});

test('parseIsoDate: 낮 12시로 만들어 시간대·서머타임에 하루 밀리지 않는다', () => {
  const { get } = load();
  const d = get('parseIsoDate')('2026-11-05');
  assert.equal([d.getFullYear(), d.getMonth(), d.getDate(), d.getHours()].join(','), '2026,10,5,12');
});

test('weekDays: 월~금 5일. 수요일·월요일·토·일 어느 날을 줘도 같은 주(일요일은 그 전 월요일 주)', () => {
  const { get } = load();
  const days = (v) => plain(get('weekDays')(v).map((d) => get('localIsoDate')(d)));
  const week = ['2026-11-23', '2026-11-24', '2026-11-25', '2026-11-26', '2026-11-27'];
  for (const v of ['2026-11-23', '2026-11-25', '2026-11-27', '2026-11-28', '2026-11-29']) {
    assert.deepEqual(days(v), week, v);
  }
  assert.equal(days('2026-11-30')[0], '2026-11-30');   // 다음 월요일은 새 주의 시작
});

test('weekBounds: 달·해가 바뀌는 주도 월요일~금요일', () => {
  const { get } = load();
  assert.deepEqual(iso(get, 'weekBounds', '2026-12-02'), ['2026-11-30', '2026-12-04']);
  assert.deepEqual(iso(get, 'weekBounds', '2027-01-01'), ['2026-12-28', '2027-01-01']);
});

test('monthBounds: 그 달 1일과 마지막 날(30일·31일·윤년 2월 포함)', () => {
  const { get } = load();
  assert.deepEqual(iso(get, 'monthBounds', '2026-11-15'), ['2026-11-01', '2026-11-30']);
  assert.deepEqual(iso(get, 'monthBounds', '2026-12-31'), ['2026-12-01', '2026-12-31']);
  assert.deepEqual(iso(get, 'monthBounds', '2026-02-10'), ['2026-02-01', '2026-02-28']);
  assert.deepEqual(iso(get, 'monthBounds', '2028-02-10'), ['2028-02-01', '2028-02-29']);
});

test('monthCells: 달력은 월요일에서 시작해 7의 배수 칸, 그 달 날짜만 inMonth', () => {
  const { get } = load();
  // 2026-11: 1일이 일요일 → 앞 6칸이 10월, 30일 → 6주 42칸
  const nov = plain(get('monthCells')('2026-11-15'));
  assert.equal(nov.length, 42);
  assert.equal(nov[0].iso, '2026-10-26');
  assert.equal(nov.filter((c) => c.inMonth).length, 30);
  assert.equal(nov[6].iso, '2026-11-01');
  assert.equal(nov[6].inMonth, true);
  assert.equal(nov[0].inMonth, false);
  assert.equal(nov[41].iso, '2026-12-06');
  // 2027-02: 1일이 월요일이고 28일 → 정확히 4주 28칸, 전부 그 달
  const feb = plain(get('monthCells')('2027-02-10'));
  assert.equal(feb.length, 28);
  assert.equal(feb[0].iso, '2027-02-01');
  assert.ok(feb.every((c) => c.inMonth));
  // 모든 달력은 첫 칸이 월요일(Date 로 확인)
  for (const month of ['2026-01-10', '2026-05-10', '2026-08-10', '2026-11-10', '2028-02-10']) {
    const cells = get('monthCells')(month);
    assert.equal(cells[0].date.getDay(), 1, month);
    assert.equal(cells.length % 7, 0, month);
  }
});

test('dateLabel·shortRange: 한국어 날짜 글(월·일·요일)', () => {
  const { get } = load();
  assert.match(get('dateLabel')('2026-11-23'), /11월 23일.*월/);
  assert.match(get('dateLabel')('2026-11-23', { year: 'numeric', month: 'long' }), /2026년 11월/);
  const range = get('shortRange')('2026-11-23', '2026-11-27');
  assert.match(range, /23.*월.*~.*27.*금/);
});

test('shiftPeriod: 날은 ±1일, 주는 ±7일, 달은 ±1달(말일은 그 달 마지막 날로 줄인다)', () => {
  const run = (view, from, direction) => {
    const { get, elements } = load();
    const input = elements.get('#selectedDate') || (get('dateInput'), elements.get('#selectedDate'));
    get(`activeView = ${JSON.stringify(view)}`);
    input.value = from;
    get('shiftPeriod')(direction);
    return input.value;
  };
  assert.equal(run('day', '2026-11-30', 1), '2026-12-01');
  assert.equal(run('day', '2026-01-01', -1), '2025-12-31');
  assert.equal(run('week', '2026-11-25', 1), '2026-12-02');
  assert.equal(run('week', '2026-11-25', -1), '2026-11-18');
  assert.equal(run('month', '2026-01-31', 1), '2026-02-28');     // 31일 → 2월 말일
  assert.equal(run('month', '2026-03-31', -1), '2026-02-28');
  assert.equal(run('month', '2028-01-31', 1), '2028-02-29');     // 윤년
  assert.equal(run('month', '2026-12-15', 1), '2027-01-15');     // 해 넘김
  assert.equal(run('month', '2026-01-15', -1), '2025-12-15');
});

test('shiftPeriod: 날짜 칸이 비어 있으면 "오늘"에서 옮긴다', () => {
  const { get, elements } = load({ now: [2026, 10, 25, 12, 0, 0] });
  const input = elements.get('#selectedDate');
  input.value = '';
  get('activeView = "day"');
  get('shiftPeriod')(1);
  assert.equal(input.value, '2026-11-26');
});

test('colorForSubject: 정해 둔 과목은 정해진 색, 그 밖은 항상 같은 예비 색', () => {
  const { get } = load();
  const color = get('colorForSubject');
  assert.equal(color('국어'), '#f59e0b');
  assert.equal(color('체육'), '#f43f5e');
  const fallback = plain(get('FALLBACK_COLORS'));
  for (const subject of ['코딩', '안전한 생활', 'English', '', null, undefined]) {
    assert.ok(fallback.includes(color(subject)), String(subject));
    assert.equal(color(subject), color(subject));
  }
  // 과목 이름마다 색이 흩어져야 한다(모두 한 색이면 달력에서 과목을 못 가린다)
  const spread = new Set(['코딩', '안전한 생활', 'English', '독서', '로봇', '진로', '환경'].map(color));
  assert.ok(spread.size >= 3, `예비 색이 ${spread.size}가지뿐`);
  assert.equal(color(''), fallback[0]);          // 빈 값은 해시 0 → 첫 번째 색
  assert.equal(color(undefined), color(null));
});

test('groupedByDate: 날짜별로 묶고 들어온 순서를 지킨다', () => {
  const { get } = load();
  const records = [
    { date: '2026-11-25', period: 2 }, { date: '2026-11-24', period: 1 },
    { date: '2026-11-25', period: 1 }, { date: '2026-11-24', period: 3 },
  ];
  const groups = get('groupedByDate')(records);
  assert.deepEqual([...groups.keys()], ['2026-11-25', '2026-11-24']);
  assert.deepEqual(plain(groups.get('2026-11-25')).map((r) => r.period), [2, 1]);
  assert.deepEqual(plain(groups.get('2026-11-24')).map((r) => r.period), [1, 3]);
  assert.equal(get('groupedByDate')([]).size, 0);
});
