/**
 * 카카오 채널 하나로 두 시트를 쓰는 중계기 (school-todo-kakao/chatbot/cloudflare_worker.js 를 대신한다)
 *
 *   대여·반납·예약·빈곳·내 신청·시설…  → 시설 관리 웹앱 (admin-school-facility, Chatbot.gs)
 *   그 밖의 말(완료, 할일, 오늘, 내아이디 …) → 일정DB 웹앱 (school-todo-kakao, kakao_chatbot.gs)
 *
 * 환경 변수(Cloudflare 대시보드 > 이 워커 > Settings > Variables and Secrets):
 *   KAKAO_KEY        카카오 스킬 URL 끝에 붙는 비밀값 (기존과 같음)
 *   APPS_SCRIPT_URL  일정DB 웹앱 URL (기존과 같음)
 *   APPS_KEY         일정DB 스크립트 속성 SECRET 과 같은 값 (기존과 같음)
 *   FACILITY_URL     시설 관리 웹앱 URL (…/exec). 비워 두면 예전 중계기와 똑같이 모두 일정DB로 보낸다.
 *   FACILITY_KEY     시설 관리 스크립트 속성 CHATBOT_SECRET 과 같은 값
 *
 * 앱스 스크립트 웹앱은 POST 답을 302로 이동시키는데 카카오는 이를 못 따라가서, 여기서 대신 따라간다.
 */
// 시설 명령어는 낱말 하나로 끝나거나 뒤에 띄어쓰기가 와야 한다("시설점검 완료", "예약안내" 같은 일정 제목은 일정DB로).
const FACILITY_CMD = /^(대여\s*취소|예약\s*취소|대여|반납|빌려\s*줘|빌릴래|예약|빈\s*(곳|교실|자리|공간)|내\s*(신청|대여|예약)(\s*(목록|내역))?|시설\s*등록|시설(\s*(도움말|안내|사용법))?)(\s|\?|$)/;
// 스쿨투두의 완료 표현("○○ 완료", "○○ 했어")은 앞 낱말과 상관없이 일정DB로
const SCHEDULE_DONE = /(완료|끝|했어|끝났어|완료했어)\s*[.!]*$/;

export function routeOf(utterance) {
  const t = String(utterance || '').replace(/\s+/g, ' ').trim();
  if (SCHEDULE_DONE.test(t)) return 'schedule';
  return FACILITY_CMD.test(t) ? 'facility' : 'schedule';
}

function reply(text) {
  const msg = { version: '2.0', template: { outputs: [{ simpleText: { text } }] } };
  return new Response(JSON.stringify(msg), { status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}

export default {
  async fetch(request, env) {
    if (request.method !== 'POST') return new Response('중계 서버가 켜져 있어요.', { status: 200 });
    const url = new URL(request.url);
    if (!env.KAKAO_KEY || url.searchParams.get('key') !== env.KAKAO_KEY) {
      return new Response('forbidden', { status: 403 });
    }
    try {
      const body = await request.text();
      let utter = '';
      try { utter = (JSON.parse(body).userRequest || {}).utterance || ''; } catch (e) { /* 아래에서 일정DB로 */ }
      const toFacility = env.FACILITY_URL && routeOf(utter) === 'facility';
      const base = toFacility ? env.FACILITY_URL : env.APPS_SCRIPT_URL;
      const key = toFacility ? env.FACILITY_KEY : env.APPS_KEY;
      const target = base + (base.includes('?') ? '&' : '?') + 'key=' + encodeURIComponent(key || '');
      const res = await fetch(target, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        redirect: 'follow',
      });
      const text = await res.text();
      JSON.parse(text); // 카카오가 받을 수 있는 JSON인지 확인
      return new Response(text, { status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8' } });
    } catch (err) {
      return reply('서버 연결에 문제가 있어요. 잠시 뒤 다시 시도해 주세요.');
    }
  },
};
