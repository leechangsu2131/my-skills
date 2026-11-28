/**
 * tests/test_voice_cmd.js
 * 말로 명령(web/voice_cmd.js) 시험 — 말 해석(순수 함수)과 듣기 관리(가짜 음성 인식기).
 *
 * 실행: node tests/test_voice_cmd.js     (Node.js 만 필요)
 * 진짜 마이크·브라우저·구글 음성 인식은 쓰지 않는다. 화면에서 실제로 되는지는 교사 PC 점검표(T112).
 */
'use strict';

const assert = require('assert');
const path = require('path');
const {
  VOICE_CMD_NOTICE, vcNormalize, vcParseNumber, vcParseDuration, parseVoiceCommand, parseAlternatives,
  voiceTimerText, voiceTimerLabel, voiceCommandMessage, createVoiceListener,
} = require(path.join(__dirname, '..', 'web', 'voice_cmd.js'));

let passed = 0;
let failed = 0;
function test(name, fn) {
  try { fn(); console.log(`  ✅ ${name}`); passed++; }
  catch (e) { console.error(`  ❌ ${name}`); console.error(`     ${e.message}`); failed++; }
}
const cmd = text => (parseVoiceCommand(text) || {}).cmd || null;

/* ── 정규화·숫자 ─────────────────────── */
test('정규화: 띄어쓰기·기호·대문자를 없앤다', () => {
  assert.strictEqual(vcNormalize(' 다음  단계!! '), '다음단계');
  assert.strictEqual(vcNormalize('Timer 5분.'), 'timer5분');
  assert.strictEqual(vcNormalize(null), '');
});
test('숫자: 아라비아·한자어 수(1~99)', () => {
  const cases = [['5', 5], ['05', 5], ['오', 5], ['십', 10], ['십오', 15], ['이십', 20], ['삼십오', 35], ['구십구', 99], ['일', 1]];
  for (const [w, n] of cases) assert.strictEqual(vcParseNumber(w), n, w);
  for (const w of ['', '가', '공', '십십', '오오', '백']) assert.strictEqual(vcParseNumber(w), null, w);
});
test('시간: 분·초·분초, 한글·숫자', () => {
  assert.deepStrictEqual(vcParseDuration('5분'), { seconds: 300 });
  assert.deepStrictEqual(vcParseDuration('1분30초'), { seconds: 90 });
  assert.deepStrictEqual(vcParseDuration('삼십초'), { seconds: 30 });
  assert.deepStrictEqual(vcParseDuration('이분오초'), { seconds: 125 });
  assert.deepStrictEqual(vcParseDuration('99분59초'), { seconds: 5999 });
});
test('시간: 0·범위 밖은 오류, 형식이 아니면 null', () => {
  assert.deepStrictEqual(vcParseDuration('0분'), { error: 'zero' });
  assert.deepStrictEqual(vcParseDuration('100분'), { error: 'range' });
  assert.deepStrictEqual(vcParseDuration('99분60초'), { error: 'range' });
  for (const t of ['', '분', '5', '5분후', '오늘', null]) assert.strictEqual(vcParseDuration(t), null, String(t));
});

