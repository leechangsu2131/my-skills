/**
 * voice_cmd.js — 수업 중 말로 명령 (T112, ISSUE-053 ②)
 *
 * 🎯 수업 진행 화면에서 "다음 단계"·"타이머 5분"·"별표"처럼 **정해진 말만** 알아듣는다.
 * - 알아듣는 것: 다음 단계 · 이전 단계 · 타이머 N분(N분 M초) · 좋았음 · 고칠점 · 별표 · 녹음 시작 · 녹음 멈춰
 * - 말 **한 마디 전체**가 명령일 때만 반응한다. 수업 중 평소 하는 말("다음 단계는 토의예요", "오늘 좋았어요")이
 *   섞여 있으면 무시한다 — 선생님이 설명하다가 단계가 넘어가면 안 되기 때문.
 * - 그 밖의 말은 **버리고 글로 남기지 않는다**(이 파일은 받아 적은 글을 밖으로 내보내지 않는다).
 * - 비슷하게 들려도 알아듣게 낱말 표(CONFUSIONS)와 '여러 후보 중 하나라도 명령이면' 방식을 쓴다.
 * - 브라우저 음성 인식은 소리가 구글 서버로 간다 → 켤 때 안내는 index.html 이 한다(VOICE_CMD_NOTICE).
 *
 * 순수 함수(parseVoiceCommand 등)와, 음성 인식기·콜백을 밖에서 넣어 받는 듣기 관리(createVoiceListener)로 이루어져
 * Node 에서 시험한다: node tests/test_voice_cmd.js
 */
'use strict';

const VOICE_CMD_NOTICE =
  '말로 명령을 켜면 브라우저(크롬) 음성 인식을 써요. 이때 마이크 소리가 구글 서버로 보내져 글자로 바뀝니다.\n'
  + '정해진 명령(다음 단계·타이머·좋았음 등)만 쓰고 나머지 말은 버리며 저장하지 않아요.\n'
  + '학생 이름이나 개인 이야기가 많이 오갈 때는 꺼 두세요. 켤까요?';

/** 한글·숫자·영문만 남긴 소문자 글. */
function vcNormalize(text) {
  return String(text == null ? '' : text).toLowerCase().replace(/[^0-9a-z가-힣]/g, '');
}

/** 음성 인식이 자주 잘못 듣는 낱말 → 바른 낱말. 정규화한 글 안에서 바꾼다. */
const CONFUSIONS = [
  ['단게', '단계'], ['단제', '단계'], ['다계', '단계'], ['딘계', '단계'],
  ['이젼', '이전'], ['이저', '이전'],
  ['타임머', '타이머'], ['다이머', '타이머'], ['타이마', '타이머'], ['타이모', '타이머'],
  ['고칠짐', '고칠점'], ['고칠절', '고칠점'], ['고칠전', '고칠점'], ['고칠쩜', '고칠점'],
  ['별포', '별표'], ['벌표', '별표'], ['별효', '별표'],
  ['녹움', '녹음'], ['노금', '녹음'], ['농음', '녹음'],
  ['좋았슴', '좋았음'], ['조았음', '좋았음'], ['좋아씀', '좋았음'],
  ['멈처', '멈춰'], ['멈추어', '멈춰'],
];

/** 말끝에 붙는 공손한 꼬리. 명령 낱말을 찾은 뒤가 아니라 못 찾았을 때만 하나씩 떼어 다시 찾는다. */
const SUFFIXES = [
  '해주세요', '해줄래', '해줘요', '해줘', '해요', '해봐', '해', '주세요', '줘요', '줘',
  '기록해줘', '기록해', '기록', '으로', '로', '좀', '요', '시작해줘', '시작해', '시작', '맞춰줘', '맞춰', '켜줘',
];

/** 명령 → 알아들을 낱말(정규화·낱말 표 적용 뒤 기준). */
const COMMAND_WORDS = {
  next: ['다음단계', '다음단계로', '다음단계넘겨', '다음단계로넘어가', '다음단계넘어가'],
  prev: ['이전단계', '이전단계로', '전단계', '전단계로', '앞단계', '앞단계로', '이전단계넘겨'],
  good: ['좋았음', '좋았음기록', '좋은점', '좋은점기록', '잘됐음'],
  fix: ['고칠점', '고칠점기록', '아쉬운점', '아쉬운점기록'],
  star: ['별표', '별표시', '별표하나', '별표해줘'],
  rec_start: ['녹음시작', '녹음켜', '녹음켜줘', '녹음해', '녹음해줘'],
  rec_stop: ['녹음멈춰', '녹음멈춤', '녹음끝', '녹음종료', '녹음정지', '녹음중지', '녹음꺼', '녹음그만'],
};

