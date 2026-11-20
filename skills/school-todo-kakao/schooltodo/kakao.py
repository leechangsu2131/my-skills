"""카카오 '나에게 보내기'. 토큰 갱신 방식은 기존 main.py와 같다(새 리프레시 토큰이 오면 파일로 남긴다)."""
from __future__ import annotations

import json
from pathlib import Path

import requests

OAUTH_URL = "https://kauth.kakao.com/oauth/token"
MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


class KakaoError(RuntimeError):
    pass


def _describe(resp: requests.Response) -> str:
    """오류 코드와 설명만 뽑는다. 응답 전체나 토큰은 공개 로그에 남기지 않는다."""
    try:
        j = resp.json()
    except ValueError:
        j = {}
    code = j.get("error_code", j.get("code", ""))
    msg = j.get("error_description", j.get("msg", ""))
    hint = " (리프레시 토큰 만료: 카카오 로그인으로 새로 발급하세요)" if str(code) == "KOE322" else ""
    return f"HTTP {resp.status_code} {code} {msg}{hint}".strip()


def refresh_access_token(
    rest_api_key: str,
    refresh_token: str,
    client_secret: str = "",
    new_refresh_token_file: str | None = None,
) -> str:
    data = {"grant_type": "refresh_token", "client_id": rest_api_key, "refresh_token": refresh_token}
    if client_secret:
        data["client_secret"] = client_secret
    r = requests.post(OAUTH_URL, data=data, timeout=30)
    if not r.ok:
        raise KakaoError("토큰 갱신 실패: " + _describe(r))
    j = r.json()
    # 만료 1달 전부터는 새 리프레시 토큰이 함께 온다. 워크플로가 Secrets에 다시 저장한다.
    if j.get("refresh_token") and new_refresh_token_file:
        Path(new_refresh_token_file).write_text(j["refresh_token"])
    return j["access_token"]


def send_memo(access_token: str, text: str, link_url: str, button_title: str = "일정DB 열기") -> None:
    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": link_url, "mobile_web_url": link_url},
        "button_title": button_title,
    }
    r = requests.post(
        MEMO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=30,
    )
    if not r.ok:
        raise KakaoError("카톡 전송 실패: " + _describe(r))


FRIENDS_URL = "https://kapi.kakao.com/v1/api/talk/friends/message/default/send"


def send_friends(access_token: str, uuids: list[str], text: str, link_url: str, button_title: str = "일정DB 열기") -> None:
    """친구에게 보내기(최대 5명). 받는 사람이 같은 카카오 앱에 동의한 친구여야 한다."""
    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": link_url, "mobile_web_url": link_url},
        "button_title": button_title,
    }
    r = requests.post(
        FRIENDS_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"receiver_uuids": json.dumps(uuids), "template_object": json.dumps(template, ensure_ascii=False)},
        timeout=30,
    )
    if not r.ok:
        raise KakaoError("친구에게 보내기 실패: " + _describe(r))
    j = r.json()
    if j.get("failure_info"):  # 일부 수신자만 실패한 경우
        codes = {str(f.get("code")) for f in j["failure_info"]}
        raise KakaoError(f"친구 {len(j['failure_info'])}명에게 전달 실패 (코드 {', '.join(sorted(codes))})")


FRIENDS_LIST_URL = "https://kapi.kakao.com/v1/api/talk/friends"


def list_friends(access_token: str) -> list[dict]:
    """카카오 친구 목록(이 앱에 동의한 친구만): [{'name': 별명, 'uuid': 고유번호}]. 한 번에 최대 100명."""
    r = requests.get(
        FRIENDS_LIST_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"limit": 100},
        timeout=30,
    )
    if not r.ok:
        raise KakaoError("친구 목록 조회 실패: " + _describe(r))
    return [
        {"name": f.get("profile_nickname", ""), "uuid": f.get("uuid", ""), "id": str(f.get("id", ""))}
        for f in r.json().get("elements", [])
    ]
