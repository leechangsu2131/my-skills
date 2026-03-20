from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

try:
    from selenium import webdriver
    from selenium.common.exceptions import StaleElementReferenceException
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    SELENIUM_AVAILABLE = True
except ImportError:
    webdriver = None
    Options = None
    By = None
    EC = None
    WebDriverWait = None
    StaleElementReferenceException = Exception
    SELENIUM_AVAILABLE = False

import social_class_store
import social_guide_extract


ENV_FILE = Path(__file__).with_name(".env")
DEFAULT_REMOTE_PORT = 9222
DOUCLASS_RESOURCE_KEYWORDS = [
    "PPT",
    "수업자료",
    "수업 자료",
    "교수자료",
    "지도자료",
    "자료",
    "활동지",
]
ISCREAM_RESOURCE_KEYWORDS = [
    "과정안",
    "활동지",
    "교과서PDF",
    "공유자료실",
    "자료",
]
DEFAULT_CHROME_PROFILE_DIR = (
    Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MusicClassHelper" / "chrome_profile"
)
DEFAULT_DATA_FILE = Path(__file__).with_name("social_class_data.json")
CHROME_PATH_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
]


@dataclass
class HelperConfig:
    site_kind: str
    label: str
    base_url: str
    remote_port: int
    chrome_profile_dir: Path
    chrome_binary: str
    data_file: Path
    guide_pdf_path: Optional[Path]
    guide_extract_pages: int
    resource_keywords: List[str]
    resource_label: str


def configure_stdout() -> None:
    stream = getattr(sys, "stdout", None)
    if stream and hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


