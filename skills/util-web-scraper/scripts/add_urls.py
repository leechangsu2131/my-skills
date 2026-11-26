"""
add_urls.py - URL을 config.json에 추가하고 즉시 스크래핑 + 인덱싱 실행
사용법: python add_urls.py --urls "https://사이트A.com" "https://사이트B.com"
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import load_env

load_env()  # 중앙 .env 의 UTIL_WEB_SCRAPER__EDUSEARCH_DIR 가 있으면 EDUSEARCH_DIR 로 읽힘


def find_edusearch_dir():
    """EduSearch 폴더 위치.
    1) 중앙 .env 의 UTIL_WEB_SCRAPER__EDUSEARCH_DIR (또는 환경변수 EDUSEARCH_DIR)
    2) 없으면 my-skills 저장소 폴더의 옆 폴더 `edusearch` (GitHub 폴더 위치가 PC 마다 달라도 같은 GitHub 폴더 밑에 나란히 있으므로)
    """
    configured = os.environ.get("EDUSEARCH_DIR", "").strip()
    if configured:
        return os.path.normpath(os.path.expanduser(os.path.expandvars(configured)))
    repo_root = pathlib.Path(__file__).resolve().parents[3]  # scripts → util-web-scraper → skills → my-skills
    return str(repo_root.parent / "edusearch")


EDUSEARCH_DIR = find_edusearch_dir()
CONFIG_PATH = os.path.join(EDUSEARCH_DIR, "config.json")


def check_edusearch_dir():
    """EduSearch 폴더가 없으면 설치 방법을 알리고 종료한다."""
    if not os.path.isdir(EDUSEARCH_DIR):
        print(f"[ERROR] EduSearch 폴더를 찾을 수 없습니다: {EDUSEARCH_DIR}")
        print("  → my-skills 와 같은 GitHub 폴더 안에 받아 두세요: git clone https://github.com/leechangsu2131/edusearch")
        print("  → 다른 곳에 있으면 중앙 .env 에 UTIL_WEB_SCRAPER__EDUSEARCH_DIR=<폴더 경로> 를 적으세요.")
        sys.exit(1)


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

    check_edusearch_dir()
    added = add_urls(args.urls, use_selenium=args.selenium)

    if added and not args.no_run:
        run_scraper_and_indexer()
