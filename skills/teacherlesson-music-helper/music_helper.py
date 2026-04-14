import argparse
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import class_manager


REMOTE_PORT = 9222
BASE_URL = "https://ele.douclass.com/textbooks/30050/518?arch_id=12553"
DEFAULT_GUIDE_DIR = Path.home() / "Documents" / "지도서"
PERSISTENT_CHROME_PROFILE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MusicClassHelper" / "chrome_profile"
CHROME_PATH_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
]
BACK = "__BACK__"
MENU = "__MENU__"


def find_chrome_executable():
    for candidate in CHROME_PATH_CANDIDATES:
        if candidate and candidate.exists():
            return str(candidate)
    return "chrome"


def get_persistent_chrome_profile():
    PERSISTENT_CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    return PERSISTENT_CHROME_PROFILE_DIR


def launch_chrome_for_debugging():
    chrome_path = find_chrome_executable()
    profile_dir = get_persistent_chrome_profile()
    command = [
        chrome_path,
        f"--remote-debugging-port={REMOTE_PORT}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    ]

    try:
        creation_flags = 0
        for flag_name in ("CREATE_NEW_PROCESS_GROUP", "DETACHED_PROCESS"):
            creation_flags |= getattr(subprocess, flag_name, 0)

        subprocess.Popen(
            command,
            shell=False,
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[관리] Chrome을 디버그 포트 {REMOTE_PORT}로 자동 실행했습니다.")
        print(f"[관리] 로그인 정보는 프로젝트 밖 프로필에 저장됩니다: {profile_dir}")
        return True
    except Exception as error:
        print(f"[!] Chrome 자동 실행 실패: {error}")
        return False


def is_debug_port_open(host="127.0.0.1", port=REMOTE_PORT, timeout=0.2):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def wait_for_debug_port(retries=20, delay=0.2):
    for _ in range(retries):
        if is_debug_port_open():
            return True
        time.sleep(delay)
    return False


def connect_to_debug_chrome(options, retries=2, delay=0.2):
    last_error = None
    for _ in range(retries):
        try:
            return webdriver.Chrome(options=options)
        except Exception as error:
            last_error = error
            time.sleep(delay)
    raise last_error


def ensure_guide_dir():
    DEFAULT_GUIDE_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_GUIDE_DIR


def list_guide_pdfs():
    guide_dir = ensure_guide_dir()
    return sorted(guide_dir.glob("*.pdf"), key=lambda path: path.name.lower())


def choose_pdf_from_folder(default_path=None, allow_skip=True):
    default_text = (default_path or "").strip()
    pdf_files = list_guide_pdfs()

    print(f"\n[PDF 폴더] {DEFAULT_GUIDE_DIR}")
    if not pdf_files:
        print("  -> 폴더 안에 PDF가 없습니다. 직접 경로를 입력하거나 나중에 파일을 넣어주세요.")
    else:
        for index, pdf_file in enumerate(pdf_files, start=1):
            marker = " (현재값)" if default_text and str(pdf_file) == default_text else ""
            print(f"  {index}. {pdf_file.name}{marker}")

    if default_text:
        print(f"현재 PDF: {default_text}")

    if allow_skip:
        print("번호를 입력하거나, 직접 경로를 입력하거나, 엔터로 건너뛸 수 있습니다.")
    else:
        print("번호를 입력하거나, 직접 경로를 입력하세요. 엔터를 누르면 현재값을 유지합니다.")
    print("뒤로가기는 b, 메뉴로 가기는 m 을 입력하세요.")

    selection = prompt_with_nav("PDF 선택: ", allow_blank=allow_skip)
    if selection in {BACK, MENU}:
        return selection
    if selection is None:
        return choose_pdf_from_folder(default_path=default_path, allow_skip=allow_skip)
    if not selection:
        return default_text or None

    if selection.isdigit():
        index = int(selection) - 1
        if 0 <= index < len(pdf_files):
            return str(pdf_files[index])
        print("[!] 올바른 PDF 번호가 아닙니다. 기존 값을 유지합니다.")
        return default_text or None

    return selection


def attach_to_chrome():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    if is_debug_port_open():
        try:
            driver = connect_to_debug_chrome(opts, retries=2, delay=0.2)
            try:
                alert = driver.switch_to.alert
                print(f"[알림] 브라우저 경고창이 있어 자동으로 확인합니다: {alert.text}")
                alert.accept()
                time.sleep(1)
            except Exception:
                pass

            try:
                title = driver.title
            except Exception:
                title = "제목 확인 실패"

            print(f"[OK] Chrome connected: {title}")
            return driver, True
        except Exception as error:
            print(f"[!] 열린 디버그 크롬에 연결 실패: {error}")
            print("    새 Chrome 실행으로 복구를 시도합니다.")
    else:
        print(f"[관리] 디버그 포트 {REMOTE_PORT} 크롬이 없어 바로 새 창을 실행합니다.")

    if not launch_chrome_for_debugging():
        print("    Chrome 자동 실행에 실패했습니다.")
        return None, False

    if not wait_for_debug_port(retries=25, delay=0.2):
        print(f"[!] Chrome 창은 띄웠지만 디버그 포트 {REMOTE_PORT}가 열리지 않았습니다.")
        return None, False

    try:
        driver = connect_to_debug_chrome(opts, retries=3, delay=0.2)
        print(f"[OK] Chrome connected after auto-launch: {driver.title}")
        return driver, False
    except Exception as error:
        print(f"[!] 자동 실행 후에도 크롬 연결 실패: {error}")
        return None, False


def has_lesson_page_loaded(driver, timeout=1.0):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, "textbook-chapter"))
        )
        return True
    except Exception:
        return False


