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

    # 1. 페이지 상태에 따른 검색창/버튼 선택
    search_input = '#estimateInfoMainSchKeyWord'
    
    try:
        # 메인페이지 검색창 또는 결과페이지 검색창 대기
        is_main = await page.locator(search_input).is_visible()
        if not is_main:
            search_input = '#searchQuery'
            await page.wait_for_selector(search_input, state='visible', timeout=5000)
            
        # 검색어 입력
        await page.fill(search_input, query)
        
        # 검색 실행 (Enter 키 입력)
        async with page.expect_navigation(timeout=30000):
            await page.press(search_input, 'Enter')
            
        print("  ✅ 검색어 입력 및 이동 완료")
        
    except Exception as e:
        print(f"  ⚠ 검색 UI 사용 실패: {e}")
        print("  ℹ 직접 URL 호출 방식으로 재시도합니다.")
        
        # URL 직접 호출 백폴백
        query_encoded = urllib.parse.quote(query)
        search_url = f"https://www.s2b.kr/S2BNCustomer/S2B/scrweb/remu/rema/searchengine/s2bCustomerSearch.jsp?actionType=MAIN_SEARCH&searchQuery={query_encoded}"
        
        try:
            await page.goto(search_url, timeout=30000)
            print("  ✅ URL 직접 검색 이동 완료")
            search_input = '#searchQuery' # 이동 후에는 결과페이지 검색창 사용
        except Exception as ex:
            print(f"  ❌ 검색 페이지 이동 실패: {ex}")
            await page.screenshot(path=os.path.join(SCRIPT_DIR, 'search_error.png'), full_page=True)
            return []

    # 2. 검색 결과 페이지 로딩 대기
    item_link_selector = 'a[href^="javascript:goViewPage("]'
    try:
        # javascript:goViewPage(...) 링크가 나타날 때까지 대기
        await page.wait_for_selector(item_link_selector, state='attached', timeout=10000)
        await page.wait_for_timeout(2000) # DOM 안정화 대기
    except Exception as e:
        # 결과가 없고 검색어가 숫자(물품번호) 형태일 경우 S2B물품번호로 드롭다운 변경 후 재검색
        if query.replace('-', '').isdigit():
            print("  ℹ 검색 결과가 없습니다. 'S2B물품번호' 조건으로 재검색을 시도합니다.")
            try:
                # S2B물품번호 옵션을 가진 select 찾기
                select_locator = page.locator('select').filter(has_text='S2B물품번호').first
                await select_locator.select_option(label='S2B물품번호')
                
                # 검색어 다시 입력 및 클릭
                await page.fill(search_input, query)
                async with page.expect_navigation(timeout=30000):
                    await page.press(search_input, 'Enter')
                
                # 결과 대기
                await page.wait_for_selector(item_link_selector, state='attached', timeout=10000)
                await page.wait_for_timeout(2000)
            except Exception as ex:
                print(f"  ❌ S2B물품번호 재검색 후에도 결과를 찾을 수 없습니다: {ex}")
                return []
        else:
            print(f"  ❌ 검색 결과를 찾을 수 없거나 페이지 로딩 시간 초과: {e}")
            return []

    # 3. 검색 결과 파싱
    print("  📊 검색 결과 파싱 중...")
    items = await page.evaluate('''() => {
        const results = [];
        // 물품 체크박스(name="checkFlag")를 기준으로 각 행(tr)을 찾습니다.
        const checkboxes = document.querySelectorAll('input[name="checkFlag"]');
        
        checkboxes.forEach(chk => {
            const tr = chk.closest('tr');
            if (!tr) return;
            
            const itemId = chk.value;
            if (!itemId) return;
            
            // 이미지
            let image = '';
            const imgEl = tr.querySelector('img.detail_img');
            if (imgEl && imgEl.getAttribute('src')) {
                image = 'https://www.s2b.kr' + imgEl.getAttribute('src');
            }
            
            // 제목
            let title = '';
            const titleA = tr.querySelector('.obj_name .l01 a');
            if (titleA) {
                title = titleA.textContent.replace(/\\s+/g, ' ').trim();
            }
            
            // 가격
            let price = '';
            const priceLi = tr.querySelector('.lt_mulpumprice li:first-child');
            if (priceLi) {
                price = priceLi.textContent.trim();
            }
            
            // 링크 (S2B 특성상 세션 연동이 필요할 수 있으나 유추된 팝업 주소 제공)
            const link = 'https://www.s2b.kr/S2BNCustomer/S2B/scrweb/remu/rema/search/estimateInfoSchMain.jsp?param_value=' + itemId;
            
            // 중복 방지
            if (!results.find(r => r.id === itemId)) {
                results.push({
                    id: itemId,
                    title: title,
                    price: price,
                    image: image,
                    link: link
                });
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
        queries = ["초시계", "202604067720487", "202603107266074", "202410149686835"]
        
        for query in queries:
            print(f"\\n--- 테스트: '{query}' ---")
            items = await search_items(page, query)
            if items:
                print(f"✅ 검색 테스트 성공! 찾은 항목 수: {len(items)}")
            else:
                print(f"❌ 검색 테스트 실패 (결과 없음)")
            await page.wait_for_timeout(2000)

        await page.wait_for_timeout(3000)
        await browser.close()

if __name__ == "__main__":
    import io
    # Windows CP949 인코딩 문제 방지
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stdout') and hasattr(sys.stdout, 'buffer') else sys.stdout
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stderr') and hasattr(sys.stderr, 'buffer') else sys.stderr
    
    asyncio.run(run_search_test())
