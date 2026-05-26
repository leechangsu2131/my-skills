"""
S2B 학교장터 - 견적서(장바구니) 담기 모듈
"""

import asyncio
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

async def add_to_cart(page, item_id, quantity=1, dry_run=False):
    """
    특정 물품을 지정된 수량만큼 견적서(장바구니)에 담습니다.

    Args:
        page: Playwright page 객체 (로그인 완료 상태여야 함)
        item_id: 담을 물품의 G2B목록번호 (예: 202407159099092)
        quantity: 수량 (기본값 1)
        dry_run: 실제 담기를 수행하지 않고 상세 페이지까지만 시뮬레이션

    Returns:
        bool: 성공 여부
    """
    print(f"🛒 견적서 담기 시작: 물품번호 [{item_id}], 수량 [{quantity}]")
    
    # 1. 물품 상세 페이지로 직접 이동 (URL 패턴 사용)
    detail_url = f"https://www.s2b.kr/S2BNCustomer/rema100.do?forwardName=detail&f_re_estimate_code={item_id}"
    
    try:
        await page.goto(detail_url, timeout=30000)
        await page.wait_for_load_state('domcontentloaded')
        # 수량 입력창이 뜰 때까지 대기
        await page.wait_for_selector('#qnt', state='visible', timeout=10000)
    except Exception as e:
        print(f"  ❌ 물품 상세 페이지 로딩 실패: {e}")
        return False
        
    print(f"  📄 상세 페이지 이동 완료. 수량 입력 중: {quantity}")
    
    # 2. 수량 설정
    try:
        await page.fill('#qnt', str(quantity))
    except Exception as e:
        print(f"  ❌ 수량 입력 실패: {e}")
        return False
        
    if dry_run:
        print("  ℹ [DRY-RUN] 실제 견적서에 담지 않고 종료합니다.")
        return True
        
    # 3. 견적서에 담기 (fnSave() 실행)
    print("  📦 장바구니에 담는 중 (fnSave 실행)...")
    try:
        # 알림창이 뜰 수 있으므로 자동 수락 처리
        def handle_dialog(dialog):
            try:
                # 이미 처리된 다이얼로그 오류 무시
                asyncio.create_task(dialog.accept())
            except Exception:
                pass
        
        # 다이얼로그 리스너 등록
        page.on("dialog", handle_dialog)
        
        # fnSave()는 새로운 팝업창을 열고 장바구니 처리를 함
        # 팝업 대기
        async with page.expect_popup(timeout=15000) as cart_popup_info:
            await page.evaluate("fnSave();")
            
        cart_popup = await cart_popup_info.value
        await cart_popup.wait_for_load_state('domcontentloaded')
        
        # 서버 처리 시간 대기
        await cart_popup.wait_for_timeout(3000)
        await cart_popup.close()
        
        print(f"  ✅ 장바구니(견적서) 담기 성공!")
        success = True
    except Exception as e:
        print(f"  ❌ 장바구니 담기 팝업 대기 실패: {e}")
        print("  (팝업 차단이 해제되어 있는지 확인하세요. 또는 일시적 오류일 수 있습니다.)")
        success = False
    finally:
        # 핸들러 정리
        try:
            page.remove_listener("dialog", handle_dialog)
        except:
            pass
            
    return success

# =====================================================
# 단독 실행 (견적서 담기 테스트)
# =====================================================
async def run_cart_test():
    """견적서 담기 모듈 단독 테스트"""
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

        print("\\n2. 견적서 담기 테스트 (dry_run=True)...")
        # 실제 담기를 하지 않고 UI까지만 조작하는 dry_run 모드 테스트
        # 테스트용 물품 ID: 202407159099092 (A4용지)
        item_id = "202407159099092"
        success = await add_to_cart(page, item_id, quantity=2, dry_run=True)
        
        if success:
            print("\\n✅ 견적서 담기 테스트 성공 (dry_run)!")
        else:
            print("\\n❌ 견적서 담기 테스트 실패")

        await page.wait_for_timeout(3000)
        await browser.close()

if __name__ == "__main__":
    import io
    # Windows CP949 인코딩 문제 방지
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stdout') and hasattr(sys.stdout, 'buffer') else sys.stdout
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace') if hasattr(sys, 'stderr') and hasattr(sys.stderr, 'buffer') else sys.stderr
    
    asyncio.run(run_cart_test())
