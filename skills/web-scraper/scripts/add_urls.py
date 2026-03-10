"""
add_urls.py - URL을 config.json에 추가하고 즉시 스크래핑 + 인덱싱 실행
사용법: python add_urls.py --urls "https://사이트A.com" "https://사이트B.com"
"""

import argparse
import json
import os
import subprocess
import sys

EDUSEARCH_DIR = r"C:\Users\lee21\Documents\GitHub\edusearch"
CONFIG_PATH = os.path.join(EDUSEARCH_DIR, "config.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def add_urls(urls, use_selenium=False):
    config = load_config()
    existing_urls = {item["url"] for item in config.get("target_sites", [])}

    added = []
    for url in urls:
        if url in existing_urls:
            print(f"[SKIP] 이미 있음: {url}")
        else:
            config["target_sites"].append({"url": url, "use_selenium": use_selenium})
            existing_urls.add(url)
            added.append(url)
            print(f"[추가] {url}")

    if added:
        save_config(config)
        print(f"\n✅ {len(added)}개 URL 추가됨 → config.json 저장")
    else:
        print("\n변경 없음.")

    return added


def run_scraper_and_indexer():
    print("\n[1/2] 스크래핑 실행 중...")
    result = subprocess.run(
        [sys.executable, "scraper.py"],
        cwd=EDUSEARCH_DIR
    )
    if result.returncode != 0:
        print("[ERROR] scraper.py 실패")
        return

    print("\n[2/2] 인덱스 재생성 중...")
    subprocess.run(
        [sys.executable, "indexer.py"],
        cwd=EDUSEARCH_DIR
    )
    print("\n✅ 완료! http://localhost:5000 에서 검색 가능")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="URL을 EduSearch에 추가하고 수집")
    parser.add_argument("--urls", nargs="+", required=True, help="추가할 URL 목록")
    parser.add_argument("--selenium", action="store_true", help="동적 페이지 (Selenium 사용)")
    parser.add_argument("--no-run", action="store_true", help="추가만 하고 스크래핑은 하지 않음")
    args = parser.parse_args()

    added = add_urls(args.urls, use_selenium=args.selenium)

    if added and not args.no_run:
        run_scraper_and_indexer()
