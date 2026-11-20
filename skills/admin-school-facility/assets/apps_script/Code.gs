/**
 * 학교 공간·기물 3D 현황 웹앱 (구글 시트에 연결된 Apps Script)
 * 시트 메뉴: 확장 프로그램 > Apps Script 에서 이 코드를 붙여 넣으세요.
 * 시트 이름(설정, 배치, 사용신청, 기물대장)은 관리 시트와 같아야 합니다.
 */

function doGet(e) {
  var html = HtmlService.createHtmlOutputFromFile('Index').getContent();
  var params = JSON.stringify((e && e.parameter) || {}).replace(/</g, '\\u003c');
  html = html.replace('/*__PARAMS__*/{}/*__END__*/', function () { return params; });
  return HtmlService.createHtmlOutput(html)
    .setTitle('학교 공간·기물 현황')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// 접근 코드: 스크립트 속성 ACCESS_CODE 에 값을 넣으면 코드를 아는 사람만 사용할 수 있습니다.
function auth_(code) {
  var p = PropertiesService.getScriptProperties().getProperty('ACCESS_CODE');
  if (p && String(code) !== String(p)) throw new Error('접근 코드가 올바르지 않습니다.');
}

function rows_(sheet, ncols, maxRow) {
  if (!sheet) return [];
  var last = Math.min(sheet.getLastRow(), maxRow || 100000);
  if (last < 2) return [];
  return sheet.getRange(2, 1, last - 1, ncols).getValues();
}

// 설정 시트 A열 = 사용 신청을 받는 공간. 여기에 없는 방(교무실, 교장실, 행정실 등)은 3D에는 보여도 신청할 수 없다.
function bookable_(ss) {
  return rows_(ss.getSheetByName('설정'), 1, 60)
    .map(function (r) { return String(r[0]); })
    .filter(function (s) { return s !== ''; });
}

// 고정시간표 시트 = 매주 반복되는 정규 수업(특별실 사용표): 공간, 요일(월~일), 교시, 내용
function fixed_(ss) {
  return rows_(ss.getSheetByName('고정시간표'), 4, 400)
    .filter(function (r) { return r[0] !== '' && r[1] !== '' && r[2] !== ''; })
    .map(function (r) { return { room: String(r[0]), day: String(r[1]), period: String(r[2]), label: String(r[3]) }; });
}
var DAYS_ = ['월', '화', '수', '목', '금', '토', '일'];
function dayOfDateStr_(s) { var p = String(s).split('-'); return DAYS_[(new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])).getUTCDay() + 6) % 7]; }

// 사용신청 시트 11열(A~K). K열 = 상태(승인대기/확정/반려/취소). 반려·취소된 신청은 없는 것으로 본다.
function bookingRows_(ss) {
  return rows_(ss.getSheetByName('사용신청'), 11, 500).filter(function (r) { return r[10] !== '반려' && r[10] !== '취소'; });
}
// 설정 시트 J열 = 대여 가능 분류, K열 = 관리자 승인이 필요한 공간
function colList_(ss, col, n) {
  var sh = ss.getSheetByName('설정'); if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, col, Math.min(sh.getLastRow() - 1, n || 60), 1).getValues().map(function (r) { return String(r[0]).trim(); }).filter(function (s) { return s !== ''; });
}
function lendableCats_(ss) { return colList_(ss, 10); }
function approvalSpaces_(ss) { return colList_(ss, 11); }

function people_(ss) {
  var sh = ss.getSheetByName('설정');
  if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 8, Math.min(sh.getLastRow() - 1, 200), 1).getValues()
    .map(function (r) { return String(r[0]).trim(); }).filter(function (s) { return s !== ''; });
}

function norm_(s) { return String(s || '').replace(/\s+/g, ''); }

function getData(code, dateStr) {
  auth_(code);
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var tz = ss.getSpreadsheetTimeZone();

  var layout = layout_(ss);

  // 설정 시트 A열 = 사용 신청을 받는 공간
  var bookable = bookable_(ss);

  // 설정 시트 H열 = 신청자(교사) 명단. 비어 있으면 이름을 직접 입력받는다.
  var people = people_(ss);

  var periods = rows_(ss.getSheetByName('설정'), 3, 40)
    .filter(function (r) { return r[1] !== ''; })
    .map(function (r) { return { name: String(r[1]), time: String(r[2]) }; });

  var usage = bookingRows_(ss)
    .filter(function (r) {
      return r[1] instanceof Date && Utilities.formatDate(r[1], tz, 'yyyy-MM-dd') === dateStr && r[3] !== '' && r[4] !== '';
    })
    .map(function (r) { return { period: String(r[3]), space: String(r[4]), who: (r[10] === '승인대기' ? '⏳ ' : '') + String(r[5]), purpose: String(r[6]), pending: r[10] === '승인대기' }; });

  var dayName = dayOfDateStr_(dateStr), taken = {};
  usage.forEach(function (u) { taken[u.space + '|' + u.period] = 1; });
  fixed_(ss).forEach(function (f) {
    if (f.day === dayName && !taken[f.room + '|' + f.period]) usage.push({ period: f.period, space: f.room, who: f.label, purpose: '고정 일정', fixed: true });
  });

  var items = rows_(ss.getSheetByName('기물대장'), 12, 1000)
    .filter(function (r) { return r[0] !== ''; })
    .map(function (r) {
      return { id: String(r[0]), name: String(r[1]), cat: String(r[2]), spec: String(r[3]), qty: Number(r[4]) || 0,
               acq: (r[5] instanceof Date) ? Utilities.formatDate(r[5], tz, 'yyyy-MM-dd') : String(r[5] || ''),
               first: String(r[7]), loc: String(r[8]), mgr: String(r[9]), status: String(r[10]), note: String(r[11]) };
    });

  return { layout: layout, bookable: bookable, approval: approvalSpaces_(ss), lendable: lendableCats_(ss), people: people, periods: periods, usage: usage, items: items };
}

