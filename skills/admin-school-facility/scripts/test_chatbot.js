// Chatbot.gs 시험 (가짜 시트/서비스). 실행: node scripts/test_chatbot.js  (스킬 폴더에서)
// 시험하는 것: 비밀값, 계정 연결(PIN), 대여·반납·대여취소, 공간 예약·예약취소·빈곳, 날짜·교시 알아듣기.
const fs = require('fs'), crypto = require('crypto');
const code = fs.readFileSync('assets/apps_script/Code.gs', 'utf8') + '\n' + fs.readFileSync('assets/apps_script/Chatbot.gs', 'utf8');
class Sheet { constructor(r) { this.rows = r; this.hidden = false } getLastRow() { return this.rows.length } appendRow(r) { this.rows.push(r.slice()) } hideSheet() { this.hidden = true }
  getRange(r, c, nr = 1, nc = 1) { const s = this; return { getValues: () => Array.from({ length: nr }, (_, i) => Array.from({ length: nc }, (_, j) => { const row = s.rows[r - 1 + i] || []; return row[c - 1 + j] === undefined ? '' : row[c - 1 + j] })),
    setValue: v => { (s.rows[r - 1] = s.rows[r - 1] || [])[c - 1] = v }, setValues: vs => { vs.forEach((vr, i) => vr.forEach((v, j) => { (s.rows[r - 1 + i] = s.rows[r - 1 + i] || [])[c - 1 + j] = v })) }, setNumberFormat() {}, clearContent() { for (let j = 0; j < nc; j++) (s.rows[r - 1] = s.rows[r - 1] || [])[c - 1 + j] = '' } } } }
const RD = Date; const D = (y, m, d, h = 0, mi = 0) => new RD(y, m - 1, d, h, mi);
// 설정: A 공간, B 교시, C 시간, H 신청자, J 대여 가능 분류, K 승인 필요 공간
const set = [['공간', '교시', '시간', '분류', '', '', '', '신청자', '', '대여 가능 분류', '승인 필요 공간']];
const spaces = ['강당', '과학실1(204)', '과학실2(205)', '컴퓨터실'], pers = ['1교시', '2교시', '3교시', '점심', '방과후'], people = ['김교사', '박교사'], cats = ['전자기기', '체육용품'];
for (let i = 0; i < 5; i++) set.push([spaces[i] || '', pers[i] || '', '', '', '', '', '', people[i] || '', '', cats[i] || '', i === 0 ? '강당' : '']);
const items = [['관리번호'], ['B-0001', '빔프로젝터', '전자기기', '', 3, '', 0, '창고', '창고', '', '양호', ''], ['B-0002', '빔프로젝터 스크린', '전자기기', '', 1, '', 0, '창고', '창고', '', '양호', ''],
  ['B-0003', '노트북', '전자기기', '', 2, '', 0, '창고', '창고', '', '수리필요', ''], ['F-0001', '접이식 책상', '가구', '', 10, '', 0, '창고', '창고', '', '양호', '']];
const req = [['신청일', '사용일']]; for (let i = 0; i < 30; i++) req.push(['', '', '', '', '', '', '', '', '', '', '']);
const sheets = { '설정': new Sheet(set), '기물대장': new Sheet(items), '사용신청': new Sheet(req), '배치': new Sheet([['공간']]), '고정시간표': new Sheet([['공간'], ['컴퓨터실', '수', '3교시', '5-1 정보']]) };
let clock = D(2026, 11, 23, 10, 0); // 월요일
global.Date = class extends RD { constructor(...a) { if (a.length === 0) super(clock.getTime()); else super(...a) } static now() { return clock.getTime() } static UTC(...a) { return RD.UTC(...a) } static [Symbol.hasInstance](x) { return x instanceof RD } };
global.SpreadsheetApp = { getActiveSpreadsheet: () => ({ getSpreadsheetTimeZone: () => 'Asia/Seoul', getSheetByName: n => sheets[n] || null, insertSheet: n => sheets[n] = new Sheet([]) }) };
const p2 = n => String(n).padStart(2, '0'); global.Utilities = { formatDate: (d, tz, f) => { const m = { yyyy: d.getFullYear(), MM: p2(d.getMonth() + 1), dd: p2(d.getDate()), H: d.getHours(), m: d.getMinutes() }; return f.replace(/yyyy|MM|dd|H|m/g, k => m[k]); },
  computeDigest: (alg, s) => Array.from(crypto.createHash('sha256').update(s, 'utf8').digest()).map(b => b > 127 ? b - 256 : b), getUuid: () => crypto.randomUUID(), DigestAlgorithm: { SHA_256: 1 }, Charset: { UTF_8: 1 } };
