"""
iscream_evaluate.py — i-scream 교과 세부능력 및 특기사항 자동 입력 모듈

Playwright async API를 사용하여 사용자의 Chrome 브라우저(CDP)에 연결한 뒤,
i-scream 학생평가 페이지에서 과목별 학생 평가를 자동으로 입력합니다.

사용법:
    python iscream_evaluate.py --dry-run              # 시뮬레이션 실행 (저장 안 함)
    python iscream_evaluate.py --preview               # 미리보기 후 확인 대기
    python iscream_evaluate.py --student 김민준         # 특정 학생만 처리
    python iscream_evaluate.py --subject 수학           # 특정 과목만 처리
"""

import asyncio
import argparse
import time
import sys
import json
import os
import re
from pathlib import Path
from typing import Optional

# Windows 콘솔 한글/이모지 출력 인코딩 오류 방지
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from playwright.async_api import async_playwright, Browser, Page

# ===== i-scream DOM 실제 셀렉터 =====
SELECTOR_SUBJECT_RADIO = 'input[name="searchSubject"]'   # 과목 선택 라디오 버튼
SELECTOR_EDIT_BUTTON = 'button#btn-result-edit'           # 텍스트 편집 버튼
SELECTOR_SAVE_BUTTON = 'button#btn-result-edit-save[onclick="fnfooterSave()"]'  # 저장 버튼
SELECTOR_PASSWORD_INPUT = 'input#psw'                    # 패스워드 입력란 (SubjectEvaluationCheck.do)
SELECTOR_STUDENT_ITEM = 'span.nm'                        # 개별 학생 항목 (title 속성에 이름 포함)
SELECTOR_EVAL_PAGE_INDICATOR = "div.tool-area"            # 평가 페이지 식별 요소
SELECTOR_POPUP_CLOSE = "button.pop-close"                 # 팝업 닫기 버튼

# TODO: i-scream 내부에서 사용하는 과목 코드/이름이 다를 수 있으므로 확인 후 매핑 업데이트
SUBJECT_MAP = {
    "국어": "국어",
    "수학": "수학",
    "사회": "사회",
    "과학": "과학",
    "도덕": "도덕",
    "체육": "체육",
    "음악": "음악",
    "미술": "미술",
    "영어": "영어",
    "창의적 체험활동": "창체",
}

# 평가 입력 페이지 URL 패턴
# TODO: 실제 URL 확인 후 업데이트
EVAL_PAGE_URL = "SubjectEvaluation.do"

# 전역 상태 (외부에서 중단 요청 시 사용)
stop_requested = False


# =====================================================================
#  유틸리티 함수
# =====================================================================

def _load_password() -> str:
    """
    .env 파일에서 i-scream 평가 비밀번호를 로드합니다.
    없을 경우 기본값 'dlckdtn3'을 반환합니다.
    """
    own_env = Path(__file__).parent / ".env"
    if own_env.exists():
        from dotenv import load_dotenv
        load_dotenv(own_env, override=True)
    return os.environ.get("ISCREAM_EVAL_PASSWORD", "dlckdtn3")


async def hover_and_click(page: Page, selector: str, timeout: int = 3000) -> bool:
    """
    프레임을 순회하며 해당 셀렉터를 가진 요소의 실제 화면 좌표(bounding_box)를 찾아
    마우스를 자연스럽게 이동(Hover)시킨 후 클릭합니다.

    넥사크로 스타일의 숨겨진 접근성 노드(x < 0 또는 width = 0)를 건너뛰고,
    실제로 화면에 보이는 요소만 클릭 대상으로 삼습니다.

    Args:
        page: Playwright Page 객체
        selector: CSS 셀렉터 또는 text= 셀렉터
        timeout: 최대 탐색 대기 시간 (밀리초)

    Returns:
        클릭 성공 여부 (True/False)
    """
    start_time = time.time()
    while time.time() - start_time < (timeout / 1000.0):
        # 메인 페이지 + 모든 내부 프레임 순회
        frames_to_check = [page] + page.frames
        for frame in frames_to_check:
            try:
                locators = await frame.locator(selector).all()
                for loc in locators:
                    box = await loc.bounding_box()
                    # 넥사크로 접근성 노드(x=-4979 등 화면 밖) 및 크기 0인 요소 제외
                    if (box
                            and box['width'] > 0
                            and box['height'] > 0
                            and box['x'] >= 0
                            and box['y'] >= 0):
                        x = box['x'] + box['width'] / 2
                        y = box['y'] + box['height'] / 2
                        # 자연스러운 마우스 이동 (시뮬레이션)
                        try:
                            await page.mouse.move(x, y, steps=5)
                        except Exception:
                            pass
                        
                        try:
                            # Playwright 엘리먼트 자체 클릭 시도 (프레임 좌표 및 cross-origin 완벽 지원)
                            await loc.click(timeout=2000)
                            return True
                        except Exception:
                            # 엘리먼트 클릭 실패 시 마우스 좌표 클릭 폴백
                            await page.mouse.click(x, y)
                            return True
            except Exception:
                continue
        await asyncio.sleep(0.3)
    return False


async def close_popups(page: Page) -> None:
    """
    페이지에 떠 있는 공지사항/안내 팝업을 자동으로 닫습니다.
    일반적인 닫기/확인 버튼 텍스트를 순회하며 클릭을 시도합니다.
    """
    print("   -> 팝업 창이 있는지 확인합니다...")
    try:
        # 공통 팝업 닫기 텍스트 목록
        close_texts = [
            "오늘 하루 이창을 열지 않음",
            "오늘 하루 이 창을 열지 않음",
            "닫기",
            "확인",
            "close",
        ]
        for text in close_texts:
            clicked = await hover_and_click(page, f"text='{text}'", timeout=1000)
            if clicked:
                print(f"   -> 팝업 닫기 성공: '{text}' 버튼 클릭")
                await page.wait_for_timeout(500)

        # 셀렉터 기반 팝업 닫기 시도
        try:
            close_btn = page.locator(SELECTOR_POPUP_CLOSE)
            if await close_btn.count() > 0:
                await close_btn.first.click(force=True, timeout=1000)
                print("   -> 팝업 닫기 버튼(셀렉터) 클릭 완료")
        except Exception:
            pass

    except Exception as e:
        print(f"   (팝업 닫기 중 오류 — 무시합니다: {e})")


# =====================================================================
#  핵심 자동화 함수
# =====================================================================

async def connect_browser(port: int = 9222) -> tuple[Browser, Page]:
    """
    CDP(Chrome DevTools Protocol)를 통해 사용자의 Chrome 브라우저에 연결하고,
    열려 있는 탭 중에서 i-scream 페이지를 찾아 반환합니다.

    로그인은 이미 되어 있다고 가정합니다.
    i-scream 탭을 찾지 못하면 안내 메시지를 출력하고 예외를 발생시킵니다.

    Args:
        port: Chrome 원격 디버깅 포트 (기본값: 9222)

    Returns:
        (browser, page) 튜플

    Raises:
        ConnectionError: Chrome 연결 실패 시
        RuntimeError: i-scream 탭을 찾지 못했을 때
    """
    print(f"\n[연결] Chrome 원격 디버깅 포트 {port}에 연결 중...")

    playwright = await async_playwright().start()
    try:
        browser = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
    except Exception as e:
        print(f"[오류] Chrome 연결 실패: {e}")
        print("=" * 60)
        print("  Chrome이 원격 디버깅 모드로 실행 중인지 확인하세요.")
        print(f"  실행 예시: chrome.exe --remote-debugging-port={port}")
        print("  또는 launch_chrome.bat 파일을 사용하세요.")
        print("=" * 60)
        await playwright.stop()
        raise ConnectionError(f"Chrome 연결 실패 (포트 {port}): {e}")

    print("[연결] Chrome 브라우저에 성공적으로 연결되었습니다.")

    # 열려 있는 탭에서 i-scream 페이지 탐색
    iscream_page = None
    found_pages_info = []

    for ctx in browser.contexts:
        for p in ctx.pages:
            url = p.url.lower()
            try:
                title = await p.title()
            except Exception:
                title = "(제목 읽기 실패)"

            found_pages_info.append(f"  - [{title[:50]}] {p.url[:80]}")

            # URL 또는 제목에서 i-scream 관련 키워드 탐색
            if ("i-scream" in url
                    or "iscream" in url
                    or "아이스크림" in title
                    or "i-scream" in title.lower()
                    or "학생평가" in title):
                iscream_page = p

    if iscream_page is None:
        print("[오류] i-scream 페이지를 찾을 수 없습니다.")
        print("[안내] 현재 열려 있는 탭 목록:")
        for info in found_pages_info:
            print(info)
        print()
        print("=" * 60)
        print("  다음 단계를 확인하세요:")
        print("  1. Chrome이 원격 디버깅 모드로 실행 중인지 확인")
        print("  2. i-scream 홈페이지(https://www.i-scream.co.kr)에 로그인")
        print("  3. 학생평가 페이지를 열어 두세요")
        print("=" * 60)
        raise RuntimeError("i-scream 탭을 찾을 수 없습니다.")

    await iscream_page.bring_to_front()
    page_title = await iscream_page.title()
    print(f"[연결] i-scream 페이지를 찾았습니다: '{page_title}'")

    # playwright 객체를 browser에 저장 (나중에 정리용)
    browser._playwright_instance = playwright

    return browser, iscream_page


