// teacherlesson-from-neis extension/popup.js 의 최상위 함수 시험 (T15)
//
// popup.js 는 불러오는 순간 document.querySelector 로 화면 요소를 잡고 chrome.storage 를 읽는다.
// 그래서 가짜 document·chrome·Date 를 넣은 node:vm 안에서 파일 전체를 그대로 돌린다(소스는 고치지 않음).
// 시험 대상: 순수 함수(normalizeProfileKind·normalizeApproverNames·sanitizeApprovalProfiles·
// buildApprovalBatches·localMonth)와, 가짜 화면 요소만으로 확인되는 updateAbsenceSelection·
// updateCandidateProfileLabels·setAbsenceSelection.
// 대상이 아닌 것: collectOnNeisPage·collectStudentStatusOnNeis·scanAbsenceWorkQueueOnNeis 처럼 NEIS 페이지에
// 주입되는 함수(크롬 주입 구조상 안쪽 함수를 따로 불러올 수 없음), 실제 NEIS 접수·상신.
// 실제 NEIS·크롬·네트워크·학생 정보는 쓰지 않는다(예시는 '학생A').
//
// 실행: skills/teacherlesson-from-neis 폴더에서  node --test tests/popup.test.js
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(path.join(__dirname, '..', 'extension', 'popup.js'), 'utf8');
const RealDate = Date;

// 어떤 속성을 불러도 아무 일 안 하는 함수가 나오는 가짜 화면 요소. 값을 넣으면 그대로 저장한다.
function fakeElement(overrides = {}) {
  const store = {
    dataset: {},
    children: [],
    classList: {
      names: new Set(),
      add(name) { this.names.add(name); },
      remove(name) { this.names.delete(name); },
      contains(name) { return this.names.has(name); },
      toggle(name, force) {
        const on = force === undefined ? !this.names.has(name) : Boolean(force);
        if (on) this.names.add(name); else this.names.delete(name);
        return on;
      },
    },
    textContent: '',
    disabled: false,
    style: {},
    ...overrides,
  };
  return new Proxy(store, {
    get(target, prop) {
      if (prop in target) return target[prop];
      if (typeof prop === 'symbol') return undefined;
      if (prop === 'querySelector' || prop === 'closest') return () => null;
      if (prop === 'querySelectorAll') return () => [];
      return () => {};
    },
    set(target, prop, value) { target[prop] = value; return true; },
  });
}

// popup.js 를 새로 불러온다. 옵션으로 chrome.storage 에 들어 있는 값을 정한다.
// 돌려주는 state.failStorage 를 true 로 바꾸면 그 뒤의 저장소 읽기가 오류를 낸다.
async function load({ stored = {}, now = [2026, 10, 25, 12, 0, 0] } = {}) {
  const state = { failStorage: false };
  const elements = new Map();
  const document = {
    querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, fakeElement());
      return elements.get(selector);
    },
    createElement() { return fakeElement(); },
  };
  const chrome = {
    storage: {
      local: {
        get: async () => { if (state.failStorage) throw new Error('저장소 오류'); return stored; },
        set: async () => {},
        remove: async () => {},
      },
      onChanged: { addListener() {} },
    },
    tabs: { create() {} },
    runtime: { getURL: (p) => p, sendMessage: async () => ({}) },
  };
  class FakeDate extends RealDate {
    constructor(...args) { super(...(args.length ? args : now)); }
  }
  const context = vm.createContext({ document, chrome, Date: FakeDate, console });
  vm.runInContext(SOURCE, context, { filename: 'popup.js' });
  const get = (code) => vm.runInContext(code, context);
  await get('approvalProfilesReady');
  return { get, elements, context, state };
}

// vm 안에서 만든 배열·객체는 다른 Object.prototype 을 쓰므로 비교 전에 평범한 값으로 옮긴다.
const plain = (value) => JSON.parse(JSON.stringify(value));