let lockFree = true; global.LockService = { getScriptLock: () => ({ waitLock() {}, tryLock() { return lockFree }, releaseLock() {} }) };
const cacheMap = {}; global.CacheService = { getScriptCache: () => ({ get: k => cacheMap[k] || null, put: (k, v) => { cacheMap[k] = v }, remove: k => { delete cacheMap[k] } }) };
let props = { CHATBOT_SECRET: 'secret-123', ACCESS_CODE: 'acc', ADMIN_CODE: '0000' }; global.PropertiesService = { getScriptProperties: () => ({ getProperty: k => props[k] || null }) };
global.HtmlService = {}; global.ContentService = { MimeType: { JSON: 'json' }, createTextOutput: t => ({ text: t, setMimeType() { return this } }) };
eval(code + ';Object.assign(global,{setPin,myRequests,adminResetPin,doPost,chatHandle_,chatDate_,chatWords_});');

let pass = 0, fail = 0; const ck = (n, c, x) => { c ? (pass++, console.log('  OK ', n)) : (fail++, console.log('  FAIL', n, x === undefined ? '' : JSON.stringify(x))) };
const say = (t, uid = 'U-KIM') => chatHandle_(t, uid);
const post = (t, key, uid = 'U-KIM') => JSON.parse(doPost({ parameter: { key }, postData: { contents: JSON.stringify({ userRequest: { utterance: t, user: { id: uid } } }) } }).text).template.outputs[0].simpleText.text;

console.log('비밀값·연결');
ck('비밀값 틀리면 거절', post('시설', 'wrong') === '접근할 수 없어요.');
ck('비밀값 맞으면 도움말', post('시설', 'secret-123').includes('대여 빔프로젝터'));
ck('연결 전에는 아이디 안내', say('대여 빔프로젝터').includes('U-KIM') && say('대여 빔프로젝터').includes('연결되지'));
setPin('acc', '김교사', '1234'); setPin('acc', '박교사', '5678');
const FAIL = '연결하지 못했어요';
ck('명단에 없는 이름 연결 거절', say('시설등록 홍길동 1234').includes(FAIL));
ck('틀린 PIN 연결 거절(같은 문구)', say('시설등록 김교사 9999').includes(FAIL));
ck('PIN 없는 사람도 같은 문구(명단·PIN 여부가 안 드러남)', say('시설등록 이교사 1234', 'U-X').includes(FAIL));
ck('카톡으로 틀려도 웹앱 PIN 잠금은 안 걸림', (() => { for (let i = 0; i < 5; i++) say('시설등록 김교사 000' + i, 'U-ATTACK'); return myRequests('acc', '김교사', '1234').ok === true; })());
ck('카톡 계정당 등록 시도 제한(5번 틀리면 맞는 PIN도 거절)', say('시설등록 김교사 1234', 'U-ATTACK').includes('너무 많아') && !(sheets['챗봇연결'] && sheets['챗봇연결'].rows.some(x => x[1] === 'U-ATTACK')));
ck('PIN 없이 보내면 형식 안내', say('시설등록 김교사').includes('시설등록 이름 PIN'));
ck('연결 성공(띄어 쓴 이름도 명단 이름으로 저장)', say('시설등록 김 교사 1234').includes('연결했어요') && sheets['챗봇연결'].rows.length === 2 && sheets['챗봇연결'].rows[1][0] === '김교사');
ck('같은 계정 다시 연결하면 덮어씀', say('시설등록 김교사 1234').includes('다시 연결') && sheets['챗봇연결'].rows.length === 2);
say('시설등록 박교사 5678', 'U-PARK');
ck('시도 제한 걸린 계정은 맞는 PIN도 거절', say('시설등록 박교사 5678', 'U-ATTACK').includes('너무 많아'));

