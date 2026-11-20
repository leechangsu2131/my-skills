/**
 * 카카오톡 챗봇으로 기물 대여·반납, 공간 예약을 하는 부분 (Code.gs와 같은 Apps Script 프로젝트에 파일로 추가)
 *
 * 카카오 오픈빌더 스킬 → (Cloudflare 중계기) → 이 웹앱의 doPost.
 * 스크립트 속성:
 *   CHATBOT_SECRET  중계기가 붙여 보내는 비밀값(?key=). 비어 있으면 챗봇을 받지 않는다.
 *   ACCESS_CODE     (Code.gs와 같음) 웹앱 접근 코드. 챗봇 예약도 이 값으로 같은 규칙을 거친다.
 *
 * 본인 확인: '챗봇연결' 탭의 [이름, 챗봇아이디]. 카톡에서 `시설등록 이름 PIN`(웹앱에서 정한 PIN)으로
 * 스스로 연결하거나, 관리자가 아이디를 직접 적는다. 연결된 뒤에는 카톡에서 PIN을 묻지 않는다.
 * 대화 내용은 카카오 서버를 거치므로 학생 이름 같은 개인정보는 목적에 적지 않게 안내한다.
 */

var CHAT_LINK_SHEET_ = '챗봇연결';
var CHAT_MAX_LIST_ = 8;

function doPost(e) {
  try {
    var secret = PropertiesService.getScriptProperties().getProperty('CHATBOT_SECRET');
    var given = (e && e.parameter && e.parameter.key) || '';
    if (!secret || String(given) !== String(secret)) return chatJson_('접근할 수 없어요.');
    var body = JSON.parse((e.postData && e.postData.contents) || '{}');
    var req = body.userRequest || {};
    var uid = String((req.user && req.user.id) || '');
    return chatJson_(chatHandle_(String(req.utterance || ''), uid));
  } catch (err) {
    return chatJson_('처리 중 오류가 났어요: ' + err.message);
  }
}

function chatJson_(text) {
  var out = { version: '2.0', template: { outputs: [{ simpleText: { text: String(text).slice(0, 990) } }] } };
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

var CHAT_HELP_ = [
  '시설 챗봇은 이렇게 말해 주세요.',
  '• 대여 빔프로젝터 (오늘 하루)',
  '• 대여 빔프로젝터 2개 3일 / 대여 B-0001 금요일까지',
  '• 반납 / 반납 빔프로젝터 / 반납 R0003',
  '• 대여취소 R0003 (시작 전만)',
  '• 예약 강당 내일 3교시 학년 행사',
  '• 예약취소 12 (번호는 "내 신청"에 나와요)',
  '• 빈곳 내일 3교시',
  '• 내 신청'
].join('\n');

// 말 → 답(글자). 테스트에서 직접 부른다.
function chatHandle_(utter, uid) {
  var text = String(utter || '').replace(/\s+/g, ' ').trim();
  var flat = text.replace(/\s+/g, '');
  if (!uid) return '카카오 사용자 정보를 받지 못했어요.';
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  if (/^시설(도움말|안내|사용법)?$/.test(flat) || flat === '시설?') return CHAT_HELP_;
  var m = text.match(/^시설\s*등록\s+(.+?)\s+(\d{4,8})$/);
  if (m) return chatLocked_(function () { return chatRegister_(ss, uid, m[1], m[2]); });
  if (/^시설\s*등록/.test(text)) return '이렇게 보내 주세요: 시설등록 이름 PIN\n(PIN은 웹앱 "내 신청"에서 정한 숫자예요. 없으면 웹앱에서 먼저 정하거나 관리자에게 연결을 부탁하세요.)';

  var who = chatWho_(ss, uid);
  if (!who) return '아직 연결되지 않은 카카오 계정이에요.\n• 시설등록 이름 PIN 으로 직접 연결하거나\n• 관리자에게 아래 아이디를 알려 주세요.\n\n' + uid;

  if (/^내(신청|대여|예약)(목록|내역)?$/.test(flat)) return chatMine_(ss, who);
  m = text.match(/^대여\s*취소\s*(.*)$/);
  if (m) return chatLocked_(function () { return chatCancelLoan_(ss, who, m[1]); });
  m = text.match(/^예약\s*취소\s*(.*)$/);
  if (m) return chatLocked_(function () { return chatCancelSpace_(ss, who, m[1]); });
  m = text.match(/^(?:대여|빌려\s*줘|빌릴래)\s*(.*)$/);
  if (m) return chatLocked_(function () { return chatLoan_(ss, who, m[1]); });
  m = text.match(/^반납\s*(.*)$/);
  if (m) return chatLocked_(function () { return chatReturn_(ss, who, m[1]); });
  m = text.match(/^예약\s*(.*)$/);
  if (m) return chatBook_(ss, who, m[1]); // submitRequest가 스스로 잠근다
  m = text.match(/^빈\s*(?:곳|교실|자리|공간)\s*(.*)$/);
  if (m) return chatFree_(ss, m[1]);
  return CHAT_HELP_;
}

// 카카오는 몇 초 안에 답을 받아야 하므로 잠금은 짧게 기다린다.
function chatLocked_(fn) {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(4000)) return '다른 신청을 처리하는 중이에요. 잠시 뒤 다시 보내 주세요.';
  try { return fn(); } finally { lock.releaseLock(); }
}