async def navigate_to_evaluation(page: Page) -> bool:
    """
    현재 페이지가 과목별 세부능력 평가 입력(SubjectEvaluation.do) 페이지가 아닌 경우,
    해당 페이지로 이동합니다. 이미 해당 페이지에 있으면 이동을 생략합니다.

    Args:
        page: Playwright Page 객체

    Returns:
        성공 여부 (True/False)
    """
    print("\n[네비게이션] 평가 입력 페이지 확인 중...")

    # 팝업 먼저 닫기
    await close_popups(page)

    # .env에서 패스워드 로드
    password = _load_password()

    # 1. 모든 프레임에서 비밀번호 입력란이 있는지 확인
    password_frame = None
    for frame in [page] + page.frames:
        try:
            password_input = frame.locator(SELECTOR_PASSWORD_INPUT)
            if await password_input.count() > 0:
                password_frame = frame
                break
        except Exception:
            continue

    current_url = page.url.lower()

    # 2. 이미 평가 페이지(SubjectEvaluation.do)에 있고 비밀번호 검증도 통과한 상태라면
    if "subjectevaluation.do" in current_url and "check.do" not in current_url and not password_frame:
        print("   -> 이미 평가 입력 페이지에 있습니다. 이동을 생략합니다.")
        return True

    # 3. 비밀번호 확인 페이지/프레임이 감지된 경우 자동 비밀번호 입력 시도
    if password_frame:
        print("   -> 패스워드 확인 화면(또는 프레임) 감지 완료. 자동 입력을 시도합니다...")
        try:
            password_input = password_frame.locator(SELECTOR_PASSWORD_INPUT)
            await password_input.fill(password)
            await page.wait_for_timeout(500)

            # 확인 버튼 클릭 시도 (다양한 셀렉터 매칭)
            confirm_clicked = False
            for btn_sel in ["a:has-text('확인')", "button:has-text('확인')", "a.cbtn_rtyp1", "text='확인'", "a[onclick*='fnSubmit']"]:
                try:
                    btn = password_frame.locator(btn_sel)
                    if await btn.count() > 0:
                        await btn.first.click(timeout=2000)
                        confirm_clicked = True
                        break
                except Exception:
                    continue

            if confirm_clicked:
                print("   -> 패스워드 입력 및 확인 클릭 성공. 페이지 이동 대기 중...")
                for _ in range(15):
                    await page.wait_for_timeout(1000)
                    has_pwd_still = False
                    for frame in [page] + page.frames:
                        try:
                            if await frame.locator(SELECTOR_PASSWORD_INPUT).count() > 0:
                                has_pwd_still = True
                                break
                        except Exception:
                            continue
                    if "subjectevaluation.do" in page.url.lower() and "check.do" not in page.url.lower() and not has_pwd_still:
                        print("   -> 평가 입력 페이지 진입 성공!")
                        await page.wait_for_timeout(1000)
                        return True
        except Exception as e:
            print(f"   [오류] 패스워드 자동 입력 중 예외 발생: {e}")

    # 4. 그 외의 경우 직접 URL 이동 시도
    try:
        print("   -> 평가 입력 페이지로 직접 이동을 시도합니다...")
        await page.goto("https://www.i-scream.co.kr/user/subjectevaluation/SubjectEvaluation.do", timeout=15000)
        await page.wait_for_timeout(3000)

        # 이동 후 비밀번호 확인 페이지인 경우 자동 비밀번호 입력
        password_frame = None
        for frame in [page] + page.frames:
            try:
                password_input = frame.locator(SELECTOR_PASSWORD_INPUT)
                if await password_input.count() > 0:
                    password_frame = frame
                    break
            except Exception:
                continue

        if password_frame:
            print("   -> 이동 후 패스워드 확인 페이지 감지. 비밀번호 자동 입력 진행...")
            password_input = password_frame.locator(SELECTOR_PASSWORD_INPUT)
            await password_input.fill(password)
            await page.wait_for_timeout(500)
            confirm_clicked = False
            for btn_sel in ["a:has-text('확인')", "button:has-text('확인')", "a.cbtn_rtyp1", "text='확인'", "a[onclick*='fnSubmit']"]:
                try:
                    btn = password_frame.locator(btn_sel)
                    if await btn.count() > 0:
                        await btn.first.click(timeout=2000)
                        confirm_clicked = True
                        break
                except Exception:
                    continue
            if confirm_clicked:
                await page.wait_for_timeout(3000)

        # 최종 프레임 및 URL 상태 확인
        has_pwd_still = False
        for frame in [page] + page.frames:
            try:
                if await frame.locator(SELECTOR_PASSWORD_INPUT).count() > 0:
                    has_pwd_still = True
                    break
            except Exception:
                continue

        if "subjectevaluation.do" in page.url.lower() and "check.do" not in page.url.lower() and not has_pwd_still:
            print("   -> 평가 입력 페이지 진입 완료!")
            return True

    except Exception as e:
        print(f"   [네비게이션 오류] 직접 이동 중 오류 발생: {e}")

    # 최종 폴백: 메뉴 클릭 시도 및 수동 대기
    print("   -> 메뉴 클릭 및 수동 이동 대기 모드로 전환합니다...")
    menu_keywords = ["AI평어", "평어", "학생평가", "교과평가", "세부능력", "특기사항"]
    nav_success = False

    for keyword in menu_keywords:
        clicked = await hover_and_click(page, f"text='{keyword}'", timeout=2000)
        if clicked:
            print(f"   -> '{keyword}' 메뉴 클릭 성공")
            await page.wait_for_timeout(2000)
            nav_success = True
            break

    # 수동 대기 루프 (최대 2분)
    if not nav_success or "subjectevaluation.do" not in page.url.lower() or "check.do" in page.url.lower():
        print("   -> 수동으로 비밀번호 입력 및 확인을 눌러 '교과 평가(AI평어)' 페이지로 진입해 주세요. (최대 2분 대기)")
        for _ in range(40):
            if stop_requested:
                return False
            has_pwd_still = False
            for frame in [page] + page.frames:
                try:
                    if await frame.locator(SELECTOR_PASSWORD_INPUT).count() > 0:
                        has_pwd_still = True
                        break
                except Exception:
                    continue
            if "subjectevaluation.do" in page.url.lower() and "check.do" not in page.url.lower() and not has_pwd_still:
                print("   -> 평가 입력 페이지 감지 완료!")
                nav_success = True
                break
            await page.wait_for_timeout(3000)

    if nav_success or ("subjectevaluation.do" in page.url.lower() and "check.do" not in page.url.lower()):
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)
        await close_popups(page)
        print("   [네비게이션 완료] 평가 입력 페이지에 진입했습니다.")
        return True

    print("   [오류] 평가 입력 페이지 이동에 실패했습니다.")
    return False