function submitRequest(code, p) {
  auth_(code);
  if (!p || !p.date || !p.period || !p.space || !String(p.who || '').trim()) {
    return { ok: false, msg: '날짜, 교시, 공간, 이름을 모두 입력해 주세요.' };
  }
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var tz = ss.getSpreadsheetTimeZone();
    if (bookable_(ss).indexOf(String(p.space)) < 0) {
      return { ok: false, msg: '"' + p.space + '"은(는) 사용 신청을 받지 않는 공간이에요. (교무실·교장실·행정실 같은 곳은 신청할 수 없어요)' };
    }
    var fx = fixed_(ss).filter(function (f) { return f.room === String(p.space) && f.day === dayOfDateStr_(p.date) && f.period === String(p.period); })[0];
    if (fx) return { ok: false, msg: '그 시간에는 ' + fx.label + ' 일정이 있어요. 다른 시간을 골라 주세요.' };
    var sh = ss.getSheetByName('사용신청');
    var N = 500;
    var vals = sh.getRange(2, 1, N - 1, 11).getValues();
    var people = people_(ss), who = String(p.who).trim();
    if (people.length && people.map(norm_).indexOf(norm_(who)) < 0) {
      return { ok: false, msg: '신청자 명단에 없는 이름입니다. 관리자에게 명단 추가를 요청해 주세요.' };
    }
    var target = -1;
    for (var i = 0; i < vals.length; i++) {
      var r = vals[i], dead = (r[10] === '반려' || r[10] === '취소');
      var sameSlot = !dead && r[1] instanceof Date && Utilities.formatDate(r[1], tz, 'yyyy-MM-dd') === p.date && String(r[3]) === p.period;
      if (sameSlot && String(r[4]) === p.space) return { ok: false, msg: '이미 신청된 시간입니다. (' + r[5] + ')' };
      if (sameSlot && norm_(r[5]) === norm_(who)) {
        return { ok: false, msg: '같은 시간(' + p.period + ')에 이미 ' + r[4] + ' 사용을 신청하셨습니다. 한 시간에는 한 곳만 신청할 수 있어요.' };
      }
      if (target < 0 && r[1] === '' && r[3] === '' && r[4] === '') target = i + 2;
    }
    if (target < 0) return { ok: false, msg: '신청 칸이 가득 찼습니다. 관리자에게 알려 주세요.' };
    var parts = p.date.split('-');
    var d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    sh.getRange(target, 1).setValue(new Date());
    sh.getRange(target, 2).setValue(d);
    sh.getRange(target, 4, 1, 4).setValues([[p.period, p.space, String(p.who).trim(), String(p.purpose || '').trim()]]);
    var needs = approvalSpaces_(ss).indexOf(String(p.space)) >= 0;
    sh.getRange(target, 11).setValue(needs ? '승인대기' : '확정');
    return needs ? { ok: true, pending: true, msg: '관리자 승인 후에 확정돼요. 승인되면 이 시간은 다른 분이 신청할 수 없어요.' } : { ok: true };
  } finally {
    lock.releaseLock();
  }
}

function layout_(ss) {
  return rows_(ss.getSheetByName('배치'), 8, 400)
    .filter(function (r) { return r[0] !== ''; })
    .map(function (r) {
      var f = Number(r[1]) || 1, fe = Number(r[2]) || f;
      return { space: String(r[0]), floor: f, floorEnd: Math.max(f, fe), x: Number(r[3]) || 0, y: Number(r[4]) || 0,
               w: Number(r[5]) || 6, d: Number(r[6]) || 6, h: Number(r[7]) || 0 };
    });
}

// ===================== 학생용: 빈 교실 찾기 · QR 사용 시작 =====================
// 학생 화면 주소: (웹앱 주소)?mode=student  /  교실 QR: (웹앱 주소)?mode=student&room=러닝허브1
// 스크립트 속성 STUDENT_CODE 를 넣으면 주소의 &c=코드 와 맞아야 열립니다(QR에 코드를 함께 넣어 인쇄).
// 학생에게는 선생님 이름·물품 정보를 주지 않고, 학급·별명은 '학생사용' 시트에만 남깁니다.

function studentAuth_(code) {
  var p = PropertiesService.getScriptProperties().getProperty('STUDENT_CODE');
  if (p && String(code) !== String(p)) throw new Error('접근 코드가 올바르지 않습니다.');
}

function hhmm_(min) { return ('0' + Math.floor(min / 60)).slice(-2) + ':' + ('0' + (min % 60)).slice(-2); }
function minOf_(d, tz) { return Number(Utilities.formatDate(d, tz, 'H')) * 60 + Number(Utilities.formatDate(d, tz, 'm')); }
function dayStr_(d, tz) { return Utilities.formatDate(d, tz, 'yyyy-MM-dd'); }

