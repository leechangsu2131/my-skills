/**
 * 카카오톡 챗봇(카카오 i 오픈빌더 스킬 서버) v2 — 일정DB 담당자별 완료 기록
 *
 * 설치: 일정DB 구글 시트 > 확장 프로그램 > Apps Script 에 이 코드를 붙여 넣고 '웹 앱'으로 배포한다.
 * (자세한 순서는 kakao_chatbot_setup.md)
 *
 * 시트 구조
 *  - 일정DB  : 기존 열 + '담당' 열. 담당에 이름(쉼표로 여러 명)·그룹 이름·'전체'를 적으면 그 사람들의 할 일이 된다.
 *              담당이 비어 있으면 공유 일정(행사 등)이거나 선생님 본인의 할 일(상태 칸에 ✔)이다.
 *  - 구성원  : 이름 | 그룹 | 챗봇아이디 | 역할(관리자/일반) | 이메일   (사람 추가는 한 줄)
 *  - 완료기록: 시각 | 키 | 이름 | 내용   (누가 무엇을 끝냈는지 한 줄씩 쌓임. 없으면 자동으로 만든다)
 *
 * 챗봇에게 보내는 말
 *   완료 탄소중립 / 탄소중립 완료 / 나 완료했어(남은 할 일이 하나일 때)
 *   되돌리기 탄소중립
 *   할일 (내 할일)      → 내가 해야 할 남은 일
 *   오늘               → 오늘 일정
 *   현황 [키워드]       → (관리자) 담당 지정된 일정의 완료/미완료 현황
 *   완료 탄소중립 이영희 → (관리자) 다른 사람 몫을 대신 처리   /   되돌리기 탄소중립 이영희
 *   내아이디            → 처음 한 번, 내 챗봇 아이디 확인(구성원 탭에 넣기)
 */
const SHEET_NAME = '일정DB';
const MEMBERS_SHEET = '구성원';
const DONE_SHEET = '완료기록';
const MEMBER_HEAD = ['이름', '그룹', '챗봇아이디', '역할', '이메일'];
const DONE_HEAD = ['시각', '키', '이름', '내용'];
const DONE_MARK = '✔';
const TASK_CATEGORY = '개인';
const MAX_LIST = 6;
const TZ = 'Asia/Seoul';

function doPost(e) {
  try {
    const props = PropertiesService.getScriptProperties();
    const secret = props.getProperty('SECRET');
    const given = (e && e.parameter && e.parameter.key) || '';
    if (!secret || given !== secret) return json_('접근할 수 없어요.');
    const body = JSON.parse(e.postData.contents);
    const req = body.userRequest || {};
    const utter = String(req.utterance || '').trim();
    const uid = String((req.user && req.user.id) || '');
    const lock = LockService.getScriptLock(); // 두 사람이 동시에 완료해도 기록이 꼬이지 않게
    lock.waitLock(3000);
    try {
      return json_(handle_(utter, uid, props));
    } finally {
      lock.releaseLock();
    }
  } catch (err) {
    return json_('처리 중 오류가 났어요: ' + err.message);
  }
}

// 브라우저로 주소를 열어 봤을 때(GET) 살아 있는지만 알려 준다.
function doGet() {
  return ContentService.createTextOutput('일정DB 챗봇 서버가 켜져 있어요.');
}