async def select_subject(page: Page, subject_name: str) -> bool:
    """
    과목 선택 라디오 버튼에서 지정된 과목을 선택합니다.

    SUBJECT_MAP을 통해 한글 과목명을 i-scream 내부 이름으로 변환합니다.

    Args:
        page: Playwright Page 객체
        subject_name: 한글 과목명 (예: '국어', '수학')

    Returns:
        선택 성공 여부 (True/False)
    """
    print(f"\n[과목 선택] '{subject_name}' 과목 선택 중...")

    # 과목명 매핑
    subject_name = subject_name.strip()
    mapped_name = SUBJECT_MAP.get(subject_name, subject_name)

    # 0. 중복 선택 방지
    for frame in [page] + page.frames:
        try:
            is_already_selected = await frame.evaluate(f"""(mappedName) => {{
                if (typeof $ !== 'undefined') {{
                    var radio = $("input[name='searchSubject'][value='" + mappedName + "']");
                    return radio.prop('checked') === true && $('.field-tit li[data-division="subject"]').hasClass('act');
                }}
                return false;
            }}""", mapped_name)
            if is_already_selected:
                print(f"   -> '{subject_name}' 과목이 이미 활성화되어 있어 과목 전환을 생략합니다.")
                return True
        except Exception:
            continue

    # dialog 핸들러 설정 (과목 전환 시 미저장 경고창 발생 대응)
    async def handle_subject_dialog(dialog):
        print(f"   -> [과목 선택 다이얼로그] 감지: '{dialog.message}'. 자동 수락(Accept)합니다.")
        try:
            await dialog.accept()
        except Exception as de:
            print(f"   -> 다이얼로그 수락 중 예외: {de}")

    page.on("dialog", handle_subject_dialog)

    try:
        # 1. JQuery를 이용한 programmatic 선택 시도 (매우 빠르고 프레임/오버레이/스크롤 무관 작동)
        print(f"   -> JQuery를 통해 '{mapped_name}' 과목 선택 및 검색 확인 함수(fnSchFieldConfirm) 직접 호출 시도...")
        try:
            # 메인 페이지 및 모든 프레임에서 JQuery 실행 시도
            for frame in [page] + page.frames:
                try:
                    success = await frame.evaluate(f"""(mappedName) => {{
                        if (typeof $ !== 'undefined') {{
                            var radio = $("input[name='searchSubject'][value='" + mappedName + "']");
                            if (radio.length > 0) {{
                                // division 검색을 활성화하기 위해 탭에 act 클래스 설정
                                $('.field-tit li[data-division="subject"]').addClass('act');
                                radio.prop('checked', true).trigger('change');
                                if (typeof fnSchFieldConfirm !== 'undefined') {{
                                    fnSchFieldConfirm();
                                    return true;
                                }}
                            }}
                        }}
                        return false;
                    }}""", mapped_name)
                    if success:
                        print(f"   -> JQuery를 이용한 과목 전환 성공! ({frame.url})")
                        await page.wait_for_timeout(3000)
                        return True
                except Exception:
                    continue
        except Exception as je:
            print(f"   (JQuery 선택 시도 중 예외 - DOM 폴백 진행: {je})")

        # 2. DOM 기반 폴백 로직 (JQuery가 실패하거나 정의되지 않은 경우)
        await page.wait_for_timeout(1000)
        
        # 모든 프레임 순회하며 탐색
        for frame in [page] + page.frames:
            try:
                radio_selector = f'input[name="searchSubject"][value="{mapped_name}"]'
                radio = frame.locator(radio_selector).first
                
                # 가벼운 wait_for로 요소 존재 확인
                try:
                    await radio.wait_for(state="attached", timeout=3000)
                except Exception:
                    pass
                    
                if await frame.locator(radio_selector).count() > 0:
                    print(f"   -> 프레임 내 '{mapped_name}' 과목 라디오 버튼 감지 완료. JS 클릭 시도...")
                    
                    # division 검색을 활성화하기 위해 탭에 act 클래스 설정
                    await frame.evaluate('''() => { $(".field-tit li[data-division='subject']").addClass("act"); }''')
                    
                    # 이미 선택된 것처럼 보일 때 change 이벤트가 씹히지 않도록 강제 초기화 후 클릭
                    await radio.evaluate("el => { el.checked = false; }")
                    await page.wait_for_timeout(200)

                    # JS click 실행
                    await radio.evaluate("el => el.click()")
                    await page.wait_for_timeout(500)
                    
                    # change 이벤트 디스패치 (JQuery 및 바인딩된 리스너 실행용)
                    await radio.evaluate("el => { el.checked = true; el.dispatchEvent(new Event('change', { bubbles: true })); }")
                    print(f"   -> JS 클릭 및 이벤트 디스패치 완료 ('{mapped_name}')")
                    
                    # 검색 확인(btn-ok) 버튼 클릭 추가
                    ok_btn = frame.locator('div.sch-field-button button.btn-ok').first
                    if await ok_btn.count() > 0:
                        await ok_btn.evaluate("el => el.click()")
                        print("   -> 검색 확인(btn-ok) 버튼 클릭 완료")
                    else:
                        page_ok_btn = page.locator('div.sch-field-button button.btn-ok').first
                        if await page_ok_btn.count() > 0:
                            await page_ok_btn.evaluate("el => el.click()")
                            print("   -> 메인 페이지 검색 확인(btn-ok) 버튼 클릭 완료")
                            
                    await page.wait_for_timeout(3000) # 로딩 및 렌더링 완료 대기
                    return True
            except Exception as fe:
                print(f"   (프레임 내 과목 선택 시도 중 예외 - 계속 검색: {fe})")
                continue

        # 폴백: 라벨 텍스트 기반으로 모든 프레임에서 직접 클릭 시도
        label_selector = f'label:has-text("{mapped_name}")'
        for frame in [page] + page.frames:
            try:
                label = frame.locator(label_selector).first
                try:
                    await label.wait_for(state="attached", timeout=2000)
                except Exception:
                    pass
                    
                if await frame.locator(label_selector).count() > 0:
                    # division 검색을 활성화하기 위해 탭에 act 클래스 설정
                    await frame.evaluate('''() => { $(".field-tit li[data-division='subject']").addClass("act"); }''')
                    
                    # JS click fallback
                    await label.evaluate("el => el.click()")
                    print(f"   -> 프레임 내 라벨 JS 클릭으로 '{mapped_name}' 과목 선택 완료")
                    
                    # 검색 확인(btn-ok) 버튼 클릭 추가
                    ok_btn = frame.locator('div.sch-field-button button.btn-ok').first
                    if await ok_btn.count() > 0:
                        await ok_btn.evaluate("el => el.click()")
                    else:
                        page_ok_btn = page.locator('div.sch-field-button button.btn-ok').first
                        if await page_ok_btn.count() > 0:
                            await page_ok_btn.evaluate("el => el.click()")
                            
                    await page.wait_for_timeout(3000)
                    return True
            except Exception:
                continue

        print(f"   [오류] '{subject_name}' 과목 선택 수단을 찾지 못했습니다.")
        return False

    except Exception as e:
        print(f"   [오류] 과목 선택 중 예외 발생: {e}")
        return False
    finally:
        try:
            page.remove_listener("dialog", handle_subject_dialog)
        except Exception:
            pass


async def select_student(page: Page, student_name: str) -> bool:
    """
    학생 목록에서 지정된 학생을 선택합니다.
    테이블 입력 방식이므로 별도의 학생 선택 탭 클릭은 생략하고 성공 처리합니다.
    """
    # 테이블 내에 학생 입력란이 함께 노출되어 있으므로 개별 클릭은 무시하고 통과시킵니다.
    print(f"   [학생 선택 생략] '{student_name}' 학생은 입력 단계에서 해당 행을 직접 찾아 입력합니다.")
    return True


def calculate_student_level(student_name: str, subject: str, records: list[dict] = None) -> str:
    """
    Supabase 기록 통계를 바탕으로 학생의 교과 수준(최상, 상, 중, 하)을 계산합니다.
    """
    try:
        import supabase_fetch
        import eval_builder
        
        # Supabase에서 기록 패치 및 요약본 빌드 (전달받지 않은 경우에만 패치)
        if records is None:
            records = supabase_fetch.fetch_all_records()
        student_records = supabase_fetch.get_records_for_student(records, student_name)
        if not student_records:
            return "중"
        summary = eval_builder.build_eval_summary(student_name, student_records)
        subj_sum = summary['subjects'].get(subject)
        if not subj_sum:
            return "중"
        
        pos_pct = subj_sum.get('positive_pct', 0)
        neg_pct = subj_sum.get('negative_pct', 0)
        count = subj_sum.get('count', 0)
        
        if count == 0:
            return "중"
        if neg_pct >= 25.0:
            return "하"
        if pos_pct >= 60.0:
            return "최상"
        if pos_pct >= 30.0:
            return "상"
        return "중"
    except Exception as e:
        print(f"   (수준 계산 중 예외 발생, 기본값 '중' 사용: {e})")
        return "중"


def extract_unit_number(unit_text: str) -> Optional[int]:
    """
    단원 텍스트(예: "1. 생생하게 표현해요", "5. 길이와 시간")에서 단원 번호 숫자를 파싱하여 반환합니다.
    """
    if not unit_text:
        return None
    text = unit_text.strip()
    match = re.match(r'^([1-9])(?:\D|$)', text)
    if match:
        return int(match.group(1))
    return None


