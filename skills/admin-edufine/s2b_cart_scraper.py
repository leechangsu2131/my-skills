import asyncio
import os
import sys
import importlib

# admin-s2b-buyer의 로그인 모듈을 재사용하기 위해 path 추가
S2B_PATH = r'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\admin-s2b-buyer'
if S2B_PATH not in sys.path:
    sys.path.insert(0, S2B_PATH)

from dotenv import load_dotenv

async def get_s2b_cart_items():
    """
    S2B 사이트에 로그인하여 장바구니(견적서 접수 목록)의 품목들을 추출합니다.
    Returns:
        list of dict: [{"name": "...", "quantity": "...", "unit_price": "..."}, ...]
    """
    # 매번 최신 s2b_login 코드를 로드
    import s2b_login as _s2b_login_mod
    importlib.reload(_s2b_login_mod)
    s2b_do_login = _s2b_login_mod.login

    load_dotenv(os.path.join(S2B_PATH, '.env'))
    uid = os.getenv('S2B_USER_ID')
    pwd = os.getenv('S2B_USER_PW')

    if not uid or not pwd:
        print("[ERROR] S2B 계정 정보가 .env에 없습니다.")
        return []

    from playwright.async_api import async_playwright
    browser = None
    p = None
    try:
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 900}, locale='ko-KR')
        page = await context.new_page()

        print("[S2B Scraper] 로그인 진행 중...")
        login_success = await s2b_do_login(page, uid, pwd)
        if not login_success:
            print("[S2B Scraper] 로그인 실패")
            return []
        
        print("[S2B Scraper] 장바구니(견적서 접수 목록) 이동 중...")
        await page.goto("https://www.s2b.kr/S2BNCustomer/remc100.do?forwardName=estimateList")
        await page.wait_for_load_state('domcontentloaded')
        await page.wait_for_timeout(2000)
        
        print("[S2B Scraper] 품목 분석 중...")
        items = await page.evaluate(r'''() => {
            const results = [];
            const checkboxes = document.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(cb => {
                const tr = cb.closest('tr');
                if (tr) {
                    const tds = tr.querySelectorAll('td');
                    const aTag = tr.querySelector('a');
                    if (aTag && tds.length > 5) {
                        let name = aTag.innerText.trim();
                        // 이름에 포함된 [규격: 어쩌고] 또는 줄바꿈 등 지저분한 텍스트 제거
                        name = name.replace(/\[규격.*?\]/g, '').replace(/\(수량:.*?\)/g, '').trim();
                        name = name.split('\n')[0].trim(); // 첫 줄만 물품명으로 사용
                        
                        // 수량
                        const qtyInput = tr.querySelector('input[name*="qty"]' ) || tr.querySelector('input[type="text"]');
                        let qty = '';
                        if (qtyInput) qty = qtyInput.value;
                        
                        // 제시금액
                        let price = '';
                        tds.forEach(td => {
                            const text = td.innerText.replace(/,/g, '').replace(/원/g, '').trim();
                            // 숫자만 있고 100 이상인 경우 금액일 확률이 높음 (수량은 보통 작음)
                            if (/^\d+$/.test(text) && parseInt(text) > 100) {
                                if (!price) price = text;
                            }
                        });
                        
                        if (name && name !== "구분") {
                            results.push({ name, quantity: qty, unit_price: price });
                        }
                    }
                }
            });
            return results;
        }''')
        
        print(f"[S2B Scraper] 총 {len(items)}개 품목 발견.")
        return items
    except Exception as e:
        print(f"[S2B Scraper] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        if p:
            try:
                await p.stop()
            except Exception:
                pass

if __name__ == "__main__":
    res = asyncio.run(get_s2b_cart_items())
    print(res)