def login_if_needed(driver, wait, reuse_existing_browser=False):
    print("\n[STEP 1] 로그인 상태 확인...")

    try:
        if has_lesson_page_loaded(driver, timeout=1.0):
            print("  -> 차시 페이지가 이미 열려 있습니다.")
            return True

        driver.get(BASE_URL)
        if has_lesson_page_loaded(driver, timeout=2.0):
            print("  -> 차시 페이지로 바로 이동했습니다.")
            return True

        login_links = driver.find_elements(
            By.XPATH,
            "//a[contains(@href, 'sign.dongapublishing.com') or contains(@href, 'guest_login')]",
        )
        logout_links = driver.find_elements(
            By.XPATH, "//a[contains(@href, 'logout') or contains(@class, 'logout')]"
        )

        if logout_links:
            print("  -> 이미 로그인된 상태입니다.")
            return True

        if login_links:
            print("  -> 로그인 버튼이 보여서 helper Chrome에서 직접 로그인하도록 준비합니다.")
            login_url = (
                "https://sign.douclass.com/authlogin/guest_login.donga"
                "?returl=https://ele.douclass.com/textbooks/30050/518?arch_id=12553"
            )
            driver.get(login_url)
            time.sleep(0.5)

            try:
                alert = driver.switch_to.alert
                print(f"  -> 알림창 확인: {alert.text}")
                alert.accept()
                time.sleep(0.5)
            except Exception:
                pass

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//input|//button|//a",
                        )
                    )
                )
            except Exception:
                pass

            answer = prompt_enter_after_browser_action(
                "  -> 방금 열린 helper Chrome 창에서 직접 로그인해주세요.\n"
                "     로그인 완료 후 엔터를 누르면 차시 페이지로 돌아가 확인합니다."
            )
            if answer.lower() == "b":
                print("  -> 로그인을 취소했습니다.")
                return False

            driver.get(BASE_URL)
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "textbook-chapter")))
                print("  -> 로그인 후 차시 페이지 로딩을 확인했습니다.")
                return True
            except Exception:
                print("  [!] 로그인 후에도 차시 페이지를 불러오지 못했습니다.")
                return False

        if has_lesson_page_loaded(driver, timeout=2.0):
            print("  -> 차시 페이지 로딩을 확인했습니다.")
            return True

        if reuse_existing_browser:
            print("  -> 현재 열린 helper Chrome 창을 그대로 사용합니다. 차시 페이지가 보이도록 맞춰주세요.")
            answer = prompt_enter_after_browser_action(
                "  -> helper Chrome에서 차시 페이지를 직접 열거나 로그인한 뒤 엔터를 눌러주세요."
            )
            if answer.lower() == "b":
                print("  -> 작업을 취소했습니다.")
                return False
            if has_lesson_page_loaded(driver, timeout=2.0):
                print("  -> 현재 열린 차시 페이지를 확인했습니다.")
                return True

    except Exception as error:
        print(f"  [!] 로그인 확인 중 오류: {error}")
        return False

    return True


def prepare_lesson_page(driver, unit_text=None):
    driver.get(BASE_URL)
    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CLASS_NAME, "txbd-fold-subject"))
        )
    except Exception:
        time.sleep(1)

    try:
        driver.execute_script("window.scrollTo(0, 0);")
    except Exception:
        pass

    try:
        alert = driver.switch_to.alert
        print(f"  -> 알림창 확인: {alert.text}")
        alert.accept()
        time.sleep(1)
    except Exception:
        pass

    try:
        folding_toggles = driver.find_elements(By.CLASS_NAME, "folding-box-toggle")
        for toggle in folding_toggles:
            try:
                parent = toggle.find_element(By.XPATH, "..")
                parent_class = parent.get_attribute("class")
                if "folding-open" not in parent_class:
                    driver.execute_script("arguments[0].click();", toggle)
                    time.sleep(0.5)
            except Exception:
                pass
    except Exception:
        pass

    if unit_text:
        ensure_unit_loaded(driver, unit_text)


