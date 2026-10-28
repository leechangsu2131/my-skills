"""
scraper.py - 개인용 웹 스크래퍼
사용법: python scraper.py
       python scraper.py --selenium  (동적/로그인 페이지용)
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import argparse
import json
import os
from datetime import datetime
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

# ──────────────────────────────────────────
# 설정 (config.json 없을 시 기본값 사용)
# ──────────────────────────────────────────
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "target_sites": [
        # 아래에 실제 스크래핑할 사이트 URL을 추가하세요
        # {"url": "https://example.com/page1", "use_selenium": False},
        # {"url": "https://example.com/page2", "use_selenium": True},
    ],
    "delay_seconds": 5,
    "max_summary_chars": 1000,
    "user_agent": "MyPersonalSearchBot/1.0 (Personal use only)",
    "chromedriver_path": "/usr/local/bin/chromedriver",
    "db_path": "data.db"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # 기본 config.json 생성
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
        print(f"[INFO] config.json 생성됨. URL을 추가하고 다시 실행하세요.")
        return DEFAULT_CONFIG


# ──────────────────────────────────────────
# DB 초기화
# ──────────────────────────────────────────
def init_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            title    TEXT,
            url      TEXT UNIQUE,
            keywords TEXT,
            summary  TEXT,
            site     TEXT,
            scraped_at TEXT
        )
    ''')
    conn.commit()
    return conn


# ──────────────────────────────────────────
# robots.txt 확인
# ──────────────────────────────────────────
def can_fetch(url, user_agent):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        allowed = rp.can_fetch(user_agent, url)
        if not allowed:
            print(f"  [BLOCKED] robots.txt에 의해 차단됨: {url}")
        return allowed
    except Exception:
        return True  # robots.txt 없으면 허용으로 간주


# ──────────────────────────────────────────
# 정적 페이지 스크래핑 (requests + BeautifulSoup)
# ──────────────────────────────────────────
def scrape_static(url, headers):
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding  # 한국어 인코딩 자동 감지

    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.title.string.strip() if soup.title else "제목 없음"

    # 메타 키워드
    meta_kw = soup.find("meta", attrs={"name": "keywords"})
    keywords = meta_kw.get("content", "") if meta_kw else ""

    # 메타 설명
    meta_desc = soup.find("meta", attrs={"name": "description"})
    description = meta_desc.get("content", "") if meta_desc else ""

    # 본문 텍스트 추출 (불필요한 태그 제거)
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    body_text = " ".join(soup.get_text(separator=" ").split())

    summary = (description + " " + body_text)[:1000]

    return title, keywords, summary


# ──────────────────────────────────────────
# 동적 페이지 스크래핑 (Selenium)
# ──────────────────────────────────────────
def scrape_dynamic(url, chromedriver_path):
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
    except ImportError:
        raise ImportError("selenium이 설치되지 않았습니다: pip install selenium")

    options = Options()
    options.add_argument("--headless")          # 창 없이 실행
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        time.sleep(3)  # JS 렌더링 대기

        title = driver.title

        # 메타 키워드
        keywords = ""
        metas = driver.find_elements(By.XPATH, '//meta[@name="keywords"]')
        if metas:
            keywords = metas[0].get_attribute("content") or ""

        # 본문 요약
        body = driver.find_element(By.TAG_NAME, "body")
        summary = body.text[:1000]

        return title, keywords, summary
    finally:
        driver.quit()


# ──────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="개인용 웹 스크래퍼")
    parser.add_argument("--url", help="단일 URL 스크래핑 (config 무시)")
    parser.add_argument("--selenium", action="store_true", help="Selenium 사용")
    args = parser.parse_args()

    config = load_config()
    conn = init_db(config["db_path"])
    c = conn.cursor()
    headers = {"User-Agent": config["user_agent"]}

    # URL 목록 결정
    if args.url:
        url_list = [{"url": args.url, "use_selenium": args.selenium}]
    else:
        url_list = config["target_sites"]

    if not url_list:
        print("[INFO] 스크래핑할 URL이 없습니다.")
        print("       config.json의 target_sites에 URL을 추가하거나")
        print("       --url 옵션으로 직접 지정하세요.")
        print("       예: python scraper.py --url https://example.com")
        return

    success, fail = 0, 0

    for item in url_list:
        url = item.get("url", "")
        use_selenium = item.get("use_selenium", False)

        print(f"\n[처리중] {url}")

        # robots.txt 확인
        if not can_fetch(url, config["user_agent"]):
            fail += 1
            continue

        try:
            if use_selenium:
                title, keywords, summary = scrape_dynamic(url, config["chromedriver_path"])
            else:
                title, keywords, summary = scrape_static(url, headers)

            site = urlparse(url).netloc
            scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            c.execute("""
                INSERT OR REPLACE INTO pages (title, url, keywords, summary, site, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, url, keywords, summary, site, scraped_at))
            conn.commit()

            print(f"  [OK] '{title[:50]}...' 저장 완료")
            success += 1

        except Exception as e:
            print(f"  [ERROR] {e}")
            fail += 1

        time.sleep(config["delay_seconds"])  # 속도 제한

    conn.close()
    print(f"\n완료: 성공 {success}건 / 실패 {fail}건")
    print("다음 단계: python indexer.py 실행")


if __name__ == "__main__":
    main()