test('normalizeProfileKind: 앞뒤 공백 제거·가운데 공백 하나로·40자까지·빈 값은 빈 글자', async () => {
  const { get } = await load();
  const fn = get('normalizeProfileKind');
  assert.equal(fn('  결석신고  '), '결석신고');
  assert.equal(fn('교외  체험\t학습\n신청'), '교외 체험 학습 신청');
  assert.equal(fn('가　나'), '가 나');                    // 전각 공백도 공백
  assert.equal(fn(null), '');
  assert.equal(fn(undefined), '');
  assert.equal(fn(0), '');                                    // 0 도 "빈 값"으로 본다(|| 때문)
  assert.equal(fn(1234), '1234');
  assert.equal(fn('가'.repeat(60)), '가'.repeat(40));
});

test('normalizeApproverNames: 줄마다 한 명·공백 제거·빈 줄 버림·중복 제거(처음 것 유지)·40자까지', async () => {
  const { get } = await load();
  const fn = (v) => plain(get('normalizeApproverNames')(v));
  assert.deepEqual(fn('교감\n교장'), ['교감', '교장']);
  assert.deepEqual(fn('  교감 \r\n\r\n 교장\r\n'), ['교감', '교장']);
  assert.deepEqual(fn('교장\n교감\n교장\n교감'), ['교장', '교감']);
  assert.deepEqual(fn('가'.repeat(50) + '\n' + '가'.repeat(45)), ['가'.repeat(40)]);   // 자른 뒤 같으면 중복
  assert.deepEqual(fn(''), []);
  assert.deepEqual(fn(null), []);
  assert.deepEqual(fn(undefined), []);
  assert.deepEqual(fn('   \n  '), []);
});

test('sanitizeApprovalProfiles: 올바른 저장값은 정리해서 돌려주고, 이상한 값은 빈 객체·버림', async () => {
  const { get } = await load();
  const fn = (v) => plain(get('sanitizeApprovalProfiles')(v));
  assert.deepEqual(fn({ 결석신고: ['담임', '교감', '교장'] }), { 결석신고: ['담임', '교감', '교장'] });
  // 종류 이름은 공백 정리, 결재자는 중복·빈 칸 정리
  assert.deepEqual(fn({ '  교외  체험학습 ': [' 교감 ', '', '교감', '교장'] }), { '교외 체험학습': ['교감', '교장'] });
  // 이상한 입력 전체
  for (const bad of [null, undefined, 'text', 42, true, ['결석신고'], [['교감']]]) {     // 배열은 {"0": …} 처럼 읽히면 안 된다
    assert.deepEqual(fn(bad), {}, JSON.stringify(bad));
  }
  // 결재자가 없거나 배열이 아닌 종류, 이름이 빈 종류는 버린다
  assert.deepEqual(fn({ A: [], B: ['  '], C: '교감', D: null, E: { 0: '교감' }, '': ['교감'], '   ': ['교감'], F: ['교감'] }), { F: ['교감'] });
});

test('sanitizeApprovalProfiles: 이름만 다르게 적힌 같은 종류는 나중 것이 이긴다(지금 동작을 기록)', async () => {
  const { get } = await load();
  const out = plain(get('sanitizeApprovalProfiles')({ 결석신고: ['담임'], ' 결석신고 ': ['교감'] }));
  assert.deepEqual(out, { 결석신고: ['교감'] });
});

test('불러올 때 저장된 결재선을 정리해서 쓰고, 저장소 읽기가 실패하면 빈 결재선', async () => {
  const stored = { teacherlessonNeisApprovalProfiles: { ' 결석신고 ': ['담임', '담임', '교감'], 이상함: 'x' } };
  const a = await load({ stored });
  assert.deepEqual(plain(a.get('approvalProfiles')), { 결석신고: ['담임', '교감'] });

  // 이미 결재선이 들어 있는 상태에서 저장소 읽기가 실패하면, 남은 값을 쓰지 않고 빈 결재선으로 돌린다
  a.get('approvalProfiles = { 결석신고: ["담임"] }');
  a.state.failStorage = true;
  await a.get('loadApprovalProfiles()');
  assert.deepEqual(plain(a.get('approvalProfiles')), {});
});