def parse_env_lines(lines: Iterable[str]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_env_file(path: Path = ENV_FILE) -> Dict[str, str]:
    if not path.exists():
        return {}
    return parse_env_lines(path.read_text(encoding="utf-8").splitlines())


def parse_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def detect_site_kind(url: str) -> str:
    lowered = (url or "").lower()
    if "i-scream.co.kr" in lowered:
        return "iscream"
    if "douclass.com" in lowered:
        return "douclass"
    return "generic"


def default_resource_keywords_for_site(site_kind: str) -> List[str]:
    if site_kind == "iscream":
        return ISCREAM_RESOURCE_KEYWORDS
    return DOUCLASS_RESOURCE_KEYWORDS


def resolve_config(path: Path = ENV_FILE) -> HelperConfig:
    env_values = load_env_file(path)

    def get_value(key: str, default: str = "") -> str:
        return (os.environ.get(key) or env_values.get(key) or default).strip()

    base_url = get_value("SOCIAL_CLASS_BASE_URL")
    site_kind = detect_site_kind(base_url)
    remote_port_text = get_value("SOCIAL_CLASS_REMOTE_PORT", str(DEFAULT_REMOTE_PORT))
    try:
        remote_port = int(remote_port_text)
    except ValueError:
        remote_port = DEFAULT_REMOTE_PORT

    profile_dir_text = get_value("SOCIAL_CLASS_CHROME_PROFILE_DIR", str(DEFAULT_CHROME_PROFILE_DIR))
    chrome_profile_dir = Path(profile_dir_text).expanduser()

    chrome_binary = get_value("SOCIAL_CLASS_CHROME_PATH")
    data_file_text = get_value("SOCIAL_CLASS_DATA_FILE", str(DEFAULT_DATA_FILE))
    data_file = Path(data_file_text).expanduser()
    guide_pdf_text = get_value("SOCIAL_CLASS_GUIDE_PDF")
    guide_pdf_path = Path(guide_pdf_text).expanduser() if guide_pdf_text else None
    guide_extract_pages_text = get_value("SOCIAL_CLASS_GUIDE_EXTRACT_PAGES", "4")
    try:
        guide_extract_pages = max(1, int(guide_extract_pages_text))
    except ValueError:
        guide_extract_pages = 4

    keywords = parse_csv(
        get_value(
            "SOCIAL_CLASS_RESOURCE_KEYWORDS",
            ",".join(default_resource_keywords_for_site(site_kind)),
        )
    )
    resource_label = get_value("SOCIAL_CLASS_RESOURCE_LABEL", "수업 자료") or "수업 자료"
    label = get_value("SOCIAL_CLASS_LABEL", "사회 수업 도우미") or "사회 수업 도우미"

    return HelperConfig(
        site_kind=site_kind,
        label=label,
        base_url=base_url,
        remote_port=remote_port,
        chrome_profile_dir=chrome_profile_dir,
        chrome_binary=chrome_binary,
        data_file=data_file,
        guide_pdf_path=guide_pdf_path,
        guide_extract_pages=guide_extract_pages,
        resource_keywords=keywords,
        resource_label=resource_label,
    )


def validate_config(config: HelperConfig) -> bool:
    if config.base_url:
        return True

    print("[!] SOCIAL_CLASS_BASE_URL 값이 비어 있습니다.")
    print(f"    `{ENV_FILE}` 파일을 만들고 `{ENV_FILE.with_name('.env.example')}`를 참고해 주세요.")
    return False


def resolve_guide_pdf_path(
    config: HelperConfig,
    override_path: Optional[str] = None,
    saved_path: Optional[str] = None,
) -> Optional[str]:
    for candidate in (override_path, saved_path, str(config.guide_pdf_path) if config.guide_pdf_path else ""):
        cleaned = (candidate or "").strip()
        if cleaned:
            return str(Path(cleaned).expanduser())
    return None


def extract_guide_if_available(
    config: HelperConfig,
    exact_title: str,
    *,
    unit_text: Optional[str] = None,
    guide_pdf_path: Optional[str] = None,
) -> Optional[str]:
    resolved_path = resolve_guide_pdf_path(config, override_path=guide_pdf_path)
    if not resolved_path:
        print("\n[STEP 3] 지도서 PDF 경로가 설정되지 않아 추출은 건너뜁니다.")
        return None

    return social_guide_extract.do_extract(
        resolved_path,
        exact_title,
        unit_text=unit_text,
        extract_pages=config.guide_extract_pages,
    )


def ensure_selenium_available() -> bool:
    if SELENIUM_AVAILABLE:
        return True

    print("[!] selenium 이 설치되어 있지 않습니다.")
    print("    `pip install selenium` 으로 설치한 뒤 다시 실행해 주세요.")
    return False


def find_chrome_executable(config: HelperConfig) -> str:
    if config.chrome_binary:
        return config.chrome_binary
    for candidate in CHROME_PATH_CANDIDATES:
        if candidate and candidate.exists():
            return str(candidate)
    return "chrome"


def get_persistent_chrome_profile(config: HelperConfig) -> Path:
    config.chrome_profile_dir.mkdir(parents=True, exist_ok=True)
    return config.chrome_profile_dir


def launch_chrome_for_debugging(config: HelperConfig) -> bool:
    chrome_path = find_chrome_executable(config)
    profile_dir = get_persistent_chrome_profile(config)
    command = [
        chrome_path,
        f"--remote-debugging-port={config.remote_port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        config.base_url or "about:blank",
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
        print(f"[안내] Chrome 원격 디버깅 포트 {config.remote_port}로 실행했습니다.")
        print(f"[안내] 재사용 프로필 경로: {profile_dir}")
        return True
    except Exception as error:
        print(f"[!] Chrome 실행 실패: {error}")
        return False


def is_debug_port_open(host: str = "127.0.0.1", port: int = DEFAULT_REMOTE_PORT, timeout: float = 0.2) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def wait_for_debug_port(port: int, retries: int = 25, delay: float = 0.2) -> bool:
    for _ in range(retries):
        if is_debug_port_open(port=port):
            return True
        time.sleep(delay)
    return False


def connect_to_debug_chrome(options: Any, retries: int = 3, delay: float = 0.2) -> Any:
    last_error = None
    for _ in range(retries):
        try:
            return webdriver.Chrome(options=options)
        except Exception as error:
            last_error = error
            time.sleep(delay)
    raise last_error


def attach_to_chrome(config: HelperConfig) -> tuple[Any, bool]:
    if not ensure_selenium_available():
        return None, False

    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{config.remote_port}")

    if is_debug_port_open(port=config.remote_port):
        try:
            driver = connect_to_debug_chrome(options)
            print(f"[OK] 기존 Chrome에 연결했습니다: {safe_title(driver)}")
            return driver, True
        except Exception as error:
            print(f"[!] 기존 Chrome 연결 실패: {error}")

    if not launch_chrome_for_debugging(config):
        return None, False

    if not wait_for_debug_port(config.remote_port):
        print(f"[!] Chrome 디버그 포트 {config.remote_port}가 열리지 않았습니다.")
        return None, False

    try:
        driver = connect_to_debug_chrome(options)
        print(f"[OK] 새 Chrome에 연결했습니다: {safe_title(driver)}")
        return driver, False
    except Exception as error:
        print(f"[!] 새 Chrome 연결 실패: {error}")
        return None, False


def safe_title(driver: Any) -> str:
    try:
        return driver.title
    except Exception:
        return "(제목 확인 실패)"


def page_ready_locators(config: HelperConfig) -> List[tuple[Any, str]]:
    if config.site_kind == "iscream":
        return [
            (By.CSS_SELECTOR, "h4.unit_sub"),
            (By.CSS_SELECTOR, "ul.unit_list > li > a[href='#none']"),
        ]

    return [
        (By.CLASS_NAME, "textbook-chapter"),
        (By.CLASS_NAME, "txbd-fold-subject"),
    ]


def switch_to_live_window(
    driver: Any,
    prefer_last: bool = True,
    url_hint: Optional[str] = None,
) -> bool:
    try:
        handles = list(driver.window_handles)
    except Exception:
        return False

    if not handles:
        return False

    ordered_handles = list(reversed(handles)) if prefer_last else handles
    host_hint = ""
    if url_hint:
        try:
            host_hint = urlparse(url_hint).netloc.lower()
        except Exception:
            host_hint = ""

    fallback_handle = None
    for handle in ordered_handles:
        try:
            driver.switch_to.window(handle)
            driver.execute_script("return document.readyState")
            current_url = (driver.current_url or "").lower()
            if host_hint and host_hint in current_url:
                return True
            if fallback_handle is None:
                fallback_handle = handle
        except Exception:
            continue

    if fallback_handle is not None:
        try:
            driver.switch_to.window(fallback_handle)
            return True
        except Exception:
            return False
    return False


def ensure_live_driver(driver: Any, config: HelperConfig) -> Any:
    if driver and switch_to_live_window(driver, url_hint=config.base_url):
        return driver

    print("[안내] 현재 창 연결이 끊겨 브라우저 세션을 다시 확인합니다.")
    new_driver, _ = attach_to_chrome(config)
    if new_driver and switch_to_live_window(new_driver, url_hint=config.base_url):
        print(f"[OK] 브라우저 세션을 다시 연결했습니다: {safe_title(new_driver)}")
        return new_driver
    return None


def has_lesson_page_loaded(driver: Any, config: HelperConfig, timeout: float = 1.0) -> bool:
    for locator in page_ready_locators(config):
        try:
            WebDriverWait(driver, timeout).until(EC.presence_of_element_located(locator))
            return True
        except Exception:
            continue
    return False


def handle_alert(driver: Any) -> None:
    try:
        alert = driver.switch_to.alert
        print(f"[알림] 브라우저 알림을 확인했습니다: {alert.text}")
        alert.accept()
        time.sleep(0.5)
    except Exception:
        pass


def login_if_needed(driver: Any, wait: Any, config: HelperConfig) -> tuple[bool, Any, Any]:
    print("\n[STEP 1] 수업 페이지와 로그인 상태를 확인합니다...")

    try:
        driver = ensure_live_driver(driver, config)
        if not driver:
            print("[!] 사용할 수 있는 Chrome 창을 찾지 못했습니다.")
            return False, driver, wait
        wait = WebDriverWait(driver, 10)

        driver.get(config.base_url)
        handle_alert(driver)
        if has_lesson_page_loaded(driver, config, timeout=2.0):
            print("  -> 수업 페이지가 정상적으로 열렸습니다.")
            return True, driver, wait

        answer = prompt_enter_after_browser_action(
            "  -> 연결된 Chrome 창에서 직접 로그인하거나 접근 권한을 확인해 주세요.\n"
            "     준비가 끝나면 Enter를 눌러 다시 수업 페이지를 확인합니다."
        )
        if answer.lower() == "b":
            print("  -> 로그인을 취소했습니다.")
            return False, driver, wait

        driver = ensure_live_driver(driver, config)
        if not driver:
            print("[!] 로그인 후 다시 붙을 수 있는 Chrome 창을 찾지 못했습니다.")
            return False, driver, wait
        wait = WebDriverWait(driver, 10)

        driver.get(config.base_url)
        handle_alert(driver)
        if has_lesson_page_loaded(driver, config, timeout=4.0):
            print("  -> 로그인 후 수업 페이지 로딩을 확인했습니다.")
            return True, driver, wait

        wait.until(EC.any_of(*[EC.presence_of_element_located(locator) for locator in page_ready_locators(config)]))
        print("  -> 로그인 후 수업 페이지 로딩을 확인했습니다.")
        return True, driver, wait
    except Exception as error:
        print(f"[!] 수업 페이지 준비 중 오류가 발생했습니다: {error}")
        return False, driver, wait


def prepare_lesson_page(driver: Any, config: HelperConfig, unit_text: Optional[str] = None) -> None:
    driver.get(config.base_url)
    handle_alert(driver)

    if config.site_kind == "iscream":
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h4.unit_sub"))
            )
        except Exception:
            time.sleep(1)
        return

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
        folding_toggles = driver.find_elements(By.CLASS_NAME, "folding-box-toggle")
        for toggle in folding_toggles:
            try:
                parent = toggle.find_element(By.XPATH, "..")
                parent_class = parent.get_attribute("class") or ""
                if "folding-open" not in parent_class:
                    driver.execute_script("arguments[0].click();", toggle)
                    time.sleep(0.2)
            except Exception:
                continue
    except Exception:
        pass

    if unit_text:
        ensure_unit_loaded(driver, unit_text)


def collect_douclass_lessons(driver: Any) -> List[Dict[str, Any]]:
    lessons: List[Dict[str, Any]] = []
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

            lessons.append(
                {"title": title_text, "chapter": element, "unit_title": current_unit_title}
            )
        except StaleElementReferenceException:
            continue
        except Exception:
            continue

    return lessons


def clean_iscream_unit_title(text: str) -> str:
    normalized = normalize_space(text)
    for noise in [
        "사회 골든벨 Quiz",
        "사회 알짜정리 학습지",
        "교과서PDF",
        "공유자료실",
    ]:
        normalized = normalized.replace(noise, " ")
    return normalize_space(normalized)


def collect_iscream_lessons(driver: Any) -> List[Dict[str, Any]]:
    lessons: List[Dict[str, Any]] = []
    unit_containers = driver.find_elements(
        By.XPATH,
        "//li[./h4[contains(@class,'unit_sub')] and ./ul[contains(@class,'unit_list') and not(contains(@class,'unit_detail'))]]",
    )

    for container in unit_containers:
        try:
            unit_title = clean_iscream_unit_title(
                container.find_element(By.XPATH, "./h4[contains(@class,'unit_sub')]").text
            )
        except Exception:
            unit_title = ""

        lesson_items = container.find_elements(
            By.XPATH,
            "./ul[contains(@class,'unit_list') and not(contains(@class,'unit_detail'))]/li",
        )
        for lesson_item in lesson_items:
            try:
                title_link = lesson_item.find_element(By.XPATH, "./a[1]")
                title_text = normalize_space(title_link.text)
                if not title_text:
                    continue
                lessons.append(
                    {
                        "title": title_text,
                        "chapter": lesson_item,
                        "unit_title": unit_title,
                    }
                )
            except Exception:
                continue

    return lessons


def collect_lessons(driver: Any, config: HelperConfig) -> List[Dict[str, Any]]:
    if config.site_kind == "iscream":
        return collect_iscream_lessons(driver)
    return collect_douclass_lessons(driver)


def ensure_unit_loaded(driver: Any, unit_text: str) -> None:
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
        return


def normalize_space(text: str) -> str:
    return " ".join((text or "").split())


def extract_numbers(text: str) -> List[str]:
    return re.findall(r"\d+", text or "")


def unit_matches(unit_title: str, unit_text: str) -> bool:
    normalized_title = normalize_space(unit_title)
    normalized_query = normalize_space(unit_text)
    if not normalized_query:
        return True
    if normalized_query in normalized_title:
        return True

    title_numbers = extract_numbers(normalized_title)
    query_numbers = extract_numbers(normalized_query)
    if title_numbers and query_numbers:
        return title_numbers[0] == query_numbers[0]
    return False


def lesson_matches(title_text: str, lesson_text: str) -> bool:
    normalized_title = normalize_space(title_text)
    normalized_lesson = normalize_space(lesson_text)
    if normalized_lesson and normalized_title == normalized_lesson:
        return True

    lesson_numbers = extract_numbers(normalized_lesson)
    title_match = re.search(r"\[(.*?)\]\s*(.*)", normalized_title)
    if title_match:
        bracket_text = title_match.group(1)
        topic_text = title_match.group(2)
        title_numbers = extract_numbers(bracket_text)

        if lesson_numbers and title_numbers:
            return set(lesson_numbers).issubset(set(title_numbers))
        if not lesson_numbers and normalized_lesson and normalized_lesson in topic_text:
            return True

    return normalized_lesson in normalized_title if normalized_lesson else False


def normalize_match_text(text: str) -> str:
    return normalize_space(text).lower()


def resource_match_score(text: str, keywords: Iterable[str]) -> int:
    normalized_text = normalize_match_text(text)
    best_score = 0
    for keyword in keywords:
        normalized_keyword = normalize_match_text(keyword)
        if normalized_keyword and normalized_keyword in normalized_text:
            best_score = max(best_score, len(normalized_keyword))
    return best_score


def button_descriptor(element: Any) -> str:
    parts = [
        element.text or "",
        element.get_attribute("title") or "",
        element.get_attribute("aria-label") or "",
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())


def find_iscream_resource_button(chapter: Any, keywords: Iterable[str]) -> Optional[Any]:
    anchors = chapter.find_elements(By.XPATH, "./a")
    resource_anchors = anchors[1:] if len(anchors) > 1 else []
    candidates: List[tuple[int, int, Any]] = []

    for element in resource_anchors:
        try:
            descriptor = button_descriptor(element)
            if not descriptor:
                continue
            score = resource_match_score(descriptor, keywords)
            if score:
                candidates.append((score, len(descriptor), element))
        except Exception:
            continue

    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return candidates[0][2]

    if resource_anchors:
        return resource_anchors[0]
    return None


def find_resource_button(chapter: Any, keywords: Iterable[str], site_kind: str = "generic") -> Optional[Any]:
    if site_kind == "iscream":
        return find_iscream_resource_button(chapter, keywords)

    search_paths = [
        ".//*[contains(@class, 'textbook-chapter-btn')]//a | "
        ".//*[contains(@class, 'textbook-chapter-btn')]//button",
        ".//a[contains(@class, 'btn')] | .//button[contains(@class, 'btn')]",
    ]
    candidates: List[tuple[int, int, Any]] = []

    for xpath in search_paths:
        for element in chapter.find_elements(By.XPATH, xpath):
            try:
                class_name = element.get_attribute("class") or ""
                if "resource-title" in class_name:
                    continue
                descriptor = button_descriptor(element)
                if not descriptor:
                    continue
                score = resource_match_score(descriptor, keywords)
                if score:
                    candidates.append((score, len(descriptor), element))
            except Exception:
                continue
        if candidates:
            break

    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return candidates[0][2]

    fallback_buttons = chapter.find_elements(
        By.XPATH,
        ".//*[contains(@class, 'textbook-chapter-btn')]//a | "
        ".//*[contains(@class, 'textbook-chapter-btn')]//button",
    )
    if len(fallback_buttons) == 1:
        return fallback_buttons[0]
    return None


def open_resource_for_lesson(
    driver: Any,
    config: HelperConfig,
    unit_text: str,
    lesson_text: str,
    manual_click: bool = False,
) -> Optional[str]:
    print(f"\n[STEP 2] '{unit_text}' / '{lesson_text}' 차시의 {config.resource_label}를 찾습니다...")
    driver = ensure_live_driver(driver, config)
    if not driver:
        print("[!] 사용할 수 있는 Chrome 창을 찾지 못했습니다.")
        return None
    prepare_lesson_page(driver, config, unit_text=unit_text)
    lessons = collect_lessons(driver, config)
    print(f"  -> 총 {len(lessons)}개의 차시 블록을 확인했습니다.")

    for item in lessons:
        title_text = item["title"]
        chapter = item["chapter"]
        current_unit_title = item["unit_title"]
        if not unit_matches(current_unit_title, unit_text):
            continue
        if not lesson_matches(title_text, lesson_text):
            continue

        print(f"  -> 대상 차시를 찾았습니다: [{current_unit_title}] {title_text}")
        highlight_lesson(driver, chapter)

        if manual_click:
            answer = prompt_enter_after_browser_action(
                f"  -> 브라우저에서 '{config.resource_label}' 버튼을 직접 클릭한 뒤 Enter를 눌러 주세요."
            )
            clear_highlight(driver, chapter)
            if answer.lower() == "b":
                print("  -> 자료 열기를 취소했습니다.")
                return None
            return title_text

        button = find_resource_button(chapter, config.resource_keywords, config.site_kind)
        if button is None:
            print(f"  [!] 자동으로 '{config.resource_label}' 버튼을 찾지 못했습니다.")
            answer = prompt_enter_after_browser_action(
                f"  -> 브라우저에서 직접 '{config.resource_label}' 버튼을 클릭한 뒤 Enter를 눌러 주세요."
            )
            clear_highlight(driver, chapter)
            if answer.lower() == "b":
                print("  -> 자료 열기를 취소했습니다.")
                return None
            return title_text

        button_label = button_descriptor(button) or config.resource_label
        print(f"  -> 버튼을 찾았습니다: {button_label}")
        click_resource_button(driver, button)
        clear_highlight(driver, chapter)
        return title_text

    print(f"[!] '{unit_text}' / '{lesson_text}' 차시를 찾지 못했습니다.")
    return None


def click_resource_button(driver: Any, button: Any) -> None:
    if not switch_to_live_window(driver):
        raise RuntimeError("자료를 열 브라우저 창을 찾지 못했습니다.")

    before_handles = set(driver.window_handles)
    driver.execute_script("arguments[0].click();", button)
    time.sleep(1)
    handle_alert(driver)

    after_handles = set(driver.window_handles)
    if len(after_handles) > len(before_handles):
        new_window = (after_handles - before_handles).pop()
        driver.switch_to.window(new_window)
        print(f"  -> 새 창으로 전환했습니다: {safe_title(driver)}")
    else:
        print(f"  -> 현재 창에서 자료를 열었습니다: {safe_title(driver)}")


def highlight_lesson(driver: Any, chapter: Any) -> None:
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
            chapter,
        )
        driver.execute_script(
            "arguments[0].style.outline='3px solid #ff7a00'; "
            "arguments[0].style.outlineOffset='4px';",
            chapter,
        )
    except Exception:
        pass


