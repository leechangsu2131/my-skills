// 확장을 다시 불러온 뒤(옛 NEIS 탭) 의 동작 시험 (ISSUE-004)
//
// content.js(확장 쪽)와 neis-reader.js(화면 쪽)를 가짜 화면·가짜 chrome·가짜 NEIS 객체와 함께
// 한 node:vm 안에서 그대로 돌린다. 실제 NEIS·크롬·네트워크·학생 정보는 쓰지 않는다.
//
// 실행: skills/teacherlesson-from-neis 폴더에서  node --test tests/context_lost.test.js
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const read = (name) => fs.readFileSync(path.join(__dirname, '..', 'extension', name), 'utf8');
const READER = read('neis-reader.js');
const CONTENT = read('content.js');
const WEEKS = [['20261102', '20261106'], ['20261109', '20261113'], ['20261116', '20261120'], ['20261123', '20261127']];
const GUIDE = /확장 프로그램이 갱신되었습니다/;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function element() {
  const handlers = {};
  return {
    textContent: '', className: '', hidden: false, style: {}, handlers,
    classList: { toggle() { }, contains() { return false; } },
    setAttribute() { }, append() { }, replaceChildren() { }, setPointerCapture() { },
    addEventListener(type, handler) { handlers[type] = handler; },
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 100, height: 100 }),
  };
}

/* lostAt: 이 번호의 sendMessage 부터 '무효화' 오류(1 = 첫 호출). 0 = 처음부터 모든 API 가 오류. */
function load({ lostAt = Infinity, onSend = () => { } } = {}) {
  const invalid = () => { throw new Error('Extension context invalidated.'); };
  const calls = { messages: [], sent: [], errors: [] };
  const state = { lost: lostAt === 0 };
  const chrome = {
    storage: {
      local: {
        get: async () => (state.lost ? invalid() : {}),
        set: async () => (state.lost ? invalid() : undefined),
      },
      onChanged: { addListener: () => { if (state.lost) invalid(); } },
    },
    runtime: {
      sendMessage: async (message) => {
        if (calls.messages.length + 1 >= lostAt) state.lost = true;
        if (state.lost) invalid();
        calls.messages.push(message.type);
        if (message.type === 'CHECK_WEEK_CACHE') return { ok: true, fresh: {} };
        return { ok: true, imported: 1 };
      },
    },
  };

  const elements = new Map();
  const query = (selector) => {
    if (!elements.has(selector)) elements.set(selector, element());
    return elements.get(selector);
  };
  const listeners = [];
  const search = { weekBgngYmd: WEEKS[0][0], weekEndYmd: WEEKS[0][1] };
  const lessons = {
    getRowCount: () => 1,
    isModified: () => false,
    getValue: (_row, column) => ({ pirNm: '1', monAllTiYmd: search.weekBgngYmd, monEtbSbjtNm: '국어' })[column] ?? '',
  };
  const controls = {
    dsWikLrn: lessons,
    dsWeekList: {
      getRowCount: () => WEEKS.length,
      getValue: (row, column) => ({ weekBgngYmd: WEEKS[row][0], weekEndYmd: WEEKS[row][1], weekCnt: String(row + 1) })[column] ?? '',
    },
    dmSearch: { getValue: (key) => search[key], setValue: (key, value) => { search[key] = value; } },
    cmbWeek: { selectItem() { } },
    subSelectWikInfo: {
      send: async () => {
        calls.sent.push(search.weekBgngYmd);
        onSend(calls.sent.length, state);
        await sleep(20); // 실제 조회처럼 화면 안 알림(postMessage)보다 오래 걸린다
      },
    },
  };
  const app = { app: { id: 'edu/sw/els/edc/tm/els_edctm06_m00' }, lookup: (id) => controls[id] };

  let observer = null;
  let clock = 0;
  const window = {
    innerWidth: 1200,
    innerHeight: 800,
    cpr: { core: { Platform: { INSTANCE: { getAllRunningAppInstances: () => [app] } } } },
    addEventListener(type, handler) { if (type === 'message') listeners.push(handler); },
    postMessage(data) {
      setImmediate(() => {
        for (const handler of listeners) {
          try { handler({ source: window, data }); } catch (error) { calls.errors.push(error); }
        }
      });
    },
  };
  const host = { ...element(), attachShadow: () => ({ querySelector: query }) };
  const context = vm.createContext({
    window,
    chrome,
    document: { getElementById: () => null, createElement: () => host, documentElement: { appendChild() { } } },
    location: { href: 'https://x.neis.go.kr/', origin: 'https://x.neis.go.kr', pathname: '/' },
    performance: { getEntriesByType: () => [], now: () => (clock += 1) },
    PerformanceObserver: class { constructor(callback) { observer = callback; } observe() { } },
    setTimeout: (handler, ms) => setTimeout(handler, ms / 100), // 600ms·4초 대기를 짧게
    clearTimeout,
    Intl, URL,
  });
  vm.runInContext(CONTENT, context);
  vm.runInContext(READER, context);

  return {
    calls,
    state,
    status: () => query('#status').textContent,
    openViewer: () => query('#openViewer').handlers.click({ preventDefault() { } }),
    async userQuery() {
      observer({ getEntries: () => [{ name: 'https://x.neis.go.kr/els_edc_tm06_003.do', startTime: (clock += 100), responseEnd: 1 }] });
      await sleep(400);
    },
  };
}