/* ── 명령 해석 ───────────────────────── */
test('다음·이전 단계', () => {
  for (const t of ['다음 단계', '다음 단계로', '다음 단계로!', '다음단계 넘겨', '다음 단계로 넘어가']) assert.strictEqual(cmd(t), 'next', t);
  for (const t of ['이전 단계', '이전 단계로', '앞 단계로', '전 단계']) assert.strictEqual(cmd(t), 'prev', t);
});
test('타이머: 숫자·한글·분초·어순·꼬리', () => {
  const sec = t => (parseVoiceCommand(t) || {}).seconds;
  assert.strictEqual(sec('타이머 5분'), 300);
  assert.strictEqual(sec('타이머 오분'), 300);
  assert.strictEqual(sec('타이머 1분 30초'), 90);
  assert.strictEqual(sec('5분 타이머'), 300);
  assert.strictEqual(sec('타이머 10분 시작'), 600);
  assert.strictEqual(sec('타이머 3분으로 맞춰줘'), 180);
  assert.strictEqual(sec('타이머 삼십초'), 30);
  assert.strictEqual(cmd('타이머 5분'), 'timer');
});
test('타이머: 시간이 이상하면 안내 오류', () => {
  assert.deepStrictEqual(parseVoiceCommand('타이머 0분'), { cmd: 'timer_error', reason: 'zero' });
  assert.deepStrictEqual(parseVoiceCommand('타이머 200분'), { cmd: 'timer_error', reason: 'range' });
});
test('기록 명령: 좋았음·고칠점·별표', () => {
  for (const t of ['좋았음', '좋았음 기록', '좋았음 기록해줘']) assert.strictEqual(cmd(t), 'good', t);
  for (const t of ['고칠점', '고칠 점', '고칠점 기록', '고칠 점 기록해']) assert.strictEqual(cmd(t), 'fix', t);
  for (const t of ['별표', '별표 해줘', '별표!', '별 표']) assert.strictEqual(cmd(t), 'star', t);
});
test('녹음 시작·멈춰', () => {
  for (const t of ['녹음 시작', '녹음 시작해', '녹음 시작해줘', '녹음 켜']) assert.strictEqual(cmd(t), 'rec_start', t);
  for (const t of ['녹음 멈춰', '녹음 멈춰줘', '녹음 종료', '녹음 정지', '녹음 끝', '녹음 그만']) assert.strictEqual(cmd(t), 'rec_stop', t);
});
test('비슷하게 들려도(낱말 표): 단게·이젼·타임머·고칠짐·벌표·노금', () => {
  assert.strictEqual(cmd('다음 단게'), 'next');
  assert.strictEqual(cmd('이젼 단계'), 'prev');
  assert.strictEqual(cmd('타임머 5분'), 'timer');
  assert.strictEqual(cmd('다이머 오분'), 'timer');
  assert.strictEqual(cmd('고칠짐'), 'fix');
  assert.strictEqual(cmd('벌표'), 'star');
  assert.strictEqual(cmd('노금 시작'), 'rec_start');
  assert.strictEqual(cmd('녹음 멈처'), 'rec_stop');
  assert.strictEqual(cmd('좋았슴'), 'good');
});
test('명령이 아닌 말은 null — 수업 중 평소 말에 반응하지 않는다', () => {
  const talk = [
    '다음 단계는 토의 활동이에요', '오늘 좋았어요', '여러분 잘했어요', '별표 친 것 보세요', '타이머는 칠판 옆에 있어요',
    '녹음해서 들려줄게요', '다음으로 넘어가 볼까요', '이전 단계에서 배운 것을 떠올려 봐요', '고칠 점이 있으면 말해 주세요',
    '지금부터 녹음을 시작하겠습니다 여러분 조용히 해 주세요', '네', '', '   ', '다음', '타이머',
  ];
  for (const t of talk) assert.strictEqual(parseVoiceCommand(t), null, t);
});
test('40자가 넘는 긴 말은 명령 낱말이 들어 있어도 버린다', () => {
  assert.strictEqual(parseVoiceCommand('다음 단계 ' + '가'.repeat(40)), null);
});
test('여러 후보: 하나라도 명령이면 그 명령', () => {
  assert.deepStrictEqual(parseAlternatives(['다음 단어', '다음 단게', '다음 단계는']), { cmd: 'next' });
  assert.strictEqual(parseAlternatives(['아무 말', '그냥 이야기']), null);
  assert.strictEqual(parseAlternatives([]), null);
  assert.strictEqual(parseAlternatives(null), null);
});

