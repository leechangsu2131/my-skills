"""
하이톡 DOM 탐색 스크립트
========================
로그인된 하이톡 페이지에서 실제 DOM 구조를 분석하여
자동화에 필요한 셀렉터를 찾아줍니다.

사용법:
  1. launch_chrome_hiclass.bat 실행
  2. 하이클래스 로그인 → 하이톡 페이지 이동
  3. python explore_dom.py
"""

import io
import time
import json
import os
import sys

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_PATH = os.path.join(SCRIPT_DIR, "requirements.txt")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
except ModuleNotFoundError:
    print("[✗] selenium이 설치되어 있지 않습니다.")
    print(f'    설치: python -m pip install -r "{REQUIREMENTS_PATH}"')
    sys.exit(1)

REMOTE_PORT = 9223


def attach():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    print(f"[✓] 크롬 연결: {driver.title}")
    print(f"    URL: {driver.current_url}")
    return driver


def explore(driver):
    results = {}

    print("\n" + "=" * 60)
    print("  🔍 하이톡 DOM 탐색")
    print("=" * 60)

    # 1. 검색 입력란 찾기
    print("\n📋 [1] 검색 입력란 탐색...")
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for i, inp in enumerate(inputs):
        try:
            if inp.is_displayed():
                ph = inp.get_attribute("placeholder") or ""
                cls = inp.get_attribute("class") or ""
                id_ = inp.get_attribute("id") or ""
                typ = inp.get_attribute("type") or ""
                print(f"  input[{i}]: placeholder='{ph}' class='{cls}' id='{id_}' type='{typ}'")
                if any(kw in ph for kw in ["이름", "검색", "태그"]):
                    results["search_input"] = {
                        "placeholder": ph, "class": cls, "id": id_
                    }
                    print(f"    → ✅ 검색란으로 판단!")
        except Exception as e:
            continue

    # 2. textarea 찾기 (채팅 입력란)
    print("\n📋 [2] 채팅 입력란 탐색...")
    textareas = driver.find_elements(By.TAG_NAME, "textarea")
    for i, ta in enumerate(textareas):
        try:
            if ta.is_displayed():
                ph = ta.get_attribute("placeholder") or ""
                cls = ta.get_attribute("class") or ""
                id_ = ta.get_attribute("id") or ""
                print(f"  textarea[{i}]: placeholder='{ph}' class='{cls}' id='{id_}'")
                results["chat_textarea"] = {
                    "placeholder": ph, "class": cls, "id": id_
                }
                print(f"    → ✅ 채팅 입력란으로 판단!")
        except Exception:
            continue

    # contenteditable div도 탐색
    editables = driver.find_elements(By.CSS_SELECTOR, "[contenteditable='true']")
    for i, ed in enumerate(editables):
        try:
            if ed.is_displayed():
                cls = ed.get_attribute("class") or ""
                id_ = ed.get_attribute("id") or ""
                print(f"  contenteditable[{i}]: class='{cls}' id='{id_}'")
                results["chat_contenteditable"] = {"class": cls, "id": id_}
        except Exception:
            continue

    # 3. 보내기 버튼 찾기
    print("\n📋 [3] 보내기 버튼 탐색...")
    buttons = driver.find_elements(By.TAG_NAME, "button")
    for i, btn in enumerate(buttons):
        try:
            if btn.is_displayed():
                text = btn.text.strip()
                cls = btn.get_attribute("class") or ""
                id_ = btn.get_attribute("id") or ""
                if text:
                    print(f"  button[{i}]: text='{text}' class='{cls}' id='{id_}'")
                if "보내기" in text or "send" in cls.lower():
                    results["send_button"] = {
                        "text": text, "class": cls, "id": id_
                    }
                    print(f"    → ✅ 보내기 버튼으로 판단!")
        except Exception:
            continue

    # 4. 학생/학부모 목록 탐색
    print("\n📋 [4] 학생 목록 탐색...")
    keywords = ["contact", "user", "member", "chat-list", "list-item",
                "student", "parent", "학부모"]

    for kw in keywords:
        elements = driver.find_elements(By.CSS_SELECTOR, f"[class*='{kw}']")
        if elements:
            print(f"  [class*='{kw}']: {len(elements)}개 발견")
            for j, el in enumerate(elements[:3]):
                try:
                    text = el.text[:50].replace("\n", " ")
                    cls = el.get_attribute("class")
                    tag = el.tag_name
                    print(f"    [{j}] <{tag} class='{cls}'> {text}...")
                except Exception:
                    continue

    # 5. XPath로 학부모/학생 텍스트 포함 요소 직접 탐색
    print("\n📋 [5] '학부모' 텍스트 포함 요소...")
    try:
        xpath = "//*[contains(text(), '학부모')]"
        parental = driver.find_elements(By.XPATH, xpath)
        print(f"  '학부모' 텍스트 포함: {len(parental)}개")
        for j, el in enumerate(parental[:10]):
            try:
                text = el.text[:60].replace("\n", " ")
                cls = el.get_attribute("class") or ""
                tag = el.tag_name
                parent = el.find_element(By.XPATH, "..")
                parent_cls = parent.get_attribute("class") or ""
                parent_tag = parent.tag_name
                print(f"    [{j}] <{tag}.{cls[:30]}> '{text}'")
                print(f"         부모: <{parent_tag}.{parent_cls[:30]}>")
                if j == 0:
                    results["student_item_example"] = {
                        "tag": tag, "class": cls,
                        "parent_tag": parent_tag, "parent_class": parent_cls
                    }
            except Exception:
                continue
    except Exception:
        pass

    # 6. 결과 저장
    print("\n" + "=" * 60)
    print("  📊 탐색 결과 요약")
    print("=" * 60)
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # 결과를 파일로 저장
    import os
    out_path = os.path.join(os.path.dirname(__file__), "dom_selectors.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 결과 저장: {out_path}")
    print("  이 결과를 hitalk_sender.py가 자동으로 참조합니다.")


if __name__ == "__main__":
    driver = attach()
    explore(driver)
