#!/usr/bin/env python3
"""Index.html(Apps Script 3D 웹앱 화면)로 '대화 안에서 바로 열어볼 수 있는' 미리보기 HTML을 만든다.
- 가짜 google.script.run + 샘플 데이터(config의 공간·교시·층 배치 기반)를 넣는다.
- 게시용 규칙 반영: viewport-fit=cover, 안전 영역 여백, 다크 모드 색 변수.
사용법: python make_preview.py --index ../assets/apps_script/Index.html --config config.json --date 2026-10-16 --out preview.html
"""
import argparse, json, re

ap = argparse.ArgumentParser()
ap.add_argument("--index", required=True)
ap.add_argument("--config", required=True)
ap.add_argument("--date", required=True, help="미리보기 기본 날짜 yyyy-mm-dd")
ap.add_argument("--out", required=True)
a = ap.parse_args()

cfg = json.load(open(a.config, encoding="utf-8"))
s = open(a.index, encoding="utf-8").read()

# ---- 게시용 head / 테마 ----
s = s.replace('<meta name="viewport" content="width=device-width, initial-scale=1">',
  '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<title>학교 공간·기물 3D 현황 (미리보기)</title>')
tokens = """
  :root{--bg:#f4f6f9;--surface:#ffffff;--text:#222222;--border:#d8dde6;--border2:#cfd5df;--muted:#777777;--labbg:rgba(255,255,255,.88);--scene:#eef1f6;--soft:#eceff4;--formbg:#f4f6f9;--usedtxt:#2d7a2d;--tblused:#c6e0b4;--sky1:#9cc4e6;--sky2:#eef4fb;color-scheme:light dark;
    box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
  @media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#14171c;--surface:#1d2128;--text:#e6e8ec;--border:#323944;--border2:#3a424f;--muted:#9aa3b2;--labbg:rgba(29,33,40,.88);--scene:#14171c;--soft:#2a303a;--formbg:#14171c;--usedtxt:#7fd07f;--tblused:#2f5a2f;--sky1:#0d1626;--sky2:#2a3b57}}
  :root[data-theme="dark"]{--bg:#14171c;--surface:#1d2128;--text:#e6e8ec;--border:#323944;--border2:#3a424f;--muted:#9aa3b2;--labbg:rgba(29,33,40,.88);--scene:#14171c;--soft:#2a303a;--formbg:#14171c;--usedtxt:#7fd07f;--tblused:#2f5a2f;--sky1:#0d1626;--sky2:#2a3b57}
  html{height:100%;scroll-padding-top:env(safe-area-inset-top,0px)}
"""
s = s.replace('<style>\n', '<style>\n' + tokens, 1)
rep = [('height:100vh;display:flex;flex-direction:column}', 'height:100%;display:flex;flex-direction:column}'),
 ('background:#f4f6f9;height','background:var(--bg);height'), ('color:#222;','color:var(--text);'),
 ('background:#fff;border-bottom:1px solid #d8dde6','background:var(--surface);border-bottom:1px solid var(--border)'),
 ('#bar label{font-size:12px;color:#555}','#bar label{font-size:12px;color:var(--muted)}'),
 ('border:1px solid #bcc3d0;border-radius:6px;background:#fff}','border:1px solid var(--border2);border-radius:6px;background:var(--surface);color:var(--text)}'),
 ('background:rgba(255,255,255,.88);border-radius:4px;padding:1px 5px;white-space:nowrap;border:1px solid #cfd5df','background:var(--labbg);border-radius:4px;padding:1px 5px;white-space:nowrap;border:1px solid var(--border2)'),
 ('overflow:auto;background:#fff;padding:10px','overflow:auto;background:var(--surface);padding:10px'),
 ('#tablev td,#tablev th{border:1px solid #cfd5df','#tablev td,#tablev th{border:1px solid var(--border2)'),
 ('#tablev td.used{background:#c6e0b4}','#tablev td.used{background:var(--tblused)}'),
 ('#tablev td.free{color:#aaa}','#tablev td.free{color:var(--muted)}'),
 ('#panel{width:300px;background:#fff;border-left:1px solid #d8dde6','#panel{width:300px;background:var(--surface);border-left:1px solid var(--border)'),
 ('border-bottom:1px solid #eceff4','border-bottom:1px solid var(--soft)'), ('.used{color:#2d7a2d;','.used{color:var(--usedtxt);'),
 ('.small{font-size:12px;color:#777}','.small{font-size:12px;color:var(--muted)}'),
 ('background:rgba(255,255,255,.9);border:1px solid #cfd5df','background:var(--labbg);border:1px solid var(--border2)'),
 ('#gate div{background:#fff','#gate div{background:var(--surface)'), ('#msg{font-size:12px;color:#777}','#msg{font-size:12px;color:var(--muted)}'),
 ('background:#f4f6f9;border-radius:6px;display:none}','background:var(--formbg);border-radius:6px;display:none}'),
 ('.free{color:#999}','.free{color:var(--muted)}'),
 ('#canvas{position:absolute;inset:0;background:linear-gradient(#9cc4e6,#eef4fb)}','#canvas{position:absolute;inset:0;background:linear-gradient(var(--sky1),var(--sky2))}'), ('border-top:1px solid #d8dde6}}','border-top:1px solid var(--border)}}'),
 ('<span style="color:#999">비어있음</span>','<span style="opacity:.6">비어있음</span>')]
