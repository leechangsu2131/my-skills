// util-storagemap server.js 의 순수 함수·StorageMapService 시험 (T07)
//
// server.js 는 불러오는 순간 express·Supabase·TLS 설정을 하고 함수도 내보내지 않는다.
// 그래서 server.js 글에서 필요한 구간만 잘라 node:vm 안에서 돌린다(소스는 고치지 않음).
// 네트워크·비밀값·실제 Supabase 없이 가짜(stub)만 쓴다.
//
// 실행: skills/util-storagemap 폴더에서  node --test tests/
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(path.join(__dirname, '..', 'server.js'), 'utf8');

function between(startMarker, endMarker) {
  const start = SOURCE.indexOf(startMarker);
  const end = SOURCE.indexOf(endMarker, start + 1);
  if (start === -1 || end === -1) {
    throw new Error(`server.js 에서 구간을 찾지 못함: ${startMarker} ~ ${endMarker} (server.js 구조가 바뀜 → 시험의 자르는 기준을 고쳐야 함)`);
  }
  return SOURCE.slice(start, end);
}

// server.js 에서 가져올 구간 (TLS·express 부분은 제외)
const CODE = [
  between('const truthyValues', 'const useInsecureTls'),
  between('const TABLES = {', 'const systemCaCertificates'),
  between('function parseTags', 'const storageService = new StorageMapService'),
].join('\n');

const EXPORTS = `({
  isTruthy, TABLES, COLUMNS, ID_COLUMNS, nowIso, makeId, toNumber, optionalString,
  stripUndefined, pickRecord, countStats, unwrapErrorDetails, formatSupabaseError,
  parseTags, NORMALIZE, StorageMapService,
})`;

// env: 가짜 환경변수. createClientCalls: 가짜 createClient 가 받은 인자를 쌓는다.
function load(env = {}) {
  const createClientCalls = [];
  const sandbox = {
    process: { env: { ...env } },
    console: { log() {}, warn() {}, error() {} },
    createClient: (...args) => {
      createClientCalls.push(args);
      return { fake: true };
    },
    systemCaFetch: async () => { throw new Error('시험에서 네트워크를 쓰면 안 됨'); },
    useSystemCaFetch: false,
    usingSystemCa: false,
    useInsecureTls: false,
  };
  vm.createContext(sandbox);
  const api = vm.runInContext(`${CODE}\n${EXPORTS}`, sandbox);
  return { ...api, createClientCalls };
}

const lib = load();

// 배열·객체는 vm 안에서 만들어져 prototype 이 달라 deepStrictEqual 이 실패한다 → JSON 으로 맞춰 비교
const plain = (value) => JSON.parse(JSON.stringify(value));

// ───────── isTruthy ─────────
test('isTruthy: 1/true/yes/on 은 참(대소문자·공백 무시)', () => {
  for (const v of ['1', 'true', 'TRUE', ' Yes ', 'on', 1, true]) {
    assert.equal(lib.isTruthy(v), true, `값 ${JSON.stringify(v)}`);
  }
});

test('isTruthy: 그 밖의 값은 거짓', () => {
  for (const v of ['', ' ', '0', 'false', 'no', 'off', 'maybe', undefined, null, 0, false]) {
    assert.equal(lib.isTruthy(v), false, `값 ${JSON.stringify(v)}`);
  }
});

// ───────── toNumber ─────────
test('toNumber: 숫자·숫자 문자열은 그대로 숫자로', () => {
  assert.equal(lib.toNumber(5), 5);
  assert.equal(lib.toNumber('12.5'), 12.5);
  assert.equal(lib.toNumber('-3'), -3);
});

test('toNumber: 숫자가 아니면 기본값(생략하면 0)', () => {
  assert.equal(lib.toNumber('abc'), 0);
  assert.equal(lib.toNumber('abc', 7), 7);
  assert.equal(lib.toNumber(undefined, 120), 120);
  assert.equal(lib.toNumber(NaN, 9), 9);
  assert.equal(lib.toNumber(Infinity, 9), 9);
  assert.equal(lib.toNumber({}, 4), 4);
});

