const fs = require('fs'), vm = require('vm');
const TZ = 'Asia/Seoul';
const fmtDate = d => new Date(d).toLocaleDateString('sv-SE', { timeZone: TZ });
const today = fmtDate(new Date());
const off = n => fmtDate(new Date(new Date(today + 'T00:00:00+09:00').getTime() + n * 86400000));

let tabs, props, lockCalls;
function mkSheet(name) {
  return {
    name,
    getDataRange: () => ({ getValues: () => tabs[name].map(r => r.slice()) }),
    getRange: (r, c) => ({ setValue: v => { while (tabs[name].length < r) tabs[name].push([]); const row = tabs[name][r-1]; while (row.length < c) row.push(''); row[c-1] = v; } }),
    appendRow: row => tabs[name].push(row.slice()),
    deleteRow: r => tabs[name].splice(r - 1, 1),
  };
}
const ctx = {
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => props[k] }) },
  ContentService: { MimeType: { JSON: 'json' }, createTextOutput: t => ({ text: t, setMimeType() { return this; } }) },
  LockService: { getScriptLock: () => ({ waitLock: () => { lockCalls++; }, releaseLock: () => {} }) },
  Utilities: { formatDate: (d, tz, f) => /HH/.test(f) ? new Date(d).toLocaleString('sv-SE', { timeZone: tz }).slice(0, 16) : fmtDate(d) },
  SpreadsheetApp: { getActive: () => ({
    getSheetByName: n => tabs[n] ? mkSheet(n) : null,
    insertSheet: n => { tabs[n] = []; return mkSheet(n); },
  }) },
  console, Date, JSON, String, Math, Object, Number, Array,
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('kakao_chatbot.gs', 'utf8') + '\n;globalThis.doPost=doPost;globalThis.doGet=doGet;', ctx);

const H = ['키','날짜','구분','내용','상태','출처','대상','담당'];
function reset() {
  lockCalls = 0;
  props = { SECRET: 's3cret', ALLOWED_IDS: 'U-teacher' };
  tabs = {
    '일정DB': [H,
      ['k1', off(7),  '개인', '탄소중립 실천학급 결과보고서 제출', '', '수동', '3학년', '김철수, 이영희, 박민수'],
      ['k2', off(10), '개인', '프로젝트 학습 보고서 제출', '', '수동', '3학년', '3학년교사'],
      ['k3', off(3),  '학교', '한마당 인솔', '', '수동', '3학년', ''],
      ['k4', off(5),  '개인', '학급자율운영비 집행', '', '수동', '3학년', ''],
      ['k5', off(8),  '개인', '교구 신청서 제출', '', '수동', '3학년', '전체'],
      ['k6', off(9),  '개인', '엉뚱한 담당 시험', '', '수동', '3학년', '최아무개'],
      ['k7', off(-2), '개인', '밀린 선생님 할 일', '', '수동', '3학년', ''],
      ['k8', today,   '출장', '오늘 출장', '', '수동', '3학년', ''],
    ],
    '구성원': [['이름','그룹','챗봇아이디','역할','이메일'],
      ['김철수', '3학년교사', 'U-kim', '일반', 'kim@x.kr'],
      ['이영희', '3학년교사', 'U-lee', '일반', ''],
      ['박민수', '4학년교사', 'U-park', '일반', ''],
      ['이창수', '3학년교사', 'U-admin2', '관리자', ''],
    ],
    '완료기록': [['시각','키','이름','내용']],
  };
}
function say(utter, uid = 'U-teacher', key = 's3cret') {
  const e = { parameter: { key }, postData: { contents: JSON.stringify({ userRequest: { utterance: utter, user: { id: uid } } }) } };
  return JSON.parse(ctx.doPost(e).text).template.outputs[0].simpleText.text;
}
const statusOf = k => tabs['일정DB'].find(r => r[0] === k)[4];
const doneRows = () => tabs['완료기록'].slice(1);
let pass = 0, fail = 0;
function check(name, cond, extra) { if (cond) pass++; else { fail++; console.log('FAIL', name, '\n   ', extra === undefined ? '' : extra); } }