def collect_lessons(driver):
    lessons = []
    current_unit_title = ""
    ordered_elements = driver.find_elements(
        By.XPATH,
        "//*[contains(concat(' ', normalize-space(@class), ' '), ' txbd-fold-subject ') "
        "or contains(concat(' ', normalize-space(@class), ' '), ' textbook-chapter ')]",
    )

    for element in ordered_elements:
        try:
            class_name = element.get_attribute("class") or ""
            if "txbd-fold-subject" in class_name:
                current_unit_title = element.text.strip() or current_unit_title
                continue

            if "textbook-chapter" not in class_name:
                continue

            title_el = element.find_element(By.CLASS_NAME, "resource-title")
            title_text = title_el.text.strip()
            if not title_text:
                continue

            unit_title = current_unit_title
            if not unit_title:
                try:
                    unit_title = element.find_element(
                        By.XPATH,
                        "./ancestor::*[.//*[contains(concat(' ', normalize-space(@class), ' '), ' txbd-fold-subject ')]][1]"
                        "//*[contains(concat(' ', normalize-space(@class), ' '), ' txbd-fold-subject ')]",
                    ).text.strip()
                except Exception:
                    unit_title = ""

            lessons.append(
                {"title": title_text, "chapter": element, "unit_title": unit_title}
            )
        except StaleElementReferenceException:
            continue
        except Exception:
            continue

    return lessons


def collect_unit_titles(driver):
    titles = []
    for element in driver.find_elements(By.CLASS_NAME, "txbd-fold-subject"):
        text = element.text.strip()
        if text and text not in titles:
            titles.append(text)
    return titles


def ensure_unit_loaded(driver, unit_text):
    folding_boxes = driver.find_elements(By.CLASS_NAME, "folding-box")
    for folding_box in folding_boxes:
        try:
            subject_el = folding_box.find_element(By.CLASS_NAME, "txbd-fold-subject")
            subject_text = subject_el.text.strip()
        except Exception:
            continue

        if not unit_matches(subject_text, unit_text):
            continue

        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'start', behavior: 'instant'});",
                subject_el,
            )
        except Exception:
            pass

        try:
            box_class = folding_box.get_attribute("class") or ""
            if "folding-open" not in box_class:
                toggle = folding_box.find_element(By.CLASS_NAME, "folding-box-toggle")
                driver.execute_script("arguments[0].click();", toggle)
                time.sleep(0.3)
        except Exception:
            pass

        try:
            WebDriverWait(driver, 4).until(
                lambda d: any(
                    title.text.strip()
                    for title in folding_box.find_elements(By.CLASS_NAME, "resource-title")
                )
            )
        except Exception:
            pass
        return


def extract_numbers(text):
    return re.findall(r"\d+", text or "")


def unit_matches(unit_title, unit_text):
    normalized_title = (unit_title or "").strip()
    normalized_query = (unit_text or "").strip()
    if not normalized_query:
        return True
    if normalized_query in normalized_title:
        return True

    title_numbers = extract_numbers(normalized_title)
    query_numbers = extract_numbers(normalized_query)
    if title_numbers and query_numbers:
        return title_numbers[0] == query_numbers[0]
    return False


def lesson_matches(title_text, lesson_text):
    normalized_title = " ".join((title_text or "").split())
    normalized_lesson = " ".join((lesson_text or "").split())
    if normalized_lesson and normalized_title == normalized_lesson:
        return True

    lesson_nums = extract_numbers(lesson_text)
    title_match = re.search(r"\[(.*?)\]\s*(.*)", title_text)

    if title_match:
        bracket_text = title_match.group(1)
        topic_text = title_match.group(2)
        title_nums = extract_numbers(bracket_text)

        if lesson_nums and title_nums:
            return set(lesson_nums).issubset(set(title_nums))
        if not lesson_nums and lesson_text in topic_text:
            return True
        return lesson_text in title_text

    return lesson_text in title_text


def lesson_reference_candidates(lesson_text, exact_title=None):
    candidates = []
    for value in (exact_title, lesson_text):
        normalized = " ".join((value or "").split())
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return candidates


def lessons_in_unit(lessons, unit_text):
    return [item for item in lessons if unit_matches(item["unit_title"], unit_text)]


def found_unit_titles(lessons):
    titles = []
    for item in lessons:
        unit_title = (item.get("unit_title") or "").strip()
        if unit_title and unit_title not in titles:
            titles.append(unit_title)
    return titles