def clear_highlight(driver: Any, chapter: Any) -> None:
    try:
        driver.execute_script(
            "arguments[0].style.outline=''; arguments[0].style.outlineOffset='';",
            chapter,
        )
    except Exception:
        pass


def run_lesson(
    config: HelperConfig,
    unit_text: str,
    lesson_text: str,
    *,
    save_name: Optional[str] = None,
    source_name: Optional[str] = None,
    guide_pdf_path: Optional[str] = None,
    manual_click: bool = False,
) -> bool:
    if not validate_config(config):
        return False

    driver, _reused_existing_browser = attach_to_chrome(config)
    if not driver:
        return False

    wait = WebDriverWait(driver, 10)

    print("\n" + "=" * 55)
    print(f" {config.label} 시작 ({unit_text} / {lesson_text})")
    print("=" * 55)

    login_ok, driver, wait = login_if_needed(driver, wait, config)
    if not login_ok:
        return False

    exact_title = open_resource_for_lesson(
        driver,
        config,
        unit_text,
        lesson_text,
        manual_click=manual_click,
    )
    if not exact_title:
        return False

    resolved_guide_pdf_path = resolve_guide_pdf_path(config, override_path=guide_pdf_path)
    extract_guide_if_available(
        config,
        exact_title,
        unit_text=unit_text,
        guide_pdf_path=resolved_guide_pdf_path,
    )

    if save_name:
        social_class_store.upsert_saved_lesson(
            save_name,
            unit_text,
            lesson_text,
            exact_title=exact_title,
            guide_pdf_path=resolved_guide_pdf_path,
            storage_path=config.data_file,
        )
        print(f"[저장] '{save_name}' 이름으로 수업 구성을 저장했습니다.")

    social_class_store.record_recent_run(
        unit_text,
        lesson_text,
        exact_title=exact_title,
        saved_name=source_name or save_name,
        guide_pdf_path=resolved_guide_pdf_path,
        storage_path=config.data_file,
    )
    print("[저장] 최근 실행 기록을 남겼습니다.")
    return True


