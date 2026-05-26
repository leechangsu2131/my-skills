"""
S2B 로그인 페이지 HTML 구조 탐색 스크립트

.env 없이 S2B 로그인 페이지에 접속하여 HTML 구조를 분석합니다.
개인이용자 탭, 아이디/비밀번호 input, 로그인 버튼의 정확한 선택자를 파악합니다.
"""

import asyncio
import os
import sys
import io

# Windows CP949 인코딩 문제 해결
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

async def explore_login_page():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] playwright 미설치. pip install playwright && playwright install chromium")
        sys.exit(1)

    print("=" * 60)
    print("[INFO] S2B 학교장터 로그인 페이지 구조 탐색")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ko-KR',
        )
        page = await context.new_page()

        # 로그인 페이지 접속
        print("\n[STEP] S2B 로그인 페이지 접속 중...")
        await page.goto("https://www.s2b.kr/S2BNCustomer/Login.do",
                        wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        print(f"  URL: {page.url}")
        print(f"  제목: {await page.title()}")

        # 1. 전체 페이지 스크린샷
        ss_path = os.path.join(SCRIPT_DIR, 'explore_login_page.png')
        await page.screenshot(path=ss_path, full_page=True)
        print(f"\n[SCREENSHOT] 로그인 페이지: {ss_path}")

        # 2. 탭/메뉴 요소 탐색
        print("\n" + "=" * 60)
        print("[ANALYSIS] 탭/메뉴 요소 분석")
        print("=" * 60)

        tab_elements = await page.evaluate('''() => {
            const results = [];
            const selectors = ['a', 'button', 'li', 'span', 'div', 'label', 'input[type="radio"]', 'input[type="button"]'];
            for (const sel of selectors) {
                document.querySelectorAll(sel).forEach(el => {
                    const text = el.textContent?.trim() || '';
                    if (text && text.length < 40 && (
                        text.includes('개인') || text.includes('이용자') ||
                        text.includes('수요') || text.includes('기관') ||
                        text.includes('공급') || text.includes('업체') ||
                        text.includes('로그인') || text.includes('LOGIN') ||
                        text.includes('인증') || text.includes('탭') ||
                        text.includes('회원')
                    )) {
                        results.push({
                            tag: el.tagName,
                            id: el.id || '',
                            name: el.getAttribute('name') || '',
                            cls: (el.className || '').toString().substring(0, 60),
                            href: el.getAttribute('href') || '',
                            onclick: (el.getAttribute('onclick') || '').substring(0, 80),
                            type: el.getAttribute('type') || '',
                            text: text.substring(0, 50),
                            visible: el.offsetParent !== null || el.offsetHeight > 0,
                        });
                    }
                });
            }
            return results;
        }''')

        if tab_elements:
            for el in tab_elements:
                vis = "[V]" if el.get('visible') else "[H]"
                print(f"  {vis} <{el['tag']}> id='{el['id']}' class='{el['cls']}' "
                      f"onclick='{el['onclick'][:50]}' -> '{el['text']}'")
        else:
            print("  (탭/메뉴 요소를 찾지 못했습니다)")

        # 3. 입력 필드 탐색
        print("\n" + "=" * 60)
        print("[ANALYSIS] 입력 필드(input) 분석")
        print("=" * 60)

        inputs = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('input, select, textarea').forEach(el => {
                results.push({
                    tag: el.tagName,
                    type: el.getAttribute('type') || '',
                    name: el.getAttribute('name') || '',
                    id: el.id || '',
                    cls: (el.className || '').toString().substring(0, 50),
                    placeholder: el.getAttribute('placeholder') || '',
                    value: el.value?.substring(0, 30) || '',
                    visible: el.offsetParent !== null || el.offsetHeight > 0,
                    maxlength: el.getAttribute('maxlength') || '',
                });
            });
            return results;
        }''')

        if inputs:
            for inp in inputs:
                vis = "[V]" if inp.get('visible') else "[H]"
                print(f"  {vis} <{inp['tag']}> type='{inp['type']}' name='{inp['name']}' "
                      f"id='{inp['id']}' class='{inp['cls'][:40]}' "
                      f"placeholder='{inp['placeholder']}' maxlength='{inp['maxlength']}'")
        else:
            print("  (입력 필드를 찾지 못했습니다)")

        # 4. 버튼 요소 탐색
        print("\n" + "=" * 60)
        print("[ANALYSIS] 버튼 요소 분석")
        print("=" * 60)

        buttons = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('button, input[type="submit"], input[type="button"], a.btn, a[class*="btn"], [role="button"], a[onclick]').forEach(el => {
                const text = (el.textContent?.trim() || el.value || '').substring(0, 30);
                if (text) {
                    results.push({
                        tag: el.tagName,
                        id: el.id || '',
                        cls: (el.className || '').toString().substring(0, 50),
                        type: el.getAttribute('type') || '',
                        onclick: (el.getAttribute('onclick') || '').substring(0, 80),
                        href: (el.getAttribute('href') || '').substring(0, 60),
                        text: text,
                        visible: el.offsetParent !== null || el.offsetHeight > 0,
                    });
                }
            });
            return results;
        }''')

        if buttons:
            for btn in buttons:
                vis = "[V]" if btn.get('visible') else "[H]"
                print(f"  {vis} <{btn['tag']}> id='{btn['id']}' class='{btn['cls'][:40]}' "
                      f"onclick='{btn['onclick'][:50]}' -> '{btn['text']}'")
        else:
            print("  (버튼 요소를 찾지 못했습니다)")

        # 5. iframe 확인
        print("\n" + "=" * 60)
        print("[ANALYSIS] iframe 확인")
        print("=" * 60)

        iframes = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('iframe').forEach(el => {
                results.push({
                    src: el.src || '',
                    id: el.id || '',
                    name: el.getAttribute('name') || '',
                    cls: (el.className || '').toString().substring(0, 50),
                });
            });
            return results;
        }''')

        if iframes:
            for iframe in iframes:
                print(f"  <iframe> id='{iframe['id']}' name='{iframe['name']}' src='{iframe['src'][:80]}'")
        else:
            print("  (iframe 없음)")

        # 6. form 요소 확인
        print("\n" + "=" * 60)
        print("[ANALYSIS] form 요소 분석")
        print("=" * 60)

        forms = await page.evaluate('''() => {
            const results = [];
            document.querySelectorAll('form').forEach(el => {
                results.push({
                    id: el.id || '',
                    name: el.getAttribute('name') || '',
                    action: el.getAttribute('action') || '',
                    method: el.getAttribute('method') || '',
                    cls: (el.className || '').toString().substring(0, 50),
                });
            });
            return results;
        }''')

        if forms:
            for form in forms:
                print(f"  <form> id='{form['id']}' name='{form['name']}' "
                      f"action='{form['action']}' method='{form['method']}'")
        else:
            print("  (form 요소 없음)")

        # 7. 페이지 HTML 소스 저장
        html_content = await page.content()
        html_path = os.path.join(SCRIPT_DIR, 'login_page_source.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\n[SAVED] 페이지 소스: {html_path}")

        # 8. 개인이용자 탭 클릭 시도
        print("\n" + "=" * 60)
        print("[ACTION] '개인이용자' 관련 요소 클릭 시도")
        print("=" * 60)

        personal_clicked = False
        personal_selectors = [
            'text=개인이용자',
            'a:has-text("개인이용자")',
            'button:has-text("개인이용자")',
            'li:has-text("개인이용자")',
            'label:has-text("개인이용자")',
            'span:has-text("개인이용자")',
            'input[value*="개인"]',
            'text=개인',
            'a:has-text("개인")',
        ]

        for sel in personal_selectors:
            try:
                el = page.locator(sel)
                count = await el.count()
                if count > 0 and await el.first.is_visible():
                    print(f"  [FOUND] 선택자: {sel} (count={count})")
                    await el.first.click()
                    personal_clicked = True
                    await page.wait_for_timeout(2000)

                    # 클릭 후 스크린샷
                    ss2_path = os.path.join(SCRIPT_DIR, 'explore_after_personal_tab.png')
                    await page.screenshot(path=ss2_path, full_page=True)
                    print(f"  [SCREENSHOT] 탭 클릭 후: {ss2_path}")

                    # 클릭 후 visible 입력 필드 확인
                    inputs_after = await page.evaluate('''() => {
                        const results = [];
                        document.querySelectorAll('input').forEach(el => {
                            if (el.offsetParent !== null || el.offsetHeight > 0) {
                                results.push({
                                    type: el.getAttribute('type') || '',
                                    name: el.getAttribute('name') || '',
                                    id: el.id || '',
                                    placeholder: el.getAttribute('placeholder') || '',
                                });
                            }
                        });
                        return results;
                    }''')
                    print("  [AFTER CLICK] visible 입력 필드:")
                    for inp in inputs_after:
                        print(f"    type='{inp['type']}' name='{inp['name']}' "
                              f"id='{inp['id']}' placeholder='{inp['placeholder']}'")

                    # 클릭 후 페이지 소스도 저장
                    html2 = await page.content()
                    html2_path = os.path.join(SCRIPT_DIR, 'login_page_after_tab.html')
                    with open(html2_path, 'w', encoding='utf-8') as f:
                        f.write(html2)
                    print(f"  [SAVED] 탭 클릭 후 소스: {html2_path}")
                    break
            except Exception as e:
                continue

        if not personal_clicked:
            print("  [WARN] '개인이용자' 요소를 찾지 못했습니다. 수동으로 확인해주세요.")

        # 브라우저 유지 (10초)
        print("\n[WAIT] 10초간 브라우저 유지 (수동 확인 가능)...")
        await page.wait_for_timeout(10000)

        await browser.close()

    print("\n[DONE] 탐색 완료!")
    print(f"  스크린샷: {SCRIPT_DIR}")
    print(f"  HTML 소스: login_page_source.html")


if __name__ == "__main__":
    asyncio.run(explore_login_page())