function handle_(utter, uid, props) {
  const text = utter.replace(/\s+/g, ' ').trim();
  // '내 아이디', '아이디', 'id'처럼 띄어쓰기·표현이 달라도 알아듣는다.
  if (/^(?:내\s*)?(?:챗봇\s*)?(?:아이디|id)(?:\s*(?:알려\s*줘|확인))?[?!.]*$/i.test(text)) {
    return '선생님의 챗봇 아이디예요:\n' + uid + '\n선생님께 전달하면 구성원 탭에 등록해 줘요.';
  }
  const ctx = context_(props, uid);
  if (!ctx.me && !ctx.isAdmin) {
    // 무엇을 보냈든 아이디를 함께 알려 준다(이메일·이름을 보내는 경우가 많다).
    return '아직 등록되지 않은 사용자예요.\n아래 아이디를 선생님께 알려 주세요.\n\n' + uid;
  }
  let m = text.match(/^(?:되돌리기|취소)\s+(.+)$/);
  if (m) return undo_(ctx, m[1]);
  m = text.match(/^(?:완료|끝)\s+(.+)$/) || text.match(/^(.+?)\s*(?:완료했어|완료|끝났어|했어)$/);
  if (m) return complete_(ctx, /^(나|저|내가|다|전부|모두)$/.test(m[1]) ? '' : m[1]);
  if (/^(완료|끝|완료했어|다\s*했어|끝났어)$/.test(text)) return complete_(ctx, '');
  m = text.match(/^현황(?:\s+(.+))?$/);
  if (m) return ctx.isAdmin ? status_(ctx, m[1] || '') : '현황은 관리자만 볼 수 있어요. "할일"로 내 할 일을 확인하세요.';
  if (/^(?:내\s*)?할\s*일$/.test(text)) return listMine_(ctx);
  if (text === '오늘') return listToday_(ctx);
  return ctx.isAdmin
    ? '이렇게 말해 주세요:\n• 완료 탄소중립\n• 되돌리기 탄소중립\n• 할일 / 오늘\n• 현황\n• 완료 탄소중립 이영희 (대신 처리)'
    : '이렇게 말해 주세요:\n• 완료 탄소중립\n• 되돌리기 탄소중립\n• 할일 / 오늘';
}

// ---------- 사용자·담당자 ----------
function context_(props, uid) {
  const members = readMembers_();
  const me = members.filter(function (m) { return m.uid && m.uid === uid; })[0] || null;
  const adminIds = String(props.getProperty('ALLOWED_IDS') || '').split(',').map(trim_).filter(Boolean);
  const isAdmin = adminIds.indexOf(uid) >= 0 || (!!me && me.role === '관리자');
  return { members: members, me: me, isAdmin: isAdmin };
}

// '담당' 칸 → 사람들. 이름, 그룹 이름, '전체'를 쉼표로 섞어 쓸 수 있다.
function resolveAssignees_(damdang, members) {
  const names = [];
  const unknown = [];
  String(damdang || '').split(/[,，、]/).map(trim_).filter(Boolean).forEach(function (tok) {
    let found = [];
    if (tok === '전체') found = members;
    else {
      found = members.filter(function (m) { return m.name === tok; });
      if (!found.length) found = members.filter(function (m) { return m.groups.indexOf(tok) >= 0; });
    }
    if (!found.length) unknown.push(tok);
    found.forEach(function (m) { if (names.indexOf(m.name) < 0) names.push(m.name); });
  });
  return { names: names, unknown: unknown };
}

// ---------- 완료 / 되돌리기 ----------
// 관리자는 말 끝에 이름을 붙여 다른 사람 몫을 처리한다.
function splitTarget_(ctx, arg) {
  const parts = trim_(arg).split(' ').filter(Boolean);
  let named = null;
  if (parts.length) {
    const last = parts[parts.length - 1];
    named = ctx.members.filter(function (m) { return m.name === last; })[0] || null;
    if (named) parts.pop();
  }
  return { kw: parts.join(' '), named: named };
}

