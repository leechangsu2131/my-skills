"""
하이클래스 하이톡(HiTalk) 시험점수 개별 전송 스크립트
====================================================
구글시트에서 학생별 점수를 읽어, 하이톡으로 학부모에게 개별 메시지를 보냅니다.

흐름:
  1. config.json에서 설정 로드
  2. gws CLI로 구글시트에서 점수 데이터 읽기
  3. Selenium으로 하이클래스 하이톡에 연결
  4. 각 학생에 대해: 검색 → 클릭 → 메시지 입력 → 전송

사용법:
  1. launch_chrome_hiclass.bat 으로 크롬 실행
  2. 하이클래스 직접 로그인 → 하이톡 페이지 이동
  3. python hitalk_sender.py              (실제 전송)
  4. python hitalk_sender.py --dry-run    (미리보기만)
"""

import io
import json
import subprocess
import time
import sys
import os
import argparse
import shutil

def _wrap_stream_utf8(stream):
    """pythonw 등 콘솔이 없는 환경에서도 안전하게 UTF-8 래핑"""
    if stream is None or not hasattr(stream, "buffer"):
        return stream
    try:
        return io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace")
    except Exception:
        return stream


# Windows 터미널 UTF-8 인코딩 설정
if sys.platform == "win32":
    sys.stdout = _wrap_stream_utf8(getattr(sys, "stdout", None))
    sys.stderr = _wrap_stream_utf8(getattr(sys, "stderr", None))

SELENIUM_IMPORT_ERROR = None
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import (
        NoSuchElementException, StaleElementReferenceException, TimeoutException
    )
except ModuleNotFoundError as exc:
    SELENIUM_IMPORT_ERROR = exc
    webdriver = None
    Options = None
    By = None
    WebDriverWait = None
    EC = None
    Keys = None
    ActionChains = None
    NoSuchElementException = Exception
    StaleElementReferenceException = Exception
    TimeoutException = Exception

# ──────────────────────────────────────
# 설정 로드
# ──────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
REQUIREMENTS_PATH = os.path.join(SCRIPT_DIR, "requirements.txt")
DEFAULT_MESSAGE_FILE_PATH = os.path.join(SCRIPT_DIR, "custom_message_template.txt")
PLACEHOLDER_SPREADSHEET_MARKERS = (
    "여기에",
    "구글시트_URL",
    "구글시트_",
)
GWS_EXECUTABLE = None


def is_placeholder_spreadsheet_id(value):
    """예시용 spreadsheet_id가 아직 남아 있는지 확인"""
    value = (value or "").strip()
    return (
        not value
        or any(value.startswith(marker) for marker in PLACEHOLDER_SPREADSHEET_MARKERS)
        or "복사한_ID" in value
    )


def print_dependency_help(missing_dependencies):
    """설치되지 않은 필수 의존성 안내"""
    print("[✗] 실행에 필요한 도구가 설치되지 않았습니다.")
    print("    아래 명령을 먼저 실행해 주세요:")
    for name, install_command in missing_dependencies:
        print(f"    - {name}: {install_command}")
    print("    설치 후 새 터미널을 열고 다시 실행하면 가장 안전합니다.")


def find_gws_executable():
    """Windows에서는 gws.cmd 경로를 우선 사용"""
    candidates = ["gws.cmd", "gws"] if os.name == "nt" else ["gws"]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def check_runtime_dependencies():
    """실행 전에 필요한 도구가 설치되어 있는지 확인"""
    global GWS_EXECUTABLE
    missing_dependencies = []

    if SELENIUM_IMPORT_ERROR is not None:
        missing_dependencies.append(
            ("selenium", f'python -m pip install -r "{REQUIREMENTS_PATH}"')
        )

    GWS_EXECUTABLE = find_gws_executable()
    if GWS_EXECUTABLE is None:
        missing_dependencies.append(
            ("gws CLI", "npm install -g @aspect-build/gws")
        )

    if missing_dependencies:
        print_dependency_help(missing_dependencies)
        sys.exit(1)


def load_config(config_path=CONFIG_PATH):
    """config.json 로드"""
    if not os.path.exists(config_path):
        print(f"[✗] config.json을 찾을 수 없습니다: {config_path}")
        print("    config.json 파일을 먼저 설정해 주세요.")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    if is_placeholder_spreadsheet_id(config.get("spreadsheet_id", "")):
        print("[✗] config.json의 spreadsheet_id를 실제 구글시트 ID로 바꿔주세요.")
        print("    시트 URL: https://docs.google.com/spreadsheets/d/<여기가_ID>/edit")
        sys.exit(1)

    return config


