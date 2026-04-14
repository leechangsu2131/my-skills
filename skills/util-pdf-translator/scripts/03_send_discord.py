#!/usr/bin/env python3
"""
03_send_discord.py - 번역 결과를 Discord로 전송합니다.

사용법:
  python 03_send_discord.py --chapter 1    # 챕터 1 번역본 Discord 전송
"""

import json
import os
import sys
import argparse
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path(__file__).parent / "output"
TOC_PATH = Path(__file__).parent / "toc.json"
DISCORD_MAX_LEN = 1900  # Discord 메시지 한도 2000자 (여유 포함)


def load_toc() -> list[dict]:
    if not TOC_PATH.exists():
        return []
    with open(TOC_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_translated_text(chapter_num: int) -> str:
    file_path = OUTPUT_DIR / f"chapter_{str(chapter_num).zfill(2)}_translated.txt"
    if not file_path.exists():
        print(f"❌ 번역 파일이 없습니다: {file_path}")
        print("   먼저 02_gems_translate.js를 실행하세요.")
        sys.exit(1)
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def send_to_discord(webhook_url: str, content: str) -> bool:
    """Discord Webhook으로 메시지를 전송합니다."""
    payload = {"content": content}
    resp = requests.post(webhook_url, json=payload, timeout=10)
    if resp.status_code in (200, 204):
        return True
    print(f"  ⚠️  Discord 전송 실패 (HTTP {resp.status_code}): {resp.text}")
    return False


def split_message(text: str, max_len: int = DISCORD_MAX_LEN) -> list[str]:
    """긴 텍스트를 Discord 한도에 맞게 분할합니다."""
    chunks = []
    lines = text.split("\n")
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"

    if current.strip():
        chunks.append(current.strip())

    return chunks


def send_chapter(chapter_num: int, webhook_url: str) -> None:
    toc = load_toc()
    chapter = next((c for c in toc if c["chapter"] == chapter_num), None)
    title = chapter["title"] if chapter else f"Chapter {chapter_num}"
    emoji = os.getenv("CHAPTER_EMOJI", "📖")

    print(f"\n📤 Discord로 챕터 {chapter_num} '{title}' 전송 중...")

    text = load_translated_text(chapter_num)

    # 헤더 메시지
    header = (
        f"{emoji} **챕터 {chapter_num}: {title}**\n"
        f"{'─' * 40}"
    )
    send_to_discord(webhook_url, header)
    time.sleep(0.5)

    # 본문 분할 전송
    chunks = split_message(text)
    print(f"   총 {len(chunks)}개 메시지로 분할 전송")

    for i, chunk in enumerate(chunks, 1):
        success = send_to_discord(webhook_url, chunk)
        if success:
            print(f"   ✅ {i}/{len(chunks)} 전송 완료")
        else:
            print(f"   ❌ {i}/{len(chunks)} 전송 실패")
        time.sleep(0.5)  # Rate limit 방지

    print(f"\n✅ 챕터 {chapter_num} Discord 전송 완료!")


def main():
    parser = argparse.ArgumentParser(description="번역 결과 Discord 전송")
    parser.add_argument("--chapter", required=True, type=int, help="전송할 챕터 번호")
    parser.add_argument("--webhook", type=str, help="Discord Webhook URL (.env 대체)")
    args = parser.parse_args()

    webhook_url = args.webhook or os.getenv("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        print("❌ Discord Webhook URL이 없습니다. .env의 DISCORD_WEBHOOK_URL을 설정하세요.")
        sys.exit(1)

    send_chapter(args.chapter, webhook_url)


if __name__ == "__main__":
    main()