function complete_(ctx, arg) {
  const sp = splitTarget_(ctx, arg);
  if (sp.named && !ctx.isAdmin && !(ctx.me && sp.named.name === ctx.me.name)) {
    return '다른 사람 몫은 관리자만 처리할 수 있어요.';
  }
  const target = sp.named || ctx.me;
  const s = readSheet_(ctx.members);
  const done = readDone_();
  const k = norm_(sp.kw);
  const match = function (r) { return !k || norm_(r.text).indexOf(k) >= 0; };
  const mine = target
    ? s.rows.filter(function (r) {
        return r.status !== DONE_MARK && r.assignees.indexOf(target.name) >= 0 && !isDone_(done, r.key, target.name) && match(r);
      })
    : [];
  // 담당이 비어 있는 선생님 본인의 할 일(상태 칸 방식)은 관리자만, 이름을 지정하지 않았을 때
  const legacy = ctx.isAdmin && !sp.named
    ? s.rows.filter(function (r) { return !r.damdang && r.status === '' && match(r); })
    : [];
  const cands = mine.concat(legacy);
  if (!cands.length) {
    return '"' + (sp.kw || '남은 일') + '"에 해당하는 남은 일정을 못 찾았어요.' + (target || ctx.isAdmin ? '\n"할일"로 남은 일정을 확인해 보세요.' : '');
  }
  if (cands.length > 1) return ambiguous_(cands);
  const h = cands[0];
  if (!h.damdang) {
    s.sheet.getRange(h.row, s.idx.status + 1).setValue(DONE_MARK);
    return '✔ 완료 처리했어요\n' + line_(h);
  }
  appendDone_(h.key, target.name, h.text);
  const done2 = readDone_();
  const n = h.assignees.filter(function (name) { return isDone_(done2, h.key, name); }).length;
  const total = h.assignees.length;
  let reply = '✔ 완료 처리했어요 (' + n + '/' + total + ')\n' + line_(h);
  if (target && (!ctx.me || target.name !== ctx.me.name)) reply += '\n(' + target.name + ' 님 몫)';
  if (n >= total) {
    s.sheet.getRange(h.row, s.idx.status + 1).setValue(DONE_MARK);
    reply += '\n🎉 담당자 모두 완료했어요';
  }
  return reply;
}

function undo_(ctx, arg) {
  const sp = splitTarget_(ctx, arg);
  if (sp.named && !ctx.isAdmin && !(ctx.me && sp.named.name === ctx.me.name)) {
    return '다른 사람 몫은 관리자만 되돌릴 수 있어요.';
  }
  const target = sp.named || ctx.me;
  const s = readSheet_(ctx.members);
  const done = readDone_();
  const k = norm_(sp.kw);
  if (!k) return '어떤 일정인지 말해 주세요. 예: 되돌리기 탄소중립';
  const match = function (r) { return norm_(r.text).indexOf(k) >= 0; };
  const mine = target
    ? s.rows.filter(function (r) { return r.assignees.indexOf(target.name) >= 0 && isDone_(done, r.key, target.name) && match(r); })
    : [];
  const legacy = ctx.isAdmin && !sp.named
    ? s.rows.filter(function (r) { return !r.damdang && r.status === DONE_MARK && match(r); })
    : [];
  const cands = mine.concat(legacy);
  if (!cands.length) return '"' + sp.kw + '"에 해당하는 완료한 일정을 못 찾았어요.';
  if (cands.length > 1) return ambiguous_(cands);
  const h = cands[0];
  if (!h.damdang) {
    s.sheet.getRange(h.row, s.idx.status + 1).setValue('');
    return '↩ 되돌렸어요\n' + line_(h);
  }
  deleteDone_(h.key, target.name);
  if (h.status === DONE_MARK) s.sheet.getRange(h.row, s.idx.status + 1).setValue('');
  return '↩ 되돌렸어요\n' + line_(h) + (ctx.me && target.name === ctx.me.name ? '' : '\n(' + target.name + ' 님 몫)');
}

// ---------- 조회 ----------
function listMine_(ctx) {
  const s = readSheet_(ctx.members);
  const done = readDone_();
  const today = todayStr_();
  const mine = ctx.me
    ? s.rows.filter(function (r) {
        return r.status !== DONE_MARK && r.assignees.indexOf(ctx.me.name) >= 0 && !isDone_(done, r.key, ctx.me.name);
      })
    : [];
  const legacy = ctx.isAdmin
    ? s.rows.filter(function (r) { return !r.damdang && r.cat === TASK_CATEGORY && r.status === ''; })
    : [];
  const tasks = mine.concat(legacy).sort(byDate_);
  if (!tasks.length) return '남은 할 일이 없어요 🎉';
  const shown = tasks.slice(0, MAX_LIST + 2);
  return '📌 남은 할 일\n' + shown.map(function (r) {
    const d = dayDiff_(today, r.date);
    const tag = d < 0 ? '⚠ 지연 ' + (-d) + '일' : d === 0 ? '오늘' : 'D-' + d;
    return '• ' + md_(r.date) + ' (' + tag + ') ' + r.text;
  }).join('\n') + (tasks.length > shown.length ? '\n… 외 ' + (tasks.length - shown.length) + '건' : '');
}

