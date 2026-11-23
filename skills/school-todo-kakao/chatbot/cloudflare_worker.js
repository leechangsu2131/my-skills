/**
 * 카카오 오픈빌더 스킬 요청 → (이동을 대신 따라가서) 구글 앱스 스크립트 웹앱에 전달하는 중계기
 *
 * 왜 필요한가: 앱스 스크립트 웹앱은 POST에 대한 답을 다른 주소로 '이동(302)' 시켜서 주는데,
 *              카카오 스킬 호출은 이 이동을 따라가지 못해 'skill exec error'가 난다. 이 워커가 대신 따라가 준다.
 *
 * 환경 변수(Cloudflare 대시보드 > 이 워커 > Settings > Variables and Secrets):
 *   KAKAO_KEY        카카오 스킬 URL 끝에 붙일 비밀값 (예: ...workers.dev/?key=KAKAO_KEY)
 *   APPS_SCRIPT_URL  앱스 스크립트 웹 앱 URL (…/exec, ?key= 는 넣지 않는다)
 *   APPS_KEY         앱스 스크립트 속성 SECRET 과 같은 값
 */
export default {
  async fetch(request, env) {
    if (request.method !== 'POST') return new Response('중계 서버가 켜져 있어요.', { status: 200 });
    const url = new URL(request.url);
    if (!env.KAKAO_KEY || url.searchParams.get('key') !== env.KAKAO_KEY) {
      return new Response('forbidden', { status: 403 });
    }
    try {
      const body = await request.text();
      const target = env.APPS_SCRIPT_URL + (env.APPS_SCRIPT_URL.includes('?') ? '&' : '?') + 'key=' + encodeURIComponent(env.APPS_KEY);
      const res = await fetch(target, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        redirect: 'follow', // 구글의 302 이동을 여기서 따라간다
      });
      const text = await res.text();
      JSON.parse(text); // 카카오가 받을 수 있는 JSON인지 확인(아니면 아래에서 오류 안내로 바꿈)
      return new Response(text, { status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8' } });
    } catch (err) {
      const msg = { version: '2.0', template: { outputs: [{ simpleText: { text: '서버 연결에 문제가 있어요. 잠시 뒤 다시 시도해 주세요.' } }] } };
      return new Response(JSON.stringify(msg), { status: 200, headers: { 'Content-Type': 'application/json; charset=utf-8' } });
    }
  },
};