def run_saved_lesson(
    config: HelperConfig,
    name: str,
    *,
    guide_pdf_path: Optional[str] = None,
    manual_click: bool = False,
) -> bool:
    saved = social_class_store.get_saved_lesson(name, storage_path=config.data_file)
    if not saved:
        print(f"[!] '{name}' 저장 구성을 찾지 못했습니다.")
        return False

    lesson_query = saved.get("exact_title") or saved["lesson"]
    return run_lesson(
        config,
        saved["unit"],
        lesson_query,
        source_name=saved["name"],
        guide_pdf_path=guide_pdf_path or saved.get("guide_pdf_path"),
        manual_click=manual_click,
    )


def print_saved_lessons(config: HelperConfig) -> None:
    saved_lessons = social_class_store.list_saved_lessons(storage_path=config.data_file)
    if not saved_lessons:
        print("저장된 수업 구성이 없습니다.")
        return

    print("\n[저장된 수업 구성]")
    for index, item in enumerate(saved_lessons, start=1):
        title_label = item.get("exact_title") or "정확한 제목 없음"
        guide_label = Path(item["guide_pdf_path"]).name if item.get("guide_pdf_path") else "지도서 미설정"
        print(
            f"{index}. {item['name']} | {item['unit']} | {item['lesson']} | "
            f"{title_label} | {guide_label}"
        )


