#!/usr/bin/env python3
"""퀴즈 듀얼 화면(duel.html)을 '가짜 Supabase'와 묶어, 같은 브라우저의 두 탭에서 서로 겨뤄 볼 수 있는 미리보기로 만든다.
가짜 서버는 schema.sql 의 규칙(채점·시간 제한·중복 제출 무시·한 번에 한 대결)을 그대로 흉내 내고, 탭 사이 알림은 BroadcastChannel로 전달한다.
사용법: python make_duel_preview.py --html ../assets/duel_supabase/web/duel.html --out duel_preview.html
"""
import argparse, json, re
ap = argparse.ArgumentParser(); ap.add_argument("--html", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
s = open(a.html, encoding="utf-8").read()

QS = [
 ("과학", "지구가 태양 주위를 한 바퀴 도는 데 걸리는 시간은?", ["1일", "1개월", "1년", "10년"], 2),
 ("과학", "물이 끓기 시작하는 온도는 (보통 기압에서)?", ["50°C", "100°C", "150°C", "0°C"], 1),
 ("과학", "식물이 광합성을 할 때 필요한 것이 아닌 것은?", ["빛", "물", "이산화탄소", "소금"], 3),
 ("수학", "3/4 + 1/4 의 값은?", ["1/2", "1", "4/8", "3/8"], 1),
 ("수학", "12 × 8 은?", ["86", "96", "106", "88"], 1),
 ("수학", "한 변이 5cm인 정사각형의 넓이는?", ["10cm²", "20cm²", "25cm²", "15cm²"], 2),
 ("사회", "우리나라의 수도는?", ["부산", "대구", "서울", "광주"], 2),
 ("사회", "독도가 속한 바다는?", ["동해", "서해", "남해", "태평양"], 0),
 ("국어", "\"하늘이 높다\"에서 서술어는?", ["하늘이", "높다", "하늘", "이"], 1),
 ("상식", "무지개의 색깔은 모두 몇 가지로 말하나요?", ["5가지", "6가지", "7가지", "8가지"], 2),
 ("안전", "교실 안에서 지진이 나면 먼저 해야 할 행동은?", ["창문으로 뛰어간다", "책상 아래로 들어가 머리를 보호한다", "엘리베이터를 탄다", "소리를 지르며 달린다"], 1),
 ("안전", "화재가 났을 때 가장 알맞은 이동 방법은?", ["젖은 수건으로 코와 입을 막고 낮은 자세로 대피", "엘리베이터 이용", "짐을 챙긴 뒤 이동", "불이 난 곳을 확인하러 간다"], 0),
]

MOCK = r"""
<script>
(function () {
  var QS = __QS__;
  var KEY = 'mockdb_v1';
  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || { players: {}, duels: {}, answers: {} }; } catch (e) { return { players: {}, duels: {}, answers: {} }; } }
  function save(db) { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch (e) {} }
  var bc = null; try { bc = new BroadcastChannel('mockdb_events'); } catch (e) {}
  var listeners = [];
  function dispatch(m) { listeners.forEach(function (l) { if (l.event !== m.event) return; if (l.fk && String(m.row[l.fk]) !== l.fv) return; l.cb({ 'new': m.row }); }); }
  function emit(event, row) { var m = { event: event, row: JSON.parse(JSON.stringify(row)) }; if (bc) bc.postMessage(m); setTimeout(function () { dispatch(m); }, 0); }
  if (bc) bc.onmessage = function (e) { dispatch(e.data); };
  var uid = (function () { var u = ''; try { u = sessionStorage.getItem('mockuid') || ''; if (!u) { u = 'u' + Math.random().toString(36).slice(2, 10); sessionStorage.setItem('mockuid', u); } } catch (e) { u = 'u' + Math.random().toString(36).slice(2, 10); } return u; })();
  function fail(m) { throw new Error(m); }
  function iso(t) { return new Date(t).toISOString(); }
  function newCode(db) { var al = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789', c; do { c = ''; for (var i = 0; i < 6; i++) c += al[Math.floor(Math.random() * al.length)]; } while (Object.keys(db.players).some(function (k) { return db.players[k].code === c; })); return c; }
  function resolveRound(db, d) {
    if (d.status !== 'playing') return;
    var qa = QS[d.q_ids[d.round - 1]][3], a1 = db.answers[d.id + '|' + d.round + '|' + d.p1] || {}, a2 = db.answers[d.id + '|' + d.round + '|' + d.p2] || {}, p1 = 0, p2 = 0;
    if (a1.correct) p1 = 10; if (a2.correct) p2 = 10;
    if (a1.correct && a2.correct) { if (a1.at < a2.at) p1 += 3; else if (a2.at < a1.at) p2 += 3; }
    d.p1_score += p1; d.p2_score += p2;
    d.last_result = { round: d.round, correct: qa, p1_choice: a1.choice == null ? null : a1.choice, p2_choice: a2.choice == null ? null : a2.choice, p1_points: p1, p2_points: p2 };
    if (d.round >= d.total_rounds) { d.status = 'finished'; d.finished_at = iso(Date.now()); d.winner = d.p1_score > d.p2_score ? d.p1 : (d.p2_score > d.p1_score ? d.p2 : null); }
    else { d.round++; d.p1_done = d.p2_done = false; d.round_started_at = iso(Date.now()); }
  }
  function view(db, d) {
    var me1 = d.p1 === uid, q = d.status === 'playing' ? QS[d.q_ids[d.round - 1]] : null, opp = db.players[me1 ? d.p2 : d.p1] || {};
    return { id: d.id, status: d.status, round: d.round, total_rounds: d.total_rounds, i_am_p1: me1,
      my_score: me1 ? d.p1_score : d.p2_score, opp_score: me1 ? d.p2_score : d.p1_score, my_done: me1 ? d.p1_done : d.p2_done, opp_done: me1 ? d.p2_done : d.p1_done,
      opp_nickname: opp.nickname, question: q ? { body: q[1], choices: q[2] } : null, round_started_at: d.round_started_at, server_now: iso(Date.now()), round_seconds: 20,
      last_result: d.last_result || null, result: d.status !== 'finished' ? null : (d.winner == null ? 'draw' : (d.winner === uid ? 'win' : 'lose')) };
  }
  function mine(db, did) { var d = db.duels[did]; if (!d || (d.p1 !== uid && d.p2 !== uid)) fail('대결을 찾을 수 없어요'); return d; }
  var RPC = {
    ensure_player: function (db, a) {
      var n = String(a.nick || '').trim(), t = String(a.team_in || '').trim() || null;
      if (n.length < 1 || n.length > 12) fail('별명은 1~12글자로 써 주세요'); if (t && t.length > 8) fail('팀 이름은 8글자 이하로 써 주세요');
      var p = db.players[uid]; if (!p) p = db.players[uid] = { id: uid, code: newCode(db) }; p.nickname = n; p.team = t; return p.code;
    },
    my_active_duel: function (db) { var best = null; Object.keys(db.duels).forEach(function (k) { var d = db.duels[k]; if (d.status === 'playing' && (d.p1 === uid || d.p2 === uid) && Date.now() - new Date(d.round_started_at).getTime() < 600000) best = d.id; }); return best; },
    join_duel_by_code: function (db, a) {
      if (!db.players[uid]) fail('먼저 별명을 정해 주세요');
      var code = String(a.opp_code || '').trim().toUpperCase(), opp = Object.keys(db.players).filter(function (k) { return db.players[k].code === code; })[0];
      if (!opp) fail('코드를 찾을 수 없어요'); if (opp === uid) fail('나와는 대결할 수 없어요');
      Object.keys(db.duels).forEach(function (k) { var d = db.duels[k]; if (d.status === 'playing' && Date.now() - new Date(d.round_started_at).getTime() > 600000 && [d.p1, d.p2].some(function (x) { return x === uid || x === opp; })) d.status = 'cancelled'; });
      if (Object.keys(db.duels).some(function (k) { var d = db.duels[k]; return d.status === 'playing' && [d.p1, d.p2].some(function (x) { return x === uid || x === opp; }); })) fail('둘 중 한 명이 이미 대결 중이에요');
      var ids = QS.map(function (_, i) { return i; }).sort(function () { return Math.random() - 0.5; }).slice(0, 5);
      var d = { id: 'd' + Math.random().toString(36).slice(2, 10), p1: uid, p2: opp, status: 'playing', total_rounds: 5, round: 1, q_ids: ids, p1_score: 0, p2_score: 0, p1_done: false, p2_done: false, round_started_at: iso(Date.now()), last_result: null, winner: null };
      db.duels[d.id] = d; db.__new = d; return d.id;
    },
    get_duel: function (db, a) { return view(db, mine(db, a.did)); },
    submit_answer: function (db, a) {
      var d = mine(db, a.did); if (d.status !== 'playing') return view(db, d);
      var ch = Number(a.ch); if (!(ch >= 0 && ch <= 3)) fail('보기 번호가 올바르지 않아요');
      if (Date.now() > new Date(d.round_started_at).getTime() + 25000) { resolveRound(db, d); return view(db, d); }
      var k = d.id + '|' + d.round + '|' + uid; if (db.answers[k]) return view(db, d);
      db.answers[k] = { choice: ch, correct: ch === QS[d.q_ids[d.round - 1]][3], at: Date.now() };
      if (d.p1 === uid) d.p1_done = true; else d.p2_done = true;
      if (d.p1_done && d.p2_done) resolveRound(db, d); return view(db, d);
    },
    tick_duel: function (db, a) { var d = mine(db, a.did); if (d.status === 'playing' && Date.now() >= new Date(d.round_started_at).getTime() + 20000) resolveRound(db, d); return view(db, d); },
    cancel_duel: function (db, a) { var d = db.duels[a.did]; if (d && d.status === 'playing' && (d.p1 === uid || d.p2 === uid)) d.status = 'cancelled'; return null; },
    team_leaderboard: function (db) {
      var m = {}; Object.keys(db.duels).forEach(function (k) { var d = db.duels[k]; if (d.status !== 'finished') return; [d.p1, d.p2].forEach(function (p) { var t = (db.players[p] || {}).team; if (!t) return; var r = m[t] || (m[t] = { team: t, wins: 0, games: 0 }); r.games++; if (d.winner === p) r.wins++; }); });
      return Object.keys(m).map(function (k) { return m[k]; }).sort(function (x, y) { return y.wins - x.wins || y.games - x.games; });
    }
  };
  function Channel() { var mine = []; this.on = function (type, f, cb) { var l = { event: f.event, cb: cb }; var m = String(f.filter || '').match(/^(\w+)=eq\.(.+)$/); if (m) { l.fk = m[1]; l.fv = m[2]; } mine.push(l); listeners.push(l); return this; }; this.subscribe = function () { return this; }; this._off = function () { listeners = listeners.filter(function (l) { return mine.indexOf(l) < 0; }); }; }
  window.supabase = { createClient: function () { return {
    auth: { getSession: async function () { return { data: { session: { user: { id: uid } } } }; }, signInAnonymously: async function () { return { data: {}, error: null }; }, getUser: async function () { return { data: { user: { id: uid } } }; } },
    rpc: function (name, args) { return new Promise(function (res) { setTimeout(function () {
      try { var db = load(), out = RPC[name](db, args || {}), nd = db.__new, ud = null; delete db.__new; save(db);
        if (nd) emit('INSERT', nd); if (args && args.did && db.duels[args.did]) emit('UPDATE', db.duels[args.did]);
        res({ data: out, error: null }); } catch (e) { res({ data: null, error: { message: e.message } }); } }, 120); }); },
    channel: function () { return new Channel(); }, removeChannel: function (c) { if (c && c._off) c._off(); }
  }; } };
  window.mockReset = function () { try { localStorage.removeItem(KEY); sessionStorage.removeItem('mockuid'); } catch (e) {} location.reload(); };
})();
</script>
""".replace("__QS__", json.dumps([[q[0], q[1], q[2], q[3]] for q in QS], ensure_ascii=False))

tag = '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js"></script>'
assert tag in s
s = s.replace(tag, MOCK)
s = s.replace('<div id="app"></div>', '<div id="pv" class="small" style="max-width:520px;margin:0 auto;padding:10px 14px 0">미리보기 · 같은 브라우저에서 이 페이지를 <b>두 탭</b>으로 열고, 한 탭의 6자리 코드를 다른 탭에 입력하면 대결이 시작돼요. 데이터는 이 브라우저에만 저장돼요. <button onclick="mockReset()" style="padding:3px 8px;font-size:12px">초기화</button></div>\n<div id="app"></div>')
s = s.replace("var params = new URLSearchParams(location.search), join = (params.get('join') || '').toUpperCase();", "var params = new URLSearchParams(location.search), join = (params.get('join') || '').toUpperCase();")
open(a.out, "w", encoding="utf-8").write(s)
print("saved", a.out)