// ---------- 연결(카톡 계정 ↔ 신청자 이름) ----------
function chatLinkSheet_(ss) {
  var sh = ss.getSheetByName(CHAT_LINK_SHEET_);
  if (!sh) { sh = ss.insertSheet(CHAT_LINK_SHEET_); sh.appendRow(['이름', '챗봇아이디', '연결한 날']); }
  return sh;
}
function chatWho_(ss, uid) {
  var sh = ss.getSheetByName(CHAT_LINK_SHEET_);
  if (!sh || sh.getLastRow() < 2) return '';
  var rows = sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues();
  for (var i = 0; i < rows.length; i++) {
    if (String(rows[i][1]).trim() === uid && String(rows[i][0]).trim()) {
      var name = String(rows[i][0]).trim();
      return inPeople_(ss, name) ? name : '';
    }
  }
  return '';
}
function chatRegister_(ss, uid, name, pin) {
  name = String(name).trim();
  if (!inPeople_(ss, name)) return '신청자 명단에 없는 이름이에요. 관리자에게 명단 추가를 요청해 주세요.';
  var chk = pinCheck_(ss, name, pin);
  if (!chk.ok) return chk.msg;
  var sh = chatLinkSheet_(ss), last = sh.getLastRow();
  var rows = last >= 2 ? sh.getRange(2, 1, last - 1, 2).getValues() : [];
  for (var i = 0; i < rows.length; i++) {
    if (String(rows[i][1]).trim() === uid) { sh.getRange(i + 2, 1, 1, 3).setValues([[name, uid, new Date()]]); return name + ' 선생님으로 다시 연결했어요.\n"시설"이라고 보내면 사용법이 나와요.'; }
  }
  sh.appendRow([name, uid, new Date()]);
  return name + ' 선생님으로 연결했어요. 이제 카톡에서는 PIN 없이 쓸 수 있어요.\n"시설"이라고 보내면 사용법이 나와요.';
}

// ---------- 날짜·교시 알아듣기 ----------
function chatToday_(ss) { return dayStr_(new Date(), ss.getSpreadsheetTimeZone()); }
function chatAddDays_(ds, n) {
  var p = ds.split('-'), d = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2] + n));
  return d.getUTCFullYear() + '-' + ('0' + (d.getUTCMonth() + 1)).slice(-2) + '-' + ('0' + d.getUTCDate()).slice(-2);
}
// 한 낱말이 날짜면 'yyyy-MM-dd', 아니면 ''. 요일은 오늘 포함 가장 가까운 그 요일.
function chatDate_(word, today) {
  var w = String(word).replace(/(까지|부터|에)$/, '');
  var rel = { '오늘': 0, '내일': 1, '모레': 2, '글피': 3 };
  if (rel.hasOwnProperty(w)) return chatAddDays_(today, rel[w]);
  var dm = w.match(/^(?:이번\s*주\s*)?([월화수목금토일])(?:요일)?$/);
  if (dm) {
    var want = DAYS_.indexOf(dm[1]), now = DAYS_.indexOf(dayOfDateStr_(today));
    return chatAddDays_(today, (want - now + 7) % 7);
  }
  dm = w.match(/^다음\s*주\s*([월화수목금토일])(?:요일)?$/);
  if (dm) {
    var mon = chatAddDays_(today, 7 - DAYS_.indexOf(dayOfDateStr_(today)));
    return chatAddDays_(mon, DAYS_.indexOf(dm[1]));
  }
  var y = +today.slice(0, 4), mo, d;
  dm = w.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (dm) { y = +dm[1]; mo = +dm[2]; d = +dm[3]; }
  else if ((dm = w.match(/^(\d{1,2})[\/.](\d{1,2})\.?$/)) || (dm = w.match(/^(\d{1,2})월(\d{1,2})일$/))) { mo = +dm[1]; d = +dm[2]; }
  else return '';
  if (!(mo >= 1 && mo <= 12 && d >= 1 && d <= 31)) return '';
  var s = y + '-' + ('0' + mo).slice(-2) + '-' + ('0' + d).slice(-2);
  if (!dm[0].match(/^\d{4}-/) && s < today) s = (y + 1) + s.slice(4); // 연도 없이 지난 날짜를 말하면 내년
  return s;
}
function chatPeriods_(ss) {
  return rows_(ss.getSheetByName('설정'), 2, 40).map(function (r) { return String(r[1]).trim(); }).filter(function (s) { return s !== ''; });
}
function chatPeriod_(word, periods) {
  var w = norm_(word);
  for (var i = 0; i < periods.length; i++) if (norm_(periods[i]) === w) return periods[i];
  var m = w.match(/^(\d{1,2})(교시)?$/);
  if (m) for (var j = 0; j < periods.length; j++) if (norm_(periods[j]) === m[1] + '교시') return periods[j];
  return '';
}
function chatFmt_(ds) { return Number(ds.slice(5, 7)) + '/' + Number(ds.slice(8, 10)) + '(' + dayOfDateStr_(ds) + ')'; }