function periodsInfo_(ss) {
  var out = [];
  rows_(ss.getSheetByName('설정'), 3, 40).forEach(function (r) {
    if (r[1] === '') return;
    var m = String(r[2]).match(/(\d{1,2}):(\d{2})\s*[-~\u2013]\s*(\d{1,2}):(\d{2})/);
    out.push({ name: String(r[1]), time: String(r[2]), from: m ? Number(m[1]) * 60 + Number(m[2]) : null, to: m ? Number(m[3]) * 60 + Number(m[4]) : null });
  });
  return out;
}

// 설정 시트 I열 = 학생이 쓸 수 있는 공간(빈 교실)
function openRooms_(ss) {
  var sh = ss.getSheetByName('설정');
  if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 9, Math.min(sh.getLastRow() - 1, 100), 1).getValues()
    .map(function (r) { return String(r[0]).trim(); }).filter(function (s) { return s !== ''; });
}

function sessionSheet_(ss) {
  var sh = ss.getSheetByName('학생사용');
  if (!sh) { sh = ss.insertSheet('학생사용'); sh.appendRow(['시작', '공간', '학급·별명', '활동', '종료예정', '종료(실제)']); }
  return sh;
}

function sessions_(ss, limitRows) {
  var sh = sessionSheet_(ss), last = sh.getLastRow();
  if (last < 2) return [];
  var n = Math.min(last - 1, limitRows || 3000), start = last - n + 1;
  return sh.getRange(start, 1, n, 6).getValues().map(function (r, i) {
    return { row: start + i, start: r[0], room: String(r[1]), label: String(r[2]), activity: String(r[3]), endPlanned: r[4], endActual: r[5] };
  }).filter(function (s) { return s.start instanceof Date; });
}

function isActive_(s, now) { return !s.endActual && s.endPlanned instanceof Date && s.endPlanned.getTime() > now.getTime(); }

function bookingsFor_(ss, tz, day, periods) {
  var pm = {}; periods.forEach(function (p) { pm[p.name] = p; });
  return bookingRows_(ss)
    .filter(function (r) { return r[1] instanceof Date && dayStr_(r[1], tz) === day && r[3] !== '' && r[4] !== ''; })
    .map(function (r) { var p = pm[r[3]] || {}; return { room: String(r[4]), period: String(r[3]), from: p.from, to: p.to }; })
    .concat(fixed_(ss).filter(function (f) { return f.day === dayOfDateStr_(day); }).map(function (f) { var p = pm[f.period] || {}; return { room: f.room, period: f.period, from: p.from, to: p.to, fixed: true }; }))
    .filter(function (b) { return b.from != null && b.to != null; });
}

function getStudentData(code) {
  studentAuth_(code);
  var ss = SpreadsheetApp.getActiveSpreadsheet(), tz = ss.getSpreadsheetTimeZone();
  var now = new Date(), today = dayStr_(now, tz), nowMin = minOf_(now, tz);
  var periods = periodsInfo_(ss), open = openRooms_(ss);
  var bookings = bookingsFor_(ss, tz, today, periods), sess = sessions_(ss, 600), rooms = {};
  open.forEach(function (room) {
    var tb = bookings.filter(function (b) { return b.room === room; }).sort(function (a, b) { return a.from - b.from; });
    var segs = tb.map(function (b) { return { type: 'teacher', period: b.period, from: hhmm_(b.from), to: hhmm_(b.to) }; });
    var act = null;
    sess.forEach(function (s) {
      if (s.room !== room || dayStr_(s.start, tz) !== today) return;
      var endD = s.endActual instanceof Date ? s.endActual : s.endPlanned, on = isActive_(s, now);
      segs.push({ type: 'student', from: hhmm_(minOf_(s.start, tz)), to: hhmm_(minOf_(endD, tz)), activity: s.activity, active: on });
      if (on) act = s;
    });
    var st = { state: 'free', until: '', next: '' };
    var cur = tb.filter(function (b) { return b.from <= nowMin && nowMin < b.to; })[0];
    if (cur) { st.state = 'teacher'; st.until = hhmm_(cur.to); st.period = cur.period; }
    else if (act) { st.state = 'student'; st.until = hhmm_(minOf_(act.endPlanned, tz)); st.activity = act.activity; }
    var nx = tb.filter(function (b) { return b.from > nowMin; })[0];
    if (nx) st.next = hhmm_(nx.from);
    segs.sort(function (a, b) { return a.from < b.from ? -1 : (a.from > b.from ? 1 : 0); });
    st.today = segs; rooms[room] = st;
  });
  return { layout: layout_(ss), open: open, periods: periods.map(function (p) { return { name: p.name, time: p.time }; }), rooms: rooms, now: { date: today, time: hhmm_(nowMin) } };
}