def get_unit_key(unit_text: str) -> str:
    """
    단원 텍스트에서 고유한 키(숫자 또는 전체 텍스트)를 추출하여 반환합니다.
    """
    if not unit_text:
        return ""
    u_num = extract_unit_number(unit_text)
    if u_num is not None:
        return str(u_num)
    return unit_text.strip()


def determine_target_units(student_name: str, subject: str, records: list[dict]) -> list[int]:
    """
    Supabase 기록을 분석하여 학생의 해당 과목에 대한 관련 단원 번호 목록을 반환합니다.
    최신 기록에 나타난 단원일수록 앞에 위치합니다.
    """
    import supabase_fetch
    student_records = supabase_fetch.get_records_for_student(records, student_name)
    subject_records = [r for r in student_records if (r.get("과목") or "").strip() == subject]
    # 날짜 내림차순 정렬 (최신순)
    subject_records = sorted(subject_records, key=lambda r: r.get("날짜", ""), reverse=True)
    
    target_units = []
    
    # 과목별 키워드 매칭용 정의
    unit_keywords = {
        "국어": {
            1: ["낭송", "실감", "시", "말하기", "목소리", "몸짓", "표정", "감각", "생생"],
            2: ["쉬어 읽기", "문장의 짜임", "띄어 읽기", "분명", "유창"],
            3: ["문단", "중심문장", "뒷받침", "글쓰기", "짜임새"],
            4: ["내용 파악", "질문", "답변", "중요한 내용"],
            5: ["연극", "역할놀이", "인물", "마음", "전해요"],
            6: ["자신 있게", "읽고 써요", "어찌하다", "어떠하다"]
        },
        "수학": {
            1: ["덧셈", "뺄셈", "받아올림", "받아내림", "계산"],
            2: ["도형", "직각", "평면도형", "삼각형", "사각형", "직각삼각형", "그리기", "작도", "삼각자"],
            3: ["나눗셈", "나누기"],
            4: ["곱셈", "곱하기", "곱셈구구"],
            5: ["길이", "시간", "덧셈과 뺄셈 등 길이와 시간", "어림", "시각"],
            6: ["분수", "소수"]
        }
    }
    
    for rec in subject_records:
        title = rec.get("기록제목") or ""
        content = rec.get("내용") or ""
        combined = f"{title} {content}"
        
        # 1) 정규표현식으로 단원 번호 추출 (예: "5단원", "2 단원")
        matches = re.findall(r'([1-6])\s*단원', combined)
        for m in matches:
            val = int(m)
            if val not in target_units:
                target_units.append(val)
                
        # 2) 키워드 매칭
        if subject in unit_keywords:
            for u_num, kwds in unit_keywords[subject].items():
                for kwd in kwds:
                    if kwd in combined:
                        if u_num not in target_units:
                            target_units.append(u_num)
                            
    return target_units


def _level_fallback_order(level: str) -> list[str]:
    """i-scream 수준을 기준으로 같은 수준 우선, 인접 수준 순서로 탐색합니다."""
    if level == "최상":
        return ["최상", "상", "중", "하"]
    if level == "상":
        return ["상", "최상", "중", "하"]
    if level == "하":
        return ["하", "중", "상", "최상"]
    return ["중", "상", "하", "최상"]


def _is_free_count(text: str) -> bool:
    """평가기준 사용 인원이 0명인 행만 자동 선택 대상으로 봅니다."""
    normalized = (text or "").replace(" ", "")
    return normalized in ("0명", "0")


def _get_grade_targets(
    grade_data: dict | None,
    student_name: str,
    subject: str,
) -> list[dict]:
    """
    data/*.md 단계배정표에서 학생-과목별 단원 수준을 가져옵니다.
    최대 2개 단원을 선택하며, 미응시 등 i-scream 수준이 없는 항목은 제외합니다.
    """
    if not grade_data:
        return []
    try:
        import grade_data_parser

        units = grade_data_parser.get_student_grade_for_subject(
            grade_data, student_name, subject
        )
    except Exception as e:
        print(f"   -> [경고] 단계배정표 조회 실패: {e}")
        return []

    targets = []
    seen_units = set()
    for unit in units:
        unit_num = unit.get("unit_num")
        level = unit.get("iscream_level")
        if unit_num is None or not level:
            continue
        if unit_num in seen_units:
            continue
        seen_units.add(unit_num)
        targets.append({
            "unit_num": unit_num,
            "unit_label": unit.get("unit_label") or f"{unit_num}단원",
            "level": level,
            "raw_level": unit.get("raw_level") or "",
        })
        if len(targets) >= 2:
            break
    return targets


async def _ensure_ai_generation_mode(page: Page) -> bool:
    """생성 유형을 AI생성형으로 전환합니다. 매번 fnSearchAiSubjectList()를 호출하여 AI 테이블 상태를 새로고침합니다."""
    for frame in [page] + page.frames:
        try:
            radio = frame.locator("input#rb-type-ai").first
            if await radio.count() == 0:
                continue
            if not await radio.is_checked():
                print("   -> 생성 유형을 AI생성형으로 전환합니다.")
                await radio.evaluate("el => el.click()")
                await radio.evaluate(
                    "el => el.dispatchEvent(new Event('change', { bubbles: true }))"
                )
            else:
                print("   -> 이미 AI 생성형 모드입니다. AI 테이블을 새로고침합니다.")
            # 항상 fnSearchAiSubjectList() 호출하여 AI 테이블 상태 초기화
            # (학생 간 전환 시 이전 학생의 선택/결과가 남아있는 문제 방지)
            try:
                await frame.evaluate(
                    "() => { if (typeof fnSearchAiSubjectList === 'function') fnSearchAiSubjectList(); }"
                )
            except Exception:
                pass
            await page.wait_for_timeout(2000)
            return True
        except Exception:
            continue
    print("   -> [경고] AI생성형 라디오(#rb-type-ai)를 찾지 못했습니다.")
    return False


def _iscream_level_to_ai_lv(level: str) -> str | None:
    """i-scream 수준명을 AI생성형 단원표 버튼 data-lv 값으로 바꿉니다."""
    return {
        "최상": "1",
        "상": "2",
        "중": "3",
        "하": "4",
    }.get(level)


async def _select_ai_unit_levels(page: Page, grade_targets: list[dict]) -> int:
    """
    AI생성형 단원표에서 단계배정표 기준으로 최대 2개 단원의 성취수준을 클릭합니다.
    표 구조: tr#ai-tr* > 단원명 td + data-lv 1(최상), 2(상), 3(중), 4(하) 버튼.
    """
    if not grade_targets:
        return 0

    target_frame = None
    for frame in [page] + page.frames:
        try:
            if await frame.locator(".evaluation-example.type-ai tr[id^='ai-tr'] button[data-lv]").count() > 0:
                target_frame = frame
                break
        except Exception:
            continue

    if target_frame is None:
        print("   -> [경고] AI생성형 단원표(tr#ai-tr*)를 찾지 못했습니다.")
        return 0

    # target_frame 식별 완료 후: 이전 학생의 선택 하이라이트 초기화
    # NOTE: i-scream은 .unit-wrap.highlight + button.highlight 두 가지 모두 사용
    # fnCreativeAiEvaluation은 '.evaluation-example.type-ai .unit-wrap.highlight'를 읽음
    try:
        hl_count = await target_frame.evaluate("""() => {
            var count = 0;
            // button highlight 제거
            document.querySelectorAll(".evaluation-example.type-ai tr[id^='ai-tr'] button.highlight[data-lv]").forEach(function(btn) {
                btn.classList.remove('highlight');
                btn.innerText = 'O';
                count++;
            });
            // unit-wrap highlight 제거 (fnCreativeAiEvaluation이 실제로 읽는 셀렉터)
            document.querySelectorAll(".evaluation-example.type-ai .unit-wrap.highlight").forEach(function(el) {
                el.classList.remove('highlight');
                count++;
            });
            return count;
        }""")
        if hl_count > 0:
            print(f"   -> [AI생성형] 이전 선택된 성취수준 {hl_count}개 초기화 완료 (JS)")
            await page.wait_for_timeout(300)
    except Exception as e:
        print(f"   -> [참고] AI 테이블 하이라이트 초기화 중 예외 (무시): {e}")

    clicked = 0
    for target in grade_targets[:2]:
        unit_num = target.get("unit_num")
        level = target.get("level")
        data_lv = _iscream_level_to_ai_lv(level)
        if unit_num is None or not data_lv:
            continue

        rows = await target_frame.locator(".evaluation-example.type-ai tr[id^='ai-tr']").all()
        matched = False
        for row in rows:
            unit_text = await row.locator("td").first.inner_text()
            if extract_unit_number(unit_text) != unit_num:
                continue

            btn = row.locator(f'button[data-lv="{data_lv}"]').first
            if await btn.count() == 0:
                break

            print(
                f"   -> [AI생성형] {target.get('unit_label')} "
                f"{target.get('raw_level')}({level}) 성취수준 클릭"
            )
            # Click and trigger events
            await btn.evaluate("el => el.click()")
            await btn.evaluate(
                "el => el.dispatchEvent(new Event('change', { bubbles: true }))"
            )
            # Force highlight classes and text content for robustness across all unit variants
            await btn.evaluate("el => { el.classList.add('highlight'); el.innerText = 'V'; }")
            await row.locator(".unit-wrap").evaluate("el => el.classList.add('highlight')")
            
            await page.wait_for_timeout(500)
            clicked += 1
            matched = True
            break

        if not matched:
            print(
                f"   -> [경고] AI생성형 단원표에서 {target.get('unit_label')} "
                f"{target.get('raw_level')}({level}) 버튼을 찾지 못했습니다."
            )

    return clicked