// ---------- 물품 찾기 ----------
function chatItems_(ss) {
  return rows_(ss.getSheetByName('기물대장'), 12, 1000).filter(function (r) { return r[0] !== ''; })
    .map(function (r) { return { id: String(r[0]), name: String(r[1]), cat: String(r[2]), qty: Number(r[4]) || 0, status: String(r[10]) }; });
}
// 관리번호가 같으면 그것, 이름이 같으면 그것들, 아니면 이름에 검색어가 들어간 것들
function chatFindItems_(items, q) {
  var n = norm_(q).toLowerCase();
  if (!n) return [];
  var byId = items.filter(function (it) { return norm_(it.id).toLowerCase() === n; });
  if (byId.length) return byId;
  var exact = items.filter(function (it) { return norm_(it.name).toLowerCase() === n; });
  if (exact.length) return exact;
  return items.filter(function (it) { return norm_(it.name).toLowerCase().indexOf(n) >= 0; });
}

// ---------- 대여 ----------
// 예: "빔프로젝터", "빔프로젝터 2개 3일", "B-0001 내일부터 금요일까지"
function chatLoan_(ss, who, rest) {
  var today = chatToday_(ss), qty = 1, start = today, due = '', days = 0, q = [];
  String(rest || '').split(' ').forEach(function (w) {
    if (!w) return;
    var m;
    if ((m = w.match(/^(\d+)개$/))) { qty = +m[1]; return; }
    if ((m = w.match(/^(\d+)일(간|동안)?$/))) { days = +m[1]; return; }
    var d = chatDate_(w, today);
    if (d && /부터$/.test(w)) { start = d; return; }
    if (d) { due = d; return; }
    q.push(w);
  });
  if (!q.length) return '무엇을 빌릴지 말해 주세요. 예) 대여 빔프로젝터';
  if (!due) due = days > 0 ? chatAddDays_(start, days - 1) : start;
  var all = chatItems_(ss), found = chatFindItems_(all, q.join(' '));
  if (!found.length) return '"' + q.join(' ') + '"에 맞는 물품을 못 찾았어요. 이름 일부나 관리번호로 다시 말해 주세요.';
  var ok = found.filter(function (it) { return lendable_(ss, it).ok; });
  if (!ok.length) return found.length === 1 ? found[0].name + ': ' + lendable_(ss, found[0]).why : '찾은 물품이 모두 지금은 대여 대상이 아니에요.\n' + chatItemList_(found);
  if (ok.length > 1) return '여러 물품이 있어요. 관리번호로 다시 말해 주세요. 예) 대여 ' + ok[0].id + '\n' + chatItemList_(ok);
  var r = requestLoanAs_(ss, who, { id: ok[0].id, qty: qty, start: start, due: due, purpose: '카톡 신청' });
  if (!r.ok) return r.msg;
  return '대여했어요 ✔ ' + r.id + '\n' + r.name + ' ' + r.qty + '개 · ' + chatFmt_(r.start) + (r.due !== r.start ? ' ~ ' + chatFmt_(r.due) : ' 하루') +
    '\n다 쓰면 "반납 ' + r.id + '"라고 보내 주세요.';
}
function chatItemList_(items) {
  return items.slice(0, CHAT_MAX_LIST_).map(function (it) { return '• ' + it.id + ' ' + it.name + ' (' + it.status + ')'; }).join('\n') +
    (items.length > CHAT_MAX_LIST_ ? '\n… 외 ' + (items.length - CHAT_MAX_LIST_) + '개' : '');
}