def click_ppt_for_lesson(driver, unit_text, lesson_text, manual_click=False):
    print(f"\n[STEP 2] '{unit_text}' '{lesson_text}' PPT 열기 시도...")
    prepare_lesson_page(driver, unit_text=unit_text)
    lessons = collect_lessons(driver)
    print(f"  -> 총 {len(lessons)}개의 차시 블록을 확인합니다.")
    unit_lesson_list = lessons_in_unit(lessons, unit_text)

    extracted_title = None

    for item in lessons:
        try:
            title_text = item["title"]
            chapter = item["chapter"]
            current_unit_title = item["unit_title"]
            if not unit_matches(current_unit_title, unit_text):
                continue
            if not lesson_matches(title_text, lesson_text):
                continue

            print(f"  -> 차시를 찾았습니다: [{current_unit_title}] {title_text}")
            extracted_title = title_text

            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
                    chapter,
                )
                driver.execute_script(
                    "arguments[0].style.outline='3px solid #ff7a00'; arguments[0].style.outlineOffset='4px';",
                    chapter,
                )
            except Exception:
                pass

            if manual_click:
                answer = prompt_enter_after_browser_action(
                    "  -> 이미 열린 helper Chrome을 쓰고 있으므로 PPT는 브라우저에서 직접 클릭해주세요.\n"
                    "     클릭을 마쳤으면 엔터를 눌러 계속합니다."
                )
                try:
                    driver.execute_script(
                        "arguments[0].style.outline=''; arguments[0].style.outlineOffset='';",
                        chapter,
                    )
                except Exception:
                    pass
                if answer.lower() == "b":
                    print("  -> PPT 열기를 취소했습니다.")
                    return None
                return extracted_title

            buttons = chapter.find_elements(By.XPATH, ".//a[contains(@class, 'btn')]")
            for btn in buttons:
                btn_text = btn.text.strip()
                if "PPT" not in btn_text.upper():
                    continue

                print("  -> 수업 PPT 버튼을 클릭합니다.")
                before_handles = set(driver.window_handles)
                try:
                    driver.execute_script("arguments[0].click();", btn)
                except Exception:
                    btn.click()

                time.sleep(2)
                after_handles = set(driver.window_handles)
                if len(after_handles) > len(before_handles):
                    new_window = (after_handles - before_handles).pop()
                    driver.switch_to.window(new_window)
                    print(f"  -> 새 창으로 전환 완료: {driver.title}")
                return extracted_title

        except StaleElementReferenceException:
            continue

    print(f"  [!] '{lesson_text}'에 해당하는 차시를 찾지 못했습니다.")
    if unit_lesson_list:
        print(f"  -> 단원 '{unit_text}'에서 찾을 수 있는 차시는 아래와 같습니다.")
        for item in unit_lesson_list:
            print(f"     - {item['title']}")
    else:
        print(f"  -> 단원 '{unit_text}'에 해당하는 목록 자체를 찾지 못했습니다.")
        unit_titles = collect_unit_titles(driver) or found_unit_titles(lessons)
        if unit_titles:
            print("  -> 현재 읽힌 단원 제목:")
            for title in unit_titles:
                print(f"     - {title}")
    return extracted_title


def find_lesson_position(driver, unit_text, lesson_text):
    prepare_lesson_page(driver, unit_text=unit_text)
    lessons = collect_lessons(driver)
    print(f"  -> 총 {len(lessons)}개의 차시 블록을 확인합니다.")

    for index, item in enumerate(lessons):
        if unit_matches(item["unit_title"], unit_text) and lesson_matches(item["title"], lesson_text):
            return lessons, index

    return lessons, -1


def find_lesson_position_from_candidates(driver, unit_text, references):
    prepare_lesson_page(driver, unit_text=unit_text)
    lessons = collect_lessons(driver)
    print(f"  -> 총 {len(lessons)}개의 차시 블록을 확인합니다.")

    for reference in references:
        for index, item in enumerate(lessons):
            if unit_matches(item["unit_title"], unit_text) and lesson_matches(item["title"], reference):
                return lessons, index, reference

    return lessons, -1, None