console.log('날짜 알아듣기 (오늘 = 2026-11-23 월)');
const t = '2026-11-23';
ck('내일', chatDate_('내일', t) === '2026-11-24'); ck('금요일까지', chatDate_('금요일까지', t) === '2026-11-27'); ck('월(오늘)', chatDate_('월', t) === '2026-11-23');
ck('다음주화요일', chatDate_('다음주화요일', t) === '2026-12-01'); ck('12/3', chatDate_('12/3', t) === '2026-12-03'); ck('1월5일 → 내년', chatDate_('1월5일', t) === '2027-01-05');
ck('날짜 아닌 말', chatDate_('빔프로젝터', t) === '' && chatDate_('13/40', t) === '');
ck('없는 날짜 2/30', chatDate_('2/30', t) === '');
ck('어제(11/22)는 내년으로 넘기지 않음', chatDate_('11/22', t) === '2026-11-22');
ck('띄어 쓴 "다음 주 수요일 까지"를 한 낱말로', chatWords_('빔 다음 주 수요일 까지').join('|') === '빔|다음주수요일까지');
ck('띄어 쓴 "12월 3일"', chatWords_('강당 12월 3일 3교시').join('|') === '강당|12월3일|3교시');

console.log('대여·반납');
ck('검색어가 여러 물품에 맞으면 관리번호로 다시 묻기', say('대여 빔').includes('여러 물품'));
let r = say('대여 B-0001 2개 3일'); ck('관리번호로 대여 2개 3일', r.includes('R0001') && r.includes('11/25'), r);
ck('대여신청 시트에 기록', sheets['대여신청'].rows[1][5] === '김교사' && sheets['대여신청'].rows[1][9] === '승인');
r = say('대여 B-0001 2개', 'U-PARK'); ck('남은 수량 초과 거절', r.includes('1개'), r);
ck('수리필요 물품 거절', say('대여 노트북').includes('수리필요'));
ck('대여 대상 아닌 분류 거절', say('대여 접이식 책상').includes('대여 대상이 아니'));
ck('없는 물품', say('대여 피아노').includes('못 찾았어요'));
ck('이름이 정확히 같으면 바로 그 물품(빔프로젝터 ≠ 스크린)', say('대여 빔프로젝터 1개', 'U-PARK').includes('B-0001') === false && sheets['대여신청'].rows.some(x => x[5] === '박교사' && x[2] === 'B-0001'));
r = say('대여 스크린 내일부터 금요일까지'); const futureId = (r.match(/R\d{4}/) || [''])[0]; ck('미래 대여', futureId && r.includes('11/24') && r.includes('11/27'), r);
ck('반납 여러 개 아님: 시작된 것만 고름 → 바로 반납', say('반납').includes('R0001'));
r = say('반납'); ck('반납할 것 없음', r.includes('없어요'), r);
r = say('반납 ' + futureId, 'U-PARK'); ck('남의 대여 반납 불가', !r.includes('반납했어요'), r);
ck('시작 전 대여 취소', say('대여취소 스크린').includes('취소했어요'));
ck('취소할 것 없음', say('대여취소').includes('없어요'));
r = say('대여 스크린 금요일'); ck('날짜 하나만 말하면 그날 하루', r.includes('11/27(금) 하루'), r); say('대여취소 스크린');
r = say('대여 스크린 다음주 수요일까지'); ck('띄어 쓴 "다음주 수요일까지"', r.includes('~ 12/2(수)'), r); say('반납 스크린');
ck('없는 날짜는 물품 이름으로 읽지 않음', say('대여 스크린 2/30까지').includes('없는 날짜'));
ck('어제 날짜 대여 거절', say('대여 스크린 11/22').includes('지난 날짜'));