async def _click_ai_generate_button(page: Page) -> bool:
    """AI생성형 선택 후 AI평어 생성 버튼을 누릅니다."""
    selectors = [
        "span#aiCreateBtn",
        ".btns-right.type-ai a",
        "a:has-text('AI평어 생성')",
        "button:has-text('AI평어 생성')",
    ]
    for frame in [page] + page.frames:
        for selector in selectors:
            try:
                loc = frame.locator(selector).first
                if await loc.count() == 0:
                    continue
                if not await loc.is_visible():
                    continue
                print("   -> AI평어 생성 버튼을 클릭합니다.")
                if selector == "span#aiCreateBtn":
                    await loc.evaluate("el => el.closest('a,button')?.click()")
                else:
                    await loc.evaluate("el => el.click()")
                await page.wait_for_timeout(3000)
                return True
            except Exception:
                continue
    print("   -> [경고] AI평어 생성 버튼을 찾지 못했습니다.")
    return False


def is_raw_log_text(text: str) -> bool:
    """
    입력된 텍스트가 Supabase 날짜별 원본 기록(글머리기호 포함) 형태인지 검증합니다.
    """
    if not text:
        return True
    stripped = text.strip()
    if stripped.startswith('•') or stripped.startswith('-'):
        return True
    if re.search(r'\d{4}-\d{2}-\d{2}:', stripped):
        return True
    return False


