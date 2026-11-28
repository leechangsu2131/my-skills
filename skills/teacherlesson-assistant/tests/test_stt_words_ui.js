// 받아쓰기 사전 칸(T111 ③) 순수 함수 시험:  node tests/test_stt_words_ui.js  (teacherlesson-assistant 폴더에서)
const assert = require('assert');
const { parseWordLines, parseFixLines, formatWordLines, formatFixLines } = require('../web/stt_words.js');

let pass = 0;
function t(name, fn) { fn(); pass++; console.log('ok -', name); }

t('낱말 줄: 빈 줄·공백·중복 제거', () => assert.deepStrictEqual(parseWordLines(' 가 \n\n나\r\n가\n  \n다'), ['가', '나', '다']));
t('낱말 줄: 빈 값', () => { assert.deepStrictEqual(parseWordLines(''), []); assert.deepStrictEqual(parseWordLines(null), []); });
t('고쳐 쓰기: → -> => = 모두 읽음', () => {
  const { fixes, bad } = parseFixLines('알림 장 → 알림장\n모둠활동->모둠 활동\n가=>나\n다=라');
  assert.deepStrictEqual(fixes, { '알림 장': '알림장', '모둠활동': '모둠 활동', 가: '나', 다: '라' });
  assert.deepStrictEqual(bad, []);
});
t('고쳐 쓰기: 첫 표시에서만 나눔', () => assert.deepStrictEqual(parseFixLines('가 → 나 → 다').fixes, { 가: '나 → 다' }));
t('고쳐 쓰기: 나눌 수 없는 줄은 줄 번호로 알림', () => {
  const { fixes, bad } = parseFixLines('가 → 나\n표시 없음\n\n → 틀린말없음\n다 → 라');
  assert.deepStrictEqual(bad, [2, 4]);
  assert.deepStrictEqual(fixes, { 가: '나', 다: '라' });
});
t('고쳐 쓰기: 같은 틀린 말은 뒤 줄이 이김', () => assert.deepStrictEqual(parseFixLines('가 → 나\n가 → 다').fixes, { 가: '다' }));
t('고쳐 쓰기: 맞는 말을 비워도 허용(지우기)', () => assert.deepStrictEqual(parseFixLines('음 → ').fixes, { 음: '' }));
t('보여 주기 → 다시 읽기 왕복', () => {
  const fixes = { '알림 장': '알림장', 학생에이: '학생A' };
  assert.deepStrictEqual(parseFixLines(formatFixLines(fixes)).fixes, fixes);
  assert.deepStrictEqual(parseWordLines(formatWordLines(['가', '나'])), ['가', '나']);
});
t('보여 주기 모양', () => { assert.strictEqual(formatFixLines({ a: 'b' }), 'a → b'); assert.strictEqual(formatWordLines(['a', 'b']), 'a\nb'); assert.strictEqual(formatFixLines(null), ''); });

t('접었다 펼 때: 처음엔 채우고, 안 고쳤으면 다시 채우고, 고쳤으면 그대로 둠', () => {
  const { sttCanRefill } = require('../web/stt_words.js');
  const last = { words: 'a\nb', fixes: 'x → y' };
  assert.strictEqual(sttCanRefill({ words: '', fixes: '' }, null), true);                       // 한 번도 안 채움
  assert.strictEqual(sttCanRefill({ words: 'a\nb', fixes: 'x → y' }, last), true);             // 안 고침 → 서버 값 다시 받아도 안전
  assert.strictEqual(sttCanRefill({ words: 'a\nb\nc', fixes: 'x → y' }, last), false);        // 낱말 칸을 고침
  assert.strictEqual(sttCanRefill({ words: 'a\nb', fixes: 'x → z' }, last), false);            // 고쳐 쓰기 칸을 고침
  assert.strictEqual(sttCanRefill({ words: '', fixes: '' }, { words: '', fixes: '' }), true);   // 빈 사전을 안 고침
});

console.log(`${pass} passed`);
