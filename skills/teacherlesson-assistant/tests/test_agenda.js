/**
 * tests/test_agenda.js
 * web/agenda.js 순수 함수 시험.  실행: node tests/test_agenda.js
 */
'use strict';
const assert = require('assert');
const path = require('path');
const { breakLine, agendaList, quickAdd } = require(path.join(__dirname, '..', 'web', 'agenda.js'));

const periods = [
  { no: 1, start: '09:00', end: '09:40' }, { no: 2, start: '09:50', end: '10:30' },
  { no: 3, start: '10:50', end: '11:30' },
];
const lessons = [{ period: 2, subject: '수학' }, { period: 3, subject: '국어' }, { period: 3, subject: '국어' }];
const at = (h, m) => h * 60 + m;

const tests = [];
const t = (name, fn) => tests.push([name, fn]);

t('교시 사이에만 한 줄이 나온다', () => {
  assert.strictEqual(breakLine(periods, lessons, at(9, 40), 2), '☕ 쉬는 시간 · 다음 2교시 수학 · 오늘까지 할 일 2개');
  assert.strictEqual(breakLine(periods, lessons, at(9, 49), 0), '☕ 쉬는 시간 · 다음 2교시 수학 · 오늘까지 할 일 없음');
  assert.strictEqual(breakLine(periods, lessons, at(10, 45), null), '☕ 쉬는 시간 · 다음 3교시 국어');
  for (const m of [at(8, 30), at(9, 0), at(9, 39), at(9, 50), at(10, 29), at(10, 50), at(11, 30), at(15, 0)]) {
    assert.strictEqual(breakLine(periods, lessons, m, 1), '', String(m));
  }
});
t('다음 교시에 수업이 없거나 교시 설정이 뒤섞여도 된다', () => {
  assert.strictEqual(breakLine(periods, [], at(9, 45), null), '☕ 쉬는 시간 · 다음 2교시 수업 없음');
  assert.strictEqual(breakLine([periods[2], periods[0], periods[1]], lessons, at(9, 45), null), '☕ 쉬는 시간 · 다음 2교시 수학');
  assert.strictEqual(breakLine([], lessons, at(9, 45), 1), '');
  assert.strictEqual(breakLine(undefined, undefined, at(9, 45), 1), '');
});
t('내용은 HTML 로 해석되지 않는다', () => {
  const html = agendaList({
    today: [{ category: '<b>', text: '<img src=x onerror=1>', when: '11/25(수)' }],
    tasks: [{ dday: 'D+1', left: -1, when: '11/24(화)', text: '"늦은" & 일' }, { dday: 'D-day', left: 0, when: '11/25(수)', text: '오늘 일' }],
    week: [{ category: '학교', text: '<script>', when: '11/26(목)' }], week_label: '이번 주 남은 일정',
  });
  assert.ok(!html.includes('<img') && !html.includes('<script>'));
  assert.ok(html.includes('&lt;img') && html.includes('&quot;늦은&quot; &amp; 일'));
  assert.ok(html.includes('class="late"><b>D+1</b>') && html.includes('class="now"><b>D-day</b>'));
  assert.ok(html.includes('이번 주 남은 일정') && html.includes('11/26(목)'));
});
t('비었을 때와 실패했을 때', () => {
  const empty = agendaList({ today: [], tasks: [], week: [] });
  assert.ok(empty.includes('등록된 행사 없음') && empty.includes('30일 안에 할 일 없음') && !empty.includes('✔'));
  const failed = agendaList({ reason: '시트 <접근> 불가', today: [] });
  assert.ok(failed.includes('시트 &lt;접근&gt; 불가') && !failed.includes('등록된 행사 없음'));
});

function fake(preview) {
  const sent = [], asked = [];
  const send = async body => {
    sent.push(body);
    if (!body.confirm) return preview;
    return { status: 'success', written: true };
  };
  return { sent, asked, send, ask: answer => message => { asked.push(message); return answer; } };
}
const ok = { status: 'success', written: false, line: '내일 상담 준비', parsed: { when: '11/26(목)', category: '개인', text: '상담 준비' } };

t('확인 창에서 취소하면 쓰기 요청을 보내지 않는다', async () => {
  const f = fake(ok);
  assert.strictEqual(await quickAdd(' 내일 상담 준비 ', f.send, f.ask(false)), false);
  assert.deepStrictEqual(f.sent, [{ text: ' 내일 상담 준비 ' }]);
  assert.ok(f.asked[0].includes('11/26(목) · 개인') && f.asked[0].includes('상담 준비') && f.asked[0].includes('빠른입력'));
});
t('확인하면 한 번만 쓴다', async () => {
  const f = fake(ok);
  assert.strictEqual(await quickAdd('내일  상담 준비', f.send, f.ask(true)), true);
  assert.deepStrictEqual(f.sent[1], { text: '내일 상담 준비', confirm: true });
  assert.strictEqual(f.sent.length, 2);
});
t('빈 글이거나 검사에서 걸리면 확인 창도 안 뜬다', async () => {
  const f = fake({ status: 'error', message: '지난 날짜' });
  assert.strictEqual(await quickAdd('   ', f.send, f.ask(true)), false);
  assert.strictEqual(await quickAdd('11/1 지난 일', f.send, f.ask(true)), false);
  assert.strictEqual(f.sent.length, 1);
  assert.strictEqual(f.asked.length, 0);
});
t('쓰기가 실패하면 false(입력한 글이 남는다)', async () => {
  const send = async body => (body.confirm ? { status: 'error', written: false } : ok);
  assert.strictEqual(await quickAdd('내일 상담 준비', send, () => true), false);
});

(async () => {
  for (const [name, fn] of tests) {
    try { await fn(); } catch (e) { console.error(`실패: ${name}`); throw e; }
  }
  console.log(`agenda: ${tests.length}개 통과`);
})().catch(e => { console.error(e.message); process.exit(1); });