function listToday_(ctx) {
  const s = readSheet_(ctx.members);
  const done = readDone_();
  const today = todayStr_();
  const items = s.rows.filter(function (r) {
    if (r.date !== today || r.status !== '') return false;
    if (ctx.isAdmin || !r.damdang) return true;
    return !!ctx.me && r.assignees.indexOf(ctx.me.name) >= 0 && !isDone_(done, r.key, ctx.me.name);
  });
  if (!items.length) return '오늘 등록된 일정이 없어요.';
  return '📅 오늘\n' + items.map(function (r) { return '• [' + r.cat + '] ' + r.text; }).join('\n');
}

// 관리자용: 담당이 지정된 일정의 누가 했고 누가 안 했는지
function status_(ctx, kw) {
  const s = readSheet_(ctx.members);
  const done = readDone_();
  const k = norm_(kw);
  const rows = s.rows
    .filter(function (r) { return r.damdang && r.status !== DONE_MARK && (!k || norm_(r.text).indexOf(k) >= 0); })
    .sort(byDate_);
  if (!rows.length) return '진행 중인 담당 지정 일정이 없어요.';
  const shown = rows.slice(0, 5);
  const out = shown.map(function (r) {
    if (!r.assignees.length) return '📊 ' + md_(r.date) + ' ' + r.text + '\n⚠ 담당 "' + r.unknown.join(', ') + '"을(를) 구성원 탭에서 못 찾았어요';
    const ok = r.assignees.filter(function (n) { return isDone_(done, r.key, n); });
    const no = r.assignees.filter(function (n) { return !isDone_(done, r.key, n); });
    return '📊 ' + md_(r.date) + ' ' + r.text + '  ' + ok.length + '/' + r.assignees.length +
      (ok.length ? '\n✔ ' + ok.join(', ') : '') + (no.length ? '\n⏳ ' + no.join(', ') : '') +
      (r.unknown.length ? '\n⚠ 못 찾은 담당: ' + r.unknown.join(', ') : '');
  });
  return out.join('\n\n') + (rows.length > shown.length ? '\n\n… 외 ' + (rows.length - shown.length) + '건' : '');
}

function ambiguous_(cands) {
  return '여러 개예요. 더 구체적으로 말해 주세요:\n' + cands.slice(0, MAX_LIST).map(line_).join('\n') +
    (cands.length > MAX_LIST ? '\n… 외 ' + (cands.length - MAX_LIST) + '건' : '');
}

// ---------- 시트 읽기·쓰기(열 이름으로 찾으므로 열 순서가 바뀌어도 된다) ----------
function sheet_(name, head) {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    sh.appendRow(head);
  }
  return sh;
}

function headIndex_(head) {
  return function (name, required) {
    const i = head.indexOf(name);
    if (i < 0 && required) throw new Error('"' + name + '" 열이 없어요');
    return i;
  };
}

function readMembers_() {
  const values = sheet_(MEMBERS_SHEET, MEMBER_HEAD).getDataRange().getValues();
  const col = headIndex_(values[0].map(String));
  const iName = col('이름', true), iGroup = col('그룹'), iUid = col('챗봇아이디'), iRole = col('역할'), iMail = col('이메일');
  const get = function (v, i) { return i < 0 ? '' : trim_(v[i]); };
  const out = [];
  for (let r = 1; r < values.length; r++) {
    const v = values[r];
    const name = get(v, iName);
    if (!name) continue;
    out.push({
      name: name,
      groups: get(v, iGroup).split(/[,，、]/).map(trim_).filter(Boolean),
      uid: get(v, iUid),
      role: get(v, iRole),
      email: get(v, iMail),
    });
  }
  return out;
}