def print_recent_runs(config: HelperConfig, limit: int) -> None:
    recent_runs = social_class_store.list_recent_runs(limit=limit, storage_path=config.data_file)
    if not recent_runs:
        print("최근 실행 기록이 없습니다.")
        return

    print(f"\n[최근 실행 {len(recent_runs)}건]")
    for index, item in enumerate(recent_runs, start=1):
        name_label = item["saved_name"] or "직접 실행"
        title_label = item["exact_title"] or "정확한 제목 없음"
        guide_label = Path(item["guide_pdf_path"]).name if item.get("guide_pdf_path") else "지도서 미설정"
        print(
            f"{index}. {item['ran_at']} | {name_label} | {item['unit']} | "
            f"{item['lesson']} | {title_label} | {guide_label}"
        )


def print_config_summary(config: HelperConfig) -> None:
    print("\n[설정 요약]")
    print(f"- 환경 파일: {ENV_FILE}")
    print(f"- 수업 URL: {config.base_url or '(미설정)'}")
    print(f"- 디버그 포트: {config.remote_port}")
    print(f"- 크롬 프로필: {config.chrome_profile_dir}")
    print(f"- 상태 파일: {config.data_file}")
    print(f"- 기본 지도서 PDF: {config.guide_pdf_path or '(미설정)'}")
    print(f"- 지도서 추출 페이지 수: {config.guide_extract_pages}")
    print(f"- 자료 키워드: {', '.join(config.resource_keywords) if config.resource_keywords else '(없음)'}")


