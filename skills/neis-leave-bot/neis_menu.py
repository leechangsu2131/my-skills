"""
나이스(NEIS) 셀레니움 메뉴 클릭 + 구조 파악 스크립트
=====================================================
- 왼쪽 사이드바에서 '복무' > '개인근무상황관리' 클릭을 시도합니다.
- 나이스는 새 크롬 창이 아닌 같은 창 내 모달/하단탭 구조이므로
  iframe 및 페이지 내부 요소를 직접 탐색합니다.

사용법:
  1. launch_chrome.bat (또는 PowerShell 명령)으로 크롬 실행
  2. 나이스 직접 로그인 완료
  3. python neis_menu.py
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    NoSuchElementException, StaleElementReferenceException, TimeoutException
)

REMOTE_PORT = 9222
WAIT = 5  # 초


# ─────────────────────────────────────────────
# 드라이버 연결
# ─────────────────────────────────────────────

def attach():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    print(f"[✓] 연결 성공: {driver.title}")
    return driver


# ─────────────────────────────────────────────
# 페이지 전체 구조 파악 (iframe 포함)
# ─────────────────────────────────────────────

def get_all_documents(driver):
    """메인 + 모든 iframe의 document를 리스트로 반환합니다."""
    docs = [("main", driver)]
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for i, frame in enumerate(iframes):
        frame_id = frame.get_attribute("id") or frame.get_attribute("name") or f"#{i}"
        try:
            driver.switch_to.frame(frame)
            docs.append((f"iframe[{frame_id}]", driver))
            # 중첩 iframe
            nested = driver.find_elements(By.TAG_NAME, "iframe")
            for j, nframe in enumerate(nested):
                nid = nframe.get_attribute("id") or nframe.get_attribute("name") or f"#{j}"
                try:
                    driver.switch_to.frame(nframe)
                    docs.append((f"iframe[{frame_id}] > iframe[{nid}]", driver))
                    driver.switch_to.parent_frame()
                except Exception:
                    driver.switch_to.parent_frame()
            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()
    return docs


def find_element_in_all_frames(driver, by, value, switch=True):
    """모든 frame에서 요소를 찾아 해당 frame으로 전환 후 element를 반환합니다."""
    driver.switch_to.default_content()
    try:
        el = driver.find_element(by, value)
        return el
    except NoSuchElementException:
        pass

    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for frame in iframes:
        try:
            driver.switch_to.frame(frame)
            try:
                el = driver.find_element(by, value)
                return el  # 현재 frame에 머무름
            except NoSuchElementException:
                # 중첩 iframe
                nested = driver.find_elements(By.TAG_NAME, "iframe")
                for nframe in nested:
                    try:
                        driver.switch_to.frame(nframe)
                        el = driver.find_element(by, value)
                        return el
                    except NoSuchElementException:
                        driver.switch_to.parent_frame()
            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()
    return None


# ─────────────────────────────────────────────
# 텍스트로 클릭 가능한 요소 찾기
# ─────────────────────────────────────────────

def find_clickable_by_text(driver, text, exact=False):
    """모든 frame에서 텍스트가 포함된 클릭 가능한 요소를 찾습니다."""
    tags = ["a", "li", "span", "div", "button", "td", "p"]
    
    def search_in_current_doc():
        for tag in tags:
            try:
                elements = driver.find_elements(By.TAG_NAME, tag)
                for el in elements:
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

    # 메인 document
    driver.switch_to.default_content()
    el = search_in_current_doc()
    if el:
        return el, "main"

    # iframe들
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for i, frame in enumerate(iframes):
        fid = frame.get_attribute("id") or f"#{i}"
        try:
            driver.switch_to.frame(frame)
            el = search_in_current_doc()
            if el:
                return el, f"iframe[{fid}]"
            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()

    return None, None


# ─────────────────────────────────────────────
# 메뉴 클릭 시나리오
# ─────────────────────────────────────────────

def click_menu(driver, menu_text, sub_menu_text=None):
    """왼쪽 메뉴를 클릭합니다. sub_menu_text가 있으면 펼쳐진 후 하위 항목을 클릭합니다."""
    print(f"\n[🖱 메뉴 클릭 시도: '{menu_text}']")
    el, loc = find_clickable_by_text(driver, menu_text, exact=True)
    if el is None:
        el, loc = find_clickable_by_text(driver, menu_text, exact=False)
    
    if el:
        print(f"  → 발견! ({loc}) 클릭합니다...")
        try:
            driver.execute_script("arguments[0].click();", el)
        except Exception:
            ActionChains(driver).move_to_element(el).click().perform()
        time.sleep(1.5)
        print(f"  → 클릭 완료!")
    else:
        print(f"  ✗ '{menu_text}' 메뉴를 찾을 수 없습니다.")
        return False

    if sub_menu_text:
        print(f"\n[🖱 하위 메뉴 클릭 시도: '{sub_menu_text}']")
        time.sleep(0.5)
        sub_el, sub_loc = find_clickable_by_text(driver, sub_menu_text, exact=True)
        if sub_el is None:
            sub_el, sub_loc = find_clickable_by_text(driver, sub_menu_text, exact=False)
        
        if sub_el:
            print(f"  → 발견! ({sub_loc}) 클릭합니다...")
            try:
                driver.execute_script("arguments[0].click();", sub_el)
            except Exception:
                ActionChains(driver).move_to_element(sub_el).click().perform()
            time.sleep(2)
            print(f"  → 클릭 완료!")
        else:
            print(f"  ✗ '{sub_menu_text}' 하위 메뉴를 찾을 수 없습니다.")
            return False
    
    return True


def analyze_current_state(driver):
    """현재 화면 상태(iframe, 폼 요소, 버튼 등)를 분석합니다."""
    print("\n" + "="*55)
    print(" 현재 화면 구조 분석")
    print("="*55)
    print(f"URL  : {driver.current_url}")
    print(f"제목 : {driver.title}")

    # 창 개수
    print(f"\n[창] 총 {len(driver.window_handles)}개 (나이스는 보통 1개 창만 사용)")

    # iframe 구조
    driver.switch_to.default_content()
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"\n[iframe] {len(iframes)}개:")
    for i, f in enumerate(iframes):
        fid = f.get_attribute("id") or f.get_attribute("name") or f.get_attribute("src") or f"#{i}"
        print(f"  [{i}] {fid[:80]}")

    # 모달 레이어 탐색 (display:block인 div 중 z-index 높은 것)
    modals = driver.find_elements(By.CSS_SELECTOR, "div[class*='modal'], div[class*='layer'], div[class*='pop'], div[id*='modal'], div[id*='pop']")
    visible_modals = [m for m in modals if m.is_displayed()]
    print(f"\n[모달/레이어] 표시 중인 것: {len(visible_modals)}개")
    for m in visible_modals[:5]:
        mid = m.get_attribute("id") or m.get_attribute("class") or "?"
        print(f"  - {mid[:60]}")

    # 각 iframe에서 폼 요소 분석
    print(f"\n[폼 요소 분석 (iframe 포함)]")
    driver.switch_to.default_content()
    for i, frame in enumerate(iframes):
        fid = frame.get_attribute("id") or frame.get_attribute("name") or f"#{i}"
        try:
            driver.switch_to.frame(frame)
            inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden']), textarea, select")
            if inputs:
                print(f"\n  iframe[{fid}]의 입력칸 {len(inputs)}개:")
                for inp in inputs[:10]:
                    iid = inp.get_attribute("id")
                    iname = inp.get_attribute("name")
                    itype = inp.get_attribute("type") or inp.tag_name
                    ival = inp.get_attribute("value") or ""
                    print(f"    - 타입:{itype}, id:{iid or '없음'}, name:{iname or '없음'}, 현재값:'{ival[:20]}'")
            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def run():
    driver = attach()
    
    print("\n" + "="*55)
    print(" [STEP 1] 초기 화면 상태 파악")
    print("="*55)
    analyze_current_state(driver)

    print("\n" + "="*55)
    print(" [STEP 2] '복무' 메뉴 클릭")
    print("="*55)
    click_menu(driver, "복무")
    
    print("\n" + "="*55)
    print(" [STEP 3] '개인근무상황관리' 하위 메뉴 클릭")
    print("="*55)
    click_menu(driver, "개인근무상황관리")
    time.sleep(2)

    print("\n" + "="*55)
    print(" [STEP 4] 클릭 후 화면 구조 재분석")
    print("="*55)
    analyze_current_state(driver)

    print("\n✅ 완료! 위 결과를 복사해서 채팅창에 붙여넣어 주세요.")


if __name__ == "__main__":
    run()