def resolve_path(base_path, maybe_relative_path):
    """상대 경로를 기준 파일 위치에 맞춰 절대 경로로 변환"""
    if not maybe_relative_path:
        return ""
    if os.path.isabs(maybe_relative_path):
        return maybe_relative_path
    return os.path.join(os.path.dirname(base_path), maybe_relative_path)


def load_message_template(config, args):
    """CLI, 파일, config 중에서 사용자 지정 메시지 템플릿을 선택"""
    if args.custom_message:
        return args.custom_message.strip()

    if args.message_file:
        message_file_path = resolve_path(args.config or CONFIG_PATH, args.message_file)
        with open(message_file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    if config.get("custom_message_template"):
        return str(config["custom_message_template"]).strip()

    if config.get("custom_message_file"):
        message_file_path = resolve_path(
            args.config or CONFIG_PATH,
            config["custom_message_file"],
        )
        with open(message_file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    if os.path.exists(DEFAULT_MESSAGE_FILE_PATH):
        with open(DEFAULT_MESSAGE_FILE_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()

    return None


# ──────────────────────────────────────
# 구글시트 데이터 읽기
# ──────────────────────────────────────
def read_scores(config):
    """gws CLI로 구글시트에서 점수 데이터 읽기"""
    spreadsheet_id = config["spreadsheet_id"]
    range_name = config["range"]

    print(f"\n📊 구글시트 읽는 중... (ID: {spreadsheet_id[:8]}...)")

    params_json = json.dumps({
        "spreadsheetId": spreadsheet_id,
        "range": range_name
    }, ensure_ascii=False)

    try:
        result = subprocess.run(
            [
                GWS_EXECUTABLE or "gws.cmd",
                "sheets",
                "spreadsheets",
                "values",
                "get",
                "--params",
                params_json,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError:
        print_dependency_help([
            ("gws CLI", "npm install -g @aspect-build/gws")
        ])
        sys.exit(1)

    if result.returncode != 0:
        print(f"[✗] 구글시트 읽기 실패: {result.stderr}")
        sys.exit(1)

    data = json.loads(result.stdout)
    return data.get("values", [])


def parse_students(raw_data, config):
    """raw 데이터에서 학생 이름-점수 리스트 추출"""
    name_col = config.get("name_column", 1)   # B열 = index 1
    score_col = config.get("score_column", 2)  # C열 = index 2

    if not raw_data or len(raw_data) < 2:
        print("[✗] 시트에 데이터가 없습니다.")
        return []

    header = raw_data[0]
    print(f"  📋 헤더: {header}")

    students = []
    for row in raw_data[1:]:
        if len(row) > max(name_col, score_col):
            name = str(row[name_col]).strip()
            score = str(row[score_col]).strip()
            if name and score:
                students.append({"name": name, "score": score})

    print(f"  ✅ {len(students)}명의 학생 데이터 로드 완료")
    return students


# ──────────────────────────────────────
# 코멘트 & 메시지 생성
# ──────────────────────────────────────
def get_comment(score, config):
    """점수 기반 코멘트 생성"""
    comments = config.get("comments", {})
    thresholds = config.get("comment_thresholds", {})

    try:
        s = int(score)
    except (ValueError, TypeError):
        return "수고했어요! 😊"

    # threshold 높은 순으로 정렬해서 매칭
    sorted_levels = sorted(
        thresholds.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for level, threshold in sorted_levels:
        if s >= threshold:
            return comments.get(level, "수고했어요! 😊")

    return comments.get("support", "수고했어요! 😊")


def build_message(student_name, score, config, custom_message=None):
    """전송할 메시지 생성"""
    subject = config.get("subject", "시험")
    comment = get_comment(score, config)

    if custom_message:
        template = (
            custom_message
            .replace("[학생]", "{student_name}")
            .replace("[과목]", "{subject}")
            .replace("[점수]", "{score}")
            .replace("[코멘트]", "{comment}")
        )
    else:
        template = config.get(
            "message_template",
            "📝 {subject} 결과 안내\n\n{student_name} 학생의 점수: {score}점\n💬 {comment}\n\n궁금하신 점은 편하게 문의해 주세요. 😊"
        )

    msg = template.format(
        subject=subject,
        student_name=student_name,
        score=score,
        comment=comment
    )
    return msg


# ──────────────────────────────────────
# DOM 셀렉터 캐시 로드 (explore_dom.py 결과)
# ──────────────────────────────────────
DOM_SELECTORS_PATH = os.path.join(SCRIPT_DIR, "dom_selectors.json")
_cached_selectors = {}

def load_dom_selectors():
    """explore_dom.py가 저장한 셀렉터 캐시를 로드"""
    global _cached_selectors
    if os.path.exists(DOM_SELECTORS_PATH):
        with open(DOM_SELECTORS_PATH, "r", encoding="utf-8") as f:
            _cached_selectors = json.load(f)
        print(f"  💾 DOM 셀렉터 캐시 로드: {len(_cached_selectors)}개 항목")
    return _cached_selectors


# ──────────────────────────────────────
# Selenium 브라우저 연결 & 조작
# ──────────────────────────────────────
def attach(port=9223):
    """Chrome remote debugging port로 연결"""
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{port}")
    try:
        driver = webdriver.Chrome(options=opts)
    except Exception as e:
        print(f"[✗] 크롬 연결 실패: {e}")
        print("    launch_chrome_hiclass.bat를 먼저 실행하고,")
        print("    하이클래스에 로그인 후 하이톡 페이지를 열어주세요.")
        sys.exit(1)

    print(f"[✓] 크롬 연결 성공: {driver.title}")
    return driver


def ensure_single_hitalk_tab(driver):
    """하이톡 탭이 하나만 열려 있는지 확인"""
    current_handle = driver.current_window_handle
    hitalk_tabs = []

    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "hitalk" in (driver.current_url or "").lower():
            hitalk_tabs.append({
                "handle": handle,
                "title": driver.title,
                "url": driver.current_url,
            })

    if not hitalk_tabs:
        driver.switch_to.window(current_handle)
        print("[✗] 하이톡 탭을 찾지 못했습니다.")
        print("    하이클래스에 로그인한 뒤 하이톡 탭 하나만 열어주세요.")
        sys.exit(1)

    if len(hitalk_tabs) > 1:
        driver.switch_to.window(current_handle)
        print("[✗] 하이톡 탭이 여러 개 열려 있습니다.")
        print("    같은 계정/화면이 여러 탭에 있으면 잘못된 대화창으로 전송될 수 있습니다.")
        print("    하이톡 탭을 하나만 남기고 다시 실행해 주세요.")
        for idx, tab in enumerate(hitalk_tabs, 1):
            print(f"    {idx}. {tab['title']} — {tab['url']}")
        sys.exit(1)

    driver.switch_to.window(hitalk_tabs[0]["handle"])
    return hitalk_tabs[0]


def wait_for_hitalk_ready(driver, timeout=15):
    """하이톡 페이지가 완전히 로드될 때까지 대기"""
    print("\n⏳ 하이톡 페이지 로딩 대기 중...")

    try:
        # 검색 입력란 또는 대화상대 목록이 나타날 때까지 대기
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "input[placeholder*='이름'], input[placeholder*='검색'], "
                "[class*='search'], [class*='contact'], [class*='talk']"
            ))
        )
        print("  ✅ 하이톡 로드 완료")
        return True
    except TimeoutException:
        # 좀 더 범용적으로 재시도
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "input"))
            )
            print("  ✅ 페이지 로드 확인 (범용)")
            return True
        except TimeoutException:
            print("  [⚠] 하이톡 페이지가 제대로 로드되지 않았을 수 있습니다.")
            return False