/* ── 글 만들기 ───────────────────────── */
test('타이머 입력 칸 글·이름', () => {
  assert.strictEqual(voiceTimerText(300), '5:00');
  assert.strictEqual(voiceTimerText(90), '1:30');
  assert.strictEqual(voiceTimerText(5), '0:05');
  assert.strictEqual(voiceTimerLabel(300), '5분');
  assert.strictEqual(voiceTimerLabel(90), '1분 30초');
  assert.strictEqual(voiceTimerLabel(30), '30초');
});
test('말풍선 글', () => {
  assert.strictEqual(voiceCommandMessage({ cmd: 'next' }), '다음 단계로!');
  assert.strictEqual(voiceCommandMessage({ cmd: 'timer', seconds: 90 }), '⏱ 타이머 1분 30초 시작!');
  assert.ok(voiceCommandMessage({ cmd: 'timer_error', reason: 'range' }).includes('99분 59초'));
  assert.ok(voiceCommandMessage({ cmd: 'timer_error', reason: 'zero' }).includes('0보다'));
  for (const c of ['prev', 'good', 'fix', 'star', 'rec_start', 'rec_stop']) assert.ok(voiceCommandMessage({ cmd: c }).length > 0, c);
  assert.strictEqual(voiceCommandMessage(null), '');
  assert.strictEqual(voiceCommandMessage({ cmd: '없음' }), '');
});
test('켜기 안내에 소리가 구글 서버로 간다는 말이 있다', () => {
  assert.ok(VOICE_CMD_NOTICE.includes('구글'));
  assert.ok(VOICE_CMD_NOTICE.includes('저장하지 않아요'));
});

/* ── 듣기 관리(가짜 음성 인식기) ──────── */
function harness(extra) {
  const log = { commands: [], states: [], errors: [], scheduled: [] };
  const instances = [];
  class FakeSR {
    constructor() { instances.push(this); this.started = false; this.stopped = false; }
    start() { if (FakeSR.failStart) throw new Error('InvalidStateError'); this.started = true; }
    stop() { this.stopped = true; }
  }
  FakeSR.failStart = false;
  const listener = createVoiceListener(Object.assign({
    SR: FakeSR,
    onCommand: c => log.commands.push(c),
    onState: s => log.states.push(s),
    onError: e => log.errors.push(e),
    schedule: (fn, ms) => log.scheduled.push({ fn, ms }),
  }, extra || {}));
  return { listener, log, instances, FakeSR };
}
function say(r, ...alts) {            // 끝난 결과 하나, 후보 여러 개
  const result = alts.map(t => ({ transcript: t }));
  result.isFinal = true;
  r.onresult({ resultIndex: 0, results: [result] });
}

