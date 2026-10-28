"""
nanuri_scraper.py - 수업나누리 수집기 (수동 로그인 방식)
사용법: python nanuri_scraper.py --query "감각적 표현 시감상 3학년" --pages 3

실행하면 브라우저가 열립니다 → 직접 로그인 → 터미널에서 Enter → 수집 시작
"""

import os, re, time, sqlite3, argparse
from datetime import datetime
from urllib.parse import urlencode
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

load_dotenv()
DB_PATH   = "data.db"
BASE_URL  = "http://nanuri.gyo6.net"
LOGIN_URL = f"{BASE_URL}/login/login.tc"
LIST_URL  = f"{BASE_URL}/board/list.tc"
DETAIL_URL= f"{BASE_URL}/board/detail.tc"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, url TEXT UNIQUE,
            keywords TEXT, summary TEXT,
            site TEXT, scraped_at TEXT
        )
    """)
    conn.commit()
    return conn


def get_driver():
    """브라우저 창이 보이는 Selenium 드라이버"""
    options = Options()
    options.add_argument("--window-size=1280,900")
    options.add_argument("--lang=ko-KR")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def wait_for_login(driver):
    """사용자가 직접 로그인할 때까지 기다림"""
    driver.get(LOGIN_URL)
    print("\n" + "="*50)
    print("  브라우저가 열렸습니다.")
    print("  수업나누리에 로그인해 주세요.")
    print("  로그인 완료 후 여기서 Enter를 누르세요.")
    print("="*50)
    input("  [로그인 완료 후 Enter] > ")

    # 로그인 확인
    if "login" in driver.current_url:
        # 아직 로그인 페이지면 한번 더 확인
        print("  아직 로그인 페이지입니다. 로그인 후 Enter를 눌러주세요.")
        input("  [다시 Enter] > ")

    print(f"  현재 URL: {driver.current_url}")
    return True


def scrape_list_page(driver, query, page):
    """목록 페이지에서 boardNo 수집"""
    # 사용자가 성공을 확인했던 타이핑(화면에 값 채우기) 방식입니다.
    # url 파라미터로 값을 넘기면 화면의 검색창에 문자가 박히게 됩니다.
    params = f"mn=1042&mngNo=6&searchKeyword={query}&pageIndex={page}"
    driver.get(f"{LIST_URL}?{params}")
    time.sleep(2)
    
    # [핵심 수정] 값은 세팅되었으나 조회(서치) 액션이 발생하지 않았다는 사용자 진단에 따라 전송 액션 단 1줄 추가
    try:
        driver.execute_script("document.getElementById('form1').submit();")
        time.sleep(2)
    except Exception:
        pass

    page_source = driver.page_source
    board_nos = re.findall(r"selectBoardDetail\s*\(\s*'(\d+)'\s*\)", page_source)
    board_nos = list(dict.fromkeys(board_nos))  # 중복 제거

    # 제목도 같이 추출 (가능하면)
    titles = {}
    soup = BeautifulSoup(page_source, "html.parser")
    for a in soup.find_all("a", onclick=True):
        m = re.search(r"selectBoardDetail\s*\(\s*'(\d+)'\s*\)", a.get("onclick", ""))
        if m:
            txt = a.get_text(strip=True)
            if txt:
                titles[m.group(1)] = txt

    return board_nos, titles


def scrape_detail(driver, board_no, query):
    """상세 페이지에서 제목/본문 수집"""
    detail_url = f"{DETAIL_URL}?mn=1042&mngNo=6&boardNo={board_no}"
    driver.get(detail_url)
    time.sleep(1.5)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 제목 추출 시도 (여러 패턴)
    title_el = (
        soup.find(class_=re.compile(r"subject|title|board-title|view-title", re.I)) or
        soup.find("h3") or soup.find("h4") or soup.find("h2")
    )
    title = title_el.get_text(strip=True) if title_el else f"수업나누리 {board_no}"

    # 본문 요약
    content_el = soup.find(class_=re.compile(r"content|view|board-view|view-content", re.I))
    summary = content_el.get_text(strip=True)[:500] if content_el else title

    return {
        "title":    title[:150],
        "url":      detail_url,
        "keywords": query,
        "summary":  summary,
        "site":     "nanuri.gyo6.net",
    }


def scrape_all(driver, query, max_pages=3):
    print(f"\n수집 시작: '{query}' ({max_pages}페이지)")
    all_results = []

    for page in range(1, max_pages + 1):
        board_nos, titles = scrape_list_page(driver, query, page)

        if not board_nos:
            print(f"  페이지 {page}: 결과 없음, 중단")
            break

        page_results = []
        for board_no in board_nos:
            result = scrape_detail(driver, board_no, query)
            # 목록 제목이 있으면 우선 사용
            if board_no in titles and titles[board_no]:
                result["title"] = titles[board_no][:150]
            page_results.append(result)
            time.sleep(1)

        all_results.extend(page_results)
        print(f"  페이지 {page}: {len(page_results)}개 수집 (누적 {len(all_results)}개)")
        time.sleep(3)

    return all_results


def save_to_db(conn, results):
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


def main():
    parser = argparse.ArgumentParser(description="수업나누리 수집기 (수동 로그인)")
    parser.add_argument("--query", default="감각적 표현 시감상 3학년")
    parser.add_argument("--pages", type=int, default=3)
    args = parser.parse_args()

    conn = init_db()
    driver = get_driver()

    try:
        wait_for_login(driver)
        results = scrape_all(driver, args.query, args.pages)

        if results:
            saved = save_to_db(conn, results)
            print(f"\n[완료] {saved}개 수집됨")
            print("미리보기:")
            for r in results[:5]:
                print(f"  - {r['title'][:60]}")
            print("\n다음 단계: python indexer.py")
        else:
            print("\n[경고] 수집된 자료 없음")
    finally:
        driver.quit()
        conn.close()


if __name__ == "__main__":
    main()
