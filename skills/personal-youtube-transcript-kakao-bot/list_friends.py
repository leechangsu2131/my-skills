"""친구 목록과 uuid를 보여준다. main.py와 같은 .env를 사용한다.

사용법
  py list_friends.py          친구 목록과 uuid 확인
  py list_friends.py --test   .env의 KAKAO_FRIEND_UUIDS로 테스트 메시지 보내기 (나 + 친구)

사전 조건: .env의 KAKAO_REFRESH_TOKEN이 '내' 계정으로 scope=talk_message,friends 동의 후 발급받은 토큰일 것.
(친구의 토큰은 필요 없다. 친구는 앱 멤버가 되고 동의만 하면 된다.)
"""
import sys

import requests

import main  # .env 로드와 토큰 갱신 함수를 재사용

token = main.kakao_access_token()
r = requests.get(
    "https://kapi.kakao.com/v1/api/talk/friends",
    headers={"Authorization": f"Bearer {token}"},
    params={"limit": 100},
    timeout=30,
)
print("상태 코드:", r.status_code)
data = r.json()
if r.status_code != 200:
    print(data)  # 오류 코드(-402 권한/동의 부족 등)를 확인
    raise SystemExit(1)

elements = data.get("elements", [])
print(f"친구 {data.get('total_count', len(elements))}명")
for e in elements:
    print(f"{e.get('profile_nickname')}\t{e.get('uuid')}\t수신가능={e.get('allowed_msg')}")

if not elements:
    print("응답 원문:", data)
    print(
        "목록이 비어 있음. 확인할 것:\n"
        " 1) .env의 KAKAO_REFRESH_TOKEN이 '내 계정'으로 발급한 최신 토큰인지 (친구 토큰 아님)\n"
        " 2) 친구가 멤버 목록에서 '활성'이고, 같은 계정으로 동의 주소(scope=talk_message,friends)에서 친구 목록 제공까지 동의했는지\n"
        " 3) 카톡에서 서로 친구인지, 숨김/차단이 아닌지"
    )

if "--test" in sys.argv:
    if not main.FRIEND_UUIDS:
        print(".env에 KAKAO_FRIEND_UUIDS가 없어 테스트를 건너뜁니다. 위 목록의 uuid를 넣어주세요.")
        raise SystemExit(1)
    main.kakao_send(token, "[테스트] 자막 알림 봇 테스트 메시지입니다.", "https://www.youtube.com")
    print(f"테스트 메시지 전송 시도 완료 (나 + 친구 {len(main.FRIEND_UUIDS)}명). 실패 시 위에 '친구에게 보내기 실패'가 출력됩니다.")