const SINO = { 일: 1, 이: 2, 삼: 3, 사: 4, 오: 5, 육: 6, 칠: 7, 팔: 8, 구: 9 };
const MAX_TIMER_SEC = 60 * 60;          // 수업 중 오인식으로 90분 같은 값이 켜지지 않게 60분까지(T115)

/** "5"·"05"·"오"·"십"·"십오"·"이십"·"삼십오" → 숫자. 모르면 null. (1~99) */
function vcParseNumber(word) {
  const s = String(word == null ? '' : word);
  if (/^\d{1,3}$/.test(s)) return parseInt(s, 10);
  const m = s.match(/^(?:([일이삼사오육칠팔구])?십)?([일이삼사오육칠팔구])?$/);
  if (!m || s === '') return null;
  const hasTen = s.includes('십');
  const tens = hasTen ? (m[1] ? SINO[m[1]] : 1) : 0;
  const ones = m[2] ? SINO[m[2]] : 0;
  const n = tens * 10 + ones;
  return n > 0 ? n : null;
}

/** "5분"·"1분30초"·"오분"·"삼십초" → 초. 형식이 아니면 null, 0 이하·60분 넘으면 {error}. */
function vcParseDuration(text) {
  const m = String(text || '').match(/^(?:([0-9일이삼사오육칠팔구십]+)분)?(?:([0-9일이삼사오육칠팔구십]+)초)?$/);
  if (!m || (m[1] === undefined && m[2] === undefined)) return null;
  const min = m[1] === undefined ? 0 : vcParseNumber(m[1]);
  const sec = m[2] === undefined ? 0 : vcParseNumber(m[2]);
  if (min === null || sec === null) return null;
  const total = min * 60 + sec;
  if (total <= 0) return { error: 'zero' };
  if (total > MAX_TIMER_SEC) return { error: 'range' };
  return { seconds: total };
}

function vcLookup(word) {
  for (const cmd of Object.keys(COMMAND_WORDS)) {
    if (COMMAND_WORDS[cmd].includes(word)) return cmd;
  }
  return null;
}

/** 꼬리를 하나씩 떼며(없으면 그대로) 후보 글 목록을 만든다. 긴 글 → 짧은 글 순서. */
function vcCandidates(norm) {
  const out = [norm];
  let cur = norm;
  for (let guard = 0; guard < 3; guard++) {
    const suffix = SUFFIXES.find(s => cur.length > s.length + 1 && cur.endsWith(s));
    if (!suffix) break;
    cur = cur.slice(0, -suffix.length);
    out.push(cur);
  }
  return out;
}

function vcTimerCommand(candidate) {
  const m = candidate.match(/^타이머(.+)$/) || candidate.match(/^(.+)타이머$/);
  if (!m) return null;
  const dur = vcParseDuration(m[1]);
  if (dur === null) return null;
  if (dur.error) return { cmd: 'timer_error', reason: dur.error };
  return { cmd: 'timer', seconds: dur.seconds };
}

/**
 * 한 마디(받아 적은 글) → 명령. 명령이 아니면 null(그 말은 버린다).
 * 결과: {cmd:'next'|'prev'|'good'|'fix'|'star'|'rec_start'|'rec_stop'} | {cmd:'timer', seconds} | {cmd:'timer_error', reason}
 */
function parseVoiceCommand(text) {
  let norm = vcNormalize(text);
  if (!norm || norm.length > 40) return null;          // 긴 문장은 명령이 아니라 수업 말
  for (const [wrong, right] of CONFUSIONS) {
    if (wrong !== right) norm = norm.split(wrong).join(right);
  }
  for (const candidate of vcCandidates(norm)) {
    const timer = vcTimerCommand(candidate);
    if (timer) return timer;
    const cmd = vcLookup(candidate);
    if (cmd) return { cmd };
  }
  return null;
}

/** 음성 인식이 돌려준 여러 후보 글 중 처음으로 명령이 되는 것. 없으면 null. */
function parseAlternatives(transcripts) {
  for (const t of transcripts || []) {
    const cmd = parseVoiceCommand(t);
    if (cmd) return cmd;
  }
  return null;
}

