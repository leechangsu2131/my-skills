import asyncio
import os
import sys
import io
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stdout') and hasattr(sys.stdout, 'buffer') else sys.stdout
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stderr') and hasattr(sys.stderr, 'buffer') else sys.stderr

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

from s2b_login import login as s2b_login
from s2b_search import search_items

async def explore_cart():
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
        items = await search_items(page, "A4용지")
        if not items:
            print("[ERROR] 검색 결과가 없습니다.")
            await browser.close()
            return

        first_item_id = items[0]['id']
        print(f"\n[STEP 3] 첫 번째 물품 상세 페이지 이동: {first_item_id}")
        
        # 상세 페이지 이동 로직 시뮬레이션 (새로운 탭 또는 팝업이 열릴 수 있음)
        try:
            async with page.expect_popup(timeout=3000) as popup_info:
                await page.evaluate(f"goViewPage('{first_item_id}');")
            new_page = await popup_info.value
            print("  [INFO] 새 창(팝업)으로 열렸습니다.")
        except Exception:
            # 타임아웃 발생 시 현재 페이지가 이동했을 것으로 간주
            new_page = page
            # 자바스크립트 실행은 이미 되었으므로 대기만 함
            print("  [INFO] 현재 창에서 이동했습니다.")
        await new_page.wait_for_load_state('domcontentloaded')
        await new_page.wait_for_timeout(3000)
        
        print(f"  [INFO] 상세 페이지 URL: {new_page.url}")
        
        # 스크린샷 및 소스 저장
        ss_path = os.path.join(SCRIPT_DIR, 'item_detail_page.png')
        await new_page.screenshot(path=ss_path, full_page=True)
        print(f"  [SCREENSHOT] 상세 페이지: {ss_path}")
        
        html_content = await new_page.content()
        html_path = os.path.join(SCRIPT_DIR, 'item_detail_page.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  [SAVED] 상세 페이지 소스: {html_path}")

        # 견적서 담기 관련 버튼 분석
        print("\n[ANALYSIS] 버튼 요소 파악 (견적서 담기)")
        buttons = await new_page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('a, button, input[type="button"], img').forEach(el => {
                const text = (el.textContent || el.alt || el.value || '').replace(/\s+/g, ' ').trim();
                const onclick = el.getAttribute('onclick') || '';
                const id = el.id || '';
                
                if (text.includes('견적') || text.includes('장바구니') || text.includes('담기') || onclick.includes('cart') || onclick.includes('Cart')) {
                    results.push({
                        text: text.substring(0, 30),
                        id: id,
                        onclick: onclick.substring(0, 80),
                        cls: el.className || ''
                    });
                }
            });
            return results;
        }''')
        
        for btn in buttons:
            print(f"  <{btn['id']}> class='{btn['cls']}' onclick='{btn['onclick']}' -> '{btn['text']}'")

        print("\n[WAIT] 10초 대기...")
        await new_page.wait_for_timeout(10000)
        await browser.close()
        print("\n[DONE] 탐색 완료!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(explore_cart())
