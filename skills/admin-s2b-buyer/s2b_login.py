"""
S2B 학교장터 - 개인이용자 로그인 모듈

경주시립도서관 희망도서 신청(request_books.py) 패턴을 벤치마킹하여
S2B 학교장터 개인이용자 로그인을 자동화합니다.

사용법:
    python s2b_login.py              # 로그인 테스트 (브라우저 열림)
    python s2b_login.py --headless   # 헤드리스 모드
    python s2b_login.py --screenshot # 로그인 후 스크린샷 저장
"""

import os
import sys
import asyncio
import argparse

# =====================================================
# .env 파일에서 환경변수 로드 (request_books.py 패턴)
# =====================================================
def load_env():
    """스크립트와 같은 디렉토리의 .env 파일에서 환경변수를 로드합니다."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, val = line.partition('=')
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

load_env()

# =====================================================
# 설정값
# =====================================================
S2B_USER_ID = os.environ.get('S2B_USER_ID', '')
S2B_USER_PW = os.environ.get('S2B_USER_PW', '')

# S2B URL
S2B_BASE_URL = "https://www.s2b.kr"
S2B_LOGIN_URL = "https://www.s2b.kr/S2BNCustomer/Login.do"
S2B_MAIN_URL = "https://www.s2b.kr/S2BNCustomer/S2B/"

# 스크린샷 저장 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# =====================================================
# 로그인 함수
# =====================================================
async def login(page, user_id=None, user_pw=None):
    """
    S2B 학교장터 개인이용자 로그인

    Args:
        page: Playwright page 객체
        user_id: S2B 아이디 (None이면 환경변수 사용)
        user_pw: S2B 비밀번호 (None이면 환경변수 사용)

    Returns:
        bool: 로그인 성공 여부
    """
    uid = user_id or S2B_USER_ID
    pwd = user_pw or S2B_USER_PW

    if not uid or not pwd:
        print("[ERROR] S2B 계정 정보가 설정되지 않았습니다.")
        print("   .env 파일에 S2B_USER_ID, S2B_USER_PW를 설정해주세요.")
        return False

    try:
        # 1. 로그인 페이지 접속
        print(f"[WEB] S2B 로그인 페이지 접속 중...")
        await page.goto(S2B_LOGIN_URL, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)  # 페이지 완전 로딩 대기

        print(f"   현재 URL: {page.url}")
        print(f"   페이지 제목: {await page.title()}")

        # 2. 개인이용자 탭 선택
        print(f" 개인이용자 탭 클릭...")
        tab_selector = 'ul.tabs a[href="#prlogin"]'
        
        try:
            await page.click(tab_selector)
            print("  [SUCCESS] 개인이용자 탭 클릭 성공")
            await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"  ⚠ 개인이용자 탭 클릭 실패: {e}")
            await _debug_page_elements(page)
            await page.screenshot(path=os.path.join(SCRIPT_DIR, 'login_page_debug.png'), full_page=True)
            return False

        # 3. 아이디/비밀번호 입력
        print(f" 로그인 정보 입력 중... (ID: {uid[:2]}***)")
        
        # 개인_loginForm 내부의 input 찾기
        id_selector = 'form[name="personal_loginForm"] input[name="uid"]'
        pw_selector = 'form[name="personal_loginForm"] input[name="pwd"]'
        
        try:
            await page.fill(id_selector, uid)
            print("  [SUCCESS] 아이디 입력 완료")
        except Exception as e:
            print(f"  [ERROR] 아이디 입력 실패: {e}")
            await page.screenshot(path=os.path.join(SCRIPT_DIR, 'login_id_field_debug.png'), full_page=True)
            return False

        try:
            await page.fill(pw_selector, pwd)
            print("  [SUCCESS] 비밀번호 입력 완료")
        except Exception as e:
            print(f"  [ERROR] 비밀번호 입력 실패: {e}")
            await page.screenshot(path=os.path.join(SCRIPT_DIR, 'login_pw_field_debug.png'), full_page=True)
            return False

        # 4. 로그인 버튼 클릭
        print(f"️ 로그인 버튼 클릭 중...")
        login_btn_selector = 'form[name="personal_loginForm"] .btn_login a'
        
        try:
            await page.click(login_btn_selector)
            print("  [SUCCESS] 로그인 버튼 클릭 완료")
        except Exception as e:
            print(f"  [ERROR] 로그인 버튼 클릭 실패: {e}")
            await page.screenshot(path=os.path.join(SCRIPT_DIR, 'login_button_debug.png'), full_page=True)
            return False

        # 5. 로그인 결과 확인
        try:
            await page.wait_for_load_state('domcontentloaded', timeout=15000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)

        current_url = page.url
        page_title = await page.title()
        print(f"   로그인 후 URL: {current_url}")
        print(f"   로그인 후 제목: {page_title}")

        # 로그인 성공 판별 (여러 조건)
        if 'pwd_changeinfo.jsp' in current_url:
            print("   [INFO] 비밀번호 변경 안내 페이지 감지. 메인 페이지로 강제 이동 시도...")
            await page.goto(S2B_MAIN_URL, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            current_url = page.url

        # 실패: 로그인 페이지에 여전히 있는 경우
        if 'Login.do' in current_url or 'login' in current_url.lower():
            # 에러 메시지 확인
            error_msg = await _get_error_message(page)
            if error_msg:
                print(f"  [ERROR] 로그인 실패: {error_msg}")
            else:
                print(f"  [ERROR] 로그인 실패: 로그인 페이지에서 벗어나지 못했습니다.")

            debug_path = os.path.join(SCRIPT_DIR, 'login_failed.png')
            await page.screenshot(path=debug_path, full_page=True)
            print(f"   실패 스크린샷 저장: {debug_path}")
            return False

        print(f"  [SUCCESS] 로그인 성공!")
        return True

    except Exception as e:
        print(f"[ERROR] 로그인 중 오류 발생: {e}")
        try:
            debug_path = os.path.join(SCRIPT_DIR, 'login_error.png')
            await page.screenshot(path=debug_path, full_page=True)
            print(f"   오류 스크린샷 저장: {debug_path}")
        except Exception:
            pass
        return False


async def _get_error_message(page):
    """로그인 실패 시 에러 메시지 추출 시도"""
    error_selectors = [
        '.error_msg',
        '.err_msg',
        '.alert_msg',
        '#error_message',
        '.login_error',
        'p.error',
        'span.error',
    ]
    for selector in error_selectors:
        try:
            el = page.locator(selector)
            if await el.count() > 0:
                text = await el.first.inner_text()
                if text.strip():
                    return text.strip()
        except Exception:
            continue
    return None


async def _debug_page_elements(page):
    """디버깅: 페이지의 주요 요소들을 출력합니다."""
    print("\n  === 페이지 디버그 정보 ===")

    # 탭/메뉴처럼 보이는 요소
    try:
        tabs = await page.query_selector_all('a, button, li, [role="tab"]')
        tab_texts = []
        for tab in tabs[:30]:  # 최대 30개만
            text = await tab.inner_text()
            tag = await tab.evaluate('el => el.tagName')
            href = await tab.get_attribute('href') or ''
            onclick = await tab.get_attribute('onclick') or ''
            classes = await tab.get_attribute('class') or ''
            if text.strip() and len(text.strip()) < 30:
                tab_texts.append(f"    <{tag}> class='{classes}' href='{href}' onclick='{onclick[:50]}' → '{text.strip()}'")

        if tab_texts:
            print("   클릭 가능한 요소들:")
            for t in tab_texts[:15]:
                print(t)
    except Exception as e:
        print(f"  ⚠ 요소 스캔 실패: {e}")

    # input 필드들
    try:
        inputs = await page.query_selector_all('input')
        if inputs:
            print("   입력 필드들:")
            for inp in inputs[:15]:
                input_type = await inp.get_attribute('type') or 'text'
                name = await inp.get_attribute('name') or '(없음)'
                input_id = await inp.get_attribute('id') or '(없음)'
                placeholder = await inp.get_attribute('placeholder') or ''
                visible = await inp.is_visible()
                print(f"    type='{input_type}' name='{name}' id='{input_id}' placeholder='{placeholder}' visible={visible}")
    except Exception as e:
        print(f"  ⚠ 입력 필드 스캔 실패: {e}")

    print("  === 디버그 정보 끝 ===\n")


# =====================================================
# 단독 실행 (로그인 테스트)
# =====================================================
async def run_login_test(headless=False, take_screenshot=False):
    """로그인 테스트 실행"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] playwright가 설치되지 않았습니다.")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    print("=" * 55)
    print(" S2B 학교장터 - 로그인 테스트")
    print("=" * 55)

    async with async_playwright() as p:
        # Chromium 브라우저 실행 (크롬 기반)
        browser = await p.chromium.launch(
            headless=headless,
            slow_mo=500,  # 동작을 느리게 하여 확인 가능
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ko-KR',
        )
        page = await context.new_page()

        # 로그인 시도
        success = await login(page)

        if success and take_screenshot:
            screenshot_path = os.path.join(SCRIPT_DIR, 'login_success.png')
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f" 로그인 성공 스크린샷 저장: {screenshot_path}")

        if success:
            print("\n[SUCCESS] 로그인 테스트 성공!")
            print(f"  현재 URL: {page.url}")

            # 로그인 후 잠시 대기 (확인용)
            if not headless:
                print("  ℹ 브라우저를 5초간 유지합니다 (확인 후 자동 종료)...")
                await page.wait_for_timeout(5000)
        else:
            print("\n[ERROR] 로그인 테스트 실패!")
            print("  ℹ 다음 사항을 확인해주세요:")
            print("    1. .env 파일에 S2B_USER_ID, S2B_USER_PW가 올바르게 설정되었는지")
            print("    2. 개인이용자 탭이 정상적으로 선택되었는지")
            print("    3. login_page_debug.png 스크린샷 확인")

        await browser.close()
        return success


def main():
    parser = argparse.ArgumentParser(
        description='S2B 학교장터 개인이용자 로그인 테스트'
    )
    parser.add_argument('--headless', action='store_true',
                        help='헤드리스 모드 (브라우저 창 안 보임)')
    parser.add_argument('--screenshot', action='store_true',
                        help='로그인 성공 후 스크린샷 저장')
    args = parser.parse_args()

    success = asyncio.run(run_login_test(
        headless=args.headless,
        take_screenshot=args.screenshot,
    ))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