// 요일별 이용 패턴: 이번 주 선생님 신청(월~금) + 최근 4주 학생 활동 횟수
function getRoomWeek(code, room) {
  studentAuth_(code);
  var ss = SpreadsheetApp.getActiveSpreadsheet(), tz = ss.getSpreadsheetTimeZone(), now = new Date();
  var periods = periodsInfo_(ss), names = periods.map(function (p) { return p.name; });
  var dow = Number(Utilities.formatDate(now, tz, 'u')), days = [];
  for (var d = 0; d < 5; d++) days.push(dayStr_(new Date(now.getTime() - (dow - 1 - d) * 86400000), tz));
  var teacher = periods.map(function () { return [0, 0, 0, 0, 0]; }), student = periods.map(function () { return [0, 0, 0, 0, 0]; });
  bookingRows_(ss).forEach(function (r) {
    if (String(r[4]) !== room || !(r[1] instanceof Date)) return;
    var di = days.indexOf(dayStr_(r[1], tz)), pi = names.indexOf(String(r[3]));
    if (di >= 0 && pi >= 0) teacher[pi][di] = 1;
  });
  fixed_(ss).forEach(function (f) {
    if (f.room !== room) return;
    var di = DAYS_.indexOf(f.day), pi = names.indexOf(f.period);
    if (di >= 0 && di < 5 && pi >= 0) teacher[pi][di] = 1;
  });
  var since = now.getTime() - 28 * 86400000;
  sessions_(ss, 3000).forEach(function (s) {
    if (s.room !== room || s.start.getTime() < since) return;
    var di = Number(Utilities.formatDate(s.start, tz, 'u')) - 1;
    if (di < 0 || di > 4) return;
    var m = minOf_(s.start, tz), pi = -1;
    periods.forEach(function (p, i) { if (p.from != null && m >= p.from && m < p.to) pi = i; });
    if (pi < 0) periods.forEach(function (p, i) { if (p.from != null && m >= p.from) pi = i; });
    if (pi >= 0) student[pi][di]++;
  });
  return { periods: periods.map(function (p) { return { name: p.name, time: p.time }; }), teacher: teacher, student: student, weeks: 4 };
}

function startStudentUse(code, p) {
  studentAuth_(code);
  var room = String((p && p.room) || ''), label = String((p && p.label) || '').trim();
  var act = String((p && p.activity) || '').trim().slice(0, 20), minutes = Number(p && p.minutes) || 30;
  if (!room || !label) return { ok: false, msg: '학급·번호(또는 별명)를 입력해 주세요.' };
  if (label.length > 12) return { ok: false, msg: '12글자 이하로 써 주세요. (실명 대신 학급·번호나 별명을 써요)' };
  minutes = Math.max(10, Math.min(90, minutes));
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet(), tz = ss.getSpreadsheetTimeZone();
    var now = new Date(), today = dayStr_(now, tz), nowMin = minOf_(now, tz);
    if (openRooms_(ss).indexOf(room) < 0) return { ok: false, msg: '학생이 사용할 수 있는 공간이 아니에요.' };
    var periods = periodsInfo_(ss);
    var bookings = bookingsFor_(ss, tz, today, periods).filter(function (b) { return b.room === room; });
    var cur = bookings.filter(function (b) { return b.from <= nowMin && nowMin < b.to; })[0];
    if (cur) return { ok: false, msg: '지금은 ' + (cur.fixed ? '수업·프로그램' : '선생님이 신청한') + ' 시간이에요 (' + cur.period + ', ' + hhmm_(cur.to) + '까지).' };
    var lab = norm_(label), sess = sessions_(ss, 600);
    for (var i = 0; i < sess.length; i++) {
      var s = sess[i];
      if (!isActive_(s, now)) continue;
      if (s.room === room) return { ok: false, msg: '이미 다른 모둠이 사용 중이에요 (' + hhmm_(minOf_(s.endPlanned, tz)) + ' 종료 예정).' };
      if (norm_(s.label) === lab) return { ok: false, msg: '이미 ' + s.room + ' 사용 중이에요. 먼저 "다 썼어요"를 눌러 주세요.' };
    }
    var endMin = nowMin + minutes, note = '';
    var nx = bookings.filter(function (b) { return b.from > nowMin; }).sort(function (a, b) { return a.from - b.from; })[0];
    if (nx && nx.from < endMin) { endMin = nx.from; note = (nx.fixed ? '수업·프로그램(' : '선생님 신청(') + nx.period + ') 때문에 ' + hhmm_(endMin) + '까지만 사용할 수 있어요.'; }
    if (endMin - nowMin < 5) return { ok: false, msg: '곧 선생님이 신청한 시간이라 지금은 시작할 수 없어요.' };
    var endD = new Date(now.getTime() + (endMin - nowMin) * 60000);
    var sh = sessionSheet_(ss);
    sh.appendRow([now, room, label, act, endD, '']);
    sh.getRange(sh.getLastRow(), 1, 1, 6).setNumberFormat('yyyy-mm-dd hh:mm');
    return { ok: true, until: hhmm_(endMin), note: note };
  } finally {
    lock.releaseLock();
  }
}

function endStudentUse(code, room, label) {
  studentAuth_(code);
  var lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet(), now = new Date(), lab = norm_(label);
    var sess = sessions_(ss, 600);
    for (var i = sess.length - 1; i >= 0; i--) {
      var s = sess[i];
      if (s.room === String(room) && norm_(s.label) === lab && isActive_(s, now)) {
        var c = ss.getSheetByName('학생사용').getRange(s.row, 6);
        c.setValue(now); c.setNumberFormat('yyyy-mm-dd hh:mm');
        return { ok: true };
      }
    }
    return { ok: false, msg: '사용 중인 기록을 찾지 못했어요.' };
  } finally {
    lock.releaseLock();
  }
}