def open_lesson_by_index(driver, lessons, index, manual_click=False):
    if index < 0 or index >= len(lessons):
        return None

    target = lessons[index]
    title_text = target["title"]
    chapter = target["chapter"]
    unit_title = target.get("unit_title", "")
    print(f"  -> 차시를 찾았습니다: [{unit_title}] {title_text}")

    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
            chapter,
        )
        driver.execute_script(
            "arguments[0].style.outline='3px solid #ff7a00'; arguments[0].style.outlineOffset='4px';",
            chapter,
        )
    except Exception:
        pass

    if manual_click:
        answer = prompt_enter_after_browser_action(
            "  -> 이미 열린 helper Chrome을 쓰고 있으므로 PPT는 브라우저에서 직접 클릭해주세요.\n"
            "     클릭을 마쳤으면 엔터를 눌러 계속합니다."
        )
        try:
            driver.execute_script(
                "arguments[0].style.outline=''; arguments[0].style.outlineOffset='';",
                chapter,
            )
        except Exception:
            pass
        if answer.lower() == "b":
            print("  -> PPT 열기를 취소했습니다.")
            return None
        return title_text

    buttons = chapter.find_elements(By.XPATH, ".//a[contains(@class, 'btn')]")
    for btn in buttons:
        btn_text = btn.text.strip()
        if "PPT" not in btn_text.upper():
            continue

        print("  -> 수업 PPT 버튼을 클릭합니다.")
        before_handles = set(driver.window_handles)
        try:
            driver.execute_script("arguments[0].click();", btn)
        except Exception:
            btn.click()

        time.sleep(2)
        after_handles = set(driver.window_handles)
        if len(after_handles) > len(before_handles):
            new_window = (after_handles - before_handles).pop()
            driver.switch_to.window(new_window)
            print(f"  -> 새 창으로 전환 완료: {driver.title}")
        return title_text

    print("  [!] 해당 차시에서 PPT 버튼을 찾지 못했습니다.")
    return None


def run_lesson(unit_text, lesson_text, pdf_path=None, save_name=None, source_name=None):
    driver, reused_existing_browser = attach_to_chrome()
    if not driver:
        return False

    wait = WebDriverWait(driver, 10)

    print("\n" + "=" * 55)
    print(f" 음악 수업 도우미 시작 ({unit_text} / {lesson_text})")
    print("=" * 55)

    login_ok = login_if_needed(driver, wait, reuse_existing_browser=reused_existing_browser)
    if not login_ok:
        print("[!] 로그인 또는 차시 페이지 준비가 완료되지 않아 작업을 중단합니다.")
        return False
    exact_title = click_ppt_for_lesson(
        driver,
        unit_text,
        lesson_text,
        manual_click=reused_existing_browser,
    )

    if pdf_path and exact_title:
        print("\n[STEP 3] PDF에서 해당 차시를 추출합니다.")
        import extract_pdf

        extract_pdf.do_extract(pdf_path, exact_title, unit_text=unit_text)
    elif pdf_path:
        print("\n[STEP 3] 정확한 차시 제목을 찾지 못해 PDF 추출은 건너뜁니다.")

    if not exact_title:
        print("[관리] 차시를 찾지 못했으므로 저장 및 최근 실행 기록 갱신은 건너뜁니다.")
        return False

    if save_name:
        class_manager.add_saved_class(
            save_name,
            unit_text,
            lesson_text,
            pdf_path,
            exact_title=exact_title,
        )
        print(f"\n[관리] '{save_name}' 이름으로 수업 구성을 저장했습니다.")

    class_manager.record_recent_run(
        unit_text,
        lesson_text,
        pdf_path=pdf_path,
        exact_title=exact_title,
        saved_name=source_name or save_name,
    )
    print("[관리] 최근 실행 기록도 저장했습니다.")
    return True


def find_adjacent_lesson(lessons, unit_text, references, offset):
    current_index = -1
    for index, item in enumerate(lessons):
        if not unit_matches(item["unit_title"], unit_text):
            continue
        if any(lesson_matches(item["title"], reference) for reference in references):
            current_index = index
            break

    if current_index == -1:
        return None

    target_index = current_index + offset
    if 0 <= target_index < len(lessons):
        return lessons[target_index]
    return None


def sync_saved_class_progress(saved_name, unit_text, exact_title, pdf_path):
    if not saved_name or not exact_title:
        return

    class_manager.update_saved_class(
        saved_name,
        unit=unit_text,
        lesson=exact_title,
        pdf_path=pdf_path or "",
        exact_title=exact_title,
    )


def confirm_yes_no(message, default=False):
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        answer = prompt_input(message + suffix).strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes", "ㅇ", "예"}:
            return True
        if answer in {"n", "no", "ㄴ", "아니오"}:
            return False
        print("[!] y 또는 n으로 입력해주세요.")


def run_menu_action(action):
    while True:
        result = action()
        if result == BACK:
            return True
        if result == MENU:
            return True
        return result