test('정상일 때는 나머지 주차를 조회하고 원래 주차로 돌아온다(시험 틀 확인)', async () => {
  const page = load();
  await page.userQuery();
  assert.deepEqual(page.calls.sent, [WEEKS[1][0], WEEKS[2][0], WEEKS[3][0], WEEKS[0][0]]);
  assert.match(page.status(), /자동 동기화 완료/);
  assert.deepEqual(page.calls.errors, []);
});

test('확장을 다시 불러온 옛 탭에서는 NEIS 주차를 대신 넘기지 않고 새로고침 안내를 남긴다', async () => {
  const page = load({ lostAt: 0 });
  await page.userQuery();
  assert.deepEqual(page.calls.sent, []);
  assert.match(page.status(), GUIDE);
  await page.userQuery(); // 다시 조회해도 '확인 중' 문구가 안내를 덮지 않는다
  assert.deepEqual(page.calls.sent, []);
  assert.match(page.status(), GUIDE);
  assert.deepEqual(page.calls.errors, []);
});

test('주차 확인에서 처음 끊긴 것을 알아도 주차를 넘기지 않는다', async () => {
  const page = load({ lostAt: 2 }); // 1번(수업 저장)은 되고 2번(최신 주차 확인)부터 오류
  await page.userQuery();
  assert.deepEqual(page.calls.messages, ['AUTO_SYNC_LESSONS']);
  assert.deepEqual(page.calls.sent, []);
  assert.match(page.status(), GUIDE);
});

// 끊긴 것은 가져온 주를 저장하려 할 때 알게 되고, 알림이 닿기 전에 다음 한 주 조회는 이미 시작돼 있다.
test('주차를 넘기는 중에 끊기면 이미 시작한 한 주 뒤에 멈추고 원래 주차로 돌아온다', async () => {
  const page = load({ onSend: (count, state) => { if (count === 1) state.lost = true; } });
  await page.userQuery();
  assert.deepEqual(page.calls.sent, [WEEKS[1][0], WEEKS[2][0], WEEKS[0][0]]);
  assert.match(page.status(), GUIDE);
  assert.deepEqual(page.calls.errors, []);
});

test('끊긴 뒤 "전체 보기"를 눌러도 오류 없이 안내가 남는다', async () => {
  const page = load({ lostAt: 0 });
  page.openViewer();
  await sleep(30);
  assert.match(page.status(), GUIDE);
  assert.deepEqual(page.calls.errors, []);
});