// 물건 하나의 이동·수리 이력 (기물대장의 관리번호 기준, 최신순 30건)
function getItemHistory(code, id) {
  auth_(code);
  var ss = SpreadsheetApp.getActiveSpreadsheet(), tz = ss.getSpreadsheetTimeZone();
  return rows_(ss.getSheetByName('이동수리이력'), 7, 1000)
    .filter(function (r) { return String(r[1]) === String(id); })
    .map(function (r) { return { date: (r[0] instanceof Date) ? Utilities.formatDate(r[0], tz, 'yyyy-MM-dd') : String(r[0]), kind: String(r[3]), to: String(r[4]), memo: String(r[5]), by: String(r[6]) }; })
    .sort(function (a, b) { return a.date < b.date ? 1 : (a.date > b.date ? -1 : 0); })
    .slice(0, 30);
}

// 교사용: 방 하나의 이번 주(월~금) 시간표 = 정규 수업 + 방과후·돌봄 + 그 주 교사 신청
function getRoomTimetable(code, room, dateStr) {
  auth_(code);
  var ss = SpreadsheetApp.getActiveSpreadsheet(), tz = ss.getSpreadsheetTimeZone();
  var periods = periodsInfo_(ss), names = periods.map(function (p) { return p.name; });
  var q = String(dateStr).split('-'), base = new Date(Date.UTC(+q[0], +q[1] - 1, +q[2])), dow = (base.getUTCDay() + 6) % 7, days = [];
  for (var i = 0; i < 5; i++) {
    var d = new Date(base.getTime() + (i - dow) * 86400000);
    days.push(d.getUTCFullYear() + '-' + ('0' + (d.getUTCMonth() + 1)).slice(-2) + '-' + ('0' + d.getUTCDate()).slice(-2));
  }
  var grid = names.map(function () { return [null, null, null, null, null]; });
  fixed_(ss).forEach(function (f) {
    if (f.room !== room) return;
    var di = DAYS_.indexOf(f.day), pi = names.indexOf(f.period);
    if (di < 0 || di > 4 || pi < 0) return;
    grid[pi][di] = { kind: /^방과후/.test(f.label) ? 'program' : 'regular', text: f.label.replace(/^(정규|방과후)\s*/, '').replace(/^(맞춤형|선택형)\s*/, '') };
  });
  bookingRows_(ss).forEach(function (r) {
    if (String(r[4]) !== room || !(r[1] instanceof Date)) return;
    var di = days.indexOf(dayStr_(r[1], tz)), pi = names.indexOf(String(r[3]));
    if (di >= 0 && pi >= 0) grid[pi][di] = { kind: 'booking', text: String(r[5]) + (r[6] ? ' ' + r[6] : '') };
  });
  return { periods: periods.map(function (p) { return { name: p.name, time: p.time }; }), days: days, grid: grid };
}

// ===================== 교직원 PIN · 기물 대여 · 내 신청 · 관리자 =====================
// 사람 구분: 접근 코드 + 신청자 명단(설정 H열) + 개인 PIN(4~8자리 숫자). PIN은 salt+SHA-256 해시만 '교직원PIN' 시트(숨김)에 저장한다.
// PIN이 필요한 일: 기물 대여 신청·반납·취소, 내 신청 조회, 공간 신청 취소. (공간 신청 자체는 PIN 없이 가능)
// 관리자: 스크립트 속성 ADMIN_CODE 를 설정해야 관리자 기능이 열린다. 시트에서 상태 칸을 직접 고치는 것도 같은 효과.

function sha_(s) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, s, Utilities.Charset.UTF_8)
    .map(function (b) { return ('0' + ((b < 0 ? b + 256 : b)).toString(16)).slice(-2); }).join('');
}
function pinSheet_(ss) {
  var sh = ss.getSheetByName('교직원PIN');
  if (!sh) { sh = ss.insertSheet('교직원PIN'); sh.appendRow(['이름', 'salt', 'hash', '정한 날']); try { sh.hideSheet(); } catch (e) {} }
  return sh;
}
function pinRec_(ss, who) {
  var sh = pinSheet_(ss), last = sh.getLastRow(), n = norm_(who);
  if (last < 2) return null;
  var rows = sh.getRange(2, 1, last - 1, 3).getValues();
  for (var i = 0; i < rows.length; i++) if (norm_(rows[i][0]) === n) return { row: i + 2, salt: String(rows[i][1]), hash: String(rows[i][2]) };
  return null;
}
// 시도 제한: 같은 이름으로 10분에 5번 틀리면 잠깐 막는다
function pinCheck_(ss, who, pin) {
  var cache = CacheService.getScriptCache(), key = 'pinfail:' + norm_(who), fails = Number(cache.get(key) || 0);
  if (fails >= 5) return { ok: false, msg: 'PIN을 여러 번 틀려서 10분 동안 잠겼어요. 잠시 뒤에 다시 해 주세요.' };
  var rec = pinRec_(ss, who);
  if (!rec) return { ok: false, msg: 'PIN이 아직 없어요. 먼저 "내 신청"에서 PIN을 정해 주세요.' };
  if (sha_(rec.salt + ':' + String(pin)) !== rec.hash) { cache.put(key, String(fails + 1), 600); return { ok: false, msg: 'PIN이 맞지 않아요.' }; }
  cache.remove(key);
  return { ok: true };
}
function inPeople_(ss, who) { var pp = people_(ss); return !pp.length || pp.map(norm_).indexOf(norm_(who)) >= 0; }