def find_search_input(driver):
    """하이톡 검색 입력란 찾기"""
    selectors = [
        "input[placeholder*='이름']",
        "input[placeholder*='검색']",
        "input[placeholder*='태그']",
        "input[type='text'][class*='search']",
        "input[type='search']",
    ]

    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                return el
        except NoSuchElementException:
            continue

    # 폴백: 모든 input 중 placeholder에 검색 관련 텍스트가 있는 것
    inputs = driver.find_elements(By.TAG_NAME, "input")
    for inp in inputs:
        ph = inp.get_attribute("placeholder") or ""
        if any(kw in ph for kw in ["이름", "검색", "태그"]):
            if inp.is_displayed():
                return inp

    return None


def get_active_chat_header(driver):
    """현재 우측 대화창 상단의 상대 이름 텍스트"""
    selectors = [
        ".chatting-top-wrap .chatting-opponent-info p",
        ".chatting-opponent-info p",
        ".chatting-top-wrap p",
    ]

    for sel in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                if not el.is_displayed():
                    continue
                text = el.text.strip()
                if text:
                    return text.splitlines()[0].strip()
        except Exception:
            continue

    try:
        header_text = driver.execute_script("""
            const candidates = [];
            for (const el of document.querySelectorAll('body *')) {
                const rect = el.getBoundingClientRect();
                const text = (el.innerText || '').trim();
                if (!text) continue;
                const style = getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') continue;
                if (rect.left < window.innerWidth * 0.35) continue;
                if (rect.top > 100) continue;
                if (rect.width < 20 || rect.height < 12) continue;
                candidates.push(text.split('\\n')[0].trim());
            }
            return candidates[0] || '';
        """)
        return header_text.strip()
    except Exception:
        return ""