// 확인 필요: 빈 문자열·null 은 Number() 가 0 으로 바꿔서 기본값이 아니라 0 이 된다.
// 물건 수량(quantity)이 비어 오면 기본 1 이 아니라 0 이 되는 것이 의도인지 교사 확인 필요.
test('toNumber: 현재 동작 — 빈 문자열·null 은 기본값이 아니라 0', () => {
  assert.equal(lib.toNumber('', 1), 0);
  assert.equal(lib.toNumber(null, 1), 0);
});

test('toNumber: 빈 값이면 기본값을 쓰는 것이 의도라면 (의도 확인 전까지 todo)', { todo: '수량 빈칸 → 0 이 의도인지 확인 필요 (ISSUES 참고)' }, () => {
  assert.equal(lib.toNumber('', 1), 1);
  assert.equal(lib.toNumber(null, 1), 1);
});

// ───────── optionalString / stripUndefined / pickRecord / countStats ─────────
test('optionalString: undefined·null·빈 문자열은 undefined, 나머지는 문자열로', () => {
  assert.equal(lib.optionalString(undefined), undefined);
  assert.equal(lib.optionalString(null), undefined);
  assert.equal(lib.optionalString(''), undefined);
  assert.equal(lib.optionalString('a'), 'a');
  assert.equal(lib.optionalString(0), '0');
  assert.equal(lib.optionalString(false), 'false');
});

test('stripUndefined: undefined 만 지우고 null·0·빈 문자열은 남김', () => {
  const out = lib.stripUndefined({ a: undefined, b: null, c: 0, d: '', e: 'x' });
  assert.deepEqual(plain(out), { b: null, c: 0, d: '', e: 'x' });
  assert.equal('a' in out, false);
});

test('pickRecord: 그 표의 열만 남기고 undefined 는 뺀다', () => {
  const out = lib.pickRecord('spaces', { space_id: 's9', name: '창고', description: undefined, hacker: 'x', extra: 1 });
  assert.deepEqual(plain(out), { space_id: 's9', name: '창고' });
});

test('pickRecord: 열 이름은 표마다 COLUMNS 를 따른다(items 의 tags 는 그대로)', () => {
  const out = lib.pickRecord('items', { item_id: 'i9', name: '풀', tags: ['문구'], quantity: 3, unknown: 'x' });
  assert.deepEqual(plain(out), { item_id: 'i9', name: '풀', tags: ['문구'], quantity: 3 });
});

test('pickRecord: 모르는 표 이름이면 오류', () => {
  // vm 안에서 만들어진 오류는 클래스가 달라 instanceof 가 안 맞으므로 이름으로 비교
  assert.throws(() => lib.pickRecord('nope', {}), (error) => error.name === 'TypeError');
});

test('COLUMNS·ID_COLUMNS: 표마다 id 열이 COLUMNS 안에 있다', () => {
  assert.deepEqual(Object.keys(lib.COLUMNS).sort(), Object.keys(lib.ID_COLUMNS).sort());
  for (const key of Object.keys(lib.COLUMNS)) {
    assert.ok(lib.COLUMNS[key].includes(lib.ID_COLUMNS[key]), `${key} 표에 ${lib.ID_COLUMNS[key]} 열이 없음`);
  }
});

test('TABLES: 환경변수가 없으면 기본 표 이름, 있으면 그 이름', () => {
  assert.equal(lib.TABLES.items, 'storage_map_items');
  const custom = load({ SUPABASE_TABLE_ITEMS: 'my_items' });
  assert.equal(custom.TABLES.items, 'my_items');
  assert.equal(custom.TABLES.spaces, 'storage_map_spaces');
});

test('countStats: 공간·가구·물건·이력 개수 (구역은 세지 않음)', () => {
  const out = lib.countStats({ spaces: [1], furniture: [1, 2], zones: [1, 2, 3], items: [1, 2, 3, 4], history: [] });
  assert.deepEqual(plain(out), { spaces: 1, furniture: 2, items: 4, history: 0 });
});

// ───────── makeId / nowIso ─────────
test('makeId: 앞글자 + 숫자, 연달아 불러도 형식 유지', () => {
  const id = lib.makeId('i');
  assert.match(id, /^i\d{16,}$/);
  assert.match(lib.makeId('space_'), /^space_\d{16,}$/);
});