function hasPin(code, who) { auth_(code); return { has: !!pinRec_(SpreadsheetApp.getActiveSpreadsheet(), who) }; }

function setPin(code, who, pin, oldPin) {
  auth_(code);
  var lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet(); who = String(who || '').trim();
    if (!who) return { ok: false, msg: '이름을 골라 주세요.' };
    if (!inPeople_(ss, who)) return { ok: false, msg: '신청자 명단에 없는 이름이에요. 관리자에게 명단 추가를 요청해 주세요.' };
    if (!/^\d{4,8}$/.test(String(pin))) return { ok: false, msg: 'PIN은 숫자 4~8자리로 정해 주세요.' };
    var rec = pinRec_(ss, who), salt = Utilities.getUuid(), hash = sha_(salt + ':' + String(pin)), sh = pinSheet_(ss);
    if (rec) {
      var chk = pinCheck_(ss, who, oldPin); if (!chk.ok) return { ok: false, msg: chk.msg.replace('PIN이 맞지 않아요.', '기존 PIN이 맞지 않아요. 잊으셨다면 관리자에게 초기화를 요청하세요.') };
      sh.getRange(rec.row, 2, 1, 3).setValues([[salt, hash, new Date()]]);
    } else sh.appendRow([who, salt, hash, new Date()]);
    return { ok: true };
  } finally { lock.releaseLock(); }
}

// ---- 기물 대여 ----
function loanSheet_(ss) {
  var sh = ss.getSheetByName('대여신청');
  if (!sh) { sh = ss.insertSheet('대여신청'); sh.appendRow(['신청번호', '신청일시', '관리번호', '품명', '수량', '신청자', '대여일', '반납예정일', '사용 목적', '상태', '반납일', '비고']); }
  return sh;
}
function ds_(v, tz) { return (v instanceof Date) ? dayStr_(v, tz) : String(v || ''); }
function loanRows_(ss, tz) {
  var sh = loanSheet_(ss), last = sh.getLastRow(); if (last < 2) return [];
  var n = Math.min(last - 1, 3000), start = last - n + 1;
  return sh.getRange(start, 1, n, 12).getValues().map(function (r, i) {
    return { row: start + i, id: String(r[0]), item: String(r[2]), name: String(r[3]), qty: Number(r[4]) || 0, who: String(r[5]), start: ds_(r[6], tz), due: ds_(r[7], tz), purpose: String(r[8]), status: String(r[9]), returned: ds_(r[10], tz), note: String(r[11]) };
  }).filter(function (l) { return l.id !== ''; });
}
function itemOf_(ss, id) {
  var rows = rows_(ss.getSheetByName('기물대장'), 12, 1000);
  for (var i = 0; i < rows.length; i++) if (String(rows[i][0]) === String(id)) return { id: String(rows[i][0]), name: String(rows[i][1]), cat: String(rows[i][2]), qty: Number(rows[i][4]) || 0, status: String(rows[i][10]), loc: String(rows[i][8]) };
  return null;
}
function lendable_(ss, it) {
  if (it.status !== '양호') return { ok: false, why: '상태가 "' + it.status + '"이라 지금은 빌릴 수 없어요.' };
  var cats = lendableCats_(ss);
  if (cats.length && cats.indexOf(it.cat) < 0) return { ok: false, why: '"' + it.cat + '" 분류는 대여 대상이 아니에요.' };
  return { ok: true };
}
function reserved_(loans, itemId, start, due, exceptId) {
  var t = 0;
  loans.forEach(function (l) { if (l.item === itemId && l.id !== exceptId && (l.status === '승인대기' || l.status === '승인') && !(l.due < start || due < l.start)) t += l.qty; });
  return t;
}
function daysBetween_(a, b) { var p = a.split('-'), q = b.split('-'); return Math.round((Date.UTC(+q[0], +q[1] - 1, +q[2]) - Date.UTC(+p[0], +p[1] - 1, +p[2])) / 86400000); }

// 물건 하나의 대여 현황 (교사 화면의 물품 상세에서 사용)
function getItemLoans(code, id) {
  auth_(code);
  var ss = SpreadsheetApp.getActiveSpreadsheet(), tz = ss.getSpreadsheetTimeZone(), today = dayStr_(new Date(), tz), it = itemOf_(ss, id);
  if (!it) return { lendable: false, why: '물품을 찾을 수 없어요.', total: 0, loans: [] };
  var ld = lendable_(ss, it);
  return { lendable: ld.ok, why: ld.why || '', total: it.qty, today: today,
    loans: loanRows_(ss, tz).filter(function (l) { return l.item === it.id && (l.status === '승인대기' || l.status === '승인') && l.due >= today; })
      .map(function (l) { return { id: l.id, who: l.who, qty: l.qty, start: l.start, due: l.due, status: l.status }; }) };
}