// 1. 담당자 본인이 완료 → 기록 한 줄, 진행도, 상태는 아직 비어 있음
reset();
let t = say('완료 탄소중립', 'U-kim');
check('member completes own', t.startsWith('✔ 완료 처리했어요 (1/3)') && doneRows().length === 1 && doneRows()[0][1] === 'k1' && doneRows()[0][2] === '김철수', t);
check('status stays empty until all', statusOf('k1') === '', statusOf('k1'));
check('lock used', lockCalls >= 1);
// 2. 같은 사람이 또 완료 → 남은 게 없음, 중복 기록 없음
t = say('탄소중립 완료', 'U-kim');
check('no double record', t.includes('못 찾았어요') && doneRows().length === 1, t);
// 3. 나머지 두 명이 완료하면 상태 ✔ 자동
t = say('완료 탄소중립', 'U-lee');
check('second', t.includes('(2/3)') && statusOf('k1') === '', t);
t = say('완료 탄소중립', 'U-park');
check('third → all done + status ✔', t.includes('(3/3)') && t.includes('모두 완료') && statusOf('k1') === '✔', t);
// 4. 되돌리기: 본인 기록만 삭제, 상태 ✔ 해제
t = say('되돌리기 탄소중립', 'U-park');
check('undo own + clear status', t.startsWith('↩') && doneRows().length === 2 && statusOf('k1') === '', t);
// 5. 다른 사람 몫은 일반 사용자 불가, 관리자는 가능
t = say('완료 탄소중립 박민수', 'U-kim');
check('member cannot do others', t === '다른 사람 몫은 관리자만 처리할 수 있어요.' && doneRows().length === 2, t);
t = say('완료 탄소중립 박민수', 'U-teacher');
check('admin does for others', t.includes('(3/3)') && t.includes('박민수 님 몫') && statusOf('k1') === '✔', t);
t = say('되돌리기 탄소중립 박민수', 'U-teacher');
check('admin undoes for others', t.startsWith('↩') && doneRows().length === 2, t);