def prompt_input(message: str) -> str:
    try:
        return input(message).strip()
    except EOFError:
        return ""


def prompt_enter_after_browser_action(message: str) -> str:
    print(message)
    return prompt_input("브라우저 작업이 끝나면 Enter를 눌러 주세요 (취소: b): ")


def interactive_menu(config: HelperConfig) -> bool:
    while True:
        print("\n" + "=" * 55)
        print(config.label)
        print("=" * 55)
        print("1. 새 차시 자료 열기")
        print("2. 수업 구성 저장")
        print("3. 저장된 수업 목록 보기")
        print("4. 저장된 수업 실행")
        print("5. 저장된 수업 삭제")
        print("6. 최근 실행 기록 보기")
        print("7. 현재 설정 보기")
        print("0. 종료")

        menu = prompt_input("원하는 메뉴 번호를 입력해 주세요: ")

        if menu == "1":
            unit = prompt_input("단원을 입력해 주세요: ")
            lesson = prompt_input("차시를 입력해 주세요: ")
            save_name = prompt_input("이 구성을 저장할 이름이 있으면 입력해 주세요 (없으면 Enter): ")
            default_guide = str(config.guide_pdf_path) if config.guide_pdf_path else ""
            guide_prompt = "지도서 PDF 경로가 있으면 입력해 주세요"
            if default_guide:
                guide_prompt += f" (Enter 시 기본값 사용: {default_guide})"
            guide_pdf_path = prompt_input(guide_prompt + ": ")
            run_lesson(
                config,
                unit,
                lesson,
                save_name=save_name or None,
                guide_pdf_path=guide_pdf_path or default_guide or None,
            )
        elif menu == "2":
            save_name = prompt_input("저장할 이름을 입력해 주세요: ")
            unit = prompt_input("단원을 입력해 주세요: ")
            lesson = prompt_input("차시를 입력해 주세요: ")
            exact_title = prompt_input("정확한 차시 제목이 있으면 입력해 주세요 (없으면 Enter): ")
            default_guide = str(config.guide_pdf_path) if config.guide_pdf_path else ""
            guide_prompt = "지도서 PDF 경로가 있으면 입력해 주세요"
            if default_guide:
                guide_prompt += f" (Enter 시 기본값 사용: {default_guide})"
            guide_pdf_path = prompt_input(guide_prompt + ": ")
            social_class_store.upsert_saved_lesson(
                save_name,
                unit,
                lesson,
                exact_title=exact_title or None,
                guide_pdf_path=guide_pdf_path or default_guide or None,
                storage_path=config.data_file,
            )
            print(f"[저장] '{save_name}' 구성을 저장했습니다.")
        elif menu == "3":
            print_saved_lessons(config)
        elif menu == "4":
            save_name = prompt_input("실행할 저장 이름을 입력해 주세요: ")
            run_saved_lesson(config, save_name)
        elif menu == "5":
            save_name = prompt_input("삭제할 저장 이름을 입력해 주세요: ")
            deleted = social_class_store.delete_saved_lesson(save_name, storage_path=config.data_file)
            if deleted:
                print(f"[삭제] '{save_name}' 구성을 삭제했습니다.")
            else:
                print(f"[!] '{save_name}' 구성을 찾지 못했습니다.")
        elif menu == "6":
            limit_text = prompt_input("몇 개까지 볼까요? (기본값 10): ")
            limit = int(limit_text) if limit_text.isdigit() else 10
            print_recent_runs(config, max(1, limit))
        elif menu == "7":
            print_config_summary(config)
        elif menu == "0":
            print("프로그램을 종료합니다.")
            return True
        else:
            print("[!] 올바른 메뉴 번호를 입력해 주세요.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="사회 교과서 차시 자료를 여는 반자동 수업 도우미")
    subparsers = parser.add_subparsers(dest="command")

    menu_parser = subparsers.add_parser("menu", help="대화형 메뉴 실행")
    menu_parser.set_defaults(command="menu")

    config_parser = subparsers.add_parser("config", help="현재 설정 요약 보기")
    config_parser.set_defaults(command="config")

    run_parser = subparsers.add_parser("run", help="지정한 차시 자료 바로 열기")
    run_parser.add_argument("unit", help="단원 이름")
    run_parser.add_argument("lesson", help="차시 이름")
    run_parser.add_argument("--save", dest="save_name", help="실행 후 저장할 이름")
    run_parser.add_argument("--guide-pdf", dest="guide_pdf_path", help="지도서 PDF 경로")
    run_parser.add_argument(
        "--manual",
        action="store_true",
        help="버튼 자동 클릭 대신 브라우저에서 직접 클릭하도록 안내",
    )

    saved_parser = subparsers.add_parser("saved", help="저장된 수업 구성 관리")
    saved_subparsers = saved_parser.add_subparsers(dest="saved_command")

    saved_list_parser = saved_subparsers.add_parser("list", help="저장된 수업 목록 보기")
    saved_list_parser.set_defaults(saved_command="list")

    saved_add_parser = saved_subparsers.add_parser("add", help="수업 구성 저장")
    saved_add_parser.add_argument("name", help="저장 이름")
    saved_add_parser.add_argument("unit", help="단원 이름")
    saved_add_parser.add_argument("lesson", help="차시 이름")
    saved_add_parser.add_argument("--exact-title", dest="exact_title", help="정확한 차시 제목")
    saved_add_parser.add_argument("--guide-pdf", dest="guide_pdf_path", help="지도서 PDF 경로")

    saved_run_parser = saved_subparsers.add_parser("run", help="저장된 수업 실행")
    saved_run_parser.add_argument("name", help="저장 이름")
    saved_run_parser.add_argument("--guide-pdf", dest="guide_pdf_path", help="지도서 PDF 경로")
    saved_run_parser.add_argument("--manual", action="store_true", help="브라우저에서 직접 클릭")

    saved_delete_parser = saved_subparsers.add_parser("delete", help="저장된 수업 삭제")
    saved_delete_parser.add_argument("name", help="저장 이름")

    recent_parser = subparsers.add_parser("recent", help="최근 실행 기록 보기")
    recent_parser.add_argument("--limit", type=int, default=10, help="표시할 개수")

    return parser


def handle_command(args: argparse.Namespace, config: HelperConfig) -> Optional[bool]:
    if args.command in (None, "menu"):
        return interactive_menu(config)

    if args.command == "config":
        print_config_summary(config)
        return True

    if args.command == "run":
        return run_lesson(
            config,
            args.unit,
            args.lesson,
            save_name=args.save_name,
            guide_pdf_path=args.guide_pdf_path,
            manual_click=args.manual,
        )

    if args.command == "saved":
        if args.saved_command in (None, "list"):
            print_saved_lessons(config)
            return True
        if args.saved_command == "add":
            social_class_store.upsert_saved_lesson(
                args.name,
                args.unit,
                args.lesson,
                exact_title=args.exact_title,
                guide_pdf_path=args.guide_pdf_path,
                storage_path=config.data_file,
            )
            print(f"[저장] '{args.name}' 구성을 저장했습니다.")
            return True
        if args.saved_command == "run":
            return run_saved_lesson(
                config,
                args.name,
                guide_pdf_path=args.guide_pdf_path,
                manual_click=args.manual,
            )
        if args.saved_command == "delete":
            deleted = social_class_store.delete_saved_lesson(
                args.name,
                storage_path=config.data_file,
            )
            if deleted:
                print(f"[삭제] '{args.name}' 구성을 삭제했습니다.")
            else:
                print(f"[!] '{args.name}' 구성을 찾지 못했습니다.")
            return True

    if args.command == "recent":
        print_recent_runs(config, max(1, args.limit))
        return True

    return None


def main() -> None:
    configure_stdout()
    parser = build_parser()
    args = parser.parse_args()
    config = resolve_config()
    handled = handle_command(args, config)
    if handled is None:
        parser.print_help()


if __name__ == "__main__":
    main()
