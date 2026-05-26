import asyncio
import os
import sys
import io
from dotenv import load_dotenv

# Windows CP949 인코딩 문제 해결
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# S2B 로그인 함수 가져오기
from s2b_login import login as s2b_login

async def explore_search_page():
    load_dotenv(os.path.join(SCRIPT_DIR, '.env'))
    uid = os.getenv('S2B_USER_ID')
    pwd = os.getenv('S2B_USER_PW')

    if not uid or not pwd:
        print("[ERROR] .env 파일에 S2B_USER_ID와 S2B_USER_PW가 설정되지 않았습니다.")
        sys.exit(1)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] playwright 미설치.")
        sys.exit(1)

    print("=" * 60)
    print("[INFO] S2B 학교장터 메인 페이지 및 검색창 탐색")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ko-KR',
        )
        page = await context.new_page()

        print("\n[STEP 1] 로그인 진행 중...")
        # 실제 계정으로 로그인 수행 (비밀번호 노출 방지)
        login_success = await s2b_login(page, uid, pwd)
        
        if not login_success:
            print("[ERROR] 로그인에 실패하여 탐색을 중단합니다.")
            await browser.close()
            return

        print("\n[STEP 2] 로그인 후 메인 페이지 로드 대기 (5초)...")
        await page.wait_for_timeout(5000)
        
        print(f"  URL: {page.url}")
        print(f"  제목: {await page.title()}")

        # 팝업이 있을 수 있으므로 단순 닫기 시도 (여러 패턴)
        try:
            popups = await page.locator('text=오늘 하루 보지 않기').count()
            if popups > 0:
                print(f"  [INFO] 팝업창 {popups}개 감지됨. 닫기 시도...")
                for i in range(popups):
                    await page.locator('text=오늘 하루 보지 않기').nth(i).click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        # 1. 전체 페이지 스크린샷
        ss_path = os.path.join(SCRIPT_DIR, 'after_login_main.png')
        await page.screenshot(path=ss_path, full_page=True)
        print(f"\n[SCREENSHOT] 로그인 후 메인 페이지: {ss_path}")

        # 2. 검색창 입력 필드 탐색
        print("\n" + "=" * 60)
        print("[ANALYSIS] 입력 필드(input) 분석 (검색창 찾기)")
        print("=" * 60)

        inputs = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('input[type="text"]').forEach(el => {
                if (el.offsetParent !== null || el.offsetHeight > 0) { // 보이는 요소만
                    results.push({
                        id: el.id || '',
                        name: el.getAttribute('name') || '',
                        cls: (el.className || '').toString().substring(0, 50),
                        placeholder: el.getAttribute('placeholder') || '',
                        title: el.getAttribute('title') || '',
                    });
                }
            });
            return results;
        }''')

        if inputs:
            for inp in inputs:
                print(f"  <input> id='{inp['id']}' name='{inp['name']}' placeholder='{inp['placeholder']}' title='{inp['title']}' class='{inp['cls']}'")
        else:
            print("  (입력 필드를 찾지 못했습니다)")

        # 3. 검색 버튼 탐색
        print("\n" + "=" * 60)
        print("[ANALYSIS] 검색 관련 버튼 분석")
        print("=" * 60)

        buttons = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('a, button, input[type="button"], input[type="image"], input[type="submit"], img').forEach(el => {
                const text = (el.textContent?.trim() || el.value || el.alt || '').substring(0, 30);
                const isSearch = text.includes('검색') || 
                                 text.includes('search') || 
                                 (el.id || '').toLowerCase().includes('search') || 
                                 (el.className || '').toString().toLowerCase().includes('search');
                                 
                if (isSearch && (el.offsetParent !== null || el.offsetHeight > 0)) {
                    results.push({
                        tag: el.tagName,
                        id: el.id || '',
                        cls: (el.className || '').toString().substring(0, 50),
                        text: text,
                        onclick: (el.getAttribute('onclick') || '').substring(0, 80)
                    });
                }
            });
            return results;
        }''')

        if buttons:
            for btn in buttons:
                print(f"  <{btn['tag']}> id='{btn['id']}' class='{btn['cls']}' onclick='{btn['onclick'][:50]}' -> '{btn['text']}'")
        else:
            print("  (검색 버튼을 찾지 못했습니다)")

        # 페이지 소스 저장
        html_content = await page.content()
        html_path = os.path.join(SCRIPT_DIR, 'main_page_source.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\n[SAVED] 메인 페이지 소스: {html_path}")

        print("\n[WAIT] 10초간 브라우저 유지 (수동 확인 가능)...")
        await page.wait_for_timeout(10000)

        await browser.close()
        print("\n[DONE] 탐색 완료!")

if __name__ == "__main__":
    asyncio.run(explore_search_page())
