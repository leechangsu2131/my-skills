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

async def test_add_to_cart():
    load_dotenv(os.path.join(SCRIPT_DIR, '.env'))
    uid = os.getenv('S2B_USER_ID')
    pwd = os.getenv('S2B_USER_PW')

    if not uid or not pwd:
        sys.exit(1)

    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900}, locale='ko-KR')
        page = await context.new_page()

        # 다이얼로그(alert, confirm 등) 자동 처리
        page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))

        print("1. 로그인")
        await s2b_login(page, uid, pwd)

        print("2. 물품 검색")
        items = await search_items(page, "A4용지")
        if not items:
            await browser.close()
            return
            
        first_item = items[0]
        print(f"3. 물품 상세 접속: {first_item['id']}")
        
        try:
            async with page.expect_popup(timeout=3000) as popup_info:
                await page.evaluate(f"goViewPage('{first_item['id']}');")
            new_page = await popup_info.value
        except:
            new_page = page
            
        await new_page.wait_for_load_state('domcontentloaded')
        new_page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
        await new_page.wait_for_timeout(2000)

        print("4. 수량 변경 및 장바구니(견적) 담기")
        try:
            await new_page.fill('#qnt', '2')
            
            print("  fnSave() 실행...")
            # fnSave()는 새로운 팝업을 띄우고 그쪽으로 submit함
            try:
                async with new_page.expect_popup(timeout=10000) as cart_popup_info:
                    await new_page.evaluate("fnSave();")
                cart_popup = await cart_popup_info.value
                await cart_popup.wait_for_load_state('domcontentloaded')
                print(f"  [SUCCESS] 장바구니 팝업 열림: {cart_popup.url}")
                await cart_popup.wait_for_timeout(3000)
                
                # 팝업 스크린샷
                await cart_popup.screenshot(path=os.path.join(SCRIPT_DIR, 'cart_popup.png'), full_page=True)
                
                # 팝업을 닫음
                await cart_popup.close()
            except Exception as e:
                print(f"  [WARN] 팝업 대기 중 오류: {e}")
                
        except Exception as e:
            print(f"  [ERROR] 장바구니 담기 실패: {e}")

        print("5. 테스트 종료")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_add_to_cart())
