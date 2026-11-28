const fs = require('fs'), vm = require('vm');
const TZ = 'Asia/Seoul';
const fmtDate = d => new Date(d).toLocaleDateString('sv-SE', { timeZone: TZ });
const today = fmtDate(new Date());
const off = n => fmtDate(new Date(new Date(today + 'T00:00:00+09:00').getTime() + n * 86400000));

let tabs, props, lockCalls, fetchLog = [];
let fetchMock = () => { throw new Error('fetch not mocked'); };
const resp = (code, body) => ({ getResponseCode: () => code, getContentText: () => JSON.stringify(body) });
function mkSheet(name) {
  return {
    name,
    getDataRange: () => ({ getValues: () => tabs[name].map(r => r.slice()) }),
    getRange: (r, c) => ({ setNumberFormat() { return this; }, setValue: v => { while (tabs[name].length < r) tabs[name].push([]); const row = tabs[name][r-1]; while (row.length < c) row.push(''); row[c-1] = v; } }),
    appendRow: row => tabs[name].push(row.map(v => typeof v === 'string' && v[0] === "'" ? v.slice(1) : v)), // 시트처럼 앞의 '는 텍스트 표시로만 쓰고 저장하지 않음
    deleteRow: r => tabs[name].splice(r - 1, 1),
  };
}
const ctx = {
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => props[k], setProperty: (k, v) => { props[k] = v; } }) },
  HtmlService: { createHtmlOutput: h => ({ html: h, setTitle() { return this; }, addMetaTag() { return this; } }) },
  UrlFetchApp: { fetch: (url, opt) => fetchMock(url, opt) },
  ContentService: { MimeType: { JSON: 'json' }, createTextOutput: t => ({ text: t, setMimeType() { return this; } }) },
  LockService: { getScriptLock: () => ({ waitLock: () => { lockCalls++; }, releaseLock: () => {} }) },
  Utilities: { formatDate: (d, tz, f) => /HH/.test(f) ? new Date(d).toLocaleString('sv-SE', { timeZone: tz }).slice(0, 16) : fmtDate(d) },
  SpreadsheetApp: { getActive: () => ({
    getSheetByName: n => tabs[n] ? mkSheet(n) : null,
    insertSheet: n => { tabs[n] = []; return mkSheet(n); },
    deleteSheet: sh => { delete tabs[sh.name]; },
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
t = say('내 아이디', 'U-new');
check('my id with space', t.includes('챗봇 아이디예요') && t.includes('U-new'), t);
t = say('someone@example.com', 'U-new');
check('stranger sees own id', t.startsWith('아직 등록되지 않은') && t.includes('U-new'), t);
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
// 20. 친구에게 보내기 받는 사람 등록
reset();
let pg = ctx.doGet({ parameter: { join: 'weekly' } });
check('join without config', pg.html.includes('준비 중'), pg.html);
tabs['비밀설정'] = [['KAKAO_REST_API_KEY', 'REST1'], ['KAKAO_CLIENT_SECRET', 'CS1'], ['KAKAO_REDIRECT_URI', 'https://x/exec']];
pg = ctx.doGet({ parameter: { join: 'daily' } });
check('setup moved to props and tab deleted', props.KAKAO_REST_API_KEY === 'REST1' && props.KAKAO_CLIENT_SECRET === 'CS1' && !tabs['비밀설정']);
check('join page links kakao', pg.html.includes('kauth.kakao.com/oauth/authorize') && pg.html.includes('client_id=REST1') && pg.html.includes('state=daily') && pg.html.includes('target="_top"'), pg.html);
pg = ctx.doGet();
check('home page shows both join buttons', pg.html && pg.html.includes('href="https://x/exec?join=daily"') && pg.html.includes('href="https://x/exec?join=weekly"') && pg.html.includes('target="_top"') && pg.html.includes('켜져 있어요'), pg.html || pg.text);
check('home page has no secrets', !pg.html.includes('REST1') && !pg.html.includes('CS1'), pg.html);
fetchMock = (url, opt) => { fetchLog.push([url, opt]); return url.includes('/oauth/token') ? resp(200, { access_token: 'AT' }) : resp(200, { id: 12345 }); };
pg = ctx.doGet({ parameter: { code: 'C1', state: 'daily' } });
check('callback registers', pg.html.includes('등록됐어요') && tabs['받는사람'].length === 2 && tabs['받는사람'][1][1] === '매일' && tabs['받는사람'][1][2] === '12345', JSON.stringify(tabs['받는사람']));
check('token request has secret+redirect', fetchLog[0][1].payload.client_secret === 'CS1' && fetchLog[0][1].payload.redirect_uri === 'https://x/exec');
pg = ctx.doGet({ parameter: { code: 'C2', state: 'weekly' } });
check('same person updates, no duplicate', tabs['받는사람'].length === 2 && tabs['받는사람'][1][1] === '주간출장', JSON.stringify(tabs['받는사람']));
check('no token stored', !JSON.stringify(tabs).includes('"AT"'));
fetchMock = () => resp(400, { error_code: 'KOE320' });
pg = ctx.doGet({ parameter: { code: 'bad' } });
check('token error page', pg.html.includes('등록하지 못했어요') && pg.html.includes('KOE320'), pg.html);
pg = ctx.doGet({ parameter: { error: 'access_denied' } });
check('user cancel page', pg.html.includes('취소'), pg.html);
// 22. 할 일 추가 / 추가취소 (관리자만)
reset();
const before = tabs['일정DB'].length;
t = say('추가 내일 학부모 상담 전화', 'U-teacher');
const added = tabs['일정DB'][before];
check('add appends row', tabs['일정DB'].length === before + 1 && added[1] === off(1) && added[2] === '개인' && added[3] === '학부모 상담 전화' && added[5] === '수동' && added[6] === '전체', JSON.stringify(added));
check('add key like python', added[0] === off(1).slice(5, 7) + off(1).slice(8, 10) + '-학부모상담전화', added[0]);
check('add reply', t.startsWith('✅') && t.includes('추가취소'), t);
t = say('추가 내일 학부모 상담 전화', 'U-teacher');
check('add duplicate', t.startsWith('이미 있어요') && tabs['일정DB'].length === before + 1, t);
t = say('할일', 'U-teacher');
check('added shows in 할일', t.includes('학부모 상담 전화'), t);
t = say('추가 2020-01-01 옛날 일', 'U-teacher');
check('add past date rejected', t.startsWith('지난 날짜') && tabs['일정DB'].length === before + 1, t);
t = say('추가 다음주 화요일 출장 보고 완료', 'U-teacher');
check('add wins over 완료 and 출장 category', t.startsWith('✅') && t.includes('[출장]') && doneRows().length === 0, t);
t = say('추가 내일 몰래 추가', 'U-kim');
check('add admin only', t.includes('관리자)만') && !JSON.stringify(tabs['일정DB']).includes('몰래'), t);
t = say('추가취소', 'U-teacher');
check('undo add removes last', t.startsWith('🗑') && !JSON.stringify(tabs['일정DB']).includes('출장 보고 완료'), t);
t = say('추가 취소', 'U-teacher');
check('undo add twice', t.includes('없어요'), t);
check('earlier add kept', JSON.stringify(tabs['일정DB']).includes('학부모 상담 전화'));
// 21. 자세히 보기 페이지
tabs['공유링크'] = [['VIEW_TOKEN', 'tok123'], ['DAILY_TEXT', '📅 오늘\n• [학교] <행사>'], ['WEEKLY_TEXT', '🧳 출장'], ['DAILY_UPDATED', '2026-11-23 07:00'], ['WEEKLY_UPDATED', '2026-11-16 07:00']];
pg = ctx.doGet({ parameter: { view: 'tok123', k: 'daily' } });
check('view daily escaped', pg.html.includes('&lt;행사&gt;') && pg.html.includes('07:00 기준'), pg.html);
pg = ctx.doGet({ parameter: { view: 'tok123', k: 'weekly' } });
check('view weekly own time', pg.html.includes('🧳 출장') && pg.html.includes('11-16 07:00'), pg.html);
pg = ctx.doGet({ parameter: { view: 'wrong', k: 'daily' } });
check('view wrong token blocked', pg.html.includes('볼 수 없는') && !pg.html.includes('행사'), pg.html);
console.log(pass + ' passed, ' + fail + ' failed');
reset(); say('완료 탄소중립', 'U-kim');
console.log('--- 샘플 ---'); console.log(say('현황', 'U-teacher').split('\n\n')[0]); console.log(); console.log(say('할일', 'U-kim'));