async def fill_evaluation(page: Page, student_name: str, subject: str, eval_text: str = "", grade_data: dict = None) -> bool:
    """
    해당 학생의 체크박스를 단독 선택하고, 학생 수준에 맞춰 free(0명) 상태인 평가기준 2개를 선택한 후,
    필요시 커스텀 평가문을 입력하여 저장 가능한 상태로 편집합니다.
    """
    print(f"   [평가 입력] 학생: {student_name} | 과목: {subject} | 원문 글자수: {len(eval_text)}자")

    # target_frame 감지 (성취기준 테이블이 있는 프레임)
    target_frame = page
    for frame in [page] + page.frames:
        try:
            if await frame.locator("tr[class^='exam-tr']").count() > 0:
                target_frame = frame
                break
        except Exception:
            continue

    try:
        # 1) 편집 모드 활성화 확인
        edit_btn = page.locator(SELECTOR_EDIT_BUTTON)
        if await edit_btn.is_visible():
            print("   -> '텍스트 편집' 모드 활성화 중...")
            await edit_btn.evaluate("el => el.click()")
            await page.wait_for_timeout(500)

        # 2) 학생 이름 행 tr 및 textarea 찾기
        row_xpath = f'//tr[td[contains(@class, "wordwrap") and normalize-space(text())="{student_name}"]]'
        textarea_selector = f'{row_xpath}//textarea'
        textarea = target_frame.locator(textarea_selector)

        if await textarea.count() == 0:
            print(f"   [오류] '{student_name}' 학생의 입력란(textarea)을 찾을 수 없습니다.")
            return False

        # 3) 학생 수준 계산 및 성취평가기준 자동 선택 (모드 변경 및 학생 선택을 위해 상단 이동)
        grade_targets = _get_grade_targets(grade_data, student_name, subject)
        if grade_targets:
            target_units = [t["unit_num"] for t in grade_targets]
            print(
                "   -> 단계배정표 기반 자동 선택 대상: "
                + ", ".join(
                    f"{t['unit_label']}={t['raw_level']}({t['level']})"
                    for t in grade_targets
                )
            )
        else:
            import supabase_fetch
            records = supabase_fetch.fetch_all_records()
            level = calculate_student_level(student_name, subject, records)
            target_units = determine_target_units(student_name, subject, records)
            grade_targets = [
                {"unit_num": unit_num, "unit_label": f"{unit_num}단원", "level": level, "raw_level": level}
                for unit_num in target_units[:2]
            ]
            print(f"   -> 계산된 학생 수준: {level}")
            print(f"   -> 추출된 관련 단원 우선순위: {target_units}")

        # AI 생성형 모드 시도
        if grade_targets and await _ensure_ai_generation_mode(page):
            # AI 모드로 전환한 후 학생을 선택해야 체크 상태가 유지됩니다.
            print(f"   -> '{student_name}' 학생 선택 및 체크박스 제어 중 (AI 생성형)...")
            success_click = False
            for frame in [page] + page.frames:
                try:
                    res = await frame.evaluate("""(studentName) => {
                        if (typeof $ !== 'undefined') {
                            // click 방식으로 기존 체크 해제 (prop 방식은 내부 이벤트 미발생)
                            $('.student-list.type-ai li input[type="checkbox"]:checked').each(function() {
                                this.click();
                            });
                            var li = $(".student-list.type-ai li:has(span.nm[title='" + studentName + "'])");
                            if (li.length > 0) {
                                var cb = li.find('input[type="checkbox"]')[0];
                                if (cb) {
                                    cb.click();
                                    return true;
                                }
                            }
                            var li2 = $(".student-list.type-ai li:has(span.nm:contains('" + studentName + "'))");
                            if (li2.length > 0) {
                                var cb2 = li2.find('input[type="checkbox"]')[0];
                                if (cb2) {
                                    cb2.click();
                                    return true;
                                }
                            }
                        }
                        return false;
                    }""", student_name)
                    if res:
                        success_click = True
                        break
                except Exception:
                    continue
            
            if success_click:
                print(f"   -> '{student_name}' 학생 체크박스 활성화 완료 (JQuery)")
            else:
                print(f"   -> [경고] '{student_name}' 학생 체크박스를 찾을 수 없습니다. JQuery 폴백 없이 계속 진행합니다.")
            await page.wait_for_timeout(1500)

            ai_clicked = await _select_ai_unit_levels(page, grade_targets)
            if ai_clicked > 0:
                print(f"   -> AI생성형 성취수준 자동 클릭 완료: {ai_clicked}/2개")
                await page.wait_for_timeout(1000)

                # AI 평어 생성 시도 (최대 2회 재시도)
                max_attempts = 2
                for attempt in range(1, max_attempts + 1):
                    if attempt > 1:
                        print(f"   -> AI 평어 생성 재시도 ({attempt}/{max_attempts})...")
                        await page.wait_for_timeout(1000)

                    if await _click_ai_generate_button(page):
                        # fnCreativeAiEvaluation 내부에 setTimeout 3000 있음 → 최소 4초 대기
                        print(f"   -> AI 평어 생성 대기 중 (내부 3초 지연 + AJAX)... (시도 {attempt}/{max_attempts})")
                        await page.wait_for_timeout(4000)

                        # AI 생성 후 textarea가 새로 생성되므로 DOM에서 직접 조회 (locator 사용 불가)
                        text_generated = False
                        for poll_i in range(20):
                            try:
                                txt_val = await target_frame.evaluate(f"""() => {{
                                    var row = document.evaluate(
                                        "//tr[td[contains(@class, 'wordwrap') and normalize-space(text())='{student_name}']]",
                                        document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                                    ).singleNodeValue;
                                    if (!row) return '';
                                    var ta = row.querySelector('textarea');
                                    return ta ? ta.value : '';
                                }}""")
                            except Exception:
                                txt_val = ""

                            if txt_val and len(txt_val.strip()) > 10:
                                print(f"   -> AI 평어 생성 완료 감지 ({len(txt_val.strip())}자). 이벤트 디스패치 중...")
                                # JQuery 및 UI 동기화 (새로 생성된 textarea에 대해)
                                try:
                                    await target_frame.evaluate(f"""() => {{
                                        var row = document.evaluate(
                                            "//tr[td[contains(@class, 'wordwrap') and normalize-space(text())='{student_name}']]",
                                            document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
                                        ).singleNodeValue;
                                        if (row) {{
                                            var ta = row.querySelector('textarea');
                                            if (ta) {{
                                                ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                ta.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                                            }}
                                        }}
                                    }}""")
                                except Exception:
                                    pass
                                text_generated = True
                                break
                            await page.wait_for_timeout(500)

                        if text_generated:
                            return True
                        else:
                            print(f"   -> [경고] AI 평어가 시간 내에 생성되지 않았습니다. (시도 {attempt}/{max_attempts})")
                    else:
                        print(f"   -> AI평어 생성 버튼 클릭 실패 (시도 {attempt}/{max_attempts})")

                # 모든 재시도 실패
                print("   -> [오류] AI 평어 생성이 모든 시도에서 실패했습니다. 입력을 중단합니다.")
                return False
            print("   -> AI생성형 단원표 클릭이 되지 않아 기존 예시문 선택 방식으로 폴백합니다.")
        # 폴백: 기존 예시문 선택 모드
        # 학생 체크박스 제어
        print(f"   -> '{student_name}' 학생 선택 및 체크박스 제어 중 (예시문)...")
        all_cbs = await page.locator("input[name='student'][id^='ai-student']").all()
        all_cbs += await page.locator("input[name='student'][id^='exam-student']").all()
        for cb in all_cbs:
            if await cb.is_checked():
                await cb.evaluate("el => el.click()")
                await cb.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
        
        # 대상 학생 체크박스 찾아서 클릭
        target_cb = page.locator(f'.student-list.type-exam li:has(span.nm[title="{student_name}"]) input[name="student"]').first
        if await target_cb.count() == 0:
            target_cb = page.locator(f'.student-list.type-exam li:has(span.nm:text-is("{student_name}")) input[name="student"]').first
            
        if await target_cb.count() > 0:
            await target_cb.evaluate("el => el.click()")
            await target_cb.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
            print(f"   -> '{student_name}' 학생 체크박스 활성화 완료 (폴백)")
            await page.wait_for_timeout(1000)
        else:
            print(f"   -> [경고] '{student_name}' 학생 체크박스를 찾을 수 없습니다. 계속 진행합니다.")

        # 기존 선택 항목 해제 (마우스 토글 방식)
        print("   -> 기존에 선택된 항목이 있는지 검사하고 해제(토글)합니다...")
        all_exam_rows = await target_frame.locator("tr[class^='exam-tr']").all()
        visible_rows = [r for r in all_exam_rows if await r.is_visible()]
        highlighted_rows = [r for r in visible_rows if "highlight" in (await r.get_attribute("class") or "")]
        
        if highlighted_rows:
            print(f"   -> 기존 선택 항목 감지: {len(highlighted_rows)}개. 순차 해제 진행...")
            for row in highlighted_rows:
                btn = row.locator("button.al").first
                if await btn.count() > 0:
                    btn_text = await btn.inner_text()
                    print(f"      -> 기존 선택 항목 해제: '{btn_text[:40]}...'")
                    await btn.evaluate("el => el.click()")
                    await btn.evaluate("el => { el.dispatchEvent(new Event('change', { bubbles: true })); }")
                    await page.wait_for_timeout(500)
            print("   -> 기존 선택 항목 해제 완료")
        else:
            print("   -> 기존에 선택된 항목이 없습니다. (깨끗한 상태)")
            
        # 추가 확인: textarea 청소 재확인
        await textarea.first.evaluate("el => el.value = ''")
        await textarea.first.evaluate("el => { el.dispatchEvent(new Event('input')); el.dispatchEvent(new Event('change')); el.dispatchEvent(new Event('blur')); }")
        await page.wait_for_timeout(300)

        # 우측 평가기준 테이블 행(tr) 탐색 (현재 화면에 보이는 행만 필터링)
        # :visible 가상 클래스를 사용하여 화면에 보이는 행만 빠르게 가져옵니다.
        exam_rows = await target_frame.locator("tr[class^='exam-tr']:visible").all()
        
        # 이미 이 학생에게 선택된(highlight) 개수 체크 및 단원 추적
        selected_units = set()
        highlighted_count = 0
        for row in exam_rows:
            tr_class = await row.get_attribute("class") or ""
            if "highlight" in tr_class:
                highlighted_count += 1
                row_data = await row.evaluate("""el => {
                    const tds = el.querySelectorAll('td');
                    return {
                        len: tds.length,
                        unit: tds.length >= 4 ? tds[0].innerText.trim() : ''
                    };
                }""")
                if row_data['len'] >= 4:
                    unit_key = get_unit_key(row_data['unit'])
                    if unit_key:
                        selected_units.add(unit_key)
                
        clicked_count = highlighted_count
        print(f"   -> 현재 기선택된 평가기준 개수(화면 표시): {clicked_count}개, 단원: {selected_units}")

        async def _read_exam_row(row):
            return await row.evaluate("""el => {
                const tds = el.querySelectorAll('td');
                return {
                    len: tds.length,
                    unit: tds.length >= 4 ? tds[0].innerText.trim() : '',
                    level: tds.length >= 4 ? tds[1].innerText.trim() : '',
                    count: tds.length >= 4 ? tds[3].innerText.trim() : '',
                    className: el.className
                };
            }""")

        async def _click_exam_row(row, row_data, match_kind):
            nonlocal clicked_count
            row_unit = row_data["unit"]
            row_level = row_data["level"]
            unit_key = get_unit_key(row_unit)

            if unit_key in selected_units:
                print(f"      -> [{match_kind} 건너뜀] 이미 단원 '{row_unit}'에서 선택되었습니다.")
                return False

            btn = row.locator("button.al").first
            if await btn.count() == 0:
                return False

            btn_text = await btn.inner_text()
            print(
                f"   -> [{match_kind}] 평가기준 자동 클릭 ({clicked_count + 1}/2) "
                f"| 단원: {row_unit} | 수준: [{row_level}] | 내용: '{btn_text[:40]}...'"
            )
            await btn.evaluate("el => el.click()")
            await btn.evaluate("el => { el.dispatchEvent(new Event('change', { bubbles: true })); }")
            await page.wait_for_timeout(1000)
            clicked_count += 1
            if unit_key:
                selected_units.add(unit_key)
            return True

        # 1단계: data/*.md 배정표에 있는 단원 번호와 수준을 우선 정확히 매칭합니다.
        print("   -> [1단계] 단계배정표의 단원별 수준을 기준으로 평가기준을 찾습니다.")
        for target in grade_targets:
            if clicked_count >= 2:
                break

            target_unit = target["unit_num"]
            print(
                f"      -> 대상 단원: {target['unit_label']} | "
                f"배정 수준: {target['raw_level']}({target['level']})"
            )
            for cur_level in _level_fallback_order(target["level"]):
                if clicked_count >= 2:
                    break
                for row in exam_rows:
                    if clicked_count >= 2:
                        break

                    row_data = await _read_exam_row(row)
                    if row_data["len"] < 4:
                        continue

                    row_unit_num = extract_unit_number(row_data["unit"])
                    if (
                        row_unit_num == target_unit
                        and row_data["level"] == cur_level
                        and _is_free_count(row_data["count"])
                        and "highlight" not in row_data["className"]
                    ):
                        if await _click_exam_row(row, row_data, "배정표매칭"):
                            break

        # 2단계: 지정 단원에서 못 찾은 경우, 같은 수준 계열로 다른 단원까지 보완합니다.
        if clicked_count < 2:
            fallback_levels = []
            for target in grade_targets:
                for level_name in _level_fallback_order(target["level"]):
                    if level_name not in fallback_levels:
                        fallback_levels.append(level_name)
            if not fallback_levels:
                fallback_levels = ["상", "최상", "중", "하"]

            print("   -> [2단계] 부족한 선택 개수를 전체 단원에서 보완 탐색합니다.")
            for cur_level in fallback_levels:
                if clicked_count >= 2:
                    break
                print(f"      -> 수준 '{cur_level}'의 0명 평가기준 탐색 중...")
                for row in exam_rows:
                    if clicked_count >= 2:
                        break

                    row_data = await _read_exam_row(row)
                    if row_data["len"] < 4:
                        continue

                    if (
                        row_data["level"] == cur_level
                        and _is_free_count(row_data["count"])
                        and "highlight" not in row_data["className"]
                    ):
                        await _click_exam_row(row, row_data, "보완매칭")

        print(f"   -> 평가기준 선택 동작 완료 (총 선택된 개수: {clicked_count}/2)")

        # 6) 커스텀 평가문 입력 처리
        # 사용자의 요청에 따라: "우리가 날짜와 내용을 입력할 필요는 없다. 평가기준을 클릭하면 자동으로 입력된다."
        # 따라서, textarea에 값을 직접 쓰지 않고 성취기준 클릭으로 발생한 자동 입력값만 유지합니다.
        print("   -> [입력 건너뜀] 사용자 요청에 따라 평가문 텍스트 입력을 생략하고 성취기준 클릭으로 갈음합니다.")
        return True

    except Exception as e:
        print(f"   [오류] 평가 입력 프로세스 중 예외 발생: {e}")
        return False