test('localMonth: 이번 달을 YYYY-MM 으로(한 자리 월은 0 채움), 처음 열 때 달 입력칸에 넣는다', async () => {
  const jan = await load({ now: [2026, 0, 5, 12, 0, 0] });
  assert.equal(jan.get('localMonth()'), '2026-01');
  assert.equal(jan.elements.get('#monthInput').value, '2026-01');
  const nov = await load({ now: [2026, 10, 25, 12, 0, 0] });
  assert.equal(nov.get('localMonth()'), '2026-11');
  const dec = await load({ now: [2027, 11, 31, 23, 59, 59] });
  assert.equal(dec.get('localMonth()'), '2027-12');
});

test('setStatus: 글을 넣고, 오류면 빨간색·아니면 회색', async () => {
  const { get, elements } = await load();
  const status = elements.get('#status');
  get('setStatus')('가져오는 중');
  assert.equal(status.textContent, '가져오는 중');
  assert.equal(status.style.color, '#718399');
  get('setStatus')('실패했어요', true);
  assert.equal(status.textContent, '실패했어요');
  assert.equal(status.style.color, '#a33333');
  get('setStatus')('다시 시도');                                           // 오류 뒤 일반 안내는 다시 회색
  assert.equal(status.style.color, '#718399');
});

test('buildApprovalBatches: 신청 유형별로 묶고 처음 나온 순서를 지킨다', async () => {
  const { get } = await load();
  get('approvalProfiles = { 결석신고: ["담임", "교감"], 교외체험학습: ["교장"] }');
  const items = [
    { kind: '교외체험학습', application_id: 'B1' },
    { kind: '결석신고', application_id: 'A1', absence_category_code: '02', teacher_reason: '사유1' },
    { kind: '교외체험학습', application_id: 'B2' },
    { kind: '결석신고', application_id: 'A2' },
  ];
  const out = plain(get('buildApprovalBatches')(items));
  assert.deepEqual(out.map((b) => b.kind), ['교외체험학습', '결석신고']);
  assert.deepEqual(out[0], { kind: '교외체험학습', applicationIds: ['B1', 'B2'], approvers: ['교장'], absenceCategoryCodes: {}, teacherReasons: {} });
  assert.deepEqual(out[1].applicationIds, ['A1', 'A2']);
  assert.deepEqual(out[1].approvers, ['담임', '교감']);
});

test('buildApprovalBatches: 결석신고만 결석 구분·교사 추가 내용을 담고, 고른 값 → 원래 값 → 기본값 순서로 정한다', async () => {
  const { get } = await load();
  get('approvalProfiles = { 결석신고: ["담임"] }');
  const items = [
    { kind: '결석신고', application_id: 'A1', selected_absence_category_code: '03', absence_category_code: '02', selected_teacher_reason: '고친 사유', teacher_reason: '원래 사유' },
    { kind: '결석신고', application_id: 'A2', absence_category_code: '02', teacher_reason: '원래 사유' },
    { kind: '결석신고', application_id: 'A3' },
    { kind: '결석신고', application_id: 'A4', selected_absence_category_code: '', absence_category_code: '04' },   // 빈 고른 값은 원래 값으로
    { kind: '결석신고', application_id: 'A5', selected_teacher_reason: '', teacher_reason: '원래 사유' },          // 일부러 비운 사유는 그대로 비움
    { kind: '결석신고', application_id: 'A6', selected_teacher_reason: null, teacher_reason: '원래 사유' },        // null 은 원래 값으로
  ];
  const [batch] = plain(get('buildApprovalBatches')(items));
  assert.deepEqual(batch.absenceCategoryCodes, { A1: '03', A2: '02', A3: '01', A4: '04', A5: '01', A6: '01' });
  assert.deepEqual(batch.teacherReasons, { A1: '고친 사유', A2: '원래 사유', A3: '', A4: '', A5: '', A6: '원래 사유' });
});