for x, y in rep:
    assert x in s, "Index.html이 예상과 다릅니다: " + x
    s = s.replace(x, y)
s = s.replace('<div id="bar">', '<div id="bar">\n  <span class="small" style="width:100%">미리보기 · 샘플 데이터로 동작합니다 (신청은 이 화면에서만 임시 저장)</span>', 1)

# ---- 샘플 데이터 (config 기반) ----
def L8(r):
    r = list(r) + [None] * (8 - len(r))
    return dict(space=r[0], floor=int(r[1]), floorEnd=int(r[2] or r[1]), x=r[3], y=r[4], w=r[5], d=r[6], h=r[7] or 0)
layout = [L8(r) for r in cfg["layout"]]
periods = [dict(name=p[0], time=p[1]) for p in cfg["periods"]] if cfg.get("periods") else [dict(name=n, time=t) for n, t in [("1교시","09:00-09:40"),("2교시","09:50-10:30"),("3교시","10:40-11:20"),("4교시","11:30-12:10"),("점심","12:10-13:00"),("5교시","13:00-13:40"),("6교시","13:50-14:30"),("7교시","14:40-15:20"),("방과후","15:30-17:00")]]
spaces = list(cfg["spaces"])
names = ["김교사", "박교사", "이교사", "최교사", "정교사", "윤교사", "강교사", "오교사"]
whys = ["6학년 합창 연습", "3학년 체육", "5학년 수업", "4학년 실험", "2학년 활동", "독서 수업", "1학년 체육", "학부모 상담"]
usage = []
for i, sp in enumerate(spaces[::max(1, len(spaces) // 10)][:10]):
    usage.append([a.date, periods[(i * 2) % len(periods)]["name"], sp, names[i % 8], whys[i % 8]])
open_rooms = [n for n in (cfg.get("student_rooms") or []) if n in spaces] or [n for n in spaces if re.match(r"^(러닝허브|플레이허브|다목적|드라마)", n)][:8] or spaces[:4]
for i, rm in enumerate(open_rooms[1:4]):
    usage.append([a.date, periods[(2 + i) % len(periods)]["name"], rm, names[i % 8], "수업"])
all_places = [r["space"] for r in layout] + list(cfg.get("extra_places", []))
base_items = [("접이식 책상", "가구", 10, "600x450mm"), ("접이식 의자", "가구", 24, ""), ("빔프로젝터", "전자기기", 1, "4K"), ("노트북 카트", "전자기기", 1, "30대용"),
              ("농구공", "체육용품", 20, "7호"), ("현미경", "실험기구", 12, "400배"), ("줄넘기", "체육용품", 35, ""), ("전자 피아노", "기타", 2, "88건반")]
states_cycle = ["양호", "양호", "수리필요", "양호", "양호", "수리중", "양호", "분실", "양호", "양호"]
items = []
for i, p in enumerate(all_places[:: max(1, len(all_places) // 22)][:22]):
    nm, cat, q, spec = base_items[i % len(base_items)]
    first = all_places[(i * 7 + 3) % len(all_places)]
    items.append(["A-%04d" % (i + 1), nm, q, p, states_cycle[i % len(states_cycle)], cat, spec, "2024-03-04", "홍길동", first, "램프 교체 필요" if states_cycle[i % len(states_cycle)] == "수리필요" else ""])
people = list(cfg.get("people") or names)
fixed = [list(x) for x in (cfg.get("fixed_schedule") or [])]
data = dict(layout=layout, bookable=spaces, open=open_rooms, fixed=fixed, approval=list(cfg.get("approval_spaces") or []), lendable=list(cfg.get("lendable_categories") or []), people=people, periods=periods, usage=usage, items=items)
mock = """
<script>
(function () {
  var DB = %s;

  var T0 = Date.now(), B0 = new Date('__DATE__' + 'T10:50:00').getTime();
  function nowD() { return new Date(B0 + (Date.now() - T0)); }
  function pad(n) { return ('0' + n).slice(-2); }
  function hhmm(m) { return pad(Math.floor(m / 60)) + ':' + pad(m % 60); }
  function dayS(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function minOf(d) { return d.getHours() * 60 + d.getMinutes(); }
  function norm(s) { return String(s || '').split(' ').join(''); }
  function pinfo() { return DB.periods.map(function (p) {
    var t = String(p.time).split('-'), a = (t[0] || '').split(':'), b = (t[1] || '').split(':');
    return { name: p.name, time: p.time, from: a.length === 2 ? +a[0] * 60 + +a[1] : null, to: b.length === 2 ? +b[0] * 60 + +b[1] : null };
  }); }
  DB.sessions = [{ start: B0 - 15 * 60000, room: DB.open[0], label: '5-2-7', activity: '모둠 토의', endPlanned: B0 + 15 * 60000, endActual: null }];
  var DAYN = ['월', '화', '수', '목', '금', '토', '일'];
  function dayOf(ds) { var p = ds.split('-'); return DAYN[(new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])).getUTCDay() + 6) % 7]; }
  function fixedFor(ds) { var d = dayOf(ds); return (DB.fixed || []).filter(function (f) { return f[1] === d; }); }
  function active(s, now) { return !s.endActual && s.endPlanned > now.getTime(); }
  function bookingsToday(day) {
    var pm = {}; pinfo().forEach(function (p) { pm[p.name] = p; });
    return DB.usage.filter(function (u) { return u[0] === day && u[5] !== '반려' && u[5] !== '취소' && pm[u[1]] && pm[u[1]].from != null; }).map(function (u) { return { room: u[2], period: u[1], from: pm[u[1]].from, to: pm[u[1]].to }; })
      .concat(fixedFor(day).filter(function (f) { return pm[f[2]] && pm[f[2]].from != null; }).map(function (f) { return { room: f[0], period: f[2], from: pm[f[2]].from, to: pm[f[2]].to, fixed: true }; }));
  }
  function studentData() {
    var now = nowD(), day = dayS(now), nm = minOf(now), bk = bookingsToday(day), rooms = {};
    DB.open.forEach(function (room) {
      var tb = bk.filter(function (b) { return b.room === room; }).sort(function (a, b) { return a.from - b.from; });
      var segs = tb.map(function (b) { return { type: 'teacher', period: b.period, from: hhmm(b.from), to: hhmm(b.to) }; }), act = null;
      DB.sessions.forEach(function (s) {
        if (s.room !== room || dayS(new Date(s.start)) !== day) return;
        var e = s.endActual || s.endPlanned, on = active(s, now);
        segs.push({ type: 'student', from: hhmm(minOf(new Date(s.start))), to: hhmm(minOf(new Date(e))), activity: s.activity, active: on }); if (on) act = s;
      });
      var st = { state: 'free', until: '', next: '' };
      var cur = tb.filter(function (b) { return b.from <= nm && nm < b.to; })[0];
      if (cur) { st.state = 'teacher'; st.until = hhmm(cur.to); st.period = cur.period; }
      else if (act) { st.state = 'student'; st.until = hhmm(minOf(new Date(act.endPlanned))); st.activity = act.activity; }
      var nx = tb.filter(function (b) { return b.from > nm; })[0]; if (nx) st.next = hhmm(nx.from);
      segs.sort(function (a, b) { return a.from < b.from ? -1 : (a.from > b.from ? 1 : 0); });
      st.today = segs; rooms[room] = st;
    });
    return { layout: DB.layout, open: DB.open, periods: DB.periods, rooms: rooms, now: { date: day, time: hhmm(nm) } };
  }
  function roomWeek(room) {
    var now = nowD(), dow = now.getDay() === 0 ? 7 : now.getDay(), days = [], pf = pinfo();
    for (var d = 0; d < 5; d++) days.push(dayS(new Date(now.getTime() - (dow - 1 - d) * 86400000)));
    var te = pf.map(function () { return [0, 0, 0, 0, 0]; }), stu = pf.map(function () { return [0, 0, 0, 0, 0]; });
    DB.usage.forEach(function (u) { if (u[5] === '반려' || u[5] === '취소') return; var di = days.indexOf(u[0]), pi = pf.map(function (p) { return p.name; }).indexOf(u[1]); if (u[2] === room && di >= 0 && pi >= 0) te[pi][di] = 1; });
    (DB.fixed || []).forEach(function (f) { var di = DAYN.indexOf(f[1]), pi = pf.map(function (p) { return p.name; }).indexOf(f[2]); if (f[0] === room && di >= 0 && di < 5 && pi >= 0) te[pi][di] = 1; });
    var h0 = 0; for (var i = 0; i < room.length; i++) h0 += room.charCodeAt(i);
    pf.forEach(function (p, pi) { for (var d2 = 0; d2 < 5; d2++) stu[pi][d2] = [0, 0, 1, 2, 3, 0, 1][(h0 + d2 * 3 + pi * 5) % 7]; });
    DB.sessions.forEach(function (s) { if (s.room !== room) return; var sd = new Date(s.start), di = (sd.getDay() + 6) % 7, m = minOf(sd), pi = -1; if (di > 4) return; pf.forEach(function (p, i) { if (p.from != null && m >= p.from && m < p.to) pi = i; }); if (pi >= 0) stu[pi][di]++; });
    return { periods: DB.periods, teacher: te, student: stu, weeks: 4 };
  }
  function startUse(p) {
    var now = nowD(), day = dayS(now), nm = minOf(now), label = String(p.label || '').trim(), minutes = Math.max(10, Math.min(90, +p.minutes || 30));
    if (!p.room || !label) return { ok: false, msg: '학급·번호(또는 별명)를 입력해 주세요.' };
    if (label.length > 12) return { ok: false, msg: '12글자 이하로 써 주세요. (실명 대신 학급·번호나 별명을 써요)' };
    if (DB.open.indexOf(p.room) < 0) return { ok: false, msg: '학생이 사용할 수 있는 공간이 아니에요.' };
    var bk = bookingsToday(day).filter(function (b) { return b.room === p.room; });
    var cur = bk.filter(function (b) { return b.from <= nm && nm < b.to; })[0];
    if (cur) return { ok: false, msg: '지금은 선생님이 신청한 시간이에요 (' + cur.period + ', ' + hhmm(cur.to) + '까지).' };
    for (var i = 0; i < DB.sessions.length; i++) { var s = DB.sessions[i]; if (!active(s, now)) continue;
      if (s.room === p.room) return { ok: false, msg: '이미 다른 모둠이 사용 중이에요 (' + hhmm(minOf(new Date(s.endPlanned))) + ' 종료 예정).' };
      if (norm(s.label) === norm(label)) return { ok: false, msg: '이미 ' + s.room + ' 사용 중이에요. 먼저 "다 썼어요"를 눌러 주세요.' }; }
    var end = nm + minutes, note = '', nx = bk.filter(function (b) { return b.from > nm; }).sort(function (a, b) { return a.from - b.from; })[0];
    if (nx && nx.from < end) { end = nx.from; note = '선생님 신청(' + nx.period + ') 때문에 ' + hhmm(end) + '까지만 사용할 수 있어요.'; }
    if (end - nm < 5) return { ok: false, msg: '곧 선생님이 신청한 시간이라 지금은 시작할 수 없어요.' };
    DB.sessions.push({ start: now.getTime(), room: p.room, label: label, activity: String(p.activity || '').slice(0, 20), endPlanned: now.getTime() + (end - nm) * 60000, endActual: null });
    return { ok: true, until: hhmm(end), note: note };
  }
  function endUse(room, label) {
    var now = nowD();
    for (var i = DB.sessions.length - 1; i >= 0; i--) { var s = DB.sessions[i]; if (s.room === room && norm(s.label) === norm(label) && active(s, now)) { s.endActual = now.getTime(); return { ok: true }; } }
    return { ok: false, msg: '사용 중인 기록을 찾지 못했어요.' };
  }


  var DAYMS = 86400000;
  function isoOff(n) { var d = new Date(Date.now() + n * DAYMS); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  DB.pins = {}; (DB.people || []).forEach(function (n) { DB.pins[n] = '1111'; });
  DB.loans = [];
  (function () {
    var ls = DB.items.filter(function (i) { return i[4] === '양호' && (!DB.lendable.length || DB.lendable.indexOf(i[5]) >= 0); });
    if (ls[0]) DB.loans.push({ id: 'R0001', item: ls[0][0], name: ls[0][1], qty: 1, who: DB.people[0], start: isoOff(-1), due: isoOff(1), purpose: '수업', status: '승인', returned: '' });
    if (ls[1]) DB.loans.push({ id: 'R0002', item: ls[1][0], name: ls[1][1], qty: 1, who: DB.people[1] || DB.people[0], start: isoOff(3), due: isoOff(4), purpose: '행사', status: '승인', returned: '' });
    if (ls[2]) DB.loans.push({ id: 'R0003', item: ls[2][0], name: ls[2][1], qty: 1, who: DB.people[2] || DB.people[0], start: isoOff(-6), due: isoOff(-4), purpose: '', status: '승인', returned: '' });
  })();
  if (DB.approval && DB.approval[0]) DB.usage.push(['__DATE__', '1교시', DB.approval[0], DB.people[0], '합창 연습', '승인대기']);
  function itemOf(id) { var i = DB.items.filter(function (x) { return x[0] === id; })[0]; return i ? { id: i[0], name: i[1], qty: i[2], loc: i[3], status: i[4], cat: i[5] } : null; }
  function lendOk(it) {
    if (it.status !== '양호') return { ok: false, why: '상태가 "' + it.status + '"이라 지금은 빌릴 수 없어요.' };
    if (DB.lendable.length && DB.lendable.indexOf(it.cat) < 0) return { ok: false, why: '"' + it.cat + '" 분류는 대여 대상이 아니에요.' };
    return { ok: true };
  }
  function resv(itemId, s, d) { var t = 0; DB.loans.forEach(function (l) { if (l.item === itemId && (l.status === '승인대기' || l.status === '승인') && !(l.due < s || d < l.start)) t += l.qty; }); return t; }
  function pinProblem(who, pin) { if (!DB.pins[who]) return 'PIN이 아직 없어요. 먼저 "내 신청"에서 PIN을 정해 주세요.'; return DB.pins[who] === String(pin) ? '' : 'PIN이 맞지 않아요.'; }
  function mineLoan(id, who) { var l = DB.loans.filter(function (x) { return x.id === id; })[0]; if (!l) return { err: '신청 내역을 찾을 수 없어요.' }; if (l.who !== who) return { err: '내 신청이 아니에요.' }; return { l: l }; }

  function runner(ok, fail) {
    function later(fn) { setTimeout(function () { try { ok(fn()); } catch (e) { fail(e); } }, 150); }
    return {
      withSuccessHandler: function (f) { return runner(f, fail); },
      withFailureHandler: function (f) { return runner(ok, f); },
      getStudentData: function (code) { setTimeout(function () { ok(studentData()); }, 120); },
      getRoomWeek: function (code, room) { setTimeout(function () { ok(roomWeek(room)); }, 120); },
      startStudentUse: function (code, p) { setTimeout(function () { ok(startUse(p)); }, 150); },
      endStudentUse: function (code, room, label) { setTimeout(function () { ok(endUse(room, label)); }, 150); },
      hasPin: function (code, who) { later(function () { return { has: !!DB.pins[who] }; }); },
      setPin: function (code, who, pin, old) { later(function () {
        if (DB.people.indexOf(who) < 0) return { ok: false, msg: '신청자 명단에 없는 이름이에요.' };
        if (!/^[0-9]{4,8}$/.test(String(pin))) return { ok: false, msg: 'PIN은 숫자 4~8자리로 정해 주세요.' };
        if (DB.pins[who] && DB.pins[who] !== String(old)) return { ok: false, msg: '기존 PIN이 맞지 않아요. 잊으셨다면 관리자에게 초기화를 요청하세요.' };
        DB.pins[who] = String(pin); return { ok: true }; }); },
      getItemLoans: function (code, id) { later(function () {
        var it = itemOf(id); if (!it) return { lendable: false, why: '물품을 찾을 수 없어요.', total: 0, loans: [] };
        var ld = lendOk(it), t = isoOff(0);
        return { lendable: ld.ok, why: ld.why || '', total: it.qty, today: t, loans: DB.loans.filter(function (l) { return l.item === it.id && (l.status === '승인대기' || l.status === '승인') && l.due >= t; }).map(function (l) { return { id: l.id, who: l.who, qty: l.qty, start: l.start, due: l.due, status: l.status }; }) }; }); },
      requestLoan: function (code, p) { later(function () {
        var who = String(p.who || '').trim(), t = isoOff(0);
        if (DB.people.indexOf(who) < 0) return { ok: false, msg: '신청자 명단에 없는 이름이에요.' };
        var pm = pinProblem(who, p.pin); if (pm) return { ok: false, msg: pm };
        var it = itemOf(p.id); if (!it) return { ok: false, msg: '물품을 찾을 수 없어요.' };
        var ld = lendOk(it); if (!ld.ok) return { ok: false, msg: ld.why };
        var qty = Math.floor(Number(p.qty));
        if (!(qty >= 1)) return { ok: false, msg: '수량을 1개 이상으로 적어 주세요.' };
        if (!p.start || !p.due) return { ok: false, msg: '대여일과 반납예정일을 골라 주세요.' };
        if (p.start < t) return { ok: false, msg: '지난 날짜는 신청할 수 없어요.' };
        if (p.due < p.start) return { ok: false, msg: '반납예정일은 대여일 이후여야 해요.' };
        if ((new Date(p.due) - new Date(p.start)) / DAYMS > 30) return { ok: false, msg: '한 번에 30일까지만 빌릴 수 있어요.' };
        var avail = it.qty - resv(it.id, p.start, p.due);
        if (qty > avail) return { ok: false, msg: '그 기간에 빌릴 수 있는 수량은 ' + Math.max(0, avail) + '개예요. (전체 ' + it.qty + '개)' };
        var id = 'R' + ('000' + (DB.loans.length + 1)).slice(-4);
        DB.loans.push({ id: id, item: it.id, name: it.name, qty: qty, who: who, start: p.start, due: p.due, purpose: p.purpose || '', status: '승인', returned: '' });
        return { ok: true, id: id, status: '승인', left: avail - qty }; }); },
      returnLoan: function (code, id, who, pin) { later(function () {
        var pm = pinProblem(who, pin); if (pm) return { ok: false, msg: pm }; var m = mineLoan(id, who); if (m.err) return { ok: false, msg: m.err };
        if (m.l.status !== '승인') return { ok: false, msg: '지금 상태("' + m.l.status + '")에서는 반납 처리를 할 수 없어요.' };
        m.l.status = '반납완료'; m.l.returned = isoOff(0); return { ok: true }; }); },
      cancelLoan: function (code, id, who, pin) { later(function () {
        var pm = pinProblem(who, pin); if (pm) return { ok: false, msg: pm }; var m = mineLoan(id, who); if (m.err) return { ok: false, msg: m.err };
        if (!(m.l.status === '승인대기' || (m.l.status === '승인' && m.l.start > isoOff(0)))) return { ok: false, msg: '이미 시작된 대여는 취소할 수 없어요. 반납 처리를 해 주세요.' };
        m.l.status = '취소'; return { ok: true }; }); },
      myRequests: function (code, who, pin) { later(function () {
        var pm = pinProblem(who, pin); if (pm) return { ok: false, msg: pm }; var t = isoOff(0);
        var loans = DB.loans.filter(function (l) { return l.who === who && (l.status === '승인대기' || l.status === '승인' || (l.status === '반납완료' && l.returned >= isoOff(-14))); })
          .map(function (l) { return { id: l.id, name: l.name, qty: l.qty, start: l.start, due: l.due, status: l.status, overdue: l.status === '승인' && l.due < t }; });
        var spaces = []; DB.usage.forEach(function (u, i) { if (u[3] !== who || u[5] === '반려' || u[5] === '취소' || u[0] < t) return; spaces.push({ row: i + 2, date: u[0], period: u[1], space: u[2], purpose: u[4], status: u[5] === '승인대기' ? '승인대기' : '확정' }); });
        return { ok: true, loans: loans, spaces: spaces }; }); },
      cancelMySpace: function (code, who, pin, row) { later(function () {
        var pm = pinProblem(who, pin); if (pm) return { ok: false, msg: pm }; var u = DB.usage[row - 2];
        if (!u || u[3] !== who) return { ok: false, msg: '내 신청이 아니에요.' }; if (u[0] < isoOff(0)) return { ok: false, msg: '지난 신청은 취소할 수 없어요.' };
        u[5] = '취소'; return { ok: true }; }); },
      adminSummary: function (code) { later(function () {
        if (String(code) !== '0000') throw new Error('관리자 코드가 올바르지 않습니다.'); var t = isoOff(0), pend = [];
        DB.usage.forEach(function (u, i) { if (u[5] === '승인대기') pend.push({ row: i + 2, date: u[0], period: u[1], space: u[2], who: u[3], purpose: u[4] }); });
        var b = function (l) { return { id: l.id, name: l.name, qty: l.qty, who: l.who, start: l.start, due: l.due, status: l.status, purpose: l.purpose }; }, out = DB.loans.filter(function (l) { return l.status === '승인'; });
        return { ok: true, today: t, pendingSpace: pend, pendingLoans: DB.loans.filter(function (l) { return l.status === '승인대기'; }).map(b), active: out.filter(function (l) { return l.start <= t; }).map(b),
          dueToday: out.filter(function (l) { return l.due === t; }).map(b), overdue: out.filter(function (l) { return l.due < t; }).map(b), upcoming: out.filter(function (l) { return l.start > t; }).map(b) }; }); },
      adminSetStatus: function (code, kind, key, status) { later(function () {
        if (String(code) !== '0000') throw new Error('관리자 코드가 올바르지 않습니다.');
        if (kind === 'space') { var u = DB.usage[Number(key) - 2]; if (!u) return { ok: false, msg: '신청 내역을 찾을 수 없어요.' }; u[5] = status; return { ok: true }; }
        var l = DB.loans.filter(function (x) { return x.id === key; })[0]; if (!l) return { ok: false, msg: '신청 내역을 찾을 수 없어요.' };
        l.status = status; if (status === '반납완료') l.returned = isoOff(0); return { ok: true }; }); },
      adminResetPin: function (code, who) { later(function () { if (String(code) !== '0000') throw new Error('관리자 코드가 올바르지 않습니다.'); if (!DB.pins[who]) return { ok: false, msg: '그 이름의 PIN 기록이 없어요.' }; delete DB.pins[who]; return { ok: true }; }); },
      getItemHistory: function (code, id) {
        setTimeout(function () {
          var it = DB.items.filter(function (i) { return i[0] === id; })[0], h = [];
          if (it && it[9] && it[9] !== it[3]) h.push({ date: '2025-05-02', kind: '이동', to: it[3], memo: it[9] + '에서 이동', by: '홍길동' });
          if (it && it[4] !== '양호') h.unshift({ date: '2026-09-20', kind: '수리', to: '', memo: it[4], by: '행정실' });
          ok(h);
        }, 150);
      },
      getRoomTimetable: function (code, room, date) {
        setTimeout(function () {
          var p = date.split('-'), base = new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])), dow = (base.getUTCDay() + 6) % 7, days = [], pf = pinfo(), names = pf.map(function (x) { return x.name; });
          for (var i = 0; i < 5; i++) { var dd = new Date(base.getTime() + (i - dow) * 86400000); days.push(dd.getUTCFullYear() + '-' + pad(dd.getUTCMonth() + 1) + '-' + pad(dd.getUTCDate())); }
          var grid = pf.map(function () { return [null, null, null, null, null]; });
          (DB.fixed || []).forEach(function (f) { var di = DAYN.indexOf(f[1]), pi = names.indexOf(f[2]); if (f[0] === room && di >= 0 && di < 5 && pi >= 0) grid[pi][di] = { kind: f[3].indexOf('방과후') === 0 ? 'program' : 'regular', text: f[3].replace('정규 ', '').replace('방과후 ', '').replace('맞춤형 ', '').replace('선택형 ', '') }; });
          DB.usage.forEach(function (u) { if (u[5] === '반려' || u[5] === '취소') return; var di = days.indexOf(u[0]), pi = names.indexOf(u[1]); if (u[2] === room && di >= 0 && pi >= 0) grid[pi][di] = { kind: 'booking', text: u[3] + (u[4] ? ' ' + u[4] : '') }; });
          ok({ periods: DB.periods, days: days, grid: grid });
        }, 150);
      },
      getData: function (code, date) {
        setTimeout(function () { ok({ layout: DB.layout, bookable: DB.bookable, people: DB.people, periods: DB.periods,
          approval: DB.approval, lendable: DB.lendable,
          usage: DB.usage.filter(function (u) { return u[0] === date && u[5] !== '반려' && u[5] !== '취소'; }).map(function (u) { return { period: u[1], space: u[2], who: (u[5] === '승인대기' ? '⏳ ' : '') + u[3], purpose: u[4], pending: u[5] === '승인대기' }; })
          .concat(fixedFor(date).filter(function (f) { return !DB.usage.some(function (u) { return u[0] === date && u[1] === f[2] && u[2] === f[0]; }); }).map(function (f) { return { period: f[2], space: f[0], who: f[3], purpose: '고정 일정', fixed: true }; })),
          items: DB.items.map(function (i) { return { id: i[0], name: i[1], qty: i[2], loc: i[3], status: i[4], cat: i[5], spec: i[6], acq: i[7], mgr: i[8], first: i[9], note: i[10] }; }) }); }, 150);
      },
      submitRequest: function (code, p) {
        setTimeout(function () {
          if (!p.who.trim()) return ok({ ok: false, msg: '이름을 입력해 주세요.' });
          if (DB.bookable.indexOf(p.space) < 0) return ok({ ok: false, msg: '"' + p.space + '"은(는) 사용 신청을 받지 않는 공간이에요. (교무실·교장실·행정실 같은 곳은 신청할 수 없어요)' });
          var fxm = fixedFor(p.date).filter(function (f) { return f[0] === p.space && f[2] === p.period; })[0];
          if (fxm) return ok({ ok: false, msg: '그 시간에는 ' + fxm[3] + ' 일정이 있어요. 다른 시간을 골라 주세요.' });
          if (DB.people.length && DB.people.indexOf(p.who.trim()) < 0) return ok({ ok: false, msg: '신청자 명단에 없는 이름입니다.' });
          var dup = DB.usage.filter(function (u) { return u[0] === p.date && u[1] === p.period && u[2] === p.space && u[5] !== '반려' && u[5] !== '취소'; })[0];
          if (dup) return ok({ ok: false, msg: '이미 신청된 시간입니다. (' + dup[3] + ')' });
          var mine = DB.usage.filter(function (u) { return u[5] !== '반려' && u[5] !== '취소' && u[0] === p.date && u[1] === p.period && u[3].replace(/\\s+/g, '') === p.who.replace(/\\s+/g, ''); })[0];
          if (mine) return ok({ ok: false, msg: '같은 시간(' + p.period + ')에 이미 ' + mine[2] + ' 사용을 신청하셨습니다. 한 시간에는 한 곳만 신청할 수 있어요.' });
          var needs = (DB.approval || []).indexOf(p.space) >= 0;
          DB.usage.push([p.date, p.period, p.space, p.who.trim(), p.purpose || '', needs ? '승인대기' : '확정']);
          ok(needs ? { ok: true, pending: true, msg: '관리자 승인 후에 확정돼요. 승인되면 이 시간은 다른 분이 신청할 수 없어요.' } : { ok: true });
        }, 150);
      }
    };
  }
  window.pvToggle = function () { var cur = ''; try { cur = localStorage.getItem('pvMode') || ''; localStorage.setItem('pvMode', cur === 'student' ? 'teacher' : 'student'); } catch (e) {} location.reload(); };
  document.addEventListener('DOMContentLoaded', function () { var b = document.getElementById('pvBtn'), cur = ''; try { cur = localStorage.getItem('pvMode') || ''; } catch (e) {} if (b) b.textContent = cur === 'student' ? '선생님 화면으로 보기' : '학생 화면(빈 교실 찾기)으로 보기'; });
  window.google = { script: { run: runner(function () {}, function () {}) } };
})();
</script>
""".replace("var DB = %s;", "var DB = " + json.dumps(data, ensure_ascii=False) + ";")
mock = mock.replace("__DATE__", a.date)
tag = '<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>'
assert tag in s
s = s.replace(tag, mock + tag, 1)
s = s.replace("/*__PARAMS__*/{}/*__END__*/", "(function () { var m = ''; try { m = localStorage.getItem('pvMode') || ''; } catch (e) {} return m === 'student' ? { mode: 'student' } : {}; })()")
s = s.replace('<span class="small" style="width:100%">미리보기 · 샘플 데이터로 동작합니다 (신청은 이 화면에서만 임시 저장)</span>', '<span class="small" style="width:100%">미리보기 · 샘플 데이터로 동작합니다 (기록은 이 화면에서만 임시 저장 · 샘플 PIN 1111 · 관리자 코드 0000) <button id="pvBtn" onclick="pvToggle()"></button></span>')
s = s.replace("$('date').value = todayStr();", "$('date').value = '%s';" % a.date)
open(a.out, "w", encoding="utf-8").write(s)
print("saved", a.out)