test('듣기: 켜면 시작하고 한국어·계속 듣기·후보 3개로 설정', () => {
  const { listener, log, instances } = harness();
  assert.strictEqual(listener.start(), true);
  assert.strictEqual(instances.length, 1);
  const r = instances[0];
  assert.ok(r.started && r.lang === 'ko-KR' && r.continuous === true && r.interimResults === false && r.maxAlternatives === 3);
  assert.deepStrictEqual(log.states, [true]);
  assert.strictEqual(listener.isOn(), true);
});
test('듣기: 명령만 넘기고 다른 말은 버린다', () => {
  const { listener, log, instances } = harness();
  listener.start();
  say(instances[0], '다음 단계는 토의예요');
  say(instances[0], '다음 단게', '다음 단계');
  say(instances[0], '타이머 5분');
  assert.deepStrictEqual(log.commands, [{ cmd: 'next' }, { cmd: 'timer', seconds: 300 }]);
  assert.ok(!JSON.stringify(log).includes('토의'));      // 받아 적은 글은 어디에도 남지 않는다
});
test('듣기: 끝나지 않은(중간) 결과는 무시', () => {
  const { listener, log, instances } = harness();
  listener.start();
  const interim = [{ transcript: '다음 단계' }]; interim.isFinal = false;
  instances[0].onresult({ resultIndex: 0, results: [interim] });
  assert.deepStrictEqual(log.commands, []);
});
test('듣기: 한 번에 여러 결과가 와도 새 것(resultIndex 부터)만 처리', () => {
  const { listener, log, instances } = harness();
  listener.start();
  const a = [{ transcript: '별표' }]; a.isFinal = true;
  const b = [{ transcript: '고칠점' }]; b.isFinal = true;
  instances[0].onresult({ resultIndex: 1, results: [a, b] });
  assert.deepStrictEqual(log.commands, [{ cmd: 'fix' }]);
});
test('듣기: 조용해서 끝나면 켜져 있는 동안 다시 시작', () => {
  const { listener, log, instances } = harness();
  listener.start();
  instances[0].onend();
  assert.strictEqual(log.scheduled.length, 1);
  assert.strictEqual(log.scheduled[0].ms, 300);
  log.scheduled[0].fn();
  assert.strictEqual(instances.length, 2);
  assert.ok(instances[1].started);
});
test('듣기: 끈 뒤에는 다시 시작하지 않는다', () => {
  const { listener, log, instances } = harness();
  listener.start();
  listener.stop();
  assert.ok(instances[0].stopped);
  assert.strictEqual(listener.isOn(), false);
  assert.deepStrictEqual(log.states, [true, false]);
  assert.strictEqual(log.scheduled.length, 0);
  // 예약해 둔 다시 시작이 꺼진 뒤에 실행돼도 새로 켜지지 않는다
  const h = harness();
  h.listener.start(); h.instances[0].onend(); h.listener.stop();
  h.log.scheduled[0].fn();
  assert.strictEqual(h.instances.length, 1);
});
test('듣기: 두 번 켜도 하나만, 안 켠 채 꺼도 알림 없음', () => {
  const h = harness();
  h.listener.start(); h.listener.start();
  assert.strictEqual(h.instances.length, 1);
  assert.deepStrictEqual(h.log.states, [true]);
  const g = harness();
  g.listener.stop();
  assert.deepStrictEqual(g.log.states, []);
});
test('듣기: 마이크 거부는 바로 끄고 알림', () => {
  for (const code of ['not-allowed', 'service-not-allowed']) {
    const { listener, log, instances } = harness();
    listener.start();
    instances[0].onerror({ error: code });
    assert.strictEqual(listener.isOn(), false, code);
    assert.deepStrictEqual(log.errors, ['mic'], code);
    assert.deepStrictEqual(log.states, [true, false], code);
  }
});
test('듣기: 조용함·중단 오류는 무시하고 이어 간다', () => {
  const { listener, log, instances } = harness();
  listener.start();
  instances[0].onerror({ error: 'no-speech' });
  instances[0].onerror({ error: 'aborted' });
  assert.strictEqual(listener.isOn(), true);
  assert.deepStrictEqual(log.errors, []);
});
test('듣기: 연결 오류가 3번 이어지면 끄고 알림(명령을 알아들으면 세기를 되돌림)', () => {
  const { listener, log, instances } = harness();
  listener.start();
  instances[0].onerror({ error: 'network' });
  instances[0].onerror({ error: 'network' });
  say(instances[0], '별표');                         // 중간에 잘 되면 처음부터 다시 센다
  instances[0].onerror({ error: 'network' });
  instances[0].onerror({ error: 'network' });
  assert.strictEqual(listener.isOn(), true);
  instances[0].onerror({ error: 'network' });
  assert.strictEqual(listener.isOn(), false);
  assert.deepStrictEqual(log.errors, ['network']);
});
test('듣기: 음성 인식을 못 쓰는 브라우저', () => {
  const log = { errors: [], states: [] };
  const listener = createVoiceListener({ SR: undefined, onError: e => log.errors.push(e), onState: s => log.states.push(s) });
  assert.strictEqual(listener.start(), false);
  assert.deepStrictEqual(log.errors, ['unsupported']);
  assert.deepStrictEqual(log.states, []);
  assert.strictEqual(listener.isOn(), false);
});
test('듣기: 시작하다 오류가 나면 꺼진 채로 알림', () => {
  const h = harness();
  h.FakeSR.failStart = true;
  assert.strictEqual(h.listener.start(), false);
  assert.strictEqual(h.listener.isOn(), false);
  assert.deepStrictEqual(h.log.errors, ['start']);
  assert.deepStrictEqual(h.log.states, [false]);
});

/* ── 결과 ─────────────────────────────── */
console.log(`\n결과: ${passed} 통과 / ${failed} 실패\n`);
if (failed > 0) process.exit(1);