test('buildApprovalBatches: 등록 안 된 유형은 결재자 빈 목록, 공백이 낀 유형 이름도 같은 유형으로 묶는다, 선택이 없으면 빈 목록', async () => {
  const { get } = await load();
  get('approvalProfiles = { 결석신고: ["담임"] }');
  const out = plain(get('buildApprovalBatches')([
    { kind: '처음 보는 유형', application_id: 'X1' },
    { kind: ' 결석신고 ', application_id: 'A1' },
    { kind: '결석신고', application_id: 'A2' },
  ]));
  assert.equal(out.length, 2);
  assert.deepEqual(out[0].approvers, []);
  assert.equal(out[1].kind, '결석신고');
  assert.deepEqual(out[1].applicationIds, ['A1', 'A2']);
  assert.deepEqual(out[1].absenceCategoryCodes, { A1: '01', A2: '01' });   // 공백 낀 이름도 결석신고로 취급
  assert.deepEqual(plain(get('buildApprovalBatches')([])), []);
});

// ---- 가짜 화면 요소로 확인하는 함수들 ----

function checkbox(applicationId, { checked = true, disabled = false } = {}) {
  return fakeElement({ dataset: { applicationId }, checked, disabled });
}

// 후보 목록 칸의 querySelectorAll 을 가짜로. 실제 브라우저처럼 ':checked' 선택자는 체크된 칸만 돌려준다.
function setSelectable(elements, inputs) {
  elements.get('#actionCandidates').querySelectorAll = (selector) => {
    if (!selector.includes('checkbox')) return [];
    return selector.includes(':checked') ? inputs.filter((input) => input.checked) : inputs;
  };
}

test('updateAbsenceSelection: 선택 요약 글·건수·실행 단추 상태(결석신고와 그 밖의 유형)', async () => {
  const { get, elements } = await load();
  get('approvalProfiles = { 결석신고: ["담임", "교감"] }');
  get(`absenceWorkCandidates = [
    { key: 'K1', application_id: 'A1', kind: '결석신고', status: '접수대기', class_name: '3-1', student: '학생A',
      start_date: '2026-11-24', end_date: '2026-11-24', absence_category_code: '02', reason: '', teacher_reason: '' },
    { key: 'K2', application_id: 'A2', kind: '결석신고', status: '승인요청대기', class_name: '3-1', student: '학생B',
      start_date: '2026-11-24', end_date: '2026-11-26', selected_absence_category_code: '99', reason: '감기', selected_teacher_reason: '확인함' },
    { key: 'K3', application_id: 'A3', kind: '교외체험학습', kind_label: '체험학습 신청서', status: '접수대기', class_name: '3-1', student: '학생C',
      start_date: '2026-12-01', end_date: '2026-12-02', absence_category: '인정', reason: '가족 여행' },
    { key: 'K4', application_id: 'A4', kind: '결석신고', status: '접수대기', class_name: '3-1', student: '학생D', start_date: '2026-11-20', end_date: '2026-11-20' },
  ]`);
  setSelectable(elements, [checkbox('K1'), checkbox('K2'), checkbox('K3'), checkbox('NONE')]);
  get('updateAbsenceSelection')();

  assert.equal(elements.get('#actionPreviewText').textContent, '3건 선택 · 새 접수 2건 · 승인요청 3건');
  assert.equal(elements.get('#actionSelectionSummary').textContent, [
    '[결석신고서] 3-1 학생A · 2026-11-24 · 인정결석\n신청 내용 · 기재 없음\n담임/교사 추가 내용 · 없음\n결재선(결석신고) · 담임 → 교감',
    '[결석신고서] 3-1 학생B · 2026-11-24 ~ 2026-11-26 · 구분 확인 필요\n신청 내용 · 감기\n담임/교사 추가 내용 · 확인함\n결재선(결석신고) · 담임 → 교감',
    '[체험학습 신청서] 3-1 학생C · 2026-12-01 ~ 2026-12-02 · 인정\n장소 · 가족 여행\n결재선(교외체험학습) · 결재선 미등록',
  ].join('\n'));
  assert.equal(elements.get('#actionExecuteButton').disabled, false);
  assert.deepEqual([...get('selectedWorkApplicationIds')].sort(), ['K1', 'K2', 'K3', 'NONE']);   // 화면에서 체크된 것 그대로 기억(후보에 없는 것도)
});