test('nowIso: 읽을 수 있는 ISO 시각', () => {
  const text = lib.nowIso();
  assert.match(text, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
  assert.ok(Math.abs(Date.parse(text) - Date.now()) < 5000);
});

// ───────── 오류 메시지 ─────────
test('unwrapErrorDetails: message·code 를 모으고 cause 를 따라간다', () => {
  const inner = Object.assign(new Error('안쪽'), { code: 'E_IN' });
  const outer = new Error('바깥', { cause: inner });
  assert.deepEqual(plain(lib.unwrapErrorDetails(outer)), ['바깥', '안쪽 E_IN']);
});

test('unwrapErrorDetails: 같은 내용은 한 번만, cause 는 5단계까지만', () => {
  const same = new Error('같음', { cause: new Error('같음') });
  assert.deepEqual(plain(lib.unwrapErrorDetails(same)), ['같음']);

  let chain = new Error('끝');
  for (let i = 6; i >= 1; i -= 1) chain = new Error(`단계${i}`, { cause: chain });
  const details = lib.unwrapErrorDetails(chain);
  assert.equal(details.length, 5);
  assert.equal(details[0], '단계1');
});

test('unwrapErrorDetails: 오류가 아니거나 비어 있으면 빈 목록', () => {
  assert.deepEqual(plain(lib.unwrapErrorDetails(null)), []);
  assert.deepEqual(plain(lib.unwrapErrorDetails(undefined)), []);
  assert.deepEqual(plain(lib.unwrapErrorDetails({})), []);
});

test('formatSupabaseError: 이어진 오류는 " <- " 로 잇는다', () => {
  const err = new Error('겉', { cause: new Error('속') });
  assert.equal(lib.formatSupabaseError(err), '겉 <- 속');
});

test('formatSupabaseError: 인증서 오류는 안내 문장으로 바꿔 준다', () => {
  for (const code of ['SELF_SIGNED_CERT_IN_CHAIN', 'DEPTH_ZERO_SELF_SIGNED_CERT', 'UNABLE_TO_VERIFY_LEAF_SIGNATURE']) {
    const err = new Error('fetch failed', { cause: Object.assign(new Error('cert'), { code }) });
    const text = lib.formatSupabaseError(err);
    assert.match(text, /TLS certificate trust error/);
    assert.match(text, /--use-system-ca/);
  }
});

test('formatSupabaseError: 문자열·빈 값이어도 멈추지 않는다', () => {
  assert.equal(lib.formatSupabaseError('그냥 글'), '그냥 글');
  assert.equal(lib.formatSupabaseError(null), 'null');
  assert.equal(lib.formatSupabaseError({}), '[object Object]');
});

// ───────── parseTags ─────────
test('parseTags: 배열은 문자열로 바꾸고 빈 칸은 뺀다', () => {
  assert.deepEqual(plain(lib.parseTags(['a', 'b', '', 3])), ['a', 'b', '3']);
});

test('parseTags: 쉼표로 나뉜 글은 앞뒤 공백·빈 칸을 정리', () => {
  assert.deepEqual(plain(lib.parseTags(' 문구 , 교구,, 체육 ')), ['문구', '교구', '체육']);
});

test('parseTags: JSON 배열 글은 풀어서 쓴다', () => {
  assert.deepEqual(plain(lib.parseTags('["빨강","파랑"]')), ['빨강', '파랑']);
  assert.deepEqual(plain(lib.parseTags('[1, 2]')), ['1', '2']);
  assert.deepEqual(plain(lib.parseTags('[]')), []);
});

test('parseTags: 빈 글·글이 아닌 값은 빈 목록', () => {
  for (const v of ['', '   ', undefined, null, 123, {}, true]) {
    assert.deepEqual(plain(lib.parseTags(v)), [], `값 ${JSON.stringify(v)}`);
  }
});

// 배열 안의 null·undefined 는 'null'·'undefined' 이름표가 되지 않는다(ISSUE-002 해결).
test('parseTags: 배열 안의 null·undefined 는 이름표로 만들지 않는다', () => {
  assert.deepEqual(plain(lib.parseTags(['a', null, undefined])), ['a']);
});

test('parseTags: JSON 배열 글 안의 null 도 이름표로 만들지 않고, 글자 "null" 은 그대로 둔다', () => {
  assert.deepEqual(plain(lib.parseTags('["a", null, "b"]')), ['a', 'b']);
  assert.deepEqual(plain(lib.parseTags(['null', 0, false])), ['null', '0', 'false']);
});

// ───────── NORMALIZE ─────────
test('NORMALIZE: 인자가 없어도 기본값으로 채운다', () => {
  for (const key of Object.keys(lib.NORMALIZE)) {
    assert.doesNotThrow(() => lib.NORMALIZE[key](), key);
  }
  assert.equal(lib.NORMALIZE.spaces().space_id, '');
});

test('NORMALIZE.spaces: 글로 맞추고 빈 시각은 undefined', () => {
  const out = lib.NORMALIZE.spaces({ space_id: 7, name: '창고', created_at: '' });
  assert.equal(out.space_id, '7');
  assert.equal(out.name, '창고');
  assert.equal(out.description, '');
  assert.equal(out.created_at, undefined);
});

test('NORMALIZE.furniture: 크기 기본값 120×80, 위치 기본값 0, 숫자 문자열은 숫자로', () => {
  const empty = lib.NORMALIZE.furniture({ furniture_id: 'f9' });
  assert.equal(empty.width, 120);
  assert.equal(empty.height, 80);
  assert.equal(empty.pos_x, 0);
  assert.equal(empty.pos_y, 0);
  assert.equal(empty.color, undefined);

  const given = lib.NORMALIZE.furniture({ pos_x: '30', pos_y: '40.5', width: '200', height: 'abc' });
  assert.equal(given.pos_x, 30);
  assert.equal(given.pos_y, 40.5);
  assert.equal(given.width, 200);
  assert.equal(given.height, 80);
});

test('NORMALIZE.zones: position_desc 는 비면 undefined', () => {
  const out = lib.NORMALIZE.zones({ zone_id: 'z1', furniture_id: 'f1', name: '윗칸', position_desc: '' });
  assert.equal(out.position_desc, undefined);
  assert.equal(out.name, '윗칸');
});

test('NORMALIZE.items: 분류 기본값 "기타", 수량 기본값 1, 이름표는 배열로', () => {
  const out = lib.NORMALIZE.items({ item_id: 'i9', name: '가위', furniture_id: 'f1', tags: '문구, 교구' });
  assert.equal(out.category, '기타');
  assert.equal(out.quantity, 1);
  assert.deepEqual(plain(out.tags), ['문구', '교구']);
  assert.equal(out.zone_id, undefined);
  assert.equal(out.photo_url, undefined);
  assert.equal(out.memo, '');
});

test('NORMALIZE.items: 수량 숫자 문자열은 숫자로, 숫자 아닌 글은 1', () => {
  assert.equal(lib.NORMALIZE.items({ quantity: '25' }).quantity, 25);
  assert.equal(lib.NORMALIZE.items({ quantity: 'many' }).quantity, 1);
});

test('NORMALIZE.history: moved_at 이 없으면 지금 시각, 있으면 그대로', () => {
  const auto = lib.NORMALIZE.history({ history_id: 'h1', item_id: 'i1' });
  assert.ok(!Number.isNaN(Date.parse(auto.moved_at)));
  const given = lib.NORMALIZE.history({ moved_at: '2026-01-02T03:04:05.000Z', from_zone: '' });
  assert.equal(given.moved_at, '2026-01-02T03:04:05.000Z');
  assert.equal(given.from_zone, undefined);
  assert.equal(given.note, '');
});

// ───────── StorageMapService ─────────
test('StorageMapService: 환경변수가 없으면 연결 안 함·sample 모드', () => {
  const l = load({});
  const service = new l.StorageMapService();
  assert.equal(service.client, null);
  assert.equal(service.isConfigured(), false);
  assert.equal(service.isConnected(), false);
  assert.equal(service.mode, 'sample');
  assert.equal(l.createClientCalls.length, 0);
  assert.throws(() => service.ensureConfigured(), /Supabase 환경변수/);
});

test('StorageMapService: 안내용 자리표시 값(your-project…, your_service_role_key_here)은 연결로 치지 않는다', () => {
  const l1 = load({ SUPABASE_URL: 'https://your-project.supabase.co', SUPABASE_KEY: 'dummy-key' });
  assert.equal(new l1.StorageMapService().client, null);
  const l2 = load({ SUPABASE_URL: 'https://example.invalid', SUPABASE_KEY: 'your_service_role_key_here' });
  assert.equal(new l2.StorageMapService().client, null);
  assert.equal(l1.createClientCalls.length + l2.createClientCalls.length, 0);
});

test('StorageMapService: 주소·키가 둘 다 있으면 가짜 createClient 로 만든다(키 우선순위: SERVICE_ROLE > KEY > ANON)', () => {
  const l = load({ SUPABASE_URL: 'https://example.invalid', SUPABASE_KEY: 'fake-key', SUPABASE_ANON_KEY: 'fake-anon' });
  const service = new l.StorageMapService();
  assert.equal(service.isConfigured(), true);
  assert.equal(l.createClientCalls.length, 1);
  assert.equal(l.createClientCalls[0][0], 'https://example.invalid');
  assert.equal(l.createClientCalls[0][1], 'fake-key');
  assert.equal(l.createClientCalls[0][2].auth.persistSession, false);

  const l2 = load({ SUPABASE_URL: 'https://example.invalid', SUPABASE_SERVICE_ROLE_KEY: 'fake-service', SUPABASE_KEY: 'fake-key' });
  new l2.StorageMapService();
  assert.equal(l2.createClientCalls[0][1], 'fake-service');

  const l3 = load({ SUPABASE_URL: 'https://example.invalid', SUPABASE_ANON_KEY: 'fake-anon' });
  new l3.StorageMapService();
  assert.equal(l3.createClientCalls[0][1], 'fake-anon');

  const l4 = load({ SUPABASE_URL: 'https://example.invalid' });
  assert.equal(new l4.StorageMapService().client, null);
});

test('StorageMapService.getStatus: 연결 안 된 sample 모드 상태', () => {
  const service = new lib.StorageMapService();
  const status = service.getStatus();
  assert.equal(status.authenticated, false);
  assert.equal(status.configured, false);
  assert.equal(status.readOnly, true);
  assert.equal(status.provider, 'supabase');
  assert.equal(status.mode, 'sample');
  assert.equal(status.tls.insecure, false);
  assert.equal(status.tables.items, 'storage_map_items');
  assert.ok(!Number.isNaN(Date.parse(status.timestamp)));
});

test('StorageMapService.getStatus: mode 가 supabase 면 authenticated', () => {
  const service = new lib.StorageMapService();
  service.mode = 'supabase';
  assert.equal(service.getStatus().authenticated, true);
});

function sampleService() {
  const service = new lib.StorageMapService();
  service.loadSampleData();
  return service;
}

test('loadSampleData: 샘플 공간 2·가구 3·물건 3, cache 로 돌려준다', () => {
  const service = new lib.StorageMapService();
  const cache = service.loadSampleData();
  assert.equal(cache, service.cache);
  assert.equal(cache.spaces.length, 2);
  assert.equal(cache.furniture.length, 3);
  assert.equal(cache.items.length, 3);
  assert.equal(cache.zones.length, 0);
  assert.equal(cache.history.length, 0);
});

test('replaceCache: 새 id 는 추가, 같은 id 는 그 자리에서 바꾼다', () => {
  const service = sampleService();
  const added = service.replaceCache('items', { item_id: 'i99', name: '풀' });
  assert.equal(service.cache.items.length, 4);
  assert.equal(added.item_id, 'i99');

  service.replaceCache('items', { item_id: 'i1', name: '소프라노 리코더' });
  assert.equal(service.cache.items.length, 4);
  assert.equal(service.cache.items[0].name, '소프라노 리코더');
});

test('removeCache: 지운 행을 돌려주고, 없으면 null', () => {
  const service = sampleService();
  const removed = service.removeCache('items', 'i2');
  assert.equal(removed.name, '과학 교재 세트');
  assert.equal(service.cache.items.length, 2);
  assert.equal(service.removeCache('items', 'i2'), null);
  assert.equal(service.cache.items.length, 2);
});

test('searchItems: 점수 — 이름 같음 100 > 이름 포함 80 > 분류 60 > 메모·이름표 40', () => {
  const service = sampleService();
  service.cache.items.push(
    { item_id: 'a', name: '리코더 케이스', furniture_id: 'f1', category: '가방', memo: '', tags: [] },
    { item_id: 'b', name: '악보', furniture_id: 'f1', category: '리코더용', memo: '', tags: [] },
    { item_id: 'c', name: '메모지', furniture_id: 'f1', category: '문구', memo: '리코더 시간에 사용', tags: [] },
    { item_id: 'd', name: '스티커', furniture_id: 'f1', category: '문구', memo: '', tags: ['리코더'] },
  );
  const results = service.searchItems('리코더');
  const scores = Object.fromEntries(results.map((r) => [r.item_id, r.matchScore]));
  assert.deepEqual(scores, { i1: 100, a: 80, b: 60, c: 40, d: 40 });
  assert.equal(results[0].item_id, 'i1');
  const order = plain(results.map((r) => r.matchScore));
  assert.deepEqual(order, [...order].sort((x, y) => y - x));
});

test('searchItems: 대소문자·앞뒤 공백을 무시한다', () => {
  const service = sampleService();
  service.cache.items.push({ item_id: 'u', name: 'USB 메모리', furniture_id: 'f2', category: '전자기기', memo: '', tags: [] });
  assert.equal(service.searchItems('  usb ')[0].item_id, 'u');
  assert.equal(service.searchItems('USB 메모리')[0].matchScore, 100);
});

test('searchItems: 빈 검색어·공백뿐이면 빈 목록, 못 찾으면 빈 목록', () => {
  const service = sampleService();
  assert.deepEqual(plain(service.searchItems('')), []);
  assert.deepEqual(plain(service.searchItems('   ')), []);
  assert.deepEqual(plain(service.searchItems('없는물건')), []);
});

test('searchItems: 위치(공간 > 가구)를 붙여 준다', () => {
  const service = sampleService();
  const hit = service.searchItems('리모컨')[0];
  assert.equal(hit.furniture, 'TV 수납장');
  assert.equal(hit.space, '거실 수납장');
  assert.equal(hit.path, '거실 수납장 > TV 수납장');
});

test('searchItems: 가구·공간을 못 찾으면 "위치 미정"·"공간 미정"', () => {
  const service = sampleService();
  service.cache.items.push({ item_id: 'x', name: '떠도는 물건', furniture_id: 'f-none', category: '기타', memo: '', tags: [] });
  const hit = service.searchItems('떠도는')[0];
  assert.equal(hit.furniture, '위치 미정');
  assert.equal(hit.space, '공간 미정');
  assert.equal(hit.path, '? > ?');
});

test('searchItems: 원래 cache 의 물건을 바꾸지 않는다', () => {
  const service = sampleService();
  service.searchItems('리코더');
  assert.equal('matchScore' in service.cache.items[0], false);
});

test('getSpaceData: 없는 공간은 null', () => {
  assert.equal(sampleService().getSpaceData('nope'), null);
});

test('getSpaceData: 그 공간의 가구·물건과 가구별 물건 수', () => {
  const service = sampleService();
  const data = service.getSpaceData('s1');
  assert.equal(data.space.name, '교실 창고');
  assert.deepEqual(plain(data.furniture.map((f) => [f.furniture_id, f.itemCount])), [['f1', 2], ['f2', 0]]);
  assert.deepEqual(plain(data.items.map((i) => i.item_id)), ['i1', 'i2']);
  assert.equal(data.furniture[0].items.length, 2);

  const other = service.getSpaceData('s2');
  assert.deepEqual(plain(other.items.map((i) => i.item_id)), ['i3']);
});

test('getAllData: cache 를 그대로 돌려준다', () => {
  const service = sampleService();
  assert.equal(service.getAllData(), service.cache);
});