function readDone_() {
  const values = sheet_(DONE_SHEET, DONE_HEAD).getDataRange().getValues();
  const col = headIndex_(values[0].map(String));
  const iKey = col('키', true), iName = col('이름', true);
  const out = [];
  for (let r = 1; r < values.length; r++) {
    if (trim_(values[r][iKey])) out.push({ row: r + 1, key: trim_(values[r][iKey]), name: trim_(values[r][iName]) });
  }
  return out;
}

function isDone_(done, key, name) {
  return done.some(function (d) { return d.key === key && d.name === name; });
}

function appendDone_(key, name, text) {
  const sh = sheet_(DONE_SHEET, DONE_HEAD);
  const col = headIndex_(sh.getDataRange().getValues()[0].map(String));
  const row = [];
  row[col('시각', true)] = Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd HH:mm');
  row[col('키', true)] = key;
  row[col('이름', true)] = name;
  if (col('내용') >= 0) row[col('내용')] = text;
  const n = Math.max.apply(null, [col('시각'), col('키'), col('이름'), col('내용')]) + 1;
  const full = [];
  for (let i = 0; i < n; i++) full.push(row[i] === undefined ? '' : row[i]);
  sh.appendRow(full);
}

function deleteDone_(key, name) {
  const sh = sheet_(DONE_SHEET, DONE_HEAD);
  readDone_()
    .filter(function (d) { return d.key === key && d.name === name; })
    .sort(function (a, b) { return b.row - a.row; })
    .forEach(function (d) { sh.deleteRow(d.row); });
}

function readSheet_(members) {
  const sheet = SpreadsheetApp.getActive().getSheetByName(SHEET_NAME);
  if (!sheet) throw new Error('"' + SHEET_NAME + '" 탭이 없어요');
  const values = sheet.getDataRange().getValues();
  const col = headIndex_(values[0].map(String));
  const idx = { key: col('키', true), date: col('날짜', true), cat: col('구분', true), text: col('내용', true), status: col('상태', true), damdang: col('담당') };
  const rows = [];
  for (let r = 1; r < values.length; r++) {
    const v = values[r];
    if (!trim_(v[idx.text])) continue;
    const damdang = idx.damdang < 0 ? '' : trim_(v[idx.damdang]);
    const who = resolveAssignees_(damdang, members || []);
    rows.push({
      row: r + 1,
      key: trim_(v[idx.key]),
      date: fmtDate_(v[idx.date]),
      cat: trim_(v[idx.cat]),
      text: trim_(v[idx.text]),
      status: trim_(v[idx.status]),
      damdang: damdang,
      assignees: who.names,
      unknown: who.unknown,
    });
  }
  return { sheet: sheet, idx: idx, rows: rows };
}

// ---------- 도우미 ----------
function fmtDate_(v) {
  if (Object.prototype.toString.call(v) === '[object Date]') return Utilities.formatDate(v, TZ, 'yyyy-MM-dd');
  return trim_(v).slice(0, 10);
}
function todayStr_() { return Utilities.formatDate(new Date(), TZ, 'yyyy-MM-dd'); }
function dayDiff_(from, to) {
  return Math.round((new Date(to + 'T00:00:00+09:00') - new Date(from + 'T00:00:00+09:00')) / 86400000);
}
function trim_(s) { return String(s === undefined || s === null ? '' : s).trim(); }
function norm_(s) { return String(s).replace(/\s+/g, '').toLowerCase(); }
function md_(d) { return Number(d.slice(5, 7)) + '/' + Number(d.slice(8, 10)); }
function line_(r) { return '• ' + md_(r.date) + ' ' + r.text; }
function byDate_(a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : 0; }

function json_(text) {
  const out = { version: '2.0', template: { outputs: [{ simpleText: { text: String(text).slice(0, 900) } }] } };
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}
