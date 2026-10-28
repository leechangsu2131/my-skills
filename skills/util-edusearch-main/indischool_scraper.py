"""
indischool_scraper.py - 인디스쿨 자동 로그인 + 검색 + 수집
사용법:
  python indischool_scraper.py --query "감각적 표현 시감상 3학년" --pages 3
  python indischool_scraper.py --query "감각적 표현 시감상 3학년" --pages 3 --show   ← 브라우저 보면서 실행
"""

import os
import time
import sqlite3
import argparse
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

load_dotenv()

# ── 설정 ──────────────────────────────────────────
INDISCHOOL_ID = os.getenv("INDISCHOOL_ID")
INDISCHOOL_PW = os.getenv("INDISCHOOL_PW")
DB_PATH       = "data.db"

LOGIN_URL  = "https://indischool.com/login"
SEARCH_URL = "https://indischool.com/search?query={query}&page={page}"


# ── DB 초기화 ──────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT,
            url        TEXT UNIQUE,
            keywords   TEXT,
            summary    TEXT,
            site       TEXT,
            scraped_at TEXT
        )
    """)
    conn.commit()
    return conn


# ── 드라이버 준비 (Selenium Manager 자동 ChromeDriver 다운로드) ──
def get_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--lang=ko-KR")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=options)
    return driver


# ── 로그인 ─────────────────────────────────────────
def login(driver):
    print("[1/3] 인디스쿨 로그인 중...")
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 10)

    try:
        # 확인된 필드명: username / password
        wait.until(EC.presence_of_element_located((By.ID, "username")))
        driver.find_element(By.ID, "username").clear()
        driver.find_element(By.ID, "username").send_keys(INDISCHOOL_ID)
        driver.find_element(By.ID, "password").clear()
        driver.find_element(By.ID, "password").send_keys(INDISCHOOL_PW)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(3)

        # 로그인 성공 확인 (URL이 /login이 아니면 성공)
        if "/login" not in driver.current_url:
            print(f"  ✅ 로그인 성공 (현재: {driver.current_url})")
            return True
        else:
            print("  ❌ 로그인 실패 — .env의 INDISCHOOL_ID/INDISCHOOL_PW 확인")
            return False

    except TimeoutException:
        print("  ❌ 로그인 페이지 로딩 실패 (타임아웃)")
        return False


# ── 검색 결과 한 페이지 수집 ───────────────────────
def scrape_one_page(driver, query, page):
    url = SEARCH_URL.format(query=query, page=page)
    driver.get(url)
    time.sleep(2)

    results = []

    # 인디스쿨 검색결과: /boards/{게시판}/{번호} 패턴 링크
    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/boards/']")

    for link in links:
        try:
            href  = link.get_attribute("href") or ""
            title = link.text.strip()

            # 짧거나 비어있는 항목 스킵
            if not href or len(title) < 3:
                continue

            # 요약: 부모 요소 텍스트에서 제목 제거
            try:
                parent_text = link.find_element(By.XPATH, "..").text.strip()
                summary = parent_text[:300] if parent_text else title
            except Exception:
                summary = title

            results.append({
                "title":    title[:150],
                "url":      href,
                "keywords": query,
                "summary":  summary[:500],
                "site":     "indischool.com",
            })
        except Exception:
            continue

    # 중복 URL 제거
    seen = set()
    deduped = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            deduped.append(r)

    return deduped


# ── 전체 페이지 수집 ───────────────────────────────
def scrape_search_results(driver, query, max_pages=3):
    print(f"[2/3] '{query}' 검색 중... ({max_pages}페이지)")
    all_results = []

    for page in range(1, max_pages + 1):
        page_results = scrape_one_page(driver, query, page)
        all_results.extend(page_results)
        print(f"  페이지 {page}: {len(page_results)}개 수집 (누적 {len(all_results)}개)")

        if not page_results:
            print("  → 결과 없음, 중단")
            break

        time.sleep(3)  # 속도 제한

    return all_results


# ── DB 저장 ────────────────────────────────────────
def save_to_db(conn, results):
    print(f"[3/3] DB 저장 중...")
    saved = 0
    scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for r in results:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO pages (title, url, keywords, summary, site, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (r["title"], r["url"], r["keywords"], r["summary"], r["site"], scraped_at))
            saved += 1
        except Exception:
            pass

    conn.commit()
    return saved


# ── 메인 ───────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="인디스쿨 자동 수집기")
    parser.add_argument("--query", default="감각적 표현 시감상 3학년", help="검색어")
    parser.add_argument("--pages", type=int, default=3, help="수집할 페이지 수")
    parser.add_argument("--show", action="store_true", help="브라우저 창 표시 (디버그용)")
    args = parser.parse_args()

    if not INDISCHOOL_ID or not INDISCHOOL_PW:
        print("❌ .env 파일에 INDISCHOOL_ID, INDISCHOOL_PW를 입력하세요.")
        print("   copy .env.example .env  →  메모장으로 열어서 입력")
        return

    print(f"검색어: {args.query}")
    print(f"페이지: {args.pages}페이지")
    print("-" * 40)

    conn = init_db()
    driver = get_driver(headless=not args.show)

    try:
        if not login(driver):
            return

        results = scrape_search_results(driver, args.query, args.pages)

        if results:
            saved = save_to_db(conn, results)
            print(f"\n✅ 완료: {saved}개 수집됨")
            print("\n수집된 자료 미리보기:")
            for r in results[:5]:
                print(f"  • {r['title'][:60]}")
                print(f"    {r['url']}")
            print("\n다음 단계:")
            print("  python indexer.py      ← 인덱스 생성")
            print("  python search_app.py   ← 검색앱 실행 후 localhost:5000")
        else:
            print("\n⚠️  수집된 자료가 없습니다.")
            print("   --show 옵션으로 브라우저를 보면서 확인해보세요:")
            print(f"   python indischool_scraper.py --query \"{args.query}\" --show")

    finally:
        driver.quit()
        conn.close()


if __name__ == "__main__":
    main()