async def save_evaluation(page: Page) -> bool:
    """
    저장 버튼을 클릭하고, 확인 다이얼로그가 나타나면 OK를 누릅니다.

    Args:
        page: Playwright Page 객체

    Returns:
        저장 성공 여부 (True/False)
    """
    print("   [저장] 저장 버튼 클릭 중...")

    try:
        # dialog 핸들러 설정 (브라우저 alert/confirm 자동 처리)
        dialog_handled = False

        async def handle_dialog(dialog):
            nonlocal dialog_handled
            print(f"   -> 다이얼로그 감지: '{dialog.message}'")
            try:
                await dialog.accept()
                dialog_handled = True
            except Exception as de:
                print(f"   -> 다이얼로그 수락 중 예외 (무시): {de}")

        page.on("dialog", handle_dialog)

        # 저장 버튼 클릭 시도 (구체적 셀렉터 매칭)
        save_clicked = False
        save_btn = page.locator(SELECTOR_SAVE_BUTTON)
        if await save_btn.count() > 0:
            await save_btn.first.evaluate("el => el.click()")
            save_clicked = True
            print("   -> 저장 버튼 클릭 완료 (상세 셀렉터)")
        else:
            # 폴백 셀렉터
            fallback_btn = page.locator("button#btn-result-edit-save").first
            if await fallback_btn.count() > 0:
                await fallback_btn.evaluate("el => el.click()")
                save_clicked = True
                print("   -> 저장 버튼 클릭 완료 (폴백 셀렉터)")

        if not save_clicked:
            print("   [오류] 저장 버튼을 찾을 수 없습니다.")
            page.remove_listener("dialog", handle_dialog)
            return False

        # 저장 후 다이얼로그 처리 대기
        await page.wait_for_timeout(2000)

        # dialog 핸들러 제거
        page.remove_listener("dialog", handle_dialog)

        # 저장 후 페이지 상태 안정화 대기 (다음 학생 처리 전 AI 테이블 등이 리셋되도록)
        await page.wait_for_timeout(1500)

        print("   [저장 완료] 평가가 성공적으로 저장되었습니다.")
        return True

    except Exception as e:
        print(f"   [오류] 저장 중 예외 발생: {e}")
        try:
            page.remove_listener("dialog", handle_dialog)
        except Exception:
            pass
        return False


# =====================================================================
#  통합 처리 함수
# =====================================================================

