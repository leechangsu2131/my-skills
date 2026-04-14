"""
나이스(NEIS) 셀레니움 자동화 테스트 스크립트
=============================================
사용법:
  1. launch_chrome.bat 을 먼저 실행하여 크롬을 엽니다.
  2. 열린 크롬에서 나이스(NEIS)에 직접 로그인합니다.
  3. 이 스크립트를 실행합니다.
     > python neis_test.py

주요 기능:
  - 로그인된 크롬 세션에 셀레니움이 붙어서 (attach) 동작합니다.
  - 현재 열린 창 목록, 팝업창 전환, 입력칸 목록을 자동으로 파악합니다.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    NoSuchWindowException,
    TimeoutException,
)

REMOTE_DEBUGGING_PORT = 9222
NEIS_MAIN_URL = "https://gbe.neis.go.kr/jsp/main.jsp"

# ─────────────────────────────────────────────
# 드라이버 연결 (이미 열려있는 크롬에 붙기)
# ─────────────────────────────────────────────

def attach_to_chrome():
    """원격 디버깅 포트에 연결합니다."""
    options = Options()
    options.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_DEBUGGING_PORT}")

    try:
        driver = webdriver.Chrome(options=options)
        print(f"[✓] 크롬에 연결 성공! (포트: {REMOTE_DEBUGGING_PORT})")
        return driver
    except Exception as e:
        print(f"[✗] 크롬 연결 실패: {e}")
        print("  → launch_chrome.bat 으로 크롬을 먼저 실행했는지 확인해 주세요.")
        raise


# ─────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────

def list_windows(driver):
    """현재 열린 탭/팝업창 정보를 모두 출력합니다."""
    handles = driver.window_handles
    original = driver.current_window_handle
    print(f"\n[📋 열린 창 목록] 총 {len(handles)}개")
    for i, handle in enumerate(handles):
        try:
            driver.switch_to.window(handle)
            print(f"  [{i}] 핸들: {handle[:12]}... | 제목: {driver.title[:60]} | URL: {driver.current_url[:80]}")
        except NoSuchWindowException:
            print(f"  [{i}] 핸들: {handle[:12]}... (접근 불가)")
    driver.switch_to.window(original)
    return handles


def analyze_form(driver):
    """현재 창(및 iframe 포함)에서 입력 가능한 폼 요소를 분석합니다."""
    print("\n[🔍 폼 요소 분석]")
    found = []

    # 메인 document
    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea, select")
    if inputs:
        print(f"  ● 메인 페이지 입력칸: {len(inputs)}개")
        for el in inputs:
            el_id = el.get_attribute("id")
            el_name = el.get_attribute("name")
            el_type = el.tag_name
            print(f"    - 타입:{el_type}, id:{el_id or '없음'}, name:{el_name or '없음'}")
            found.append({"doc": "main", "id": el_id, "name": el_name, "type": el_type})

    # iframe 탐색
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"  ● iframe 개수: {len(iframes)}개")
    for idx, frame in enumerate(iframes):
        frame_id = frame.get_attribute("id") or f"#{idx}"
        try:
            driver.switch_to.frame(frame)
            sub_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], textarea, select")
            if sub_inputs:
                print(f"    └─ iframe({frame_id}) 입력칸: {len(sub_inputs)}개")
                for el in sub_inputs:
                    el_id = el.get_attribute("id")
                    el_name = el.get_attribute("name")
                    el_type = el.tag_name
                    print(f"        - 타입:{el_type}, id:{el_id or '없음'}, name:{el_name or '없음'}")
                    found.append({"doc": f"iframe({frame_id})", "id": el_id, "name": el_name, "type": el_type})
            driver.switch_to.default_content()
        except Exception as e:
            print(f"    └─ iframe({frame_id}) 접근 실패: {e}")
            driver.switch_to.default_content()
    
    return found


def switch_to_popup(driver, wait_sec=5):
    """새 팝업창이 열릴 때까지 기다린 뒤 전환합니다."""
    original = driver.current_window_handle
    before = set(driver.window_handles)
    print(f"\n[⏳ 팝업창 대기 중... ({wait_sec}초)]")
    end = time.time() + wait_sec
    while time.time() < end:
        new_handles = set(driver.window_handles) - before
        if new_handles:
            popup = new_handles.pop()
            driver.switch_to.window(popup)
            print(f"[✓] 팝업창 전환 성공!")
            print(f"    제목: {driver.title}")
            print(f"    URL : {driver.current_url}")
            return popup
        time.sleep(0.5)
    print("[✗] 팝업창이 열리지 않았습니다. 직접 메뉴를 클릭해 팝업을 띄우세요.")
    return None


# ─────────────────────────────────────────────
# 메인 테스트 시나리오
# ─────────────────────────────────────────────

def run_test():
    driver = attach_to_chrome()
    print(f"\n현재 URL : {driver.current_url}")
    print(f"현재 제목: {driver.title}")

    print("\n" + "="*50)
    print(" [테스트 1] 창 목록 확인")
    print("="*50)
    handles = list_windows(driver)

    print("\n" + "="*50)
    print(" [테스트 2] 현재 창 폼 분석")
    print("="*50)
    analyze_form(driver)

    print("\n" + "="*50)
    print(" [테스트 3] 팝업창 대기 및 전환 테스트")
    print("="*50)
    print("지금 나이스에서 메뉴를 하나 클릭하여 팝업창을 열어보세요...")
    popup = switch_to_popup(driver, wait_sec=20)

    if popup:
        print("\n[팝업창 내 폼 분석 시작]")
        time.sleep(2)  # 팝업 로딩 대기
        analyze_form(driver)

        print("\n[팝업창 내 클릭 가능한 버튼 목록]")
        buttons = driver.find_elements(By.CSS_SELECTOR, "button, input[type='button'], input[type='submit'], a[href]")
        for btn in buttons[:20]:  # 최대 20개 출력
            text = btn.text.strip() or btn.get_attribute("value") or btn.get_attribute("title") or "(텍스트 없음)"
            print(f"  - {btn.tag_name}: {text[:40]}")

    print("\n" + "="*50)
    print(" ✅ 테스트 완료!")
    print("="*50)
    print("위 출력 결과를 채팅창에 붙여넣어 주시면")
    print("연가/출장 신청 자동화 코드를 작성해 드립니다.")

    # 드라이버를 종료하지 않음 (창을 유지)
    # driver.quit()


if __name__ == "__main__":
    run_test()