def run_adjacent_lesson(offset=1):
    recent_runs = class_manager.list_recent_runs(limit=1)
    if not recent_runs:
        print("[!] 최근 실행 기록이 없어 다음 차시를 찾을 수 없습니다.")
        return False

    latest = recent_runs[0]
    unit_text = latest["unit"]
    lesson_text = latest["lesson"]
    exact_title_hint = latest.get("exact_title") or ""
    pdf_path = latest.get("pdf_path") or None
    saved_name = latest.get("saved_name") or ""
    direction_label = "다음" if offset > 0 else "이전"

    driver, reused_existing_browser = attach_to_chrome()
    if not driver:
        return False

    wait = WebDriverWait(driver, 10)
    print("\n" + "=" * 55)
    print(f" 최근 실행 기준 {direction_label} 차시 찾기 ({unit_text} / {lesson_text})")
    print("=" * 55)

    login_ok = login_if_needed(driver, wait, reuse_existing_browser=reused_existing_browser)
    if not login_ok:
        print("[!] 로그인 또는 차시 페이지 준비가 완료되지 않아 작업을 중단합니다.")
        return False

    reference_candidates = lesson_reference_candidates(lesson_text, exact_title_hint)
    if saved_name:
        saved = class_manager.get_saved_class(saved_name)
        if saved:
            reference_candidates = lesson_reference_candidates(
                lesson_text,
                exact_title_hint or saved.get("exact_title") or saved.get("lesson"),
            )

    print(f"\n[STEP 2] 최근 실행한 '{lesson_text}'의 {direction_label} 차시를 찾습니다...")
    lessons, current_index, matched_reference = find_lesson_position_from_candidates(
        driver, unit_text, reference_candidates
    )
    if current_index == -1:
        print(f"  [!] 최근 차시 '{unit_text} / {lesson_text}'를 현재 목록에서 찾지 못했습니다.")
        print("  -> 최근 기록이 잘못 저장된 것 같다면 저장된 수업을 다시 실행해 현재 차시를 갱신해주세요.")
        return False

    if matched_reference and matched_reference != lesson_text:
        print(f"  -> 최근 기록 대신 실제 제목 기준으로 복구했습니다: {matched_reference}")

    target_lesson = find_adjacent_lesson(lessons, unit_text, reference_candidates, offset)
    if not target_lesson:
        print(f"  [!] {direction_label} 차시가 더 이상 없습니다.")
        return False

    target_index = lessons.index(target_lesson)
    target_title = target_lesson["title"]
    print(f"  -> {direction_label} 차시 후보: [{target_lesson['unit_title']}] {target_title}")
    exact_title = open_lesson_by_index(
        driver,
        lessons,
        target_index,
        manual_click=reused_existing_browser,
    )

    if pdf_path and exact_title:
        print("\n[STEP 3] PDF에서 해당 차시를 추출합니다.")
        import extract_pdf

        extract_pdf.do_extract(pdf_path, exact_title, unit_text=target_lesson["unit_title"])
    elif pdf_path:
        print("\n[STEP 3] 정확한 차시 제목을 찾지 못해 PDF 추출은 건너뜁니다.")

    class_manager.record_recent_run(
        target_lesson["unit_title"],
        target_title,
        pdf_path=pdf_path,
        exact_title=exact_title,
        saved_name=saved_name,
    )
    if saved_name and exact_title:
        should_update = confirm_yes_no(
            f"저장된 수업 '{saved_name}'도 [{target_lesson['unit_title']}] {exact_title}로 업데이트할까요?"
        )
        if should_update:
            sync_saved_class_progress(saved_name, target_lesson["unit_title"], exact_title, pdf_path)
            print("[관리] 저장된 수업 정보도 업데이트했습니다.")
        else:
            print("[관리] 저장된 수업 정보는 유지하고 최근 실행 기록만 남겼습니다.")
    print(f"[관리] {direction_label} 차시 실행 기록도 저장했습니다.")
    return True


def print_saved_classes():
    saved_classes = class_manager.list_saved_classes()
    if not saved_classes:
        print("저장된 수업 구성이 없습니다.")
        return

    print("\n[저장된 수업 구성]")
    for index, item in enumerate(saved_classes, start=1):
        pdf_label = Path(item["pdf_path"]).name if item["pdf_path"] else "PDF 미지정"
        title_label = item.get("exact_title") or "제목 미저장"
        print(
            f"{index}. {item['name']} | {item['unit']} | {item['lesson']} | "
            f"{title_label} | {pdf_label}"
        )


def print_recent_runs(limit):
    recent_runs = class_manager.list_recent_runs(limit=limit)
    if not recent_runs:
        print("최근 실행 기록이 없습니다.")
        return

    print(f"\n[최근 실행 {len(recent_runs)}건]")
    for index, item in enumerate(recent_runs, start=1):
        name_label = item["saved_name"] or "직접 실행"
        title_label = item["exact_title"] or "제목 확인 안 됨"
        print(
            f"{index}. {item['ran_at']} | {name_label} | {item['unit']} | "
            f"{item['lesson']} | {title_label}"
        )


def prompt_input(message):
    try:
        return input(message).strip()
    except EOFError:
        return ""


def prompt_with_nav(message, *, allow_blank=False):
    value = prompt_input(message)
    lowered = value.lower()
    if lowered in {"b", "back", "뒤로"}:
        return BACK
    if lowered in {"m", "menu", "메뉴"}:
        return MENU
    if not value and not allow_blank:
        print("[!] 값을 입력해주세요. 뒤로가기는 b, 메뉴로 가기는 m 입니다.")
        return None
    return value