test('updateAbsenceSelection: 선택이 없거나 실행 중이면 실행 단추를 막는다', async () => {
  const { get, elements } = await load();
  get(`absenceWorkCandidates = [{ key: 'K1', application_id: 'A1', kind: '결석신고', status: '접수대기', student: '학생A', start_date: '2026-11-24', end_date: '2026-11-24' }]`);

  setSelectable(elements, []);
  get('updateAbsenceSelection')();
  assert.equal(elements.get('#actionPreviewText').textContent, '0건 선택 · 새 접수 0건 · 승인요청 0건');
  assert.equal(elements.get('#actionSelectionSummary').textContent, '');
  assert.equal(elements.get('#actionExecuteButton').disabled, true);

  setSelectable(elements, [checkbox('K1')]);
  get('absenceUiExecutionInFlight = true');
  get('updateAbsenceSelection')();
  assert.equal(elements.get('#actionExecuteButton').disabled, true);      // 이미 실행 중이면 한 번 더 못 누름

  get('absenceUiExecutionInFlight = false');
  get('updateAbsenceSelection')();
  assert.equal(elements.get('#actionExecuteButton').disabled, false);
});

test('setAbsenceSelection: 막힌(disabled) 칸은 건드리지 않고 나머지만 모두 선택·해제한 뒤 요약을 갱신한다', async () => {
  const { get, elements } = await load();
  get(`absenceWorkCandidates = [
    { key: 'K1', application_id: 'A1', kind: '결석신고', status: '접수대기', student: '학생A', start_date: '2026-11-24', end_date: '2026-11-24' },
    { key: 'K2', application_id: 'A2', kind: '결석신고', status: '접수대기', student: '학생B', start_date: '2026-11-24', end_date: '2026-11-24' },
  ]`);
  const open = checkbox('K1', { checked: false });
  const locked = checkbox('K2', { checked: false, disabled: true });
  setSelectable(elements, [open, locked]);

  get('setAbsenceSelection')(true);
  assert.equal(open.checked, true);
  assert.equal(locked.checked, false);                                    // 막힌 칸은 그대로
  assert.equal(elements.get('#actionPreviewText').textContent, '1건 선택 · 새 접수 1건 · 승인요청 1건');

  get('setAbsenceSelection')(false);
  assert.equal(open.checked, false);
  assert.equal(elements.get('#actionPreviewText').textContent, '0건 선택 · 새 접수 0건 · 승인요청 0건');
});

test('updateCandidateProfileLabels: 결재선이 있으면 "저장됨", 없으면 "미등록"과 missing 표시', async () => {
  const { get, elements } = await load();
  get('approvalProfiles = { 결석신고: ["담임"] }');
  get(`absenceWorkCandidates = [
    { key: 'K1', kind: '결석신고' },
    { key: 'K2', kind: '교외체험학습' },
  ]`);
  const labelOf = (id) => {
    const status = fakeElement();
    return { status, label: fakeElement({ dataset: { applicationId: id }, querySelector: (s) => (s === '.profile-status' ? status : null) }) };
  };
  const one = labelOf('K1');
  const two = labelOf('K2');
  const gone = labelOf('K9');                                              // 후보에 없는 칸은 건드리지 않음
  elements.get('#actionCandidates').querySelectorAll = (selector) => (selector === '.action-candidate' ? [one.label, two.label, gone.label] : []);
  get('updateCandidateProfileLabels')();

  assert.equal(one.status.textContent, "'결석신고' 결재선 저장됨");
  assert.equal(one.status.classList.contains('missing'), false);
  assert.equal(two.status.textContent, "'교외체험학습' 결재선 미등록 — 아래 결재선 설정에 저장하세요");
  assert.equal(two.status.classList.contains('missing'), true);
  assert.equal(gone.status.textContent, '');
});
