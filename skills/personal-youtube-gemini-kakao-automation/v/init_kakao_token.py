import json
import os

import requests
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    app_key = os.getenv("KAKAO_REST_API_KEY", "").strip()
    redirect_uri = os.getenv("KAKAO_REDIRECT_URI", "https://example.com").strip()
    auth_code = os.getenv("KAKAO_AUTH_CODE", "").strip()
    token_file = os.getenv("KAKAO_TOKEN_FILE", "./kakao_token.json").strip()
    disable_ssl_verify = os.getenv("DISABLE_SSL_VERIFY", "true").strip().lower() in {"1", "true", "yes", "y"}

    if not app_key:
        raise ValueError("KAKAO_REST_API_KEY is required")
    if not auth_code:
        raise ValueError("KAKAO_AUTH_CODE is required")

    response = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": app_key,
            "redirect_uri": redirect_uri,
            "code": auth_code,
        },
        timeout=20,
        verify=not disable_ssl_verify,
    )
    response.raise_for_status()
    payload = response.json()
    payload["app_key"] = app_key

    with open(token_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Saved token file: {token_file}")


if __name__ == "__main__":
    main()
