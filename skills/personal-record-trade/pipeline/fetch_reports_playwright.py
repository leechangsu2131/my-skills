import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

env_path = Path(r'C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade\.env')
load_dotenv(env_path)

if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

def extract_text_with_playwright(url: str) -> str:
    print(f"   [Playwright] 접속 중: {url}")
    text_content = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=15000)
            # 불필요한 요소 제거 (광고, 스크립트 등)
            page.evaluate('''() => {
                document.querySelectorAll('script, style, noscript, iframe, img, svg').forEach(el => el.remove());
            }''')
            # 본문 텍스트 추출
            text_content = page.evaluate('document.body.innerText')
            browser.close()
    except Exception as e:
        print(f"   ❌ Playwright 추출 에러: {e}")
    return text_content

def fetch_google_news_playwright(ticker: str, company_name: str):
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("❌ SERPAPI_KEY가 .env 파일에 없습니다.")
        return
        
    # PDF 검색이 아닌 웹/뉴스 검색으로 변경
    query = f'"{company_name}" (목표주가 OR 투자의견 OR 리포트)'
    print(f"🔍 SerpApi 웹 검색 시작: {query} (API 호출 1건 차감 예상)")
    
    params = {
        "engine": "google",
        "q": query,
        "tbm": "nws", # 뉴스 탭 검색을 통해 정확도 향상 (혹은 일반 검색)
        "tbs": "qdr:m6", # 최근 6개월
        "num": 5, # 상위 5개만 추출 (Playwright 속도 고려)
        "api_key": api_key
    }
    
    try:
        resp = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"🚨 SerpApi 호출 실패: {e}")
        return

    # 뉴스 결과 파싱
    results = data.get("news_results", [])
    if not results:
        # 뉴스 결과가 없으면 일반 오가닉 결과 사용
        results = data.get("organic_results", [])[:5]
        
    unique_links = {res.get("link"): res.get("title", "article") for res in results if "link" in res}
    print(f"📑 SerpApi에서 {len(unique_links)}개의 웹/뉴스 링크를 찾았습니다.")
    
    root_dir = Path(__file__).parent.parent
    report_dir = root_dir / "data" / "report_web" / ticker
    report_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for i, (url, title) in enumerate(unique_links.items()):
        safe_title = "".join(c for c in title[:50] if c.isalnum() or c in " _-").strip()
        if not safe_title:
            safe_title = f"web_report_{i+1}"
            
        print(f"\n[{i+1}] {title}")
        content = extract_text_with_playwright(url)
        
        if content and len(content.strip()) > 100:
            # 본문에 회사명이나 티커가 있는지 간단 검증
            if company_name in content or ticker in content:
                filename = f"{safe_title}.txt"
                save_path = report_dir / filename
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(f"Title: {title}\nURL: {url}\n\n")
                    f.write(content)
                print(f"   ✅ 데이터 추출 및 저장 완료: {save_path.name}")
                count += 1
            else:
                print(f"   🗑️ 검증 실패 (본문에 사명 없음)")
        else:
            print("   🗑️ 추출된 텍스트가 너무 짧거나 없습니다.")
            
    print(f"\n🎉 총 {count}개의 유효한 웹 리서치 자료가 {report_dir}에 저장되었습니다.")

if __name__ == "__main__":
    fetch_google_news_playwright("033500", "동성화인텍")
