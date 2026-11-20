// 중계기 시험: node scripts/test_router.mjs  (스킬 폴더에서). 실제 네트워크 대신 가짜 fetch를 쓴다.
import worker, { routeOf } from '../assets/kakao/cloudflare_router.js';

let pass = 0, fail = 0;
const ck = (n, c, x) => { c ? (pass++, console.log('  OK ', n)) : (fail++, console.log('  FAIL', n, x === undefined ? '' : JSON.stringify(x))); };

console.log('말 나누기');
for (const t of ['대여 빔프로젝터', '반납', '예약 강당 내일 3교시', '빈곳 내일 3교시', '빈 교실', '내 신청', '내대여', '시설', '시설등록 김교사 1234', '대여취소 R0001', '예약 취소 12'])
  ck('시설 ← ' + t, routeOf(t) === 'facility');
for (const t of ['완료 탄소중립', '취소 탄소중립', '할일', '오늘', '내아이디', '현황', '도움말', ''])
  ck('일정 ← ' + (t || '(빈 말)'), routeOf(t) === 'schedule');

const env = { KAKAO_KEY: 'k', APPS_SCRIPT_URL: 'https://sched/exec', APPS_KEY: 'a', FACILITY_URL: 'https://fac/exec', FACILITY_KEY: 'f' };
let called = '';
globalThis.fetch = async (u) => { called = u; return new Response(JSON.stringify({ version: '2.0', template: { outputs: [] } })); };
const req = (utter, key = 'k') => new Request('https://w/?key=' + key, { method: 'POST', body: JSON.stringify({ userRequest: { utterance: utter, user: { id: 'u' } } }) });

console.log('전달');
ck('키 틀리면 403', (await worker.fetch(req('대여', 'x'), env)).status === 403);
await worker.fetch(req('대여 빔프로젝터'), env); ck('시설 웹앱 + 시설 키', called === 'https://fac/exec?key=f', called);
await worker.fetch(req('완료 탄소중립'), env); ck('일정 웹앱 + 일정 키', called === 'https://sched/exec?key=a', called);
await worker.fetch(req('대여 빔프로젝터'), { ...env, FACILITY_URL: '' }); ck('시설 주소 없으면 예전처럼 일정으로', called === 'https://sched/exec?key=a', called);
globalThis.fetch = async () => new Response('<html>오류</html>');
const r = await (await worker.fetch(req('반납'), env)).json(); ck('JSON 아닌 답이면 안내 문구', r.template.outputs[0].simpleText.text.includes('서버 연결'));

console.log('\n통과', pass, '/ 실패', fail); process.exit(fail ? 1 : 0);