console.log('공간 예약');
r = say('예약 과학실1 내일 3교시 실험'); ck('부분 이름으로 예약(과학실1)', r.includes('예약했어요') && r.includes('과학실1(204)'), r);
ck('사용신청 시트에 목적까지 기록', sheets['사용신청'].rows.some(x => x[4] === '과학실1(204)' && x[5] === '김교사' && x[6] === '실험' && x[10] === '확정'));
ck('같은 자리 다른 사람 거절', say('예약 과학실1(204) 내일 3교시', 'U-PARK').includes('이미 신청'));
ck('같은 시간 두 곳 거절', say('예약 강당 내일 3교시').includes('한 곳만'));
ck('"과학실"은 두 곳이라 다시 묻기', say('예약 과학실 내일 2교시').includes('여러 곳'));
r = say('예약 강당 내일 2') ; ck('숫자만 교시 + 승인 필요 공간 ⏳', r.includes('승인 대기') && r.includes('2교시'), r);
ck('교시 빠지면 물어봄', say('예약 강당 내일').includes('몇 교시'));
ck('예약 대상 아닌 곳', say('예약 교무실 내일 1교시').includes('예약을 받는 공간이 아니'));
ck('정규 수업 시간 거절', say('예약 컴퓨터실 수요일 3교시').includes('5-1 정보'));
r = say('예약 컴퓨터실 다음 주 수요일 2교시'); ck('띄어 쓴 다음주 수요일 → 12/2', r.includes('12/2(수)') && r.includes('예약했어요'), r);
r = say('예약 컴퓨터실 11/22 1교시'); ck('어제 날짜 예약 거절(내년으로 안 넘김)', r.includes('지난 날짜'), r);
r = say('예약 컴퓨터실 1/5 1교시'); ck('많이 지난 날짜는 내년, 답에 연도 표시', r.includes('2027년 1/5'), r);
ck('없는 날짜 예약 거절', say('예약 컴퓨터실 2/30 1교시').includes('없는 날짜'));
r = say('빈곳 내일 3교시'); ck('빈곳: 예약된 과학실1 빠짐', r.includes('3곳') && !r.includes('과학실1') && r.includes('강당'), r);
ck('빈곳: 정규 수업 빠짐', !say('빈곳 수요일 3교시').includes('컴퓨터실'));
r = say('내 신청'); ck('내 신청에 예약 4건', r.includes('공간 예약 4건') && r.includes('⏳'), r);
ck('예약취소에 날짜를 쓰면 번호로 안내', say('예약취소 11/25').includes('[번호]'));
ck('없는 번호', say('예약취소 9999').includes('올바르지'));
const row = sheets['사용신청'].rows.findIndex(x => x[4] === '강당') + 1;
ck('남의 예약 취소 거절', say('예약취소 ' + row, 'U-PARK').includes('내 신청이 아니'));
ck('번호로 예약 취소', say('예약취소 ' + row).includes('강당'));
ck('취소한 예약 다시 취소 불가', say('예약취소 ' + row).includes('내 신청이 아니'));

console.log('기타');
lockFree = false; ck('잠금이 안 잡히면 다시 보내라고 안내', say('반납').includes('잠시 뒤')); lockFree = true;
ck('모르는 말은 도움말', say('안녕').includes('시설 챗봇'));
setPin('acc', '박교사', '9999', '5678'); ck('PIN을 바꾸면 카톡 연결이 풀림', say('내 신청', 'U-PARK').includes('연결되지'));
say('시설등록 박교사 9999', 'U-PARK'); adminResetPin('0000', '박교사'); ck('관리자가 PIN 초기화해도 풀림', say('내 신청', 'U-PARK').includes('연결되지'));
sheets['챗봇연결'].rows.push(['박교사', 'U-PARK2', '', '']); ck('관리자가 직접 적은 줄(PIN확인값 없음)은 유효', say('내 신청', 'U-PARK2').includes('박교사 선생님'));
sheets['챗봇연결'].rows[1][0] = '퇴직교사'; ck('명단에서 빠진 이름으로 연결돼 있으면 막힘', say('내 신청').includes('연결되지'));

console.log('\n통과', pass, '/ 실패', fail); process.exit(fail ? 1 : 0);