// 웹앱(이름+PIN)과 카톡 챗봇(연결된 카톡 계정)이 같은 규칙을 쓰도록 본인 확인과 실제 처리를 나눈다.
// 아래의 ...As_ 함수는 본인 확인이 끝난 뒤 스크립트 잠금을 잡은 상태에서만 부른다.
function requestLoan(code, p) {
  auth_(code);
  p = p || {};
  var lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet(), who = String(p.who || '').trim();
    if (!who) return { ok: false, msg: '이름을 골라 주세요.' };
    if (!inPeople_(ss, who)) return { ok: false, msg: '신청자 명단에 없는 이름이에요.' };
    var chk = pinCheck_(ss, who, p.pin); if (!chk.ok) return chk;
    return requestLoanAs_(ss, who, p);
  } finally { lock.releaseLock(); }
}
function requestLoanAs_(ss, who, p) {
  var tz = ss.getSpreadsheetTimeZone(), today = dayStr_(new Date(), tz);
  var it = itemOf_(ss, p.id); if (!it) return { ok: false, msg: '물품을 찾을 수 없어요.' };
  var ld = lendable_(ss, it); if (!ld.ok) return { ok: false, msg: ld.why };
  var qty = Math.floor(Number(p.qty)), start = String(p.start || ''), due = String(p.due || '');
  if (!(qty >= 1)) return { ok: false, msg: '수량을 1개 이상으로 적어 주세요.' };
  if (!/^\d{4}-\d{2}-\d{2}$/.test(start) || !/^\d{4}-\d{2}-\d{2}$/.test(due)) return { ok: false, msg: '대여일과 반납예정일을 골라 주세요.' };
  if (start < today) return { ok: false, msg: '지난 날짜는 신청할 수 없어요.' };
  if (due < start) return { ok: false, msg: '반납예정일은 대여일 이후여야 해요.' };
  if (daysBetween_(start, due) > 30) return { ok: false, msg: '한 번에 30일까지만 빌릴 수 있어요.' };
  var loans = loanRows_(ss, tz), avail = it.qty - reserved_(loans, it.id, start, due);
  if (qty > avail) return { ok: false, msg: '그 기간에 빌릴 수 있는 수량은 ' + Math.max(0, avail) + '개예요. (전체 ' + it.qty + '개)' };
  var seq = 0; loans.forEach(function (l) { var m = /^R(\d+)$/.exec(l.id); if (m) seq = Math.max(seq, Number(m[1])); });
  var id = 'R' + ('000' + (seq + 1)).slice(-4), sh = loanSheet_(ss), s = start.split('-'), d = due.split('-');
  sh.appendRow([id, new Date(), it.id, it.name, qty, who, new Date(+s[0], +s[1] - 1, +s[2]), new Date(+d[0], +d[1] - 1, +d[2]), String(p.purpose || '').trim().slice(0, 40), '승인', '', '']);
  var r = sh.getLastRow(); sh.getRange(r, 2).setNumberFormat('yyyy-mm-dd hh:mm'); sh.getRange(r, 7, 1, 2).setNumberFormat('yyyy-mm-dd');
  return { ok: true, id: id, status: '승인', left: avail - qty, name: it.name, qty: qty, start: start, due: due };
}

function loanOfMine_(ss, tz, id, who) {
  var l = loanRows_(ss, tz).filter(function (x) { return x.id === String(id); })[0];
  if (!l) return { err: '신청 내역을 찾을 수 없어요.' };
  if (norm_(l.who) !== norm_(who)) return { err: '내 신청이 아니에요.' };
  return { loan: l };
}
function setLoan_(ss, row, status, returned) {
  var sh = loanSheet_(ss); sh.getRange(row, 10).setValue(status);
  if (returned) { sh.getRange(row, 11).setValue(returned); sh.getRange(row, 11).setNumberFormat('yyyy-mm-dd'); }
}
function returnLoan(code, id, who, pin) {
  auth_(code);
  var lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet(), chk = pinCheck_(ss, who, pin); if (!chk.ok) return chk;
    return returnLoanAs_(ss, id, who);
  } finally { lock.releaseLock(); }
}
function returnLoanAs_(ss, id, who) {
  var m = loanOfMine_(ss, ss.getSpreadsheetTimeZone(), id, who); if (m.err) return { ok: false, msg: m.err };
  if (m.loan.status !== '승인') return { ok: false, msg: '지금 상태("' + m.loan.status + '")에서는 반납 처리를 할 수 없어요.' };
  setLoan_(ss, m.loan.row, '반납완료', new Date()); return { ok: true, loan: m.loan };
}
function cancelLoan(code, id, who, pin) {
  auth_(code);
  var lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet(), chk = pinCheck_(ss, who, pin); if (!chk.ok) return chk;
    return cancelLoanAs_(ss, id, who);
  } finally { lock.releaseLock(); }
}
function cancelLoanAs_(ss, id, who) {
  var tz = ss.getSpreadsheetTimeZone(), today = dayStr_(new Date(), tz);
  var m = loanOfMine_(ss, tz, id, who); if (m.err) return { ok: false, msg: m.err };
  var l = m.loan;
  if (!(l.status === '승인대기' || (l.status === '승인' && l.start > today))) return { ok: false, msg: '이미 시작된 대여는 취소할 수 없어요. 반납 처리를 해 주세요.' };
  setLoan_(ss, l.row, '취소'); return { ok: true, loan: l };
}

