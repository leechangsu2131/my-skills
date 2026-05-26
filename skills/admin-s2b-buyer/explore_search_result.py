import asyncio
import os
import sys
import io
import urllib.parse
from dotenv import load_dotenv

# Windows CP949 인코딩 문제 해결
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from s2b_login import login as s2b_login

async def explore_search_result():
    load_dotenv(os.path.join(SCRIPT_DIR, '.env'))
    uid = os.getenv('S2B_USER_ID')
    pwd = os.getenv('S2B_USER_PW')

    if not uid or not pwd:
        print("[ERROR] .env 파일 설정 오류")
        sys.exit(1)

    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900}, locale='ko-KR')
        page = await context.new_page()

        print("[STEP 1] 로그인 진행 중...")
        login_success = await s2b_login(page, uid, pwd)
        if not login_success:
            await browser.close()
            return

        print("\n[STEP 2] 검색 실행 (A4용지)")
        query = "A4용지"
        
        # 메인 페이지 검색 로직 시뮬레이션
        search_input = '#estimateInfoMainSchKeyWord'
        search_btn = '#mainSearchButton'
        
        try:
            await page.wait_for_selector(search_input, state='visible', timeout=10000)
            await page.fill(search_input, query)
            await page.click(search_btn)
            print("  ✅ 검색버튼 클릭 완료")
        except Exception as e:
            print(f"  ⚠ 메인 페이지 검색 실패: {e}")
            # URL 직접 호출 백폴백
            query_encoded = urllib.parse.quote(query)
            search_url = f"https://www.s2b.kr/S2BNCustomer/S2B/scrweb/remu/rema/searchengine/s2bCustomerSearch.jsp?actionType=MAIN_SEARCH&searchField=&startIndex=&viewCount=50&viewType=LIST&sortField=RANK&priceMin=0&priceMax=0&priceMinSet=0&priceMaxSet=0&categoryLevel1Code=&categoryLevel2Code=&categoryLevel3Code=&categoryLevel3Name=&areaCode=&categoryWinStatus=none&companyCodeParam=&priceNewSet=true&publicPurchaseCode=&f_edufine_code=&submit_yn=Y&searchQuery={query_encoded}&searchRequery=&locationGbn="
            await page.goto(search_url)
            
        print("\n[STEP 3] 검색 결과 페이지 로딩 대기...")
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=15000)
        except:
            pass
        await page.wait_for_timeout(5000)
        
        # 스크린샷 및 소스 저장
        ss_path = os.path.join(SCRIPT_DIR, 'search_result_page.png')
        await page.screenshot(path=ss_path, full_page=True)
        print(f"  [SCREENSHOT] 검색 결과 페이지: {ss_path}")
        
        html_content = await page.content()
        html_path = os.path.join(SCRIPT_DIR, 'search_result_page.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  [SAVED] 검색 결과 소스: {html_path}")

        # 상품 링크 찾기 분석
        print("\n[ANALYSIS] 상품 링크 구조 파악")
        items = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('a').forEach(el => {
                const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
                const onclick = el.getAttribute('onclick') || '';
                const href = el.getAttribute('href') || '';
                
                // 물품명처럼 보이는 링크 추출 (보통 함수 호출이나 id 파라미터가 있음)
                if (text && text.length > 5 && (onclick.includes('detail') || onclick.includes('goGoods') || href.includes('goods'))) {
                    results.push({
                        text: text.substring(0, 50),
                        onclick: onclick.substring(0, 80),
                        href: href.substring(0, 80),
                        cls: el.className || ''
                    });
                }
            });
            return results;
        }''')
        
        for item in items[:20]:
            print(f"  <A> class='{item['cls']}' onclick='{item['onclick']}' href='{item['href']}' -> '{item['text']}'")

        await browser.close()
        print("\n[DONE] 탐색 완료!")

if __name__ == "__main__":
    asyncio.run(explore_search_result())
