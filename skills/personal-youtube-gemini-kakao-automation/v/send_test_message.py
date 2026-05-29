# -*- coding: utf-8 -*-
"""Send a UTF-8 test message to Discord (scheduler connectivity check)."""
from datetime import datetime

from main import load_settings, send_discord_message


def main() -> None:
    settings = load_settings()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"[스케줄러 테스트] {now} - ChesleyMorningBrief 동작 확인 (한글 인코딩 정상)"
    response = send_discord_message(settings, message)
    print("status", response.status_code)
    if response.status_code not in (200, 204):
        raise SystemExit(response.text)


if __name__ == "__main__":
    main()