def prompt_enter_after_browser_action(message):
    print(message)
    return prompt_input("브라우저 작업을 마쳤으면 엔터를 누르세요 (취소: b): ")


def interactive_menu():
    def create_run_flow():
        unit = prompt_with_nav("단원을 입력하세요 (예: 1단원): ")
        if unit in {BACK, MENU}:
            return unit
        if unit is None:
            return create_run_flow()

        lesson = prompt_with_nav("차시를 입력하세요 (예: 1~2차시): ")
        if lesson in {BACK, MENU}:
            return lesson
        if lesson is None:
            return create_run_flow()

        pdf_path = choose_pdf_from_folder()
        if pdf_path in {BACK, MENU}:
            return pdf_path

        save_name = prompt_with_nav("이 구성을 저장할 이름을 입력하세요 (없으면 엔터): ", allow_blank=True)
        if save_name in {BACK, MENU}:
            return save_name

        return run_lesson(unit, lesson, pdf_path=pdf_path or None, save_name=save_name or None)

    def create_save_flow():
        save_name = prompt_with_nav("저장 이름을 입력하세요: ")
        if save_name in {BACK, MENU}:
            return save_name
        if save_name is None:
            return create_save_flow()

        unit = prompt_with_nav("단원을 입력하세요 (예: 1단원): ")
        if unit in {BACK, MENU}:
            return unit
        if unit is None:
            return create_save_flow()

        lesson = prompt_with_nav("차시를 입력하세요 (예: 1~2차시): ")
        if lesson in {BACK, MENU}:
            return lesson
        if lesson is None:
            return create_save_flow()

        pdf_path = choose_pdf_from_folder()
        if pdf_path in {BACK, MENU}:
            return pdf_path

        class_manager.add_saved_class(save_name, unit, lesson, pdf_path or None)
        print(f"[OK] '{save_name}' 수업 구성을 저장했습니다.")
        return True

    def create_saved_run_flow():
        save_name = prompt_with_nav("실행할 저장 이름을 입력하세요: ")
        if save_name in {BACK, MENU}:
            return save_name
        if save_name is None:
            return create_saved_run_flow()

        saved = class_manager.get_saved_class(save_name)
        if not saved:
            print(f"[!] '{save_name}' 저장 수업을 찾지 못했습니다.")
            return True

        default_pdf = saved.get("pdf_path") if saved else None
        pdf_path = choose_pdf_from_folder(default_path=default_pdf)
        if pdf_path in {BACK, MENU}:
            return pdf_path

        return run_saved_class(save_name, pdf_override=pdf_path or None)

    def create_delete_flow():
        save_name = prompt_with_nav("삭제할 저장 이름을 입력하세요: ")
        if save_name in {BACK, MENU}:
            return save_name
        if save_name is None:
            return create_delete_flow()

        deleted = class_manager.delete_saved_class(save_name)
        if deleted:
            print(f"[OK] '{save_name}' 수업 구성을 삭제했습니다.")
        else:
            print(f"[!] '{save_name}' 수업 구성을 찾지 못했습니다.")
        return True

    def create_recent_flow():
        limit_text = prompt_with_nav("몇 개까지 볼까요? (기본값 10): ", allow_blank=True)
        if limit_text in {BACK, MENU}:
            return limit_text
        limit = int(limit_text) if isinstance(limit_text, str) and limit_text.isdigit() else 10
        print_recent_runs(limit=max(1, limit))
        return True

    while True:
        print("\n" + "=" * 55)
        print("음악 수업 도우미")
        print("=" * 55)
        print("입력 중 `b`는 뒤로가기, `m`은 메인 메뉴입니다.")
        print("1. 새 차시 실행")
        print("2. 수업 구성 저장")
        print("3. 저장된 수업 목록 보기")
        print("4. 저장된 수업 실행")
        print("5. 저장된 수업 삭제")
        print("6. 최근 실행 기록 보기")
        print("7. 다음 차시 실행")
        print("8. 이전 차시 실행")
        print("0. 종료")

        menu = prompt_input("원하는 메뉴 번호를 입력하세요: ")

        if menu == "1":
            run_menu_action(create_run_flow)
        elif menu == "2":
            run_menu_action(create_save_flow)
        elif menu == "3":
            print_saved_classes()
        elif menu == "4":
            run_menu_action(create_saved_run_flow)
        elif menu == "5":
            run_menu_action(create_delete_flow)
        elif menu == "6":
            run_menu_action(create_recent_flow)
        elif menu == "7":
            run_adjacent_lesson(offset=1)
        elif menu == "8":
            run_adjacent_lesson(offset=-1)
        elif menu == "0":
            print("프로그램을 종료합니다.")
            return True
        else:
            print("[!] 올바른 메뉴 번호를 입력해주세요.")