// 6. 담당이 아닌 사람은 못 함
reset();
t = say('완료 탄소중립', 'U-admin2');   // 관리자 계정이지만 담당 아님 → 이름 지정 없으면 선생님 본인 할 일(담당 없는 것)만 후보
check('admin not assignee falls back to legacy only', t.includes('못 찾았어요') && doneRows().length === 0, t);
// 7. 그룹 / 전체 담당
reset();
t = say('할일', 'U-park');   // 박민수: 4학년교사 → k2(3학년교사) 아님, k5(전체) 해당, k1(이름) 해당
check('my tasks respects 이름/전체/그룹', t.includes('탄소중립') && t.includes('교구 신청서') && !t.includes('프로젝트 학습') && !t.includes('학급자율운영비'), t);
t = say('할일', 'U-kim');
check('group task for 3학년교사', t.includes('프로젝트 학습') && t.includes('탄소중립') && t.includes('교구 신청서'), t);
t = say('완료 프로젝트', 'U-lee');
check('group member completes group task (1/2)', t.includes('(1/') && doneRows().length === 1 && doneRows()[0][1] === 'k2', t);
// 8. 키워드 모호함
reset();
t = say('완료 신청서', 'U-kim');    // 교구 신청서 하나뿐 → 처리
check('unique keyword', t.startsWith('✔') && doneRows()[0][1] === 'k5', t);
t = say('완료 보고서', 'U-kim');     // 탄소중립 결과보고서 / 프로젝트 학습 보고서 → 모호
check('ambiguous asks', t.startsWith('여러 개예요') && doneRows().length === 1, t);
// 9. '나 완료했어' / '완료' 단독: 남은 게 하나면 처리, 여럿이면 목록
reset();
t = say('나 완료했어', 'U-park');   // 박민수: k1, k5 두 개 → 모호
check('bare done asks list', t.startsWith('여러 개예요'), t);
say('완료 신청서', 'U-park');
t = say('완료', 'U-park');           // 남은 건 k1 하나
check('bare done completes single remaining', t.startsWith('✔') && t.includes('탄소중립'), t);
// 10. 선생님 본인 할 일(담당 없음, 상태 칸) — 관리자만
reset();
t = say('완료 운영비', 'U-teacher');
check('admin legacy complete', t.startsWith('✔') && statusOf('k4') === '✔' && doneRows().length === 0, t);
t = say('되돌리기 운영비', 'U-teacher');
check('admin legacy undo', t.startsWith('↩') && statusOf('k4') === '', t);
t = say('완료 운영비', 'U-kim');
check('member cannot complete legacy rows', t.includes('못 찾았어요') && statusOf('k4') === '', t);
// 11. 현황(관리자만)
reset();
say('완료 탄소중립', 'U-kim');
t = say('현황', 'U-teacher');
check('status shows done/not done', t.includes('1/3') && t.includes('✔ 김철수') && t.includes('⏳ 이영희, 박민수'), t);
check('status warns unknown assignee', t.includes('"최아무개"을(를) 구성원 탭에서 못 찾았어요'), t);
check('status excludes unassigned rows', !t.includes('운영비') && !t.includes('한마당'), t);
t = say('현황', 'U-kim');
check('status admin only', t.startsWith('현황은 관리자만'), t);
t = say('현황 탄소', 'U-admin2');
check('status keyword filter by 관리자 role', t.includes('탄소중립') && !t.includes('프로젝트'), t);
// 12. 선생님 할일: 본인(담당 없음) + 지연 표시
t = say('할일', 'U-teacher');
check('admin task list legacy + 지연', t.includes('운영비') && t.includes('⚠ 지연 2일') && !t.includes('한마당') && !t.includes('탄소중립'), t);
// 13. 오늘
t = say('오늘', 'U-kim');
check('today shows common events', t.includes('오늘 출장'), t);
// 14. 등록 안 된 사용자 / 비밀값 / 내아이디
t = say('완료 탄소중립', 'U-stranger');
check('stranger blocked', t.startsWith('아직 등록되지 않은') && doneRows().length === 1, t);
t = say('완료 탄소중립', 'U-lee', 'wrong');
check('wrong key', t === '접근할 수 없어요.', t);
t = say('내아이디', 'U-new');
check('my id works for anyone', t.includes('U-new'), t);
// 15. 탭이 없으면 자동 생성
reset();
delete tabs['완료기록']; delete tabs['구성원'];
t = say('할일', 'U-teacher');
check('tabs auto-created, admin still works', tabs['완료기록'] && tabs['구성원'] && t.includes('운영비'), t);
check('created headers', tabs['완료기록'][0].join() === '시각,키,이름,내용' && tabs['구성원'][0].join() === '이름,그룹,챗봇아이디,역할,이메일');
// 16. 담당 열이 없는 예전 시트도 동작
reset();
tabs['일정DB'] = tabs['일정DB'].map(r => r.slice(0, 7));
t = say('완료 운영비', 'U-teacher');
check('works without 담당 column', t.startsWith('✔'), t);
// 17. 열 순서가 바뀌어도 동작
reset();
tabs['일정DB'] = tabs['일정DB'].map(r => [r[3], r[7], r[0], r[1], r[4], r[2], r[5], r[6]]);
t = say('완료 탄소중립', 'U-kim');
check('column order independent', t.startsWith('✔ 완료 처리했어요 (1/3)'), t);
// 18. 응답 길이 제한 (현황이 많아도 900자 이내)
reset();
for (let i = 0; i < 12; i++) tabs['일정DB'].push(['x' + i, off(20 + i), '개인', '긴 이름의 시험 할 일 번호 ' + i + ' ' + '가'.repeat(40), '', '수동', '3학년', '김철수, 이영희, 박민수']);
t = say('현황', 'U-teacher');
check('reply within limit', t.length <= 900, t.length);
// 19. 날짜 칸이 Date 객체여도
reset();
tabs['일정DB'][1][1] = new Date(off(7) + 'T00:00:00+09:00');
t = say('완료 탄소중립', 'U-kim');
check('Date cell', t.startsWith('✔'), t);
check('doGet alive', ctx.doGet().text.includes('켜져'));
console.log(pass + ' passed, ' + fail + ' failed');
reset(); say('완료 탄소중립', 'U-kim');
console.log('--- 샘플 ---'); console.log(say('현황', 'U-teacher').split('\n\n')[0]); console.log(); console.log(say('할일', 'U-kim'));