def wait_for_chat_header(driver, student_name, previous_header="", timeout=5):
    """우측 대화창 상단 이름이 학생명과 일치할 때까지 대기"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        header = get_active_chat_header(driver)
        if student_name in header:
            return header
        time.sleep(0.3)
    return ""


def search_student(driver, student_name, wait=WebDriverWait):
    """검색란에 학생 이름 입력하여 검색"""
    search_input = find_search_input(driver)
    if not search_input:
        print(f"  [⚠] 검색란을 찾을 수 없습니다. 직접 학생 목록에서 찾습니다.")
        return False

    # 검색란 클리어 후 입력
    search_input.click()
    time.sleep(0.3)
    search_input.clear()
    time.sleep(0.2)
    # Ctrl+A로 확실히 클리어
    search_input.send_keys(Keys.CONTROL + "a")
    time.sleep(0.1)
    search_input.send_keys(Keys.DELETE)
    time.sleep(0.2)

    # 학생 이름 입력
    search_input.send_keys(student_name)
    time.sleep(1.5)  # 검색 결과 로딩 대기

    return True


def click_student(driver, student_name, timeout=5):
    """왼쪽 대화상대 목록에서 학생/학부모 항목 클릭"""
    deadline = time.time() + timeout
    previous_header = get_active_chat_header(driver)

    while time.time() < deadline:
        # 반드시 왼쪽 대화상대 목록 안에서만 찾는다.
        candidate_selectors = [
            ".profile-info-wrap",
            ".profile-text-wrap.single-name",
            ".profile-text-wrap",
            ".name",
        ]

        for sel in candidate_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, sel)
            except Exception:
                continue

            for el in elements:
                try:
                    if not el.is_displayed():
                        continue

                    text = el.text.strip()
                    if student_name not in text:
                        continue

                    # 학생 이름이 들어 있는 항목만 클릭 대상으로 인정
                    if "학부모" not in text and "(" not in text and student_name != text:
                        continue

                    target = el
                    for _ in range(4):
                        cls = (target.get_attribute("class") or "").lower()
                        if "profile-info-wrap" in cls:
                            break
                        parent = target.find_element(By.XPATH, "..")
                        if not parent:
                            break
                        target = parent

                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});",
                        target
                    )
                    time.sleep(0.2)

                    try:
                        target.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", target)

                    header = wait_for_chat_header(
                        driver,
                        student_name,
                        previous_header=previous_header,
                        timeout=3,
                    )
                    if header:
                        print(f"  ✅ '{student_name}' 학생 선택 완료 → {header}")
                        time.sleep(0.5)
                        return True
                except (StaleElementReferenceException, Exception):
                    continue

        time.sleep(0.5)

    print(f"  [✗] '{student_name}' 학생을 목록에서 찾지 못했습니다.")
    return False


def find_chat_input(driver):
    """채팅 메시지 입력란 찾기"""
    selectors = [
        "textarea[placeholder*='Enter']",
        "textarea[placeholder*='enter']",
        "textarea[placeholder*='줄바꿈']",
        "textarea[placeholder*='메시지']",
        "div[contenteditable='true']",
        "textarea",
    ]

    for sel in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                if el.is_displayed():
                    # 검색란이 아닌 채팅 입력란인지 확인
                    ph = (el.get_attribute("placeholder") or "").lower()
                    el_type = el.get_attribute("type") or ""
                    tag = el.tag_name.lower()

                    # textarea이거나, contenteditable div이면 채팅 입력란일 가능성 높음
                    if tag == "textarea":
                        return el
                    if tag == "div" and el.get_attribute("contenteditable") == "true":
                        return el
        except NoSuchElementException:
            continue

    return None


def type_message_with_newlines(driver, chat_input, message):
    """줄바꿈을 Shift+Enter로 처리하면서 메시지 입력"""
    chat_input.click()
    time.sleep(0.3)

    lines = message.split("\n")
    actions = ActionChains(driver)

    for i, line in enumerate(lines):
        if line:  # 빈 줄이 아닐 때만 텍스트 입력
            actions.send_keys(line)
        if i < len(lines) - 1:
            # 줄바꿈: Shift + Enter
            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT)

    actions.perform()
    time.sleep(0.5)


def clear_chat_input(driver, chat_input=None):
    """채팅 입력란의 현재 초안을 지운다."""
    chat_input = chat_input or find_chat_input(driver)
    if not chat_input:
        return False

    chat_input.click()
    time.sleep(0.2)
    chat_input.send_keys(Keys.CONTROL + "a")
    time.sleep(0.1)
    chat_input.send_keys(Keys.DELETE)
    time.sleep(0.2)

    # contenteditable div는 키 입력만으로 남는 경우가 있어 JS 폴백도 추가
    try:
        if chat_input.tag_name.lower() == "textarea":
            driver.execute_script("arguments[0].value = '';", chat_input)
        elif chat_input.get_attribute("contenteditable") == "true":
            driver.execute_script("arguments[0].innerHTML = '';", chat_input)
    except Exception:
        pass

    time.sleep(0.2)
    return True


def rehearse_all(driver, students, config, template):
    """실제 전송 없이 각 대화방에서 테스트 문구를 입력 후 삭제"""
    delay = max(1, min(config.get("delay_between_students", 3), 2))
    success_count = 0
    fail_list = []
    log_lines = []

    print(f"\n{'=' * 60}")
    print(f"  🧪 안전 리허설 시작 — 총 {len(students)}명")
    print(f"{'=' * 60}")
    print("  실제 전송은 하지 않고, 입력창에 테스트 문구를 띄운 뒤 바로 지웁니다.")

    for i, st in enumerate(students, 1):
        name = st["name"]
        rehearsal_message = template.format(student_name=name)

        print(f"\n{'─' * 50}")
        print(f"  [{i}/{len(students)}] {name}")
        print(f"{'─' * 50}")

        search_student(driver, name)
        if not click_student(driver, name):
            print(f"    [✗] '{name}' 학생을 목록에서 찾을 수 없어 건너뜁니다.")
            fail_list.append(name)
            clear_search(driver)
            log_lines.append(f"FAIL\t{name}\tstudent-not-found")
            continue

        chat_input = find_chat_input(driver)
        if not chat_input:
            print(f"    [✗] '{name}' 대화창 입력란을 찾지 못했습니다.")
            fail_list.append(name)
            clear_search(driver)
            log_lines.append(f"FAIL\t{name}\tchat-input-not-found")
            continue

        clear_chat_input(driver, chat_input)
        chat_input = find_chat_input(driver)
        if not chat_input:
            print(f"    [✗] '{name}' 입력란 재확보에 실패했습니다.")
            fail_list.append(name)
            clear_search(driver)
            log_lines.append(f"FAIL\t{name}\tchat-input-refresh-failed")
            continue

        chat_input.send_keys(rehearsal_message)
        time.sleep(0.8)
        clear_chat_input(driver, chat_input)
        time.sleep(0.2)

        print(f"  ✅ {name} 입력/삭제 리허설 완료")
        log_lines.append(f"OK\t{name}\t{rehearsal_message}")
        success_count += 1

        clear_search(driver)
        time.sleep(delay)

    log_path = os.path.join(SCRIPT_DIR, "rehearsal_log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"\n{'=' * 60}")
    print("  🧪 리허설 결과")
    print(f"{'=' * 60}")
    print(f"  ✅ 성공: {success_count}/{len(students)}명")
    if fail_list:
        print(f"  ✗ 실패: {', '.join(fail_list)}")
    print(f"  로그 저장: {log_path}")
    print(f"{'=' * 60}")

    return success_count, fail_list


def click_send_button(driver):
    """보내기 버튼 클릭"""
    # 방법 1: 텍스트로 찾기
    try:
        xpath = "//button[contains(text(), '보내기')]"
        buttons = driver.find_elements(By.XPATH, xpath)
        for btn in buttons:
            if btn.is_displayed():
                btn.click()
                return True
    except Exception:
        pass

    # 방법 2: 버튼 텍스트 포함 (span 안에 있을 수 있음)
    try:
        xpath = "//button[.//text()[contains(., '보내기')]]"
        buttons = driver.find_elements(By.XPATH, xpath)
        for btn in buttons:
            if btn.is_displayed():
                btn.click()
                return True
    except Exception:
        pass

    # 방법 4: Enter 키로 전송 시도 (일부 채팅앱은 Enter로 전송)
    # → HiTalk은 Enter가 전송이므로 이 방법도 사용 가능
    print("  [⚠] 보내기 버튼을 찾지 못해 Enter 키로 전송합니다.")
    chat_input = find_chat_input(driver)
    if chat_input:
        chat_input.send_keys(Keys.ENTER)
        return True

    return False


def clear_search(driver):
    """검색란 클리어"""
    search_input = find_search_input(driver)
    if search_input:
        search_input.click()
        time.sleep(0.2)
        search_input.send_keys(Keys.CONTROL + "a")
        time.sleep(0.1)
        search_input.send_keys(Keys.DELETE)
        time.sleep(0.5)


# ──────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────
def dry_run(students, config, custom_message=None):
    """드라이런: 실제 전송 없이 메시지 미리보기 (파일로도 저장)"""
    preview_lines = []

    header = f"\n{'=' * 60}\n 드라이런 모드 - 실제 전송하지 않습니다\n{'=' * 60}"
    print(header)
    preview_lines.append(header)

    for i, st in enumerate(students, 1):
        msg = build_message(st["name"], st["score"], config, custom_message=custom_message)
        block = f"\n{'─' * 50}\n  [{i}/{len(students)}] {st['name']} ({st['score']}점)\n{'─' * 50}\n{msg}"
        print(block)
        preview_lines.append(block)

    footer = f"\n{'=' * 60}\n  총 {len(students)}명에게 전송 예정\n{'=' * 60}"
    print(footer)
    preview_lines.append(footer)

    # 미리보기 파일로 저장
    preview_path = os.path.join(SCRIPT_DIR, "preview.txt")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write("\n".join(preview_lines))
    print(f"\n  미리보기 저장: {preview_path}")
    print("  확인 후 'python hitalk_sender.py' 로 실제 전송하세요.")


def send_to_all(driver, students, config, custom_message=None):
    """모든 학생에게 점수 메시지 전송"""
    delay = config.get("delay_between_students", 3)
    success_count = 0
    fail_list = []

    print(f"\n{'=' * 60}")
    print(f"  📤 전송 시작 — 총 {len(students)}명")
    print(f"{'=' * 60}")

    for i, st in enumerate(students, 1):
        name = st["name"]
        score = st["score"]
        msg = build_message(name, score, config, custom_message=custom_message)

        print(f"\n{'─' * 50}")
        print(f"  [{i}/{len(students)}] {name} ({score}점)")
        print(f"{'─' * 50}")

        # 1. 검색
        searched = search_student(driver, name)

        # 2. 학생 클릭
        if not click_student(driver, name):
            print(f"    [✗] '{name}' 학생을 목록에서 찾을 수 없어 건너뜁니다.")
            fail_list.append(name)
            clear_search(driver)
            continue

        time.sleep(1)

        # 3. 메시지 입력
        chat_input = find_chat_input(driver)
        if not chat_input:
            print(f"  [✗] {name} 건너뜀 (채팅 입력란을 찾지 못함)")
            fail_list.append(name)
            clear_search(driver)
            continue

        type_message_with_newlines(driver, chat_input, msg)

        # 4. 전송
        sent = click_send_button(driver)
        if sent:
            print(f"  ✅ {name} 전송 완료!")
            success_count += 1
        else:
            print(f"  [✗] {name} 전송 실패 (보내기 버튼을 찾지 못함)")
            fail_list.append(name)

        # 5. 검색 클리어 & 대기
        time.sleep(0.5)
        clear_search(driver)
        time.sleep(delay)

    # 결과 보고
    print(f"\n{'=' * 60}")
    print(f"  📊 전송 결과")
    print(f"{'=' * 60}")
    print(f"  ✅ 성공: {success_count}/{len(students)}명")
    if fail_list:
        print(f"  ✗ 실패: {', '.join(fail_list)}")
    print(f"{'=' * 60}")

    return success_count, fail_list


def run():
    """전체 실행 흐름"""
    parser = argparse.ArgumentParser(
        description="하이톡 시험점수 개별 전송"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="실제 전송 없이 미리보기만 표시"
    )
    parser.add_argument(
        "--config", default=None,
        help="설정 파일 경로 (기본: config.json)"
    )
    parser.add_argument(
        "--rehearsal", action="store_true",
        help="실제 전송 없이 'testing [학생이름]' 입력 후 바로 지우는 안전 리허설"
    )
    parser.add_argument(
        "--rehearsal-template",
        default="testing {student_name}",
        help="리허설 입력 문구 템플릿 (기본: 'testing {student_name}')"
    )
    parser.add_argument(
        "--custom-message",
        default=None,
        help="학생별 치환 메시지. [학생] 또는 {student_name} 사용 가능"
    )
    parser.add_argument(
        "--message-file",
        default=None,
        help="메시지 템플릿 파일 경로 (.txt). [학생], [과목], [점수], [코멘트] 사용 가능"
    )
    args = parser.parse_args()

    config = load_config(args.config or CONFIG_PATH)
    check_runtime_dependencies()
    port = config.get("remote_port", 9223)
    custom_message = load_message_template(config, args)

    print("\n" + "=" * 60)
    print("  🎯 하이톡 시험점수 개별 전송 시스템")
    print("=" * 60)
    print(f"  과목: {config.get('subject', '시험')}")
    print(f"  시트: {config['spreadsheet_id'][:12]}...")

    # 1. 구글시트에서 점수 읽기
    raw_data = read_scores(config)
    students = parse_students(raw_data, config)

    if not students:
        print("[✗] 전송할 학생 데이터가 없습니다.")
        sys.exit(1)

    # 점수 요약 출력
    print(f"\n  📋 학생 목록:")
    for st in students:
        comment = get_comment(st["score"], config)
        print(f"     {st['name']:>6s}  {st['score']:>3s}점  {comment}")

    # 2. 드라이런 모드
    if args.dry_run:
        dry_run(students, config, custom_message=custom_message)
        return

    if args.rehearsal:
        driver = attach(port)
        ensure_single_hitalk_tab(driver)

        current_url = driver.current_url
        if "hitalk" not in current_url:
            print(f"\n  현재 URL: {current_url}")
            print("  하이톡 페이지로 이동합니다...")
            driver.get(config.get("hitalk_url", "https://www.hiclass.net/hitalk"))
            time.sleep(3)

        wait_for_hitalk_ready(driver)
        rehearse_all(driver, students, config, args.rehearsal_template)
        return

    # 3. 전송 전 확인
    print(f"\n  ⚠️  {len(students)}명에게 메시지를 전송합니다.")
    confirm = input("  계속하시겠습니까? (y/n): ").strip().lower()
    if confirm not in ("y", "yes", "ㅛ"):
        print("  ❌ 취소되었습니다.")
        return

    # 4. 브라우저 연결
    driver = attach(port)
    ensure_single_hitalk_tab(driver)

    # 하이톡 페이지인지 확인
    current_url = driver.current_url
    if "hitalk" not in current_url:
        print(f"\n  현재 URL: {current_url}")
        print("  하이톡 페이지로 이동합니다...")
        driver.get(config.get("hitalk_url", "https://www.hiclass.net/hitalk"))
        time.sleep(3)

    # 하이톡 로드 대기
    wait_for_hitalk_ready(driver)

    # 5. 전송 실행
    success_count, fail_list = send_to_all(
        driver,
        students,
        config,
        custom_message=custom_message,
    )

    if fail_list:
        retry = input(f"\n  실패한 {len(fail_list)}명 재시도? (y/n): ").strip().lower()
        if retry in ("y", "yes", "ㅛ"):
            retry_students = [s for s in students if s["name"] in fail_list]
            send_to_all(driver, retry_students, config)


if __name__ == "__main__":
    run()