def build_parser():
    parser = argparse.ArgumentParser(description="음악 수업용 차시 열기 및 PDF 추출 도우미")
    subparsers = parser.add_subparsers(dest="command")

    menu_parser = subparsers.add_parser("menu", help="대화형 메뉴 실행")
    menu_parser.set_defaults(command="menu")

    run_parser = subparsers.add_parser("run", help="지정한 차시를 바로 실행")
    run_parser.add_argument("unit", help="단원명")
    run_parser.add_argument("lesson", help="차시명")
    run_parser.add_argument("--pdf", dest="pdf_path", help="교사용 PDF 경로")
    run_parser.add_argument("--save", dest="save_name", help="이 설정을 저장할 이름")

    saved_parser = subparsers.add_parser("saved", help="저장한 수업 구성 관리")
    saved_subparsers = saved_parser.add_subparsers(dest="saved_command")

    saved_list_parser = saved_subparsers.add_parser("list", help="저장된 수업 구성 목록")
    saved_list_parser.set_defaults(saved_command="list")

    saved_add_parser = saved_subparsers.add_parser("add", help="수업 구성을 저장")
    saved_add_parser.add_argument("name", help="저장 이름")
    saved_add_parser.add_argument("unit", help="단원명")
    saved_add_parser.add_argument("lesson", help="차시명")
    saved_add_parser.add_argument("--pdf", dest="pdf_path", help="교사용 PDF 경로")

    saved_run_parser = saved_subparsers.add_parser("run", help="저장된 수업 구성을 실행")
    saved_run_parser.add_argument("name", help="실행할 저장 이름")
    saved_run_parser.add_argument("--pdf", dest="pdf_override", help="PDF 경로 덮어쓰기")

    saved_delete_parser = saved_subparsers.add_parser("delete", help="저장된 수업 구성 삭제")
    saved_delete_parser.add_argument("name", help="삭제할 저장 이름")

    recent_parser = subparsers.add_parser("recent", help="최근 실행 기록 보기")
    recent_parser.add_argument("--limit", type=int, default=5, help="표시할 개수")

    next_parser = subparsers.add_parser("next", help="최근 실행 기준 다음 차시 실행")
    next_parser.set_defaults(command="next")

    previous_parser = subparsers.add_parser("previous", help="최근 실행 기준 이전 차시 실행")
    previous_parser.set_defaults(command="previous")

    return parser


def run_saved_class(name, pdf_override=None):
    saved = class_manager.get_saved_class(name)
    if not saved:
        print(f"[!] '{name}' 저장 수업을 찾지 못했습니다.")
        return False

    pdf_path = pdf_override if pdf_override is not None else saved.get("pdf_path") or None
    return run_lesson(
        saved["unit"],
        saved.get("exact_title") or saved["lesson"],
        pdf_path=pdf_path,
        source_name=saved["name"],
    )


def handle_command(args):
    if args.command == "menu":
        return interactive_menu()

    if args.command == "run":
        return run_lesson(args.unit, args.lesson, pdf_path=args.pdf_path, save_name=args.save_name)

    if args.command == "saved":
        if args.saved_command in (None, "list"):
            print_saved_classes()
            return True
        if args.saved_command == "add":
            class_manager.add_saved_class(args.name, args.unit, args.lesson, args.pdf_path)
            print(f"[OK] '{args.name}' 수업 구성을 저장했습니다.")
            return True
        if args.saved_command == "run":
            return run_saved_class(args.name, pdf_override=args.pdf_override)
        if args.saved_command == "delete":
            deleted = class_manager.delete_saved_class(args.name)
            if deleted:
                print(f"[OK] '{args.name}' 수업 구성을 삭제했습니다.")
            else:
                print(f"[!] '{args.name}' 수업 구성을 찾지 못했습니다.")
            return deleted

    if args.command == "recent":
        print_recent_runs(limit=max(1, args.limit))
        return True

    if args.command == "next":
        return run_adjacent_lesson(offset=1)

    if args.command == "previous":
        return run_adjacent_lesson(offset=-1)

    return False


def main():
    parser = build_parser()

    # Backward compatibility:
    # python music_helper.py <unit> <lesson> [pdf_path]
    if len(sys.argv) >= 3 and sys.argv[1] not in {
        "run",
        "saved",
        "recent",
        "menu",
        "next",
        "previous",
        "-h",
        "--help",
    }:
        unit_text = sys.argv[1]
        lesson_text = sys.argv[2]
        pdf_path = sys.argv[3] if len(sys.argv) > 3 else None
        run_lesson(unit_text, lesson_text, pdf_path=pdf_path)
        return

    args = parser.parse_args()
    if not handle_command(args):
        parser.print_help()


if __name__ == "__main__":
    main()