// 내 대여 중에서 고르기: 비우면 하나일 때만, 'R0003'이면 그것, 아니면 물품 이름으로
function chatPickLoan_(ss, who, arg, filter) {
  var mine = myRequestsAs_(ss, who).loans.filter(filter);
  var a = norm_(arg).toLowerCase();
  var pick = !a ? mine : mine.filter(function (l) { return l.id.toLowerCase() === a || norm_(l.name).toLowerCase().indexOf(a) >= 0; });
  return { all: mine, pick: pick };
}
function chatLoanLine_(l) { return '• ' + l.id + ' ' + l.name + ' ' + l.qty + '개 ~' + chatFmt_(l.due) + (l.overdue ? ' ⚠ 반납일 지남' : ''); }

function chatReturn_(ss, who, arg) {
  var today = chatToday_(ss);
  var c = chatPickLoan_(ss, who, arg, function (l) { return l.status === '승인' && l.start <= today; });
  if (!c.all.length) return '지금 빌리고 있는 물품이 없어요.';
  if (!c.pick.length) return '"' + arg + '"에 맞는 대여를 못 찾았어요. 빌리고 있는 물품:\n' + c.all.map(chatLoanLine_).join('\n');
  if (c.pick.length > 1) return '어느 것을 반납할까요? 번호로 말해 주세요. 예) 반납 ' + c.pick[0].id + '\n' + c.pick.map(chatLoanLine_).join('\n');
  var r = returnLoanAs_(ss, c.pick[0].id, who);
  return r.ok ? '반납했어요 ✔ ' + c.pick[0].id + ' ' + c.pick[0].name + ' ' + c.pick[0].qty + '개\n제자리에 두셨는지 한 번 확인해 주세요.' : r.msg;
}

function chatCancelLoan_(ss, who, arg) {
  var today = chatToday_(ss);
  var c = chatPickLoan_(ss, who, arg, function (l) { return l.status === '승인대기' || (l.status === '승인' && l.start > today); });
  if (!c.all.length) return '취소할 수 있는 대여가 없어요. (이미 시작된 대여는 "반납"으로 처리해 주세요.)';
  if (!c.pick.length) return '"' + arg + '"에 맞는 대여를 못 찾았어요. 취소할 수 있는 대여:\n' + c.all.map(chatLoanLine_).join('\n');
  if (c.pick.length > 1) return '어느 것을 취소할까요? 예) 대여취소 ' + c.pick[0].id + '\n' + c.pick.map(chatLoanLine_).join('\n');
  var r = cancelLoanAs_(ss, c.pick[0].id, who);
  return r.ok ? '대여를 취소했어요. ' + c.pick[0].id + ' ' + c.pick[0].name : r.msg;
}

// ---------- 공간 예약 ----------
// 예: "강당 내일 3교시 학년 행사" — 날짜를 안 말하면 오늘
function chatBook_(ss, who, rest) {
  var today = chatToday_(ss), periods = chatPeriods_(ss), date = '', period = '', words = [];
  String(rest || '').split(' ').forEach(function (w) {
    if (!w) return;
    var d = !date && chatDate_(w, today);
    if (d) { date = d; return; }
    var p = !period && chatPeriod_(w, periods);
    if (p) { period = p; return; }
    words.push(w);
  });
  if (!date) date = today;
  if (!period) return '몇 교시인지 말해 주세요. 예) 예약 강당 내일 3교시\n교시: ' + periods.join(', ');
  if (date < today) return '지난 날짜는 예약할 수 없어요.';
  var sp = chatSpace_(bookable_(ss), words);
  if (sp.err) return sp.err;
  var res = submitRequest(PropertiesService.getScriptProperties().getProperty('ACCESS_CODE') || '',
    { date: date, period: period, space: sp.space, who: who, purpose: sp.purpose || '카톡 신청' });
  if (!res.ok) return res.msg;
  return (res.pending ? '예약 신청했어요 ⏳ (관리자 승인 대기)\n' : '예약했어요 ✔\n') + sp.space + ' · ' + chatFmt_(date) + ' ' + period +
    (res.pending ? '\n승인 전까지 이 시간은 다른 분이 신청할 수 없어요.' : '');
}
// 남은 낱말에서 공간 이름 찾기. 가장 길게 맞는 이름을 고르고 나머지는 목적으로 쓴다.
function chatSpace_(spaces, words) {
  if (!words.length) return { err: '어느 공간인지 말해 주세요. 예) 예약 강당 내일 3교시' };
  for (var k = words.length; k >= 1; k--) {
    var head = norm_(words.slice(0, k).join(''));
    var hit = spaces.filter(function (s) { return norm_(s) === head; });
    if (hit.length === 1) return { space: hit[0], purpose: words.slice(k).join(' ') };
  }
  var first = norm_(words[0]);
  var part = spaces.filter(function (s) { return norm_(s).indexOf(first) >= 0; });
  if (part.length === 1) return { space: part[0], purpose: words.slice(1).join(' ') };
  if (part.length > 1) return { err: '"' + words[0] + '"에 맞는 공간이 여러 곳이에요. 정확한 이름으로 말해 주세요.\n' + part.slice(0, CHAT_MAX_LIST_).join(', ') };
  return { err: '"' + words[0] + '"은(는) 예약을 받는 공간이 아니에요.\n예약할 수 있는 곳: ' + spaces.slice(0, 20).join(', ') };
}