/** 초 → 타이머 입력 칸 글("M:SS"). */
function voiceTimerText(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
}

/** "5분"·"1분 30초"·"30초" */
function voiceTimerLabel(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60), r = s % 60;
  return (m ? m + '분' : '') + (m && r ? ' ' : '') + (r ? r + '초' : '');
}

/** 알아들었을 때 말풍선 글. */
function voiceCommandMessage(c) {
  if (!c) return '';
  switch (c.cmd) {
    case 'next': return '다음 단계로!';
    case 'prev': return '이전 단계로!';
    case 'timer': return '⏱ 타이머 ' + voiceTimerLabel(c.seconds) + ' 시작!';
    case 'timer_error': return c.reason === 'zero' ? '타이머 시간을 0보다 크게 말해 주세요.' : '타이머는 1초부터 60분까지예요.';
    case 'good': return '👍 좋았음 기록!';
    case 'fix': return '🔧 고칠점 기록!';
    case 'star': return '★ 별표!';
    case 'rec_start': return '● 녹음 시작!';
    case 'rec_stop': return '■ 녹음 멈춤!';
    default: return '';
  }
}

/**
 * 듣기 관리. 음성 인식기(SR)와 콜백을 밖에서 넣어 받는다(시험에서 가짜로 바꾸기 쉽게).
 *   opts.SR        SpeechRecognition 생성자(없으면 start() 가 'unsupported' 를 알린다)
 *   opts.onCommand(cmd)   알아들은 명령. 받아 적은 글은 넘기지 않는다
 *   opts.onState(on)      켜짐/꺼짐 바뀔 때
 *   opts.onError(code)    'unsupported' | 'mic' | 'network' | 'start'
 *   opts.schedule         다시 시작 예약(기본 setTimeout, 시험에서 바꿈)
 * 크롬 음성 인식은 조용하면 스스로 끝나므로, 켜져 있는 동안은 끝날 때마다 다시 시작한다.
 */
function createVoiceListener(opts) {
  const SR = opts.SR;
  const onCommand = opts.onCommand || function () {};
  const onState = opts.onState || function () {};
  const onError = opts.onError || function () {};
  const schedule = opts.schedule || ((fn, ms) => setTimeout(fn, ms));
  const maxErrors = opts.maxErrors || 3;
  let on = false, recognition = null, errors = 0;

  function begin() {
    try {
      recognition = new SR();
      recognition.lang = 'ko-KR';
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.maxAlternatives = 3;
      recognition.onresult = handleResult;
      recognition.onerror = handleError;
      recognition.onend = handleEnd;
      recognition.start();
    } catch (e) {
      recognition = null;
      on = false;
      onState(false);
      onError('start');
    }
  }

  function handleResult(event) {
    for (let i = event.resultIndex || 0; i < event.results.length; i++) {
      const result = event.results[i];
      if (!result.isFinal) continue;
      const transcripts = [];
      for (let a = 0; a < result.length; a++) transcripts.push(result[a].transcript);
      const cmd = parseAlternatives(transcripts);
      if (cmd) { errors = 0; onCommand(cmd); }          // 명령이 아닌 말은 여기서 사라진다
    }
  }

  function handleError(event) {
    const code = event && event.error;
    if (code === 'no-speech' || code === 'aborted') return;          // 조용했을 뿐 — onend 가 다시 시작
    if (code === 'not-allowed' || code === 'service-not-allowed') { stop(); onError('mic'); return; }
    errors += 1;
    if (errors >= maxErrors) { stop(); onError('network'); }
  }

  function handleEnd() {
    recognition = null;
    if (on) schedule(() => { if (on && !recognition) begin(); }, 300);
  }

  function start() {
    if (on) return true;
    if (!SR) { onError('unsupported'); return false; }
    on = true; errors = 0;
    begin();
    if (on) onState(true);
    return on;
  }

  function stop() {
    const was = on;
    on = false;
    const r = recognition;
    recognition = null;
    if (r) { try { r.onend = null; r.stop(); } catch (e) { /* 이미 멈춤 */ } }
    if (was) onState(false);
  }

  return { start, stop, isOn: () => on };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    VOICE_CMD_NOTICE, vcNormalize, vcParseNumber, vcParseDuration, parseVoiceCommand, parseAlternatives,
    voiceTimerText, voiceTimerLabel, voiceCommandMessage, createVoiceListener, COMMAND_WORDS, CONFUSIONS,
  };
}
