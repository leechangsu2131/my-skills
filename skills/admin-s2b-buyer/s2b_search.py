"""
S2B 학교장터 - 물품 검색 모듈
"""

import asyncio
import os
import sys
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

async def search_items(page, query):
    """
    S2B에서 물품을 검색하고 검색 결과 목록을 반환합니다.

    Args:
        page: Playwright page 객체 (로그인 완료 상태여야 함)
        query: 검색할 물품명 (예: "A4용지")

    Returns:
        list: 검색된 물품 정보 딕셔너리 리스트
              [{'title': '...', 'id': '...', 'price': '...'}, ...]
    """
    print(f"🔍 물품 검색 시작: '{query}'")

    # 1. 메인 페이지 검색창 이용
    search_input = '#estimateInfoMainSchKeyWord'
    search_btn = '#mainSearchButton'

    try:
        # 검색창이 보일 때까지 대기
        await page.wait_for_selector(search_input, state='visible', timeout=10000)
        
        # 검색어 입력
        await page.fill(search_input, query)
        
        # 검색 버튼 클릭
        # navigation을 동시에 기다림
        async with page.expect_navigation(timeout=30000):
            await page.click(search_btn)
            
        print("  ✅ 검색어 입력 및 이동 완료")
        
    except Exception as e:
        print(f"  ⚠ 메인 페이지 검색 UI 사용 실패: {e}")
        print("  ℹ 직접 URL 호출 방식으로 재시도합니다.")
        
        # URL 직접 호출 백폴백
        # S2B는 간혹 euc-kr 인코딩을 사용할 수 있으나 기본 utf-8 시도
        query_encoded = urllib.parse.quote(query)
        search_url = f"https://www.s2b.kr/S2BNCustomer/S2B/scrweb/remu/rema/searchengine/s2bCustomerSearch.jsp?actionType=MAIN_SEARCH&searchQuery={query_encoded}"
        
        try:
            await page.goto(search_url, timeout=30000)
            print("  ✅ URL 직접 검색 이동 완료")
        except Exception as ex:
            print(f"  ❌ 검색 페이지 이동 실패: {ex}")
            await page.screenshot(path=os.path.join(SCRIPT_DIR, 'search_error.png'), full_page=True)
            return []

    # 2. 검색 결과 페이지 로딩 대기
    try:
        # javascript:goViewPage(...) 링크가 나타날 때까지 대기
        item_link_selector = 'a[href^="javascript:goViewPage("]'
        await page.wait_for_selector(item_link_selector, state='attached', timeout=15000)
        await page.wait_for_timeout(2000) # DOM 안정화 대기
    except Exception as e:
        print(f"  ❌ 검색 결과를 찾을 수 없거나 페이지 로딩 시간 초과: {e}")
        await page.screenshot(path=os.path.join(SCRIPT_DIR, 'search_no_results.png'), full_page=True)
        return []

    # 3. 검색 결과 파싱
    print("  📊 검색 결과 파싱 중...")
    items = await page.evaluate('''() => {
        const results = [];
        // 물품 상세 페이지로 이동하는 링크들을 모두 찾음
        const links = document.querySelectorAll('a[href^="javascript:goViewPage("]');
        
        links.forEach(link => {
            const href = link.getAttribute('href');
            // href="javascript:goViewPage('202407159099092');" 에서 ID 추출
            const match = href.match(/'([^']+)'/);
            const itemId = match ? match[1] : '';
            
            if (itemId) {
                // 부모 요소들을 거슬러 올라가서 가격 정보 등을 찾을 수 있지만,
                // 우선은 링크 텍스트 자체(상품명 + 규격)를 가져옴
                let title = link.textContent.replace(/\\s+/g, ' ').trim();
                
                // 중복 추가 방지
                if (!results.find(r => r.id === itemId)) {
                    results.push({
                        id: itemId,
                        title: title
                    });
                }
            }
        });
        return results;
    }''')

    print(f"  ✅ 총 {len(items)}개의 물품을 찾았습니다.")
    for idx, item in enumerate(items[:5]):  # 상위 5개만 출력
        print(f"    {idx+1}. [{item['id']}] {item['title'][:50]}...")

    return items


# =====================================================
# 단독 실행 (검색 테스트)
# =====================================================
async def run_search_test():
    """검색 모듈 단독 테스트"""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(SCRIPT_DIR, '.env'))
    uid = os.getenv('S2B_USER_ID')
    pwd = os.getenv('S2B_USER_PW')

    if not uid or not pwd:
        print("❌ S2B_USER_ID, S2B_USER_PW 환경변수가 필요합니다.")
        sys.exit(1)

    try:
        from playwright.async_api import async_playwright
        from s2b_login import login as s2b_login
    except ImportError:
        print("❌ playwright 모듈 또는 s2b_login 모듈을 찾을 수 없습니다.")
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900}, locale='ko-KR')
        page = await context.new_page()

        print("1. 로그인 진행...")
        login_success = await s2b_login(page, uid, pwd)
        if not login_success:
            print("❌ 로그인 실패")
            await browser.close()
            return

        print("\\n2. 물품 검색 테스트...")
        query = "A4용지"
        items = await search_items(page, query)
        
        if items:
            print("\\n✅ 검색 테스트 성공!")
            print(f"첫 번째 물품 선택: {items[0]}")
        else:
            print("\\n❌ 검색 테스트 실패 (결과 없음)")

        await page.wait_for_timeout(3000)
        await browser.close()

if __name__ == "__main__":
    # Windows CP949 인코딩 문제 방지
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stdout') and hasattr(sys.stdout, 'buffer') else sys.stdout
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stderr') and hasattr(sys.stderr, 'buffer') else sys.stderr
    
    import io
    asyncio.run(run_search_test())
