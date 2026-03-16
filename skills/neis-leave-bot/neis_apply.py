"""
나이스(NEIS) 연가/출장 신청 자동화 스크립트
=============================================
흐름:
  1. 왼쪽 메뉴 '복무' > '개인근무상황관리' 클릭
  2. 중앙 파란색 '신청' 버튼 클릭
  3. 열린 신청 모달에서 폼 분석 및 자동 입력

사용법:
  1. launch_chrome.bat 으로 크롬 실행
  2. 나이스 직접 로그인 완료 후
  3. python neis_apply.py
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException, TimeoutException
)

REMOTE_PORT = 9222

# ══════════════════════════════════════════
# 설정: 신청할 내용을 여기서 수정하세요!
# ══════════════════════════════════════════
LEAVE_TYPE = "연가"   # "연가" 또는 "출장" 등

# 연가 설정 (필요한 경우 수정)
LEAVE_CONFIG = {
    "근무상황": "연가",    # 드롭다운 선택값
    "사유": "개인 용무",    # 사유 텍스트
}
# ══════════════════════════════════════════


def attach():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    print(f"[✓] 크롬 연결 성공: {driver.title}")
    return driver


def find_and_click_by_text(driver, text, exact=True, tags=None, timeout=5):
    """
    모든 프레임에서 텍스트로 요소를 찾아 클릭합니다.
    성공 시 True, 실패 시 False 반환.
    """
    if tags is None:
        tags = ["a", "li", "span", "div", "button", "td", "em", "p"]

    def _search(ctx):
        for tag in tags:
            try:
                els = ctx.find_elements(By.TAG_NAME, tag)
                for el in els:
                    try:
                        el_text = el.text.strip()
                        matched = (el_text == text) if exact else (text in el_text)
                        if matched and el.is_displayed():
                            return el
                    except StaleElementReferenceException:
                        continue
            except Exception:
                continue
        return None

    frames = ["main"] + list(range(len(driver.find_elements(By.TAG_NAME, "iframe"))))

    # 메인 document
    driver.switch_to.default_content()
    el = _search(driver)
    if el:
        print(f"  찾음 (main): '{text}'")
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            driver.execute_script("arguments[0].click();", el)
        except Exception:
            ActionChains(driver).move_to_element(el).click().perform()
        return True

    # iframe 탐색
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for i, frame in enumerate(iframes):
        fid = frame.get_attribute("id") or frame.get_attribute("name") or f"#{i}"
        try:
            driver.switch_to.frame(frame)
            el = _search(driver)
            if el:
                print(f"  찾음 (iframe[{fid}]): '{text}'")
                try:
                    driver.execute_script("arguments[0].scrollIntoView(true);", el)
                    driver.execute_script("arguments[0].click();", el)
                except Exception:
                    ActionChains(driver).move_to_element(el).click().perform()
                driver.switch_to.default_content()
                return True
            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()

    print(f"  ✗ '{text}' 텍스트 요소를 찾지 못했습니다.")
    return False


def analyze_modal(driver, label="모달"):
    """
    현재 화면에서 표시 중인 모달/레이어 내의 폼 요소를 분석합니다.
    """
    print(f"\n[🔍 {label} 내 입력 요소 분석]")
    all_results = []

    def search_in(ctx, doc_name):
        inputs = ctx.find_elements(By.CSS_SELECTOR,
            "input:not([type='hidden']):not([type='radio']):not([type='checkbox']), textarea, select")
        if inputs:
            print(f"\n  [{doc_name}] 입력칸 {len(inputs)}개:")
            for el in inputs:
                iid   = el.get_attribute("id")
                iname = el.get_attribute("name")
                itype = el.get_attribute("type") or el.tag_name
                ival  = el.get_attribute("value") or ""
                print(f"    • 타입:{itype:10s} id:{str(iid or '-'):25s} name:{str(iname or '-'):25s} 값:'{ival[:20]}'")
                all_results.append({"doc": doc_name, "id": iid, "name": iname, "type": itype})

        # 버튼
        btns = ctx.find_elements(By.CSS_SELECTOR, "button, input[type='button'], input[type='submit']")
        visible_btns = [b for b in btns if b.is_displayed()]
        if visible_btns:
            print(f"  [{doc_name}] 버튼 {len(visible_btns)}개:")
            for b in visible_btns[:15]:
                txt = b.text.strip() or b.get_attribute("value") or b.get_attribute("title") or "-"
                print(f"    ▶ {txt[:40]}")

    # 메인
    driver.switch_to.default_content()
    search_in(driver, "main")

    # iframe
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for i, frame in enumerate(iframes):
        fid = frame.get_attribute("id") or frame.get_attribute("name") or f"#{i}"
        try:
            driver.switch_to.frame(frame)
            search_in(driver, f"iframe[{fid}]")
            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()

    return all_results


def run():
    driver = attach()
    wait = WebDriverWait(driver, 10)

    # ──────────────────────────────────────
    # STEP 1: 왼쪽 메뉴 '복무' 클릭
    # ──────────────────────────────────────
    print("\n" + "="*55)
    print(" [STEP 1] '복무' 메뉴 클릭")
    print("="*55)
    ok = find_and_click_by_text(driver, "복무", exact=True)
    if not ok:
        # '복무'가 펼쳐진 상태거나 이름이 다를 경우 그냥 다음 단계로
        print("  → '복무' 이미 펼쳐진 상태이거나 다른 경로일 수 있음. 다음 단계 진행.")
    time.sleep(1)

    # ──────────────────────────────────────
    # STEP 2: '개인근무상황관리' 클릭
    # ──────────────────────────────────────
    print("\n" + "="*55)
    print(" [STEP 2] '개인근무상황관리' 클릭")
    print("="*55)
    ok = find_and_click_by_text(driver, "개인근무상황관리", exact=True)
    if not ok:
        find_and_click_by_text(driver, "개인근무상황관리", exact=False)
    time.sleep(3)  # 중앙 콘텐츠 로딩 대기

    # ──────────────────────────────────────
    # STEP 3: 중앙의 '신청' 버튼 클릭
    # ──────────────────────────────────────
    print("\n" + "="*55)
    print(" [STEP 3] 중앙 '신청' 버튼 클릭")
    print("="*55)
    # 중앙 그리드 상단 버튼은 보통 특정 id/class를 가짐
    # 먼저 id/class로 시도, 안되면 텍스트로 시도

    clicked = False
    # 방법 1: 버튼 텍스트 "신청"으로 찾기 (정확히 "신청"인 것)
    for btn_text in ["신청", "내신청", "대신신청", "신 청"]:
        ok = find_and_click_by_text(driver, btn_text, exact=True,
                                     tags=["button", "input", "a", "span", "em", "li"])
        if ok:
            clicked = True
            print(f"  → '{btn_text}' 버튼 클릭 성공!")
            break

    if not clicked:
        print("\n  [대안 시도] CSS 셀렉터로 버튼 직접 탐색...")
        driver.switch_to.default_content()
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for i, frame in enumerate(iframes):
            fid = frame.get_attribute("id") or f"#{i}"
            try:
                driver.switch_to.frame(frame)
                # 나이스에서 주로 쓰는 버튼 패턴
                btn_candidates = driver.find_elements(By.CSS_SELECTOR,
                    "button, .btn, [class*='btn'], input[type='button']")
                for btn in btn_candidates:
                    try:
                        txt = btn.text.strip() or btn.get_attribute("value") or ""
                        if "신청" in txt and btn.is_displayed():
                            print(f"  → CSS 탐색으로 발견: '{txt}' in iframe[{fid}]")
                            driver.execute_script("arguments[0].click();", btn)
                            clicked = True
                            break
                    except StaleElementReferenceException:
                        continue
                driver.switch_to.default_content()
                if clicked:
                    break
            except Exception:
                driver.switch_to.default_content()

    time.sleep(2)

    # ──────────────────────────────────────
    # STEP 4: 신청 모달 내 폼 분석
    # ──────────────────────────────────────
    print("\n" + "="*55)
    print(" [STEP 4] 신청 모달 폼 구조 분석")
    print("="*55)
    fields = analyze_modal(driver, "신청 모달")

    print("\n" + "="*55)
    print(" ✅ 완료!")
    print("="*55)
    if fields:
        print(f"  총 {len(fields)}개 입력 필드를 발견했습니다.")
        print("  이 결과를 채팅창에 붙여넣으면 자동입력 코드를 짜드립니다!")
    else:
        print("  입력 필드를 찾지 못했습니다.")
        print("  '신청' 버튼 클릭이 제대로 됐는지 화면을 확인해 주세요.")


if __name__ == "__main__":
    run()
