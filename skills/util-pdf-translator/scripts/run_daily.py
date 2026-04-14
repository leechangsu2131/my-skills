#!/usr/bin/env python3
"""
run_daily.py - 일일 챕터 번역 + Discord 전송 원클릭 실행

사용법:
  python run_daily.py --chapter 1    # 챕터 1 전체 자동 실행

실행 순서:
  1. PDF에서 챕터 텍스트 추출
  2. Playwright로 Gems 번역 (Node.js 호출)
  3. Discord로 전송
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = Path(__file__).parent


def run(cmd: list[str], desc: str) -> bool:
    print(f"\n{'='*50}")
    print(f"▶ {desc}")
    print(f"{'='*50}")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    if result.returncode != 0:
        print(f"\n❌ 단계 실패: {desc}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="일일 챕터 번역 자동화")
    parser.add_argument("--chapter", required=True, type=int, help="번역할 챕터 번호")
    parser.add_argument("--skip-extract", action="store_true",
                        help="텍스트 추출 건너뜀 (이미 추출된 경우)")
    parser.add_argument("--skip-translate", action="store_true",
                        help="번역 건너뜀 (이미 번역된 경우)")
    args = parser.parse_args()

    chapter = args.chapter
    print(f"\n🚀 챕터 {chapter} 번역 파이프라인 시작!")

    # Step 1: 텍스트 추출
    if not args.skip_extract:
        ok = run(
            [sys.executable, "extract_chapter.py", "--chapter", str(chapter)],
            f"Step 1/3: 챕터 {chapter} 텍스트 추출"
        )
        if not ok:
            sys.exit(1)
    else:
        print("\n⏭️  Step 1 건너뜀 (--skip-extract)")

    # Step 2: Gems 번역 (Node.js)
    if not args.skip_translate:
        node_cmd = ["node", "02_gems_translate.js", "--chapter", str(chapter)]
        ok = run(node_cmd, f"Step 2/3: Gems 자동 번역")
        if not ok:
            sys.exit(1)
    else:
        print("\n⏭️  Step 2 건너뜀 (--skip-translate)")

    # Step 3: Discord 전송
    ok = run(
        [sys.executable, "03_send_discord.py", "--chapter", str(chapter)],
        f"Step 3/3: Discord 전송"
    )
    if not ok:
        sys.exit(1)

    print(f"\n🎉 챕터 {chapter} 완료! Discord 채널을 확인하세요.")


if __name__ == "__main__":
    main()