// 내 신청 내역: 대여(진행 중 + 최근) + 앞으로의 공간 신청
function myRequests(code, who, pin) {
  auth_(code);
  var ss = SpreadsheetApp.getActiveSpreadsheet(), chk = pinCheck_(ss, who, pin);
  if (!chk.ok) return chk;
  return myRequestsAs_(ss, who);
}
function myRequestsAs_(ss, who) {
  var tz = ss.getSpreadsheetTimeZone(), today = dayStr_(new Date(), tz), n = norm_(who);
  var loans = loanRows_(ss, tz).filter(function (l) { return norm_(l.who) === n && (l.status === '승인대기' || l.status === '승인' || (l.status === '반납완료' && l.returned >= dayStr_(new Date(Date.now() - 14 * 86400000), tz))); })
    .map(function (l) { return { id: l.id, name: l.name, qty: l.qty, start: l.start, due: l.due, status: l.status, overdue: l.status === '승인' && l.due < today }; });
  var sh = ss.getSheetByName('사용신청'), spaces = [];
  if (sh && sh.getLastRow() >= 2) {
    rows_(sh, 11, 500).forEach(function (r, i) {
      if (!(r[1] instanceof Date) || norm_(r[5]) !== n || r[10] === '반려' || r[10] === '취소') return;
      var d = dayStr_(r[1], tz); if (d < today) return;
      spaces.push({ row: i + 2, date: d, period: String(r[3]), space: String(r[4]), purpose: String(r[6]), status: r[10] === '승인대기' ? '승인대기' : '확정' });
    });
  }
  return { ok: true, loans: loans, spaces: spaces };
}
function cancelMySpace(code, who, pin, row) {
  auth_(code);
  var lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet(), chk = pinCheck_(ss, who, pin); if (!chk.ok) return chk;
    return cancelMySpaceAs_(ss, who, row);
  } finally { lock.releaseLock(); }
}
function cancelMySpaceAs_(ss, who, row) {
  var tz = ss.getSpreadsheetTimeZone(), today = dayStr_(new Date(), tz);
  row = Number(row);
  if (!(row >= 2)) return { ok: false, msg: '신청 번호가 올바르지 않아요.' };
  var sh = ss.getSheetByName('사용신청'), r = sh.getRange(row, 1, 1, 11).getValues()[0];
  if (!(r[1] instanceof Date) || norm_(r[5]) !== norm_(who) || r[10] === '취소' || r[10] === '반려') return { ok: false, msg: '내 신청이 아니에요.' };
  if (dayStr_(r[1], tz) < today) return { ok: false, msg: '지난 신청은 취소할 수 없어요.' };
  sh.getRange(row, 11).setValue('취소'); return { ok: true, date: dayStr_(r[1], tz), period: String(r[3]), space: String(r[4]) };
}

// ---- 관리자 ----
function adminAuth_(code) {
  var p = PropertiesService.getScriptProperties().getProperty('ADMIN_CODE');
  if (!p) throw new Error('관리자 코드가 설정되지 않았어요. (스크립트 속성 ADMIN_CODE)');
  if (String(code) !== String(p)) throw new Error('관리자 코드가 올바르지 않습니다.');
}
function adminSummary(code) {
  adminAuth_(code);
  var ss = SpreadsheetApp.getActiveSpreadsheet(), tz = ss.getSpreadsheetTimeZone(), today = dayStr_(new Date(), tz), pendingSpace = [];
  var sh = ss.getSheetByName('사용신청');
  if (sh && sh.getLastRow() >= 2) rows_(sh, 11, 500).forEach(function (r, i) {
    if (r[10] === '승인대기' && r[1] instanceof Date) pendingSpace.push({ row: i + 2, date: dayStr_(r[1], tz), period: String(r[3]), space: String(r[4]), who: String(r[5]), purpose: String(r[6]) });
  });
  var loans = loanRows_(ss, tz), brief = function (l) { return { id: l.id, name: l.name, qty: l.qty, who: l.who, start: l.start, due: l.due, status: l.status, purpose: l.purpose }; };
  var out = loans.filter(function (l) { return l.status === '승인'; });
  return { ok: true, today: today, pendingSpace: pendingSpace,
    pendingLoans: loans.filter(function (l) { return l.status === '승인대기'; }).map(brief),
    active: out.filter(function (l) { return l.start <= today; }).map(brief),
    dueToday: out.filter(function (l) { return l.due === today; }).map(brief),
    overdue: out.filter(function (l) { return l.due < today; }).map(brief),
    upcoming: out.filter(function (l) { return l.start > today; }).map(brief) };
}
function adminSetStatus(code, kind, key, status) {
  adminAuth_(code);
  var lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet(), tz = ss.getSpreadsheetTimeZone();
    if (kind === 'space') {
      if (['확정', '반려'].indexOf(status) < 0) return { ok: false, msg: '알 수 없는 처리예요.' };
      ss.getSheetByName('사용신청').getRange(Number(key), 11).setValue(status); return { ok: true };
    }
    if (kind === 'loan') {
      if (['승인', '반려', '반납완료', '취소'].indexOf(status) < 0) return { ok: false, msg: '알 수 없는 처리예요.' };
      var l = loanRows_(ss, tz).filter(function (x) { return x.id === String(key); })[0];
      if (!l) return { ok: false, msg: '신청 내역을 찾을 수 없어요.' };
      setLoan_(ss, l.row, status, status === '반납완료' ? new Date() : null); return { ok: true };
    }
    return { ok: false, msg: '알 수 없는 종류예요.' };
  } finally { lock.releaseLock(); }
}
function adminResetPin(code, who) {
  adminAuth_(code);
  var ss = SpreadsheetApp.getActiveSpreadsheet(), rec = pinRec_(ss, who);
  if (!rec) return { ok: false, msg: '그 이름의 PIN 기록이 없어요.' };
  pinSheet_(ss).getRange(rec.row, 1, 1, 4).clearContent(); return { ok: true };
}