async def process_single(
    page: Page,
    student_name: str,
    subject: str,
    eval_text: str,
    dry_run: bool = False,
    grade_data: dict = None,
) -> dict:
    """
    한 명의 학생 + 한 과목에 대한 전체 평가 입력 흐름을 실행합니다.

    1) 과목 선택 → 2) 학생 선택 → 3) 평가 내용 입력 → 4) 저장

    dry_run=True이면 저장 단계를 건너뛰고 시뮬레이션만 수행합니다.

    Args:
        page: Playwright Page 객체
        student_name: 학생 이름
        subject: 과목명
        eval_text: 평가 내용 텍스트
        dry_run: True이면 저장 생략
        grade_data: 단계배정표 데이터 딕셔너리

    Returns:
        결과 딕셔너리 {'student', 'subject', 'status', 'fail_reason', 'processed_at'}
    """
    result = {
        'student': student_name,
        'subject': subject,
        'status': '성공',
        'fail_reason': '',
        'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    print(f"\n{'=' * 60}")
    print(f"[처리 시작] 학생: {student_name} | 과목: {subject}")
    if dry_run:
        print(f"   ⚠️  [Dry Run 모드] 실제 저장은 수행하지 않습니다.")
    print(f"   평가 내용 미리보기: {eval_text[:80]}{'...' if len(eval_text) > 80 else ''}")
    print(f"{'=' * 60}")

    try:
        # 1단계: 과목 선택
        if not await select_subject(page, subject):
            result['status'] = '실패'
            result['fail_reason'] = f'과목 선택 실패: {subject}'
            return result

        # 2단계: 학생 선택
        if not await select_student(page, student_name):
            result['status'] = '실패'
            result['fail_reason'] = f'학생 선택 실패: {student_name}'
            return result

        # 3단계: 평가 내용 입력
        if not await fill_evaluation(page, student_name, subject, eval_text, grade_data=grade_data):
            result['status'] = '실패'
            result['fail_reason'] = '평가 내용 입력 실패'
            return result

        # 4단계: 저장 (dry_run이 아닐 때만)
        if dry_run:
            print("   [Dry Run] 저장 단계를 건너뜁니다.")
            result['status'] = '시뮬레이션 완료'
        else:
            if not await save_evaluation(page):
                result['status'] = '실패'
                result['fail_reason'] = '저장 실패'
                return result

        print(f"[처리 완료] {student_name} - {subject}: {result['status']}")

    except Exception as e:
        print(f"[오류] {student_name} - {subject} 처리 중 예외 발생: {e}")
        result['status'] = '실패'
        result['fail_reason'] = str(e)

    return result


async def process_batch(
    eval_data_list: list[dict],
    port: int = 9222,
    dry_run: bool = False,
    preview: bool = False,
    grade_data: dict = None,
) -> list[dict]:
    """
    평가 데이터 목록을 일괄 처리하는 메인 엔트리 포인트입니다.

    각 항목은 {'student': str, 'subject': str, 'eval_text': str} 형식이어야 합니다.

    Args:
        eval_data_list: 평가 데이터 딕셔너리 목록
            각 항목: {'student': '이름', 'subject': '과목', 'eval_text': '평가내용'}
        port: Chrome 원격 디버깅 포트
        dry_run: True이면 저장 없이 시뮬레이션
        preview: True이면 전체 목록 미리보기 후 사용자 확인 대기

    Returns:
        처리 결과 목록 (각 항목별 결과 딕셔너리)
    """
    global stop_requested
    stop_requested = False

    results = []

    if not eval_data_list:
        print("[안내] 처리할 평가 데이터가 없습니다.")
        return results

    total = len(eval_data_list)
    print(f"\n{'#' * 60}")
    print(f"# i-scream 학생 평가 자동 입력 시작")
    print(f"# 총 {total}건 | {'Dry Run' if dry_run else '실제 실행'}")
    print(f"{'#' * 60}")

    # 미리보기 모드
    if preview:
        print(f"\n[미리보기] 처리 예정 목록 ({total}건):")
        print("-" * 60)
        for i, item in enumerate(eval_data_list, 1):
            student = item.get('student', '(미지정)')
            subject = item.get('subject', '(미지정)')
            text = item.get('eval_text', '')
            text_preview = text[:60] + '...' if len(text) > 60 else text
            print(f"  {i:3d}. [{subject}] {student}: {text_preview}")
        print("-" * 60)

        # CLI 실행 시 사용자 확인 대기
        try:
            confirm = input("\n위 목록대로 진행하시겠습니까? (y/N): ").strip().lower()
            if confirm not in ('y', 'yes', '예', 'ㅇ'):
                print("[안내] 사용자가 취소했습니다.")
                return results
        except EOFError:
            # SSE/Flask 환경에서는 input이 불가하므로 그냥 진행
            print("[안내] 비대화형 환경 — 미리보기만 수행하고 계속 진행합니다.")

    # 브라우저 연결
    try:
        browser, page = await connect_browser(port)
    except (ConnectionError, RuntimeError) as e:
        print(f"[중단] 브라우저 연결 실패로 작업을 중단합니다: {e}")
        for item in eval_data_list:
            results.append({
                'student': item.get('student', ''),
                'subject': item.get('subject', ''),
                'status': '실패',
                'fail_reason': f'브라우저 연결 실패: {e}',
                'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            })
        return results

    try:
        # 평가 입력 페이지로 이동
        if not await navigate_to_evaluation(page):
            print("[중단] 평가 입력 페이지 이동 실패로 작업을 중단합니다.")
            for item in eval_data_list:
                results.append({
                    'student': item.get('student', ''),
                    'subject': item.get('subject', ''),
                    'status': '실패',
                    'fail_reason': '평가 페이지 이동 실패',
                    'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                })
            return results

        # 과목별로 그룹화하여 과목 전환 횟수 최소화
        # (같은 과목의 학생들을 연속 처리)
        from collections import defaultdict
        subject_groups = defaultdict(list)
        for item in eval_data_list:
            subject_groups[item.get('subject', '')].append(item)

        success_count = 0
        fail_count = 0
        skip_count = 0

        item_index = 0
        for subject, items in subject_groups.items():
            if stop_requested:
                # 남은 모든 과목 그룹의 학생들을 중단 처리
                for remaining_item in items:
                    results.append({
                        'student': remaining_item.get('student', ''),
                        'subject': remaining_item.get('subject', ''),
                        'status': '사용자 중단',
                        'fail_reason': '사용자 중단 요청',
                        'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    })
                    skip_count += 1
                continue

            print(f"\n{'━' * 60}")
            print(f"📚 과목: {subject} ({len(items)}명)")
            print(f"{'━' * 60}")

            for item in items:
                if stop_requested:
                    print("\n[중단] 사용자 요청으로 작업을 중단합니다.")
                    for remaining_item in items[items.index(item):]:
                        results.append({
                            'student': remaining_item.get('student', ''),
                            'subject': remaining_item.get('subject', ''),
                            'status': '사용자 중단',
                            'fail_reason': '사용자 중단 요청',
                            'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                        })
                        skip_count += 1
                    break

                item_index += 1
                student = item.get('student', '')
                subject_name = item.get('subject', '')
                eval_text = item.get('eval_text', '')

                print(f"\n[진행률] {item_index}/{total} "
                      f"(성공: {success_count}, 실패: {fail_count}, 건너뜀: {skip_count})")

                if not eval_text or not eval_text.strip():
                    print(f"   [건너뜀] {student} - {subject_name}: 평가 내용이 비어 있습니다.")
                    results.append({
                        'student': student,
                        'subject': subject_name,
                        'status': '건너뜀',
                        'fail_reason': '평가 내용 없음',
                        'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    })
                    skip_count += 1
                    continue

                result = await process_single(
                    page, student, subject_name, eval_text, dry_run=dry_run, grade_data=grade_data
                )
                results.append(result)

                if result['status'] in ('성공', '시뮬레이션 완료'):
                    success_count += 1
                else:
                    fail_count += 1

                # 연속 처리 시 서버 부하 방지를 위한 대기
                await page.wait_for_timeout(500)

    except Exception as e:
        print(f"\n[치명적 오류] 일괄 처리 중 예외 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 브라우저 연결 해제 (탭은 닫지 않음 — CDP 특성)
        try:
            playwright_instance = getattr(browser, '_playwright_instance', None)
            await browser.close()
            if playwright_instance:
                await playwright_instance.stop()
        except Exception:
            pass

    # 최종 결과 요약
    print(f"\n{'#' * 60}")
    print(f"# 처리 완료 요약")
    print(f"#   총 처리: {total}건")
    print(f"#   성공: {success_count}건")
    print(f"#   실패: {fail_count}건")
    print(f"#   건너뜀: {skip_count}건")
    print(f"{'#' * 60}")

    return results


# =====================================================================
#  CLI 인터페이스
# =====================================================================

def _build_sample_data(
    student_filter: Optional[str] = None,
    subject_filter: Optional[str] = None,
) -> list[dict]:
    """
    테스트용 샘플 평가 데이터를 생성합니다.
    실제 운영 시에는 Supabase에서 데이터를 가져옵니다.

    Args:
        student_filter: 특정 학생 이름 필터 (None이면 전체)
        subject_filter: 특정 과목 필터 (None이면 전체)

    Returns:
        평가 데이터 목록
    """
    # TODO: 실제 운영 시 Supabase에서 데이터를 가져오도록 교체
    sample_data = [
        {
            'student': '김민준',
            'subject': '국어',
            'eval_text': '글의 구조를 파악하며 읽는 능력이 우수하고, '
                         '자신의 생각을 조리 있게 글로 표현할 수 있음.',
        },
        {
            'student': '김민준',
            'subject': '수학',
            'eval_text': '수의 연산 원리를 정확히 이해하고, '
                         '문제 해결 과정을 논리적으로 설명할 수 있음.',
        },
        {
            'student': '이서윤',
            'subject': '국어',
            'eval_text': '다양한 종류의 글을 읽고 중심 내용을 파악하는 능력이 뛰어나며, '
                         '토의에서 자신의 의견을 적극적으로 제시함.',
        },
    ]

    # 필터 적용
    if student_filter:
        sample_data = [d for d in sample_data if d['student'] == student_filter]
    if subject_filter:
        sample_data = [d for d in sample_data if d['subject'] == subject_filter]

    return sample_data


def main():
    """CLI 엔트리 포인트"""
    parser = argparse.ArgumentParser(
        description="i-scream 교과 세부능력 및 특기사항 자동 입력 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python iscream_evaluate.py --dry-run              시뮬레이션 실행 (저장 안 함)
  python iscream_evaluate.py --preview               미리보기 후 확인 대기
  python iscream_evaluate.py --student 김민준         특정 학생만 처리
  python iscream_evaluate.py --subject 수학           특정 과목만 처리
  python iscream_evaluate.py --port 9223             다른 디버깅 포트 사용

주의사항:
  - Chrome이 원격 디버깅 모드로 실행 중이어야 합니다.
  - i-scream에 이미 로그인된 상태여야 합니다.
  - DOM 셀렉터(SELECTOR_*)가 최신 상태인지 확인하세요.
        """,
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='시뮬레이션 모드 — 실제 저장을 수행하지 않습니다',
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='처리 전 전체 목록을 미리보기하고 사용자 확인을 기다립니다',
    )
    parser.add_argument(
        '--student',
        type=str,
        default=None,
        help='특정 학생 이름만 처리 (예: --student 김민준)',
    )
    parser.add_argument(
        '--subject',
        type=str,
        default=None,
        help='특정 과목만 처리 (예: --subject 수학)',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=9222,
        help='Chrome 원격 디버깅 포트 (기본값: 9222)',
    )
    parser.add_argument(
        '--data',
        type=str,
        default=None,
        help='평가 데이터 JSON 파일 경로 (미지정 시 샘플 데이터 사용)',
    )

    args = parser.parse_args()

    # 평가 데이터 준비
    if args.data:
        try:
            with open(args.data, 'r', encoding='utf-8') as f:
                eval_data = json.load(f)
            print(f"[데이터] JSON 파일에서 {len(eval_data)}건 로드: {args.data}")
        except Exception as e:
            print(f"[오류] 데이터 파일 로드 실패: {e}")
            sys.exit(1)
    else:
        print("[데이터] 샘플 데이터를 사용합니다. (실제 운영 시 --data 옵션 사용)")
        eval_data = _build_sample_data(
            student_filter=args.student,
            subject_filter=args.subject,
        )

    # 필터가 적용된 경우 안내
    if args.student:
        eval_data = [d for d in eval_data if d.get('student') == args.student]
        print(f"[필터] 학생 필터 적용: '{args.student}' ({len(eval_data)}건)")
    if args.subject:
        eval_data = [d for d in eval_data if d.get('subject') == args.subject]
        print(f"[필터] 과목 필터 적용: '{args.subject}' ({len(eval_data)}건)")

    if not eval_data:
        print("[안내] 조건에 맞는 평가 데이터가 없습니다.")
        sys.exit(0)

    # 비동기 실행
    results = asyncio.run(
        process_batch(
            eval_data,
            port=args.port,
            dry_run=args.dry_run,
            preview=args.preview,
        )
    )

    # 결과 출력
    if results:
        print(f"\n[결과] 처리 결과 상세:")
        for r in results:
            status_icon = "✅" if r['status'] in ('성공', '시뮬레이션 완료') else "❌"
            if r['status'] == '건너뜀':
                status_icon = "⏭️"
            elif r['status'] == '사용자 중단':
                status_icon = "🛑"
            print(f"  {status_icon} {r['student']} - {r['subject']}: "
                  f"{r['status']}"
                  f"{' (' + r['fail_reason'] + ')' if r['fail_reason'] else ''}")


if __name__ == '__main__':
    main()
