"""
나이스(NEIS) 연가/출장 신청 화면 자동 열기 스크립트
=====================================================
현재 버전에서는 **신청 창(모달/팝업)까지 자동으로 열어두고,
그 이후 상세 입력/제출은 사람이 직접 수행**하는 것을 목표로 합니다.

흐름:
  1. 왼쪽 메뉴 '복무' > '개인근무상황관리' 클릭
  2. 중앙 파란색 '신청' 버튼 클릭
  3. (필요한 경우) 새로 열린 신청 창/모달로 자동 전환

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

def attach():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    print(f"[✓] 크롬 연결 성공: {driver.title}")
    return driver


def _iter_frames(driver, max_depth=3):
    """
    접근 가능한 (same-origin) frame들을 DFS로 순회합니다.
    yield: (label, switch_fn)
    """
    def walk(path, depth):
        driver.switch_to.default_content()
        for frame in path:
            driver.switch_to.frame(frame)

        label = "main" if not path else " > ".join(
            [f"iframe[{(f.get_attribute('id') or f.get_attribute('name') or '#')}]"
             for f in path]
        )
        yield label, list(path)

        if depth >= max_depth:
            return

        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
        except Exception:
            frames = []

        for f in frames:
            try:
                # 자식 frame으로 들어갈 수 있는지 빠르게 검증
                driver.switch_to.frame(f)
                driver.switch_to.parent_frame()
            except Exception:
                continue
            yield from walk(path + [f], depth + 1)

    yield from walk([], 0)


def _norm(s: str) -> str:
    return " ".join((s or "").split())


def find_and_click_by_text(driver, text, exact=True, tags=None, timeout=5):
    """
    모든 프레임에서 텍스트로 요소를 찾아 클릭합니다.
    성공 시 True, 실패 시 False 반환.
    """
    if tags is None:
        tags = ["a", "li", "span", "div", "button", "td", "em", "p"]

    want = _norm(text)
    deadline = time.time() + timeout

    def _match(el) -> bool:
        try:
            if not el.is_displayed():
                return False
            candidates = [
                el.text,
                el.get_attribute("aria-label"),
                el.get_attribute("title"),
                el.get_attribute("value"),
                el.get_attribute("alt"),
            ]
            cands = [_norm(c) for c in candidates if c]
            if exact:
                return any(c == want for c in cands)
            return any(want in c for c in cands)
        except StaleElementReferenceException:
            return False
        except Exception:
            return False

    def _search_by_tags(ctx):
        for tag in tags:
            try:
                els = ctx.find_elements(By.TAG_NAME, tag)
            except Exception:
                continue
            for el in els:
                if _match(el):
                    return el
        return None

    def _search_by_xpath(ctx):
        # normalize-space(.) 기반으로 내부 텍스트도 잡기 (span 중첩 등)
        x_text = want.replace("'", "\\'")
        if exact:
            xpath = (
                "//*[self::a or self::button or self::span or self::li or self::div or self::em or self::td]"
                f"[normalize-space(.)='{x_text}']"
            )
        else:
            xpath = (
                "//*[self::a or self::button or self::span or self::li or self::div or self::em or self::td]"
                f"[contains(normalize-space(.),'{x_text}')]"
            )
        try:
            els = ctx.find_elements(By.XPATH, xpath)
        except Exception:
            return None
        for el in els:
            if _match(el):
                return el
        return None

    while time.time() < deadline:
        for frame_label, frame_path in _iter_frames(driver, max_depth=3):
            try:
                driver.switch_to.default_content()
                for f in frame_path:
                    driver.switch_to.frame(f)

                el = _search_by_tags(driver) or _search_by_xpath(driver)
                if not el:
                    continue

                print(f"  찾음 ({frame_label}): '{text}'")
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                except Exception:
                    pass

                try:
                    driver.execute_script("arguments[0].click();", el)
                except Exception:
                    try:
                        ActionChains(driver).move_to_element(el).pause(0.1).click().perform()
                    except Exception:
                        el.click()
                driver.switch_to.default_content()
                return True
            except Exception:
                driver.switch_to.default_content()
                continue

        time.sleep(0.3)

    print(f"  ✗ '{text}' 텍스트 요소를 찾지 못했습니다.")
    return False




def _switch_to_new_window_if_opened(driver, before_handles, wait_sec=2.5):
    """
    클릭 후 새 창/팝업이 열리면 그 창으로 전환합니다.
    """
    end = time.time() + wait_sec
    before = set(before_handles)
    while time.time() < end:
        now = set(driver.window_handles)
        diff = list(now - before)
        if diff:
            new_handle = diff[0]
            driver.switch_to.window(new_handle)
            print(f"  → 새 창 감지, 전환 성공: {driver.title}")
            return True
        time.sleep(0.2)
    return False


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
    before_handles = list(driver.window_handles)
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
    # 신청이 팝업으로 뜨는 케이스 대응
    switched = _switch_to_new_window_if_opened(driver, before_handles, wait_sec=3.0)
    if switched:
        time.sleep(1.0)

    print("\n" + "="*55)
    print(" ✅ 신청 화면까지 자동으로 열어 두었습니다.")
    print("="*55)
    print("  이제 이 화면에서 연가/출장 정보를 직접 입력하고 신청을 완료하시면 됩니다.")


if __name__ == "__main__":
    run()