function chatCancelSpace_(ss, who, arg) {
  var mine = myRequestsAs_(ss, who).spaces;
  var n = String(arg || '').replace(/[^\d]/g, '');
  if (!n) {
    if (mine.length === 1) n = String(mine[0].row);
    else if (!mine.length) return '앞으로의 공간 예약이 없어요.';
    else return '어느 예약을 취소할까요? 번호로 말해 주세요. 예) 예약취소 ' + mine[0].row + '\n' + mine.map(chatSpaceLine_).join('\n');
  }
  var r = cancelMySpaceAs_(ss, who, n);
  return r.ok ? '예약을 취소했어요. ' + r.space + ' · ' + chatFmt_(r.date) + ' ' + r.period : r.msg;
}
function chatSpaceLine_(s) { return '• [' + s.row + '] ' + chatFmt_(s.date) + ' ' + s.period + ' ' + s.space + (s.status === '승인대기' ? ' ⏳승인대기' : ''); }

// ---------- 조회 ----------
function chatMine_(ss, who) {
  var my = myRequestsAs_(ss, who), out = [];
  var active = my.loans.filter(function (l) { return l.status === '승인' || l.status === '승인대기'; });
  out.push('📦 대여 ' + (active.length ? active.length + '건' : '없음'));
  active.slice(0, CHAT_MAX_LIST_).forEach(function (l) { out.push(chatLoanLine_(l)); });
  out.push('', '🏫 공간 예약 ' + (my.spaces.length ? my.spaces.length + '건' : '없음'));
  my.spaces.slice(0, CHAT_MAX_LIST_).forEach(function (s) { out.push(chatSpaceLine_(s)); });
  if (my.spaces.length) out.push('', '취소: 예약취소 [번호]');
  return who + ' 선생님의 신청\n\n' + out.join('\n');
}

// 그 날·교시에 비어 있는 예약 공간 (정규 수업·신청·승인대기 모두 제외)
function chatFree_(ss, rest) {
  var today = chatToday_(ss), periods = chatPeriods_(ss), date = '', period = '';
  String(rest || '').split(' ').forEach(function (w) {
    if (!w) return;
    var d = !date && chatDate_(w, today); if (d) { date = d; return; }
    var p = !period && chatPeriod_(w, periods); if (p) period = p;
  });
  if (!date) date = today;
  if (!period) return '몇 교시인지 말해 주세요. 예) 빈곳 내일 3교시\n교시: ' + periods.join(', ');
  var tz = ss.getSpreadsheetTimeZone(), day = dayOfDateStr_(date), busy = {};
  bookingRows_(ss).forEach(function (r) {
    if (r[1] instanceof Date && dayStr_(r[1], tz) === date && String(r[3]) === period) busy[String(r[4])] = 1;
  });
  fixed_(ss).forEach(function (f) { if (f.day === day && f.period === period) busy[f.room] = 1; });
  var free = bookable_(ss).filter(function (s) { return !busy[s]; });
  return chatFmt_(date) + ' ' + period + ' 빈 곳 ' + free.length + '곳\n' + (free.length ? free.join(', ') : '모두 사용 중이에요.') +
    (free.length ? '\n\n예약: 예약 ' + free[0] + ' ' + (date === today ? '오늘' : chatFmt_(date).replace(/\(.\)$/, '')) + ' ' + period : '');
}
