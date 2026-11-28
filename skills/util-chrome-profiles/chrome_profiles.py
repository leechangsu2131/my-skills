"""Chrome·Edge 프로필 매니저 (Windows / Python 3.10+)

설치: pip install -r requirements.txt
실행: 실행.bat 더블클릭, 또는 pythonw chrome_profiles.py
점검: python chrome_profiles.py --check   (프로필·열린 창 목록만 출력하고 끝냄)

Chrome·Edge 를 평소처럼 실행하고(로그인 상태 유지) Windows API 로 창을 다룬다.
창이 어느 프로필인지는 브라우저가 창마다 붙이는 작업표시줄 앱 ID(AppUserModelID)로 알아낸다.
  Chrome 기본 프로필 → "Chrome",  Profile 4 → "Chrome.UserData.Profile4"
  Edge   기본 프로필 → "MSEdge",  Profile 1 → "MSEdge.UserData.Profile1"
프로필 키: Chrome 은 폴더명 그대로("Profile 4"), Edge 는 "edge:Profile 1".
그래서 매니저 밖에서 연 창, 매니저를 다시 켜기 전부터 열려 있던 창도 프로필별로 잡힌다.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents
                            if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir, load_env  # noqa: E402

import win32api  # noqa: E402
import win32clipboard  # noqa: E402
import win32con  # noqa: E402
import win32gui  # noqa: E402
import win32process  # noqa: E402
import win32ui  # noqa: E402
from win32com.propsys import propsys, pscon  # noqa: E402

SKILL = "util-chrome-profiles"
load_env(skill=SKILL)

LOCAL = Path(os.environ["LOCALAPPDATA"])
# prefix=프로필 키 앞머리, aumid=앱 ID 바탕, install=설치 폴더(Application 의 상위), env=User Data 덮어쓰기 설정 키
BROWSERS = [
    {"prefix": "", "label": "Chrome", "aumid": "Chrome", "exe": "chrome.exe",
     "install": Path("Google") / "Chrome", "env": "CHROME_USER_DATA_DIR"},
    {"prefix": "edge:", "label": "Edge", "aumid": "MSEdge", "exe": "msedge.exe",
     "install": Path("Microsoft") / "Edge", "env": "EDGE_USER_DATA_DIR"},
]
for _b in BROWSERS:
    _b["user_data"] = Path(os.path.expandvars(os.environ.get(_b["env"], "")) or LOCAL / _b["install"] / "User Data")
BROWSER_EXES = tuple(os.sep + b["exe"] for b in BROWSERS)
CONFIG = data_dir(SKILL) / "config.json"
UNGROUPED = "미분류"
OTHER = "기타 브라우저 창"
CHANGE_THRESHOLD = 2.0   # 32x32 흑백 축소본의 평균 밝기 차이. 클수록 둔감하다.
CAPTURE_BUDGET = 0.15    # 1초마다 캡처에 쓰는 최대 시간(초). 창이 많으면 돌아가며 찍는다.
THUMB_W, THUMB_H = 240, 150


# ───────────────────────── Chrome / Windows 유틸 ─────────────────────────
def find_exe(browser: dict) -> str | None:
    for base in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        p = Path(os.environ.get(base, "")) / browser["install"] / "Application" / browser["exe"]
        if p.exists():
            return str(p)
    return None


def load_profiles() -> dict[str, dict]:
    """설치된 브라우저마다 Local State 에서 프로필을 읽는다.
    {키: {"name": 표시 이름, "folder": 폴더명, "exe": 실행 파일, "browser": 브라우저 정보, "sid": 저장용 이름}}
    키(폴더명, Edge 는 "edge:폴더명")는 이 PC 안에서만 뜻이 있다. 설정 파일에는 PC 가 달라도 같은 계정이면 같은
    sid("acct:이메일", Edge 는 "edge:acct:이메일")로 적는다. 로그인 안 한 프로필은 폴더 키를 그대로 쓴다."""
    out = {}
    for browser in BROWSERS:
        exe, state = find_exe(browser), browser["user_data"] / "Local State"
        if not exe or not state.is_file():
            continue
        cache = json.loads(state.read_text(encoding="utf-8"))["profile"]["info_cache"]
        for folder in sorted(cache, key=_natural):
            info = cache[folder]
            name = info.get("name") or folder
            email = (info.get("user_name") or "").strip()
            name = f"{name} ({email})" if email else name
            if browser["prefix"]:
                name = f"{browser['label']} · {name}"
            key = browser["prefix"] + folder
            sid = f"{browser['prefix']}acct:{email.lower()}" if email else key
            out[key] = {"name": name, "folder": folder, "exe": exe, "browser": browser, "sid": sid}
    if not out:
        raise FileNotFoundError("Chrome·Edge 를 찾지 못했습니다.")
    seen: dict[str, int] = {}
    for info in out.values():
        seen[info["sid"]] = seen.get(info["sid"], 0) + 1
    for key, info in out.items():  # 같은 계정이 두 프로필에 있으면(드묾) 헷갈리지 않게 폴더 키로
        if seen[info["sid"]] > 1:
            info["sid"] = key
    return out


def _natural(text: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]


def _aumid_part(text: str) -> str:
    """Chrome 이 앱 ID 를 만들 때처럼 영문·숫자·점만 남긴다."""
    return re.sub(r"[^A-Za-z0-9.]", "", text)


def aumid_table(profiles: dict[str, dict]) -> dict[str, str]:
    """{창의 앱 ID: 프로필 키}"""
    table = {}
    for key, info in profiles.items():
        browser = info["browser"]
        table[f"{browser['aumid']}.{_aumid_part(browser['user_data'].name)}.{_aumid_part(info['folder'])}"] = key
        if info["folder"] == "Default":
            table[browser["aumid"]] = key
    return table


_exe_cache: dict[int, bool] = {}


def _is_chrome_pid(pid: int) -> bool:
    if pid not in _exe_cache:
        try:
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            try:
                exe = win32process.GetModuleFileNameEx(handle, 0)
            finally:
                win32api.CloseHandle(handle)
            _exe_cache[pid] = exe.lower().endswith(BROWSER_EXES)
        except Exception:
            _exe_cache[pid] = False
    return _exe_cache[pid]


def window_aumid(hwnd: int) -> str | None:
    try:
        store = propsys.SHGetPropertyStoreForWindow(hwnd, propsys.IID_IPropertyStore)
        return store.GetValue(pscon.PKEY_AppUserModel_ID).GetValue() or None
    except Exception:
        return None


def chrome_windows() -> list[int]:
    """보이는 Chrome·Edge 브라우저 창(대화상자·팝업 제외)."""
    found = []

    def callback(hwnd, _):
        if (win32gui.IsWindowVisible(hwnd) and win32gui.GetClassName(hwnd) == "Chrome_WidgetWin_1"
                and win32gui.GetWindowText(hwnd) and not win32gui.GetWindow(hwnd, win32con.GW_OWNER)
                and _is_chrome_pid(win32process.GetWindowThreadProcessId(hwnd)[1])):
            found.append(hwnd)
        return True

    win32gui.EnumWindows(callback, None)
    return found


_user32 = ctypes.windll.user32


def activate(hwnd: int) -> bool:
    """창을 앞으로. Windows 의 포그라운드 제한을 피하려고 입력 스레드를 잠시 잇는다."""
    if not win32gui.IsWindow(hwnd):
        return False
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    me = win32api.GetCurrentThreadId()
    fg = win32gui.GetForegroundWindow()
    fg_thread = win32process.GetWindowThreadProcessId(fg)[0] if fg else 0
    attached = False
    try:
        if fg_thread and fg_thread != me:
            attached = bool(_user32.AttachThreadInput(me, fg_thread, True))
        _user32.BringWindowToTop(hwnd)
        _user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            _user32.AttachThreadInput(me, fg_thread, False)
    return win32gui.GetForegroundWindow() == hwnd


def close_window(hwnd: int) -> None:
    """창의 X 버튼을 누른 것과 같다. 작성 중인 글이 있으면 Chrome 이 '나가시겠습니까?'를 묻는다."""
    if win32gui.IsWindow(hwnd):
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)


def get_clipboard() -> str | None:
    try:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        pass
    return None


def set_clipboard(text: str) -> None:
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()


def press_ctrl_v() -> None:
    press_keys([win32con.VK_CONTROL], ord("V"))


# ───── 일괄 입력의 특수 키: {Enter}, {Ctrl+A}, {대기 1} 처럼 중괄호로 적는다 ─────
_VK = win32con
SPECIAL_KEYS = {
    "enter": _VK.VK_RETURN, "엔터": _VK.VK_RETURN, "tab": _VK.VK_TAB, "탭": _VK.VK_TAB,
    "esc": _VK.VK_ESCAPE, "escape": _VK.VK_ESCAPE, "space": _VK.VK_SPACE, "스페이스": _VK.VK_SPACE,
    "backspace": _VK.VK_BACK, "bs": _VK.VK_BACK, "delete": _VK.VK_DELETE, "del": _VK.VK_DELETE,
    "insert": _VK.VK_INSERT, "up": _VK.VK_UP, "down": _VK.VK_DOWN, "left": _VK.VK_LEFT,
    "right": _VK.VK_RIGHT, "home": _VK.VK_HOME, "end": _VK.VK_END, "pageup": _VK.VK_PRIOR,
    "pagedown": _VK.VK_NEXT, **{f"f{i}": getattr(_VK, f"VK_F{i}") for i in range(1, 13)},
}
MODIFIER_KEYS = {"ctrl": _VK.VK_CONTROL, "컨트롤": _VK.VK_CONTROL, "shift": _VK.VK_SHIFT,
                 "시프트": _VK.VK_SHIFT, "alt": _VK.VK_MENU, "알트": _VK.VK_MENU}
EXTENDED_KEYS = {_VK.VK_INSERT, _VK.VK_DELETE, _VK.VK_HOME, _VK.VK_END, _VK.VK_PRIOR, _VK.VK_NEXT,
                 _VK.VK_UP, _VK.VK_DOWN, _VK.VK_LEFT, _VK.VK_RIGHT}
MAX_WAIT = 10.0


def _key_event(vk: int, up: bool) -> None:
    flags = (win32con.KEYEVENTF_KEYUP if up else 0) | (win32con.KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_KEYS else 0)
    win32api.keybd_event(vk, win32api.MapVirtualKey(vk, 0), flags, 0)


def press_keys(mods: list[int], vk: int) -> None:
    for m in mods:
        _key_event(m, False)
    _key_event(vk, False)
    _key_event(vk, True)
    for m in reversed(mods):
        _key_event(m, True)


def parse_macro(text: str) -> list[tuple]:
    """글과 {특수 키}를 차례대로 나눈다. 결과: ("text", 글) / ("keys", [수식키], vk, 이름) / ("wait", 초)
    {{ 와 }} 는 중괄호 글자 그대로. 모르는 키 이름이면 ValueError."""
    steps: list[tuple] = []
    buffer = ""
    for m in re.finditer(r"\{\{|\}\}|\{([^{}]*)\}|[^{}]+|[{}]", text):
        token = m.group(0)
        if token in ("{{", "}}"):
            buffer += token[0]
            continue
        if m.group(1) is None:
            buffer += token
            continue
        if buffer:
            steps.append(("text", buffer))
            buffer = ""
        inner = m.group(1).strip()
        wait = re.fullmatch(r"(?i)(?:대기|wait)\s*([\d.]+)\s*(?:초|s)?", inner)
        if wait:
            steps.append(("wait", min(float(wait.group(1)), MAX_WAIT)))
            continue
        parts = [p.strip().lower() for p in inner.replace(" ", "").split("+") if p.strip()]
        if not parts:
            raise ValueError(f"빈 키 이름: {token}")
        *mod_names, key_name = parts
        try:
            mods = [MODIFIER_KEYS[name] for name in mod_names]
        except KeyError as e:
            raise ValueError(f"모르는 수식 키 {e} — Ctrl·Shift·Alt 만 됩니다: {token}") from None
        if key_name in SPECIAL_KEYS:
            vk = SPECIAL_KEYS[key_name]
        elif len(key_name) == 1 and key_name.isascii() and key_name.isalnum():
            vk = ord(key_name.upper())
        else:
            raise ValueError(f"모르는 키 이름: {token}")
        steps.append(("keys", mods, vk, inner))
    if buffer:
        steps.append(("text", buffer))
    return steps


# ───── 탭 정리: UI 자동화(UIA)로 탭 줄을 읽어 지울 탭의 X 단추만 누른다(창 전환·마우스 없음) ─────
CLOSE_BUTTON_NAMES = {"닫기", "close", "탭 닫기", "close tab"}
TAB_MODES = {"others": "다른 탭", "right": "오른쪽 탭", "left": "왼쪽 탭"}


def browser_tabs(hwnd: int) -> list[dict]:
    """창의 탭을 탭 줄 순서대로 [{"name", "selected", "close"}]. 웹 페이지 안(Document)은 들여다보지 않는다."""
    import uiautomation as auto
    tabs, stack = [], [(auto.ControlFromHandle(hwnd), 0)]
    while stack:
        control, depth = stack.pop()
        try:
            kind = control.ControlTypeName
        except Exception:
            continue
        if kind == "TabItemControl":
            try:
                selected = bool(control.GetSelectionItemPattern().IsSelected)
            except Exception:
                selected = False
            buttons = [b for b in control.GetChildren() if b.ControlTypeName == "ButtonControl"]
            close = next((b for b in buttons if (b.Name or "").strip().lower() in CLOSE_BUTTON_NAMES),
                         buttons[-1] if buttons else None)
            tabs.append({"name": control.Name, "selected": selected, "close": close})
            continue
        if kind == "DocumentControl" or depth >= 14:
            continue
        children = control.GetChildren()
        stack.extend((c, depth + 1) for c in reversed(children))
    return tabs


def tabs_to_close(tabs: list[dict], mode: str) -> list[dict]:
    """지금 보는 탭(여러 개 골라 둔 경우 그 탭들)을 기준으로 닫을 탭. 보는 탭을 못 찾으면 아무것도 안 닫는다."""
    picked = [i for i, t in enumerate(tabs) if t["selected"]]
    if not picked:
        return []
    if mode == "others":
        return [t for t in tabs if not t["selected"]]
    if mode == "right":
        return tabs[picked[-1] + 1:]
    if mode == "left":
        return tabs[:picked[0]]
    raise ValueError(mode)


def close_tabs(targets: list[dict]) -> tuple[int, int]:
    """오른쪽부터 차례로 X 단추를 누른다. (닫음, 못 닫음)"""
    closed = failed = 0
    for tab in reversed(targets):
        try:
            tab["close"].GetInvokePattern().Invoke()
            closed += 1
            time.sleep(0.06)
        except Exception:
            failed += 1
    return closed, failed


# ───── 웹 페이지 글 읽기·문구 찾아 누르기 (UIA. 지금 보이는 탭의 페이지만) ─────
CLICKABLE_TYPES = ("ButtonControl", "HyperlinkControl", "MenuItemControl", "TabItemControl",
                   "ListItemControl", "CheckBoxControl", "RadioButtonControl", "SplitButtonControl")
PAUSE_LINE = re.compile(
    r"일시\s*중지|다시\s*제공|이후\s*다시|사용량.{0,30}(한도|제한|초과|다시)|한도.{0,20}(도달|초과)"
    r"|usage\s*limit|limit.{0,40}(reset|again)|resets?\s+(at|in)|try\s+again\s+(after|at|in)", re.I)
PAUSE_TAIL_LINES = 30   # 일시 중지 안내는 보통 페이지 맨 아래(입력칸 근처)에 뜬다. 대화 속 인용은 무시하려고 끝부분만 본다.


def _uia():
    import uiautomation as auto
    from uiautomation import uiautomation as core
    auto.Logger.SetLogFile("")   # 기본은 지금 폴더(저장소 안)에 @AutomationLog.txt 를 만든다 → 끔
    return auto, core._AutomationClient.instance().IUIAutomation


def page_text(hwnd: int) -> str | None:
    """창의 지금 탭 웹 페이지 글 전체. 못 읽으면 None."""
    auto, client = _uia()
    cond = client.CreatePropertyCondition(auto.PropertyId.ControlTypeProperty, auto.ControlType.DocumentControl)
    element = auto.ControlFromHandle(hwnd).Element.FindFirst(4, cond)  # 4 = TreeScope_Descendants
    if not element:
        return None
    try:
        return auto.Control.CreateControlFromElement(element).GetTextPattern().DocumentRange.GetText(-1)
    except Exception:
        return None


def find_pause_line(text: str) -> str | None:
    """페이지 끝부분에서 '사용량 일시 중지' 줄(시각이 들어 있는)을 찾는다."""
    from usage_pause import find_resume
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()][-PAUSE_TAIL_LINES:]
    for i in range(len(lines) - 1, -1, -1):
        for candidate in (lines[i], " ".join(lines[i:i + 2])):  # 시각이 다음 줄로 넘어간 경우
            if len(candidate) < 300 and PAUSE_LINE.search(candidate) and find_resume(candidate):
                return candidate
    return None


def find_clickable(hwnd: int, phrase: str):
    """창의 웹 페이지 안에서 이름이 phrase 인(없으면 phrase 가 들어간) 누를 수 있는 요소. (control, 설명) 또는 None.
    탭 줄·북마크 같은 브라우저 화면은 찾지 않는다('닫기'가 탭 닫기 단추로 잡히지 않게)."""
    auto, client = _uia()
    doc_cond = client.CreatePropertyCondition(auto.PropertyId.ControlTypeProperty, auto.ControlType.DocumentControl)
    root = auto.ControlFromHandle(hwnd).Element.FindFirst(4, doc_cond)
    if not root:
        return None
    exact = root.FindFirst(4, client.CreatePropertyCondition(auto.PropertyId.NameProperty, phrase))
    if exact:
        control = auto.Control.CreateControlFromElement(exact)
        return control, f"{control.ControlTypeName.replace('Control', '')} '{control.Name[:40]}'"
    wanted = phrase.lower()
    for type_name in CLICKABLE_TYPES:
        cond = client.CreatePropertyCondition(auto.PropertyId.ControlTypeProperty, getattr(auto.ControlType, type_name))
        found = root.FindAll(4, cond)
        for i in range(found.Length if found else 0):
            element = found.GetElement(i)
            if wanted in (element.CurrentName or "").lower():
                control = auto.Control.CreateControlFromElement(element)
                return control, f"{type_name.replace('Control', '')} '{control.Name[:40]}'"
    return None


def press_control(control, hwnd: int) -> str:
    """Invoke → 기본 동작 → 토글·선택 → (마지막 수단) 창을 앞으로 가져와 실제 클릭. 쓴 방법을 돌려준다."""
    for how, act in (("누름", lambda: control.GetInvokePattern().Invoke()),
                     ("기본 동작", lambda: control.GetLegacyIAccessiblePattern().DoDefaultAction()),
                     ("토글", lambda: control.GetTogglePattern().Toggle()),
                     ("선택", lambda: control.GetSelectionItemPattern().Select())):
        try:
            act()
            return how
        except Exception:
            continue
    # 마지막 수단: 실제 마우스 클릭. 창이 맨 앞이고, 누를 자리가 그 창 안이며 그 자리의 창이 이 창일 때만.
    if not activate(hwnd):
        raise RuntimeError("창을 앞으로 못 가져옴")
    time.sleep(0.2)
    rect = control.BoundingRectangle
    if rect.width() <= 0 or rect.height() <= 0:
        raise RuntimeError("누를 자리가 화면에 안 보임")
    x, y = rect.xcenter(), rect.ycenter()
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    at = win32gui.WindowFromPoint((x, y))
    if not (left <= x < right and top <= y < bottom) or _user32.GetAncestor(at, 2) != hwnd:
        raise RuntimeError("누를 자리가 창 밖이거나 다른 창에 가려 있음")
    if win32gui.GetForegroundWindow() != hwnd:
        raise RuntimeError("다른 창이 앞으로 옴")
    control.Click(simulateMove=False)
    return "마우스 클릭"


# ───── 자동화: claude.ai 프로젝트 지침 일괄 바꾸기 ─────
INSTR_EDIT_BUTTON = "지침 편집"          # 프로젝트 페이지 오른쪽 '지침' 카드의 연필 단추
INSTR_FIELD = "프로젝트 지침 설정"       # 편집 창(대화상자)과 그 안 글칸의 이름
INSTR_SAVE = "지침 저장"
INSTR_CANCEL = "취소"


def _by_name(hwnd: int, name: str, control_type: str | None = None):
    auto, client = _uia()
    cond = client.CreatePropertyCondition(auto.PropertyId.NameProperty, name)
    if control_type:
        cond = client.CreateAndCondition(cond, client.CreatePropertyCondition(
            auto.PropertyId.ControlTypeProperty, getattr(auto.ControlType, control_type)))
    element = auto.ControlFromHandle(hwnd).Element.FindFirst(4, cond)
    return auto.Control.CreateControlFromElement(element) if element else None


def page_url(hwnd: int) -> str | None:
    """주소창 글(예: claude.ai/project/…)."""
    auto, client = _uia()
    cond = client.CreatePropertyCondition(auto.PropertyId.ControlTypeProperty, auto.ControlType.EditControl)
    element = auto.ControlFromHandle(hwnd).Element.FindFirst(4, cond)  # 첫 글칸 = 주소창
    try:
        return auto.Control.CreateControlFromElement(element).GetValuePattern().Value if element else None
    except Exception:
        return None


def open_instructions(hwnd: int, wait: float = 6.0):
    """'지침 편집'을 눌러 편집 창의 글칸을 돌려준다. 못 열면 None."""
    field = _by_name(hwnd, INSTR_FIELD, "EditControl")
    if field:
        return field
    button = _by_name(hwnd, INSTR_EDIT_BUTTON, "ButtonControl")
    if not button:
        return None
    button.GetInvokePattern().Invoke()
    end = time.time() + wait
    while time.time() < end:
        time.sleep(0.3)
        field = _by_name(hwnd, INSTR_FIELD, "EditControl")
        if field:
            return field
    return None


def close_instructions(hwnd: int, save: bool) -> bool:
    button = _by_name(hwnd, INSTR_SAVE if save else INSTR_CANCEL, "ButtonControl")
    if not button:
        return False
    button.GetInvokePattern().Invoke()
    for _ in range(20):  # 편집 창이 닫힐 때까지
        time.sleep(0.25)
        if not _by_name(hwnd, INSTR_FIELD, "EditControl"):
            return True
    return False


def field_value(field) -> str:
    return (field.GetValuePattern().Value or "").replace("\r\n", "\n")


def fill_field(hwnd: int, field, text: str) -> bool:
    """글칸을 실제 키보드처럼 채운다(전체 선택 → 붙여넣기). 창이 맨 앞이고 글칸 글이 text 와 같으면 True."""
    if win32gui.GetForegroundWindow() != hwnd and not activate(hwnd):
        return False
    field.SetFocus()
    time.sleep(0.15)
    set_clipboard(text)
    # 키를 누르기 바로 전마다 맨 앞 창을 다시 본다(그 사이 다른 창이 앞으로 오면 그 창 글이 바뀌지 않게)
    if win32gui.GetForegroundWindow() != hwnd:
        return False
    press_keys([win32con.VK_CONTROL], ord("A"))
    time.sleep(0.05)
    if win32gui.GetForegroundWindow() != hwnd:
        return False
    press_ctrl_v()
    time.sleep(0.6)
    return win32gui.GetForegroundWindow() == hwnd and field_value(field).strip() == text.strip()


def _aria(control, name: str) -> str | None:
    m = re.search(rf"(?:^|;){name}=([^;]*)", control.AriaProperties or "")
    return m.group(1) if m else None


def find_input(hwnd: int, hint: str = ""):
    """창의 웹 페이지에서 글을 넣을 입력칸을 고른다. (control, 설명) 또는 None.
    hint 가 있으면 이름·자리표시 글(예: '답글')에 그 낱말이 든 칸만. 없으면 '여러 줄 · 맨 아래 · 넓은' 칸
    (채팅 입력 막대)을 먼저, 검색칸은 뒤로."""
    auto, client = _uia()
    doc = auto.ControlFromHandle(hwnd).Element.FindFirst(4, client.CreatePropertyCondition(
        auto.PropertyId.ControlTypeProperty, auto.ControlType.DocumentControl))
    if not doc:
        return None
    found = doc.FindAll(4, client.CreatePropertyCondition(auto.PropertyId.ControlTypeProperty,
                                                          auto.ControlType.EditControl))
    wanted = hint.strip().lower()
    candidates = []
    for i in range(found.Length if found else 0):
        control = auto.Control.CreateControlFromElement(found.GetElement(i))
        try:
            if not control.IsEnabled or not control.IsKeyboardFocusable or _aria(control, "readonly") == "true":
                continue
            rect = control.BoundingRectangle
            if rect.width() < 20 or rect.height() < 8:
                continue
        except Exception:
            continue
        label = f"{control.Name or ''} {control.HelpText or ''}".strip()
        if wanted and wanted not in label.lower():
            continue
        is_search = (control.AriaRole == "searchbox" or re.search(r"검색|search", label, re.I) is not None)
        multiline = _aria(control, "multiline") == "true"
        candidates.append(((not is_search, multiline, rect.bottom, rect.width()), control, label))
    if not candidates:
        return None
    _, control, label = max(candidates, key=lambda c: c[0])
    return control, f"입력칸 '{label[:40] or '(이름 없음)'}'"


def focus_input(hwnd: int, control) -> bool:
    """입력칸에 초점을 주고(필요하면 화면이 그 칸까지 내려감) 글 끝으로 간다. 초점이 정말 그 칸이면 True."""
    auto, client = _uia()
    try:
        control.SetFocus()
    except Exception:
        return False
    time.sleep(0.2)
    focused = auto.GetFocusedControl()
    if not focused or not client.CompareElements(focused.Element, control.Element):
        return False
    if win32gui.GetForegroundWindow() != hwnd:
        return False
    press_keys([win32con.VK_CONTROL], win32con.VK_END)   # 이미 쓴 글이 있으면 그 뒤에 이어서
    return True


def focus_in_browser_ui(hwnd: int) -> bool:
    """키보드 초점이 이 창의 브라우저 글칸(주소창 등)에 있고 웹 페이지 안이 아닌지(Ctrl+L 이 주소창으로 갔는지)."""
    auto, _ = _uia()
    try:
        control = auto.GetFocusedControl()
        if not control or control.ControlTypeName != "EditControl":
            return False
        if _user32.GetAncestor(control.NativeWindowHandle or hwnd, 2) != hwnd:
            return False
        node = control
        for _ in range(40):
            node = node.GetParentControl()
            if not node:
                return True
            if node.ControlTypeName == "DocumentControl":
                return False
            if node.NativeWindowHandle == hwnd:
                return True
        return False
    except Exception:
        return False


def write_json_atomic(path: Path, data) -> None:
    """임시 파일에 쓰고 바꿔 끼운다(쓰다가 꺼져도 원래 파일이 깨지지 않게)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def reload_and_read_instructions(hwnd: int, wait: float = 20.0) -> str | None:
    """페이지를 새로 고친 뒤(F5) 저장된 지침을 읽는다(편집 창에 남은 글이 아니라 서버에 저장된 글)."""
    if win32gui.GetForegroundWindow() != hwnd and not activate(hwnd):
        return None
    press_keys([], win32con.VK_F5)
    time.sleep(2.0)
    end = time.time() + wait
    while time.time() < end and not _by_name(hwnd, INSTR_EDIT_BUTTON, "ButtonControl"):
        time.sleep(0.5)
    field = open_instructions(hwnd)
    if not field:
        return None
    value = field_value(field)
    close_instructions(hwnd, save=False)
    return value


def compose_instructions(current: str, body: str, keep_lines: int) -> str:
    """지금 지침의 맨 위 keep_lines 줄은 그대로 두고, 그 아래를 body 로 바꾼다(사이에 빈 줄 하나)."""
    kept = current.replace("\r\n", "\n").split("\n")[:keep_lines]
    return "\n".join(kept).rstrip() + "\n\n" + body.replace("\r\n", "\n").strip("\n") + "\n"


def normalize_url(text: str) -> str:
    """'naver.com' → 'https://naver.com'. 이미 주소(https:, chrome:, file: …)거나 검색어(띄어쓰기)면 그대로."""
    text = text.strip()
    if (not text or " " in text or re.match(r"^[A-Za-z][\w+.-]*://", text)
            or re.match(r"(?i)^(about|chrome|edge|mailto|data|javascript):", text)):
        return text
    if re.match(r"(?i)^(localhost|127\.0\.0\.1|\d+\.\d+\.\d+\.\d+)(:\d+)?(/|$)", text):
        return "http://" + text
    return "https://" + text if "." in text else text


def describe_macro(steps: list[tuple]) -> str:
    out = []
    for step in steps:
        if step[0] == "text":
            body = step[1].replace("\n", "↵")
            out.append(f"글 '{body[:20]}{'…' if len(body) > 20 else ''}'")
        elif step[0] == "keys":
            out.append(f"[{step[3]}]")
        else:
            out.append(f"{step[1]:g}초 대기")
    return " → ".join(out)


def capture_bits(hwnd: int):
    """PrintWindow 로 창을 찍어 (BGRA 바이트, 너비, 높이). 다른 창에 가려져 있어도 된다."""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    w, h = right - left, bottom - top
    if w <= 0 or h <= 0:
        return None
    hdc = win32gui.GetWindowDC(hwnd)
    src = win32ui.CreateDCFromHandle(hdc)
    mem = src.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    try:
        bmp.CreateCompatibleBitmap(src, w, h)
        mem.SelectObject(bmp)
        ok = _user32.PrintWindow(hwnd, mem.GetSafeHdc(), 2)  # PW_RENDERFULLCONTENT
        bits = bmp.GetBitmapBits(True) if ok else None
    finally:
        win32gui.DeleteObject(bmp.GetHandle())
        mem.DeleteDC()
        src.DeleteDC()
        win32gui.ReleaseDC(hwnd, hdc)
    return (bits, w, h) if bits else None


# ───────────────────────── 점검 모드 (GUI 없이) ─────────────────────────
def check() -> None:
    profiles = load_profiles()
    table = aumid_table(profiles)
    for browser in BROWSERS:
        print(f"{browser['label']} User Data: {browser['user_data']}")
    print(f"설정 파일: {CONFIG}")
    print(f"프로필 {len(profiles)}개")
    for key, info in profiles.items():
        print(f"  {key:16} {info['name']}   [설정 저장 이름: {info['sid']}]")
    print("열린 브라우저 창")
    for hwnd in chrome_windows():
        aumid = window_aumid(hwnd)
        key = table.get(aumid or "", "?")
        print(f"  {hwnd:>10}  {key:16} {aumid!s:32} {win32gui.GetWindowText(hwnd)[:40]}")


if __name__ == "__main__" and "--check" in sys.argv:
    sys.stdout.reconfigure(encoding="utf-8")
    check()
    sys.exit(0)


# ───────────────────────── 화면 ─────────────────────────
import threading  # noqa: E402

import usage_pause  # noqa: E402  같은 폴더: 일시 중지 문구 → 다시 쓸 시각 (pauses.json)
import work_log  # noqa: E402  같은 폴더: 작업 시간 멈출 때 work_log.csv 에 한 줄 (ISSUE-006)
from PySide6.QtCore import QObject, QPoint, QSize, Qt, QTimer, Signal  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QCursor, QIcon, QImage, QKeySequence, QPixmap, QShortcut  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QGridLayout,
    QLineEdit,
    QHBoxLayout, QInputDialog, QLabel, QListView, QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMessageBox, QPlainTextEdit, QProgressDialog, QPushButton, QRadioButton, QSpinBox, QSplitter, QStyle,
    QSystemTrayIcon, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)


class TextScanner(QObject):
    """창들의 페이지 글을 다른 스레드에서 읽어 {hwnd: 글} 로 알려 준다(화면이 멈추지 않게)."""
    done = Signal(object)

    def __init__(self):
        super().__init__()
        self.busy = False

    def start(self, hwnds: list[int]) -> None:
        if self.busy or not hwnds:
            return
        self.busy = True
        threading.Thread(target=self._run, args=(list(hwnds),), daemon=True).start()

    def _run(self, hwnds: list[int]) -> None:
        out = {}
        try:
            import uiautomation as auto
            with auto.UIAutomationInitializerInThread():
                for hwnd in hwnds:
                    try:
                        out[hwnd] = page_text(hwnd)
                    except Exception:
                        out[hwnd] = None
        except Exception:
            pass
        finally:
            self.busy = False
            self.done.emit(out)


def fmt_hm(seconds: float) -> str:
    hours, minutes = divmod(int(seconds) // 60, 60)
    return f"{hours}:{minutes:02d}"


def fmt_long(seconds: float) -> str:
    hours, minutes = divmod(int(seconds) // 60, 60)
    return f"{hours}시간 {minutes}분" if hours else f"{minutes}분"


def parse_hotkey(text: str) -> tuple[int, int]:
    """'Ctrl+Alt+T' → (RegisterHotKey 수식 값, 가상 키). 모르면 ValueError."""
    mod_bits = {"ctrl": 0x2, "alt": 0x1, "shift": 0x4, "win": 0x8}
    *mods, key = [p.strip().lower() for p in text.split("+")]
    bits = 0x4000  # MOD_NOREPEAT
    for m in mods:
        bits |= mod_bits[m]
    vk = SPECIAL_KEYS.get(key) or (ord(key.upper()) if len(key) == 1 and key.isascii() and key.isalnum() else None)
    if not vk:
        raise ValueError(text)
    return bits, vk


class Popup(QLabel):
    """마우스 옆에 몇 초 떴다 사라지는 작은 안내(포커스를 빼앗지 않음)."""

    def __init__(self):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("QLabel { background: #202833; color: #f0f0f0; border: 1px solid #5a6a80;"
                           " padding: 10px 14px; font-size: 13px; }")
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_text(self, text: str, seconds: float = 6):
        self.setText(text)
        self.adjustSize()
        pos = QCursor.pos() + QPoint(18, 18)
        screen = QApplication.screenAt(QCursor.pos())
        if screen:  # 화면 밖으로 나가지 않게
            area = screen.availableGeometry()
            pos.setX(min(pos.x(), area.right() - self.width()))
            pos.setY(min(pos.y(), area.bottom() - self.height()))
        self.move(pos)
        self.show()
        self.raise_()
        self.hide_timer.start(int(seconds * 1000))


class InstructionsDialog(QDialog):
    """프로젝트 지침 일괄 바꾸기: 새 글 + 남길 줄 수 + 안전 설정."""

    def __init__(self, parent, scope: str):
        super().__init__(parent)
        self.setWindowTitle("프로젝트 지침 일괄 바꾸기 (claude.ai)")
        self.resize(640, 560)
        self.body = QPlainTextEdit()
        self.body.setPlaceholderText("새 지침 전체를 여기에 한 번 붙여 넣으세요(Ctrl+V).\n"
                                     "첫 줄이 [이름] 줄이어도 괜찮습니다 — 그 줄은 빼고, 창마다 원래 이름 줄을 남깁니다.")
        self.drop_first = QCheckBox("붙여 넣은 글의 첫 줄이 [ 로 시작하면 그 줄은 빼기")
        self.drop_first.setChecked(True)
        self.note = QLabel()
        self.note.setStyleSheet("color: gray")
        self.body.textChanged.connect(self.update_note)
        self.drop_first.toggled.connect(self.update_note)
        self.keep = QSpinBox()
        self.keep.setRange(1, 20)
        self.keep.setValue(1)
        self.only_bracket = QCheckBox("첫 줄이 [ 로 시작하는 창만 (작업자 이름 줄이 있는 프로젝트만)")
        self.only_bracket.setChecked(True)
        self.preview_only = QCheckBox("미리보기만 — 글칸에 넣어 확인하고 저장하지 않고 취소")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("다음: 지금 지침 읽기")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        keep_row = QHBoxLayout()
        keep_row.addWidget(QLabel("지금 지침의 맨 위"))
        keep_row.addWidget(self.keep)
        keep_row.addWidget(QLabel("줄은 그대로 두고, 그 아래를 아래 글로 바꿉니다."))
        keep_row.addStretch()
        guide = QLabel(f"대상: {scope}\n각 창은 claude.ai 프로젝트 페이지(오른쪽에 '지침' 카드)를 열어 둔 상태여야 합니다.\n"
                       "다음을 누르면 먼저 창마다 지금 지침을 읽어 무엇이 바뀌는지 보여 주고, 한 번 더 묻습니다.")
        guide.setWordWrap(True)
        box = QVBoxLayout(self)
        box.addWidget(guide)
        box.addLayout(keep_row)
        box.addWidget(self.body)
        box.addWidget(self.note)
        box.addWidget(self.drop_first)
        box.addWidget(self.only_bracket)
        box.addWidget(self.preview_only)
        box.addWidget(buttons)
        self.update_note()
        self.body.setFocus()

    def final_body(self) -> str:
        """창마다 이름 줄 아래에 들어갈 글."""
        lines = self.body.toPlainText().replace("\r\n", "\n").strip("\n").split("\n")
        if self.drop_first.isChecked() and lines and lines[0].lstrip().startswith("["):
            lines = lines[1:]
        return "\n".join(lines).strip("\n")

    def update_note(self):
        text = self.body.toPlainText().strip()
        if not text:
            self.note.setText("")
            return
        first = text.split("\n", 1)[0].strip()
        dropped = self.drop_first.isChecked() and first.startswith("[")
        self.note.setText((f"첫 줄 '{first[:40]}' 은 빼고 " if dropped else "") +
                          f"{len(self.final_body())}자를 넣습니다.")

    def accept(self):
        if not self.final_body().strip():
            QMessageBox.warning(self, "프로젝트 지침", "새 지침 글이 비어 있습니다.")
            return
        super().accept()


class GotoDialog(QDialog):
    """사이트 이동 창: 주소(최근 주소 목록) + 방식(지금 탭 / 새 탭)."""

    def __init__(self, parent, scope: str, recent: list[str], mode: str, has_windows: bool, can_launch: bool):
        super().__init__(parent)
        self.setWindowTitle("사이트 이동")
        self.resize(520, 220)
        self.url = QComboBox()
        self.url.setEditable(True)
        self.url.addItems(recent)
        self.url.setCurrentText(recent[0] if recent else "")
        self.url.lineEdit().setPlaceholderText("예: naver.com, https://www.neis.go.kr")
        self.url.lineEdit().selectAll()
        self.this_tab = QRadioButton("지금 보는 탭을 이 주소로 (창이 하나씩 앞으로 와서 주소창에 넣음)")
        self.new_tab = QRadioButton("새 탭으로 열기 (창 전환 없음 · 안 열린 프로필은 새 창으로)")
        self.this_tab.setEnabled(has_windows)
        self.new_tab.setEnabled(can_launch)
        use_new = (mode == "new" and can_launch) or not has_windows
        (self.new_tab if use_new else self.this_tab).setChecked(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("이동")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box = QVBoxLayout(self)
        box.addWidget(QLabel(f"대상: {scope}"))
        box.addWidget(self.url)
        box.addWidget(self.this_tab)
        box.addWidget(self.new_tab)
        note = QLabel("기타 브라우저 창은 '지금 탭' 방식만 되고, 주소창이 없는 창(앱 창 등)은 건너뜁니다. "
                      "지금 탭 방식은 그동안 마우스·키보드를 쓰지 마세요.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray")
        box.addWidget(note)
        box.addWidget(buttons)


class BroadcastDialog(QDialog):
    """일괄 입력 창: 글 + 특수 키 단추. 단추를 누르면 커서 자리에 {Enter} 같은 표시가 들어간다."""
    KEY_BUTTONS = ["Enter", "Shift+Enter", "Ctrl+Enter", "Tab", "Esc", "Backspace",
                   "Ctrl+A", "Ctrl+V", "Up", "Down", "F5", "대기 1"]

    def __init__(self, parent, count: int, last_text: str, mode: str = "find", hint: str = ""):
        super().__init__(parent)
        self.setWindowTitle("일괄 입력")
        self.resize(580, 500)
        self.edit = QPlainTextEdit(last_text)
        self.edit.selectAll()
        grid = QGridLayout()
        for i, name in enumerate(self.KEY_BUTTONS):
            button = QPushButton("{" + name + "}")
            button.setAutoDefault(False)
            button.clicked.connect(lambda _=False, n=name: self.insert("{" + n + "}"))
            grid.addWidget(button, i // 6, i % 6)
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        self.preview.setStyleSheet("color: gray")
        self.edit.textChanged.connect(self.update_preview)
        self.find_box = QRadioButton("입력칸을 찾아서 넣기 (커서가 없어도 — 보통 맨 아래 채팅 입력 막대)")
        self.at_cursor = QRadioButton("지금 커서가 있는 자리에 넣기")
        (self.at_cursor if mode == "cursor" else self.find_box).setChecked(True)
        self.hint = QLineEdit(hint)
        self.hint.setPlaceholderText("입력칸 이름에 든 낱말(예: 답글). 비우면 알아서 고름")
        self.hint.setToolTip("입력칸 이름이나 칸 안에 흐리게 보이는 글(자리표시)에 이 낱말이 든 칸만 고른다")
        self.find_box.toggled.connect(self.hint.setEnabled)
        self.hint.setEnabled(self.find_box.isChecked())
        hint_row = QHBoxLayout()
        hint_row.addSpacing(24)
        hint_row.addWidget(QLabel("칸 이름:"))
        hint_row.addWidget(self.hint)
        guide = QLabel(
            f"창 {count}개에 차례로 넣습니다. 창이 하나씩 앞으로 오니 그동안 마우스·키보드를 쓰지 마세요.\n"
            "특수 키는 중괄호로: {Enter} {Tab} {Esc} {Ctrl+A} {Shift+Enter} {F5} {Up} {대기 1.5}\n"
            "중괄호 글자 자체는 {{ }} 로 적습니다. 그냥 줄바꿈은 글 속 줄바꿈으로 들어갑니다.")
        guide.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("보내기")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box = QVBoxLayout(self)
        box.addWidget(guide)
        box.addWidget(self.find_box)
        box.addLayout(hint_row)
        box.addWidget(self.at_cursor)
        box.addWidget(self.edit)
        box.addLayout(grid)
        box.addWidget(self.preview)
        box.addWidget(buttons)
        self.update_preview()

    def insert(self, token: str):
        self.edit.insertPlainText(token)
        self.edit.setFocus()

    def update_preview(self):
        try:
            steps = parse_macro(self.edit.toPlainText())
            self.preview.setText("순서: " + (describe_macro(steps) or "(비어 있음)"))
            self.preview.setStyleSheet("color: gray")
        except ValueError as e:
            self.preview.setText(f"⚠ {e}")
            self.preview.setStyleSheet("color: #d04040")

    def accept(self):
        try:
            parse_macro(self.edit.toPlainText())
        except ValueError as e:
            QMessageBox.warning(self, "일괄 입력", str(e))
            return
        super().accept()

ROLE = Qt.ItemDataRole.UserRole
NAME_ROLE = Qt.ItemDataRole.UserRole + 1
DEFAULT_HOTKEYS = {"show": "Ctrl+Alt+T", "toggle": "Ctrl+Alt+S"}
HOTKEY_IDS = {"show": 0xB001, "toggle": 0xB002}
WORK_ALERT_COLOR = QColor("#ff6b6b")
DRAG = Qt.ItemFlag.ItemIsDragEnabled
DROP = Qt.ItemFlag.ItemIsDropEnabled
EDIT = Qt.ItemFlag.ItemIsEditable
ALERT_BG = QBrush(QColor("#ff9c9c"))


def to_qimage(captured) -> QImage | None:
    if not captured:
        return None
    bits, w, h = captured
    image = QImage(bits, w, h, w * 4, QImage.Format.Format_RGB32).copy()
    return image.scaled(THUMB_W, THUMB_H, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)


def signature(image: QImage) -> bytes:
    small = image.scaled(32, 32).convertToFormat(QImage.Format.Format_Grayscale8)
    return bytes(small.constBits())[:1024]


def difference(a: bytes, b: bytes) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / max(len(a), 1)


class Tree(QTreeWidget):
    def __init__(self, on_drop):
        super().__init__()
        self.on_drop = on_drop
        self.setHeaderLabels(["그룹 / 프로필", "창", "작업", "시작 URL"])
        self.setColumnWidth(0, 260)
        self.setColumnWidth(1, 34)
        self.setColumnWidth(2, 120)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed)  # 이름 바꾸기는 F2 로만
        root = self.invisibleRootItem()
        root.setFlags(root.flags() & ~DROP)  # 프로필은 그룹 안으로만 떨어진다.

    def dropEvent(self, event):
        super().dropEvent(event)
        self.on_drop()


class Manager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chrome·Edge 프로필 매니저")
        self.resize(1200, 720)
        self.profile_info = load_profiles()
        self.profiles = {key: info["name"] for key, info in self.profile_info.items()}  # 키 → 표시 이름
        self.aumids = aumid_table(self.profile_info)
        self.config_warning = ""
        try:
            self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.cfg = {}
        except Exception:  # 깨진 설정은 지우지 않고 따로 남긴다(빈 설정으로 덮어써 그룹이 사라지지 않게)
            broken = CONFIG.with_name(f"config.broken-{time.strftime('%Y%m%d-%H%M%S')}.json")
            try:
                os.replace(CONFIG, broken)
            except OSError:
                pass
            self.cfg = {}
            self.config_warning = f"설정 파일이 깨져 있어 빈 설정으로 시작했습니다. 원래 파일: {broken.name}"
        self.cfg.pop("last_broadcast", None)   # 예전 판: 일괄 입력 글 전체를 저장하던 것 지움(이제 메모리에만)
        self.last_broadcast = ""
        self.cfg_version = int(self.cfg.get("id_version", 1) or 1)
        self.cfg.setdefault("start_url", {})
        self.cfg.setdefault("aliases", {})   # 기타 Chrome 창 앱 ID → 사용자가 붙인 이름
        self.cfg.setdefault("work", {})      # 작업 시간: {프로필 키 또는 "group:이름": {start, alert_min, alerted}}
        self.cfg.setdefault("hotkeys", {})
        for name, default in DEFAULT_HOTKEYS.items():
            self.cfg["hotkeys"].setdefault(name, default)
        self.cfg.setdefault("pause_done", {})   # 이미 알린 일시 중지 줄(같은 안내가 남아 있어도 내일 시각으로 다시 적지 않게)
        self.key_of_sid = {info["sid"]: key for key, info in self.profile_info.items()}
        self.foreign = {"groups": {}, "start_url": {}, "work": {}}   # 이 PC 에 없는 계정 설정(지우지 않고 그대로 저장)
        self.cfg_from_file()
        self.popup = Popup()
        self.pause_path = usage_pause.store_path()
        self.pauses = usage_pause.load(self.pause_path)   # {sid(또는 손으로 적은 이름): {resume, seen, text}}
        self.migrate_pause_names()
        self.scanner = TextScanner()
        self.scanner.done.connect(self.on_texts)
        self.other_group: QTreeWidgetItem | None = None
        self.windows: dict[int, dict] = {}   # hwnd → 창 상태. key = 프로필 폴더명 또는 "@앱ID"
        self.capture_order: list[int] = []
        self.launch_queue: list[tuple[str, str, bool]] = []   # (프로필 키, 주소, 새 창?)
        self.building = False

        # 왼쪽: 그룹 트리
        self.tree = Tree(self.after_drop)
        self.tree.itemDoubleClicked.connect(self.on_double_click)
        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.itemSelectionChanged.connect(self.apply_filter)

        buttons = QVBoxLayout()
        for row in (
            (("열기", self.open_selected, "고른 프로필(그룹이면 그룹 전체)을 연다. 이미 열려 있으면 앞으로 가져온다. Shift 를 누르고 누르면 늘 새 창."),
             ("사이트 이동", self.go_to_site, "고른 프로필(안 고르면 열린 프로필 창 전체)을 같은 주소로 보낸다. 지금 탭을 바꾸거나 새 탭으로 연다."),
             ("일괄 입력", self.broadcast, "열린 창(고른 프로필이 있으면 그 창들)의 커서 위치에 같은 글·특수 키를 넣는다."),
             ("일괄 닫기", self.close_windows, "트리에서 고른 프로필(그룹이면 그룹 전체)의 창을 모두 닫는다. 아무것도 안 고르면 프로필 창 전체(기타 창은 직접 고를 때만)."),
             ("탭 정리 ▾", self.tab_menu, "다른 탭 닫기 / 오른쪽 탭 닫기 / 왼쪽 탭 닫기를 여러 창에 한꺼번에. 창 전환 없음.")),
            (("그룹 추가", self.add_group, "새 그룹. 이름은 그룹을 고르고 F2 로 바꾼다."),
             ("그룹 삭제", self.remove_group, "고른 그룹을 지우고 안의 프로필은 미분류로 옮긴다."),
             ("시작 URL", self.set_start_url, "고른 프로필들의 시작 URL 을 한 번에 바꾼다(비우면 해제)."),
             ("자동화 ▾", self.automation_menu, "여러 창에 같은 웹 작업을 차례로: claude.ai 프로젝트 지침 일괄 바꾸기 등")),
        ):
            line = QHBoxLayout()
            for label, slot, tip in row:
                button = QPushButton(label)
                button.setToolTip(tip)
                button.clicked.connect(slot)
                line.addWidget(button)
            buttons.addLayout(line)

        self.idle_spin = QSpinBox()
        self.idle_spin.setRange(5, 86400)
        self.idle_spin.setValue(self.cfg.get("idle_sec", 60))
        self.timer_spin = QSpinBox()
        self.timer_spin.setRange(1, 1440)
        self.timer_spin.setValue(self.cfg.get("timer_min", 10))
        self.idle_spin.valueChanged.connect(self.save)
        self.timer_spin.valueChanged.connect(self.save)
        self.filter_box = QCheckBox("트리에서 고른 것만 미리보기")
        self.filter_box.setChecked(self.cfg.get("filter", False))
        self.filter_box.toggled.connect(self.apply_filter)
        self.filter_box.toggled.connect(self.save)
        self.pause_box = QCheckBox("사용량 일시 중지 시각 찾기")
        self.pause_box.setToolTip("열린 창 페이지 끝부분에 '오후 12:10 이후 다시 제공' 같은 안내가 뜨면 그 시각을 적고 그때 알린다(20초마다 확인)")
        self.pause_box.setChecked(self.cfg.get("pause_scan", True))
        self.pause_box.toggled.connect(self.save)

        self.work_spin = QDoubleSpinBox()
        self.work_spin.setRange(0, 24)
        self.work_spin.setSingleStep(0.5)
        self.work_spin.setDecimals(1)
        self.work_spin.setSpecialValueText("끔")
        self.work_spin.setValue(self.cfg.get("work_alert_hours", 5))
        self.work_spin.setToolTip("작업 시간 재기를 시작할 때 기본으로 걸 알림. 0 = 알림 없음")
        self.work_spin.valueChanged.connect(self.save)

        settings = QHBoxLayout()
        settings.addWidget(QLabel("변화 감시(초)"))
        settings.addWidget(self.idle_spin)
        settings.addWidget(QLabel("타이머(분)"))
        settings.addWidget(self.timer_spin)
        settings.addWidget(QLabel("작업 알림(시간)"))
        settings.addWidget(self.work_spin)
        settings.addStretch()

        hk = self.cfg["hotkeys"]
        help_text = QLabel("미리보기: 클릭=창 앞으로 · 드래그/Shift+클릭=여러 개 고르기 · Del=고른 창 닫기\n"
                           "Ctrl+클릭=타이머 시작/취소 · 오른쪽 클릭=변화 감시·닫기 등 · 기타 창 이름은 F2\n"
                           f"트리 오른쪽 클릭=작업 시간 재기 · 어디서든 {hk['show']}=작업 시간 보기, "
                           f"{hk['toggle']}=지금 창 프로필 시작/멈춤")
        help_text.setStyleSheet("color: gray")

        left = QWidget()
        box = QVBoxLayout(left)
        box.addLayout(buttons)
        box.addWidget(self.tree)
        box.addLayout(settings)
        checks = QHBoxLayout()
        checks.addWidget(self.filter_box)
        checks.addWidget(self.pause_box)
        checks.addStretch()
        box.addLayout(checks)
        box.addWidget(help_text)

        # 오른쪽: 미리보기
        self.thumbs = QListWidget()
        self.thumbs.setViewMode(QListView.ViewMode.IconMode)
        self.thumbs.setResizeMode(QListView.ResizeMode.Adjust)
        self.thumbs.setMovement(QListView.Movement.Static)
        self.thumbs.setIconSize(QSize(THUMB_W, THUMB_H))
        self.thumbs.setGridSize(QSize(THUMB_W + 20, THUMB_H + 70))
        self.thumbs.setWordWrap(True)
        self.thumbs.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.thumbs.setSelectionRectVisible(True)
        self.thumbs.itemClicked.connect(self.on_thumb_click)
        self.thumbs.itemSelectionChanged.connect(self.on_thumb_selection)
        self.thumbs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.thumbs.customContextMenuRequested.connect(self.thumb_menu)
        delete_key = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.thumbs)
        delete_key.setContext(Qt.ShortcutContext.WidgetShortcut)
        delete_key.activated.connect(self.close_selected_thumbs)

        self.thumb_count = QLabel()
        self.close_thumbs_button = QPushButton("고른 창 닫기")
        self.close_thumbs_button.clicked.connect(self.close_selected_thumbs)
        clear_button = QPushButton("고르기 해제")
        clear_button.clicked.connect(self.thumbs.clearSelection)
        thumb_bar = QHBoxLayout()
        thumb_bar.addWidget(self.thumb_count)
        thumb_bar.addStretch()
        thumb_bar.addWidget(self.close_thumbs_button)
        thumb_bar.addWidget(clear_button)
        right = QWidget()
        right_box = QVBoxLayout(right)
        right_box.setContentsMargins(0, 0, 0, 0)
        right_box.addLayout(thumb_bar)
        right_box.addWidget(self.thumbs)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([500, 700])
        self.setCentralWidget(splitter)

        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Chrome·Edge 프로필 매니저")
        self.tray.activated.connect(lambda *_: (self.showNormal(), self.raise_(), self.activateWindow()))
        self.tray.show()

        self.build_tree()
        self.monitor()
        self.on_thumb_selection()
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.tree_menu)
        self.register_hotkeys()
        try:
            _uia()
        except Exception:
            pass
        if self.config_warning:
            self.statusBar().showMessage(self.config_warning, 60000)
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.start_scan)
        self.scan_timer.start(20_000)
        QTimer.singleShot(3000, self.start_scan)
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.monitor)
        self.monitor_timer.start(1000)

    # ───── 그룹 / 프로필 트리 ─────
    def group_item(self, name: str) -> QTreeWidgetItem:
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if not item.data(0, ROLE) and item.text(0) == name and item is not self.other_group:
                return item
        item = QTreeWidgetItem([name])
        item.setData(0, NAME_ROLE, name)  # 이름을 바꾸면 작업 시간을 새 이름으로 옮기려고 기억
        flags = (item.flags() | DROP) & ~DRAG
        item.setFlags(flags & ~EDIT if name == UNGROUPED else flags | EDIT)
        self.tree.addTopLevelItem(item)
        item.setExpanded(True)
        return item

    def profile_item(self, folder: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([self.profiles[folder], "", "", self.cfg["start_url"].get(folder, "")])
        item.setData(0, ROLE, folder)
        item.setToolTip(0, folder)
        item.setFlags((item.flags() | DRAG) & ~DROP & ~EDIT)
        return item

    def build_tree(self):
        self.building = True
        try:
            seen = set()
            for group in self.cfg.get("groups", []):
                parent = self.group_item(group["name"])
                for folder in group["profiles"]:
                    if folder in self.profiles and folder not in seen:
                        parent.addChild(self.profile_item(folder))
                        seen.add(folder)
            for folder in self.profiles:  # 새로 생긴 프로필은 미분류로
                if folder not in seen:
                    self.group_item(UNGROUPED).addChild(self.profile_item(folder))
        finally:
            self.building = False

    def profile_items(self) -> list[QTreeWidgetItem]:
        out = []
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            out += [group.child(j) for j in range(group.childCount())]
        return out

    def after_drop(self):
        for i in reversed(range(self.tree.topLevelItemCount())):
            item = self.tree.topLevelItem(i)
            if item.data(0, ROLE):  # 그룹 밖으로 떨어진 프로필은 미분류로
                self.tree.takeTopLevelItem(i)
                self.group_item(UNGROUPED).addChild(item)
        self.save()
        self.reorder_thumbs()

    # ───── 기타 Chrome 창(다른 데이터 폴더로 띄운 Chrome, 앱 창 등) ─────
    def other_name(self, aumid: str) -> str:
        if self.cfg["aliases"].get(aumid):
            return self.cfg["aliases"][aumid]
        if aumid.endswith(".SystemProfile"):
            return "프로필 선택 창"
        for browser in BROWSERS:
            if aumid.startswith(browser["aumid"] + "."):
                rest = aumid[len(browser["aumid"]) + 1:].replace(".", " · ")
                return rest if browser["label"] == "Chrome" else f"{browser['label']} · {rest}"
        return aumid

    def refresh_other_group(self):
        """열린 기타 창을 앱 ID 별로 트리 맨 아래 '기타 Chrome 창' 그룹에 보인다."""
        keys = sorted({st["key"] for st in self.windows.values() if not st["folder"]})
        group = self.other_group
        if not keys:
            if group is not None:
                self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(group))
                self.other_group = None
            return
        if group is None:
            group = self.other_group = QTreeWidgetItem([OTHER])
            group.setFlags(group.flags() & ~DROP & ~DRAG & ~EDIT)
            group.setForeground(0, QBrush(QColor("gray")))
            group.setToolTip(0, "다른 데이터 폴더로 띄운 Chrome(자동화용 등)·앱 창. 이름은 고르고 F2 로 바꾼다.")
            self.tree.addTopLevelItem(group)
            group.setExpanded(True)
        else:  # 사용자가 그룹을 새로 만들어도 늘 맨 아래에 둔다
            index = self.tree.indexOfTopLevelItem(group)
            if index != self.tree.topLevelItemCount() - 1:
                expanded = group.isExpanded()
                self.tree.takeTopLevelItem(index)
                self.tree.addTopLevelItem(group)
                group.setExpanded(expanded)
        have = {group.child(i).data(0, ROLE): group.child(i) for i in range(group.childCount())}
        for key, item in have.items():
            if key not in keys:
                group.removeChild(item)
        for key in keys:
            if key not in have:
                item = QTreeWidgetItem([self.other_name(key[1:]), "", "", ""])
                item.setData(0, ROLE, key)
                item.setToolTip(0, key[1:])
                item.setFlags((item.flags() | EDIT) & ~DRAG & ~DROP)
                group.addChild(item)

    def on_item_changed(self, item, column):
        if self.building or column != 0:
            return
        key = item.data(0, ROLE)
        if key and key.startswith("@"):  # 기타 창 이름 바꾸기
            aumid, name = key[1:], item.text(0).strip()
            if name and name != self.other_name(aumid):
                self.cfg["aliases"][aumid] = name
            elif not name:
                self.cfg["aliases"].pop(aumid, None)
                self.building = True
                item.setText(0, self.other_name(aumid))
                self.building = False
            self.save()
            self.monitor()
        elif not key:  # 그룹 이름 바꾸기 → 그 그룹의 작업 시간도 새 이름으로
            old, new = item.data(0, NAME_ROLE), item.text(0)
            others = [self.tree.topLevelItem(i).text(0) for i in range(self.tree.topLevelItemCount())
                      if self.tree.topLevelItem(i) is not item and self.tree.topLevelItem(i) is not self.other_group]
            if old and new != old and (new in others or new in self.foreign["groups"] or not new.strip()):
                self.building = True
                try:
                    item.setText(0, old)
                finally:
                    self.building = False
                self.statusBar().showMessage(f"'{new}' 그룹이 이미 있거나 이름이 비어 있어 바꾸지 않았습니다.", 10000)
                return
            if old and old != new and f"group:{old}" in self.cfg["work"]:
                self.cfg["work"][f"group:{new}"] = self.cfg["work"].pop(f"group:{old}")
            if old and old != new and old in self.foreign["groups"]:  # 다른 PC 계정도 새 이름 그룹으로
                self.foreign["groups"][new] = self.foreign["groups"].pop(old)
            item.setData(0, NAME_ROLE, new)
            self.save()

    def selected_profiles(self) -> list[str]:
        """트리에서 고른 키 목록(그룹이면 그 안 전체). 기타 창은 '@앱ID'."""
        result = []
        for item in self.tree.selectedItems():
            children = [item] if item.data(0, ROLE) else [item.child(i) for i in range(item.childCount())]
            result += [c.data(0, ROLE) for c in children if c.data(0, ROLE) not in result]
        return result

    # ───── 설정 파일 ↔ 이 PC 키 (다른 PC 와 함께 써도 계정 기준으로 맞게) ─────
    def sid(self, key: str) -> str:
        """이 PC 키 → 설정 파일에 적는 이름. 그룹("group:…")·기타 창("@…")은 그대로."""
        info = self.profile_info.get(key)
        return info["sid"] if info else key

    def local_key(self, sid: str) -> str | None:
        """설정 파일 이름 → 이 PC 키. 이 PC 에 없는 계정이면 None."""
        if sid in self.key_of_sid:
            return self.key_of_sid[sid]
        if sid in self.profile_info and (self.cfg_version < 2 or self.profile_info[sid]["sid"] == sid):
            return sid   # 예전(폴더 이름) 설정을 이 PC 에서 처음 옮길 때, 또는 로그인 안 한 프로필
        if sid.startswith(("group:", "@")):
            return sid
        return None

    def cfg_from_file(self):
        """파일의 sid 를 이 PC 키로 바꿔 self.cfg 에 두고, 이 PC 에 없는 계정 설정은 self.foreign 에 떼어 둔다."""
        for name in ("start_url", "work"):
            local = {}
            for sid, value in self.cfg.get(name, {}).items():
                key = self.local_key(sid)
                if key:
                    local[key] = value
                else:
                    self.foreign[name][sid] = value
            self.cfg[name] = local
        groups = []
        for group in self.cfg.get("groups", []):
            mine, others = [], []
            for sid in group.get("profiles", []):
                key = self.local_key(sid)
                (mine if key else others).append(key or sid)
            groups.append({"name": group["name"], "profiles": mine})
            if others:
                self.foreign["groups"][group["name"]] = others
        self.cfg["groups"] = groups

    def cfg_to_file(self) -> dict:
        out = dict(self.cfg)
        out["groups"] = [{"name": g["name"],
                          "profiles": [self.sid(k) for k in g["profiles"]] + self.foreign["groups"].get(g["name"], [])}
                         for g in self.cfg["groups"]]
        names = {g["name"] for g in self.cfg["groups"]}
        out["groups"] += [{"name": n, "profiles": sids} for n, sids in self.foreign["groups"].items() if n not in names]
        for name in ("start_url", "work"):
            out[name] = {**self.foreign[name], **{self.sid(k): v for k, v in self.cfg[name].items()}}
        out["id_version"] = 2   # 2 = 계정(이메일) 기준
        return out

    def migrate_pause_names(self):
        """pauses.json 의 예전 폴더 이름을 sid 로."""
        changed = False
        for name in list(self.pauses):
            key = self.local_key(name)
            if key and self.sid(key) != name and self.sid(key) not in self.pauses:
                self.pauses[self.sid(key)] = self.pauses.pop(name)
                changed = True
        for name in list(self.cfg["pause_done"]):
            key = self.local_key(name)
            if key and self.sid(key) != name:
                self.cfg["pause_done"][self.sid(key)] = self.cfg["pause_done"].pop(name)
        if changed:
            self.save_pauses()

    def save(self, *_):
        if self.building:
            return
        groups = []
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            if group is self.other_group:
                continue
            folders = [group.child(j).data(0, ROLE) for j in range(group.childCount())]
            groups.append({"name": group.text(0), "profiles": folders})
        self.cfg.update(groups=groups, idle_sec=self.idle_spin.value(),
                        timer_min=self.timer_spin.value(), filter=self.filter_box.isChecked(),
                        work_alert_hours=self.work_spin.value(), pause_scan=self.pause_box.isChecked())
        write_json_atomic(CONFIG, self.cfg_to_file())

    def add_group(self, *_):
        name, ok = QInputDialog.getText(self, "그룹 추가", "그룹 이름:")
        if ok and name.strip():
            self.group_item(name.strip())
            self.save()

    def remove_group(self, *_):
        groups = [it for it in self.tree.selectedItems() if not it.data(0, ROLE)
                  and it.text(0) != UNGROUPED and it is not self.other_group]
        for group in groups:
            children = group.takeChildren()
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(group))
            self.group_item(UNGROUPED).addChildren(children)
            self.cfg["work"].pop(f"group:{group.text(0)}", None)   # 그 그룹 작업 시간도 끝
            others = self.foreign["groups"].pop(group.text(0), [])  # 다른 PC 계정도 미분류로
            if others:
                self.foreign["groups"].setdefault(UNGROUPED, []).extend(others)
        if groups:
            self.save()

    def set_start_url(self, *_):
        folders = [k for k in self.selected_profiles() if not k.startswith("@")]
        if not folders:
            return
        url, ok = QInputDialog.getText(self, "시작 URL", f"프로필 {len(folders)}개의 시작 URL (비우면 해제):")
        if not ok:
            return
        url = url.strip()
        for item in self.profile_items():
            if item.data(0, ROLE) in folders:
                item.setText(3, url)
        for folder in folders:
            if url:
                self.cfg["start_url"][folder] = url
            else:
                self.cfg["start_url"].pop(folder, None)
        self.save()

    # ───── 창 열기 ─────
    def on_double_click(self, item, _column):
        if item.data(0, ROLE):
            self.open_profiles([item.data(0, ROLE)])

    def open_selected(self, *_):
        self.open_profiles(self.selected_profiles())

    def open_profiles(self, folders):
        force_new = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)
        for folder in folders:
            existing = [h for h, st in self.windows.items() if st["key"] == folder]
            if folder.startswith("@"):  # 기타 창은 새로 띄울 수 없어 앞으로만
                if existing:
                    activate(existing[-1])
            elif existing and not force_new:
                activate(existing[-1])
            else:
                self.launch_queue.append((folder, self.cfg["start_url"].get(folder, ""), True))
        self.launch_next()

    def launch_next(self):
        """대기열 (프로필 키, 주소, 새 창?) 을 0.4초 간격으로 하나씩 띄운다(한꺼번에 띄우면 버벅임).
        새 창이 아니면 그 프로필의 마지막 창에 새 탭으로 열린다(창이 없으면 새 창)."""
        if not self.launch_queue:
            return
        key, url, new_window = self.launch_queue.pop(0)
        info = self.profile_info[key]
        args = [info["exe"], f"--profile-directory={info['folder']}"]
        if new_window:
            args.append("--new-window")
        if url:
            args.append(url)
        subprocess.Popen(args)
        if self.launch_queue:
            QTimer.singleShot(400, self.launch_next)

    # ───── 미리보기 / 감시 / 알림 ─────
    def label(self, hwnd: int) -> str:
        st = self.windows.get(hwnd)
        if not st:
            return "닫힌 창"
        return self.profiles[st["folder"]] if st["folder"] else f"기타 · {self.other_name(st['aumid'])}"

    def sort_key(self, hwnd: int):
        order = {item.data(0, ROLE): i for i, item in enumerate(self.profile_items())}
        return (order.get(self.windows[hwnd]["key"], 10_000), hwnd)

    def reorder_thumbs(self):
        """미리보기를 트리 순서(그룹 → 프로필)대로 늘어놓는다."""
        wanted = sorted(self.windows, key=self.sort_key)
        current = [self.thumbs.item(i).data(ROLE) for i in range(self.thumbs.count())]
        if wanted == current:
            return
        while self.thumbs.count():
            self.thumbs.takeItem(0)
        for hwnd in wanted:
            self.thumbs.addItem(self.windows[hwnd]["item"])
        self.apply_filter()

    def apply_filter(self):
        chosen = set(self.selected_profiles()) if self.filter_box.isChecked() else set()
        for st in self.windows.values():
            st["item"].setHidden(bool(chosen) and st["key"] not in chosen)

    def sync_windows(self, now: float) -> bool:
        live = chrome_windows()
        changed = False
        for hwnd in [h for h in self.windows if h not in live]:  # 닫힌 창
            self.thumbs.takeItem(self.thumbs.row(self.windows.pop(hwnd)["item"]))
            changed = True
        for hwnd in live:
            if hwnd in self.windows:
                continue
            aumid = window_aumid(hwnd)
            if not aumid:
                continue  # 앱 ID 가 아직 안 붙은 막 뜬 창은 다음 차례에
            folder = self.aumids.get(aumid)
            item = QListWidgetItem()
            item.setData(ROLE, hwnd)
            item.setSizeHint(QSize(THUMB_W + 16, THUMB_H + 64))
            self.windows[hwnd] = {"folder": folder, "aumid": aumid, "key": folder or f"@{aumid}",
                                  "item": item, "sig": None, "last_change": now, "watch": False,
                                  "alerted": False, "deadline": None,
                                  "text_watch": [], "text_seen": set()}   # 글자 감시: 찾을 글, 지금 보이는 것
            changed = True
        if changed:
            self.building = True
            try:
                self.refresh_other_group()
            finally:
                self.building = False
            self.reorder_thumbs()
            counts = {}
            for st in self.windows.values():
                counts[st["key"]] = counts.get(st["key"], 0) + 1
            self.building = True
            try:
                for item in self.profile_items():
                    n = counts.get(item.data(0, ROLE), 0)
                    item.setText(1, str(n) if n else "")
            finally:
                self.building = False
        return changed

    def capture_some(self, now: float):
        """창을 돌아가며 찍는다. 한 번에 CAPTURE_BUDGET 초까지만."""
        self.capture_order = [h for h in self.capture_order if h in self.windows]
        self.capture_order += [h for h in self.windows if h not in self.capture_order]
        started = time.perf_counter()
        done = 0
        while done < len(self.capture_order) and time.perf_counter() - started < CAPTURE_BUDGET:
            hwnd = self.capture_order.pop(0)
            self.capture_order.append(hwnd)
            done += 1
            st = self.windows[hwnd]
            if win32gui.IsIconic(hwnd) or st["item"].isHidden():
                continue  # 최소화된 창은 마지막 화면 유지
            try:
                image = to_qimage(capture_bits(hwnd))
            except Exception:
                image = None
            if image is None:
                continue
            st["item"].setIcon(QIcon(QPixmap.fromImage(image)))
            sig = signature(image)
            if st["sig"] is None or difference(sig, st["sig"]) > CHANGE_THRESHOLD:
                st["last_change"] = now
                st["alerted"] = False
            st["sig"] = sig

    def monitor(self):
        now = time.time()
        self.sync_windows(now)
        self.capture_some(now)
        self.refresh_work(now)
        self.check_pauses(datetime.now())
        idle_limit = self.idle_spin.value()
        for hwnd, st in self.windows.items():
            lines = [self.label(hwnd), win32gui.GetWindowText(hwnd)[:34]]
            status = []
            if st["watch"]:
                idle = int(now - st["last_change"])
                status.append(f"감시 · 변화 없음 {idle}초")
                if idle >= idle_limit and not st["alerted"]:
                    st["alerted"] = True
                    self.alert(hwnd, f"{idle_limit}초 동안 화면 변화가 없습니다.")
            if st["deadline"]:
                remaining = int(st["deadline"] - now)
                if remaining <= 0:
                    st["deadline"] = None
                    self.alert(hwnd, f"{self.timer_spin.value()}분 타이머가 끝났습니다.")
                else:
                    status.append(f"타이머 {remaining // 60}:{remaining % 60:02d}")
            work = self.cfg["work"].get(st["key"])
            if work:
                status.append(f"작업 {fmt_hm(now - work['start'])}")
            pause = self.pause_text(st["key"], datetime.now())
            if pause:
                status.append(pause)
            if st["text_watch"]:
                status.append("글자 감시" + (" ●" if st["text_seen"] else ""))
            if status:
                lines.append(" · ".join(status))
            st["item"].setText("\n".join(lines))

    def alert(self, hwnd: int, message: str):
        st = self.windows[hwnd]
        st["item"].setBackground(ALERT_BG)
        self.tray.showMessage(self.label(hwnd), message)
        QApplication.beep()

    def on_thumb_click(self, item):
        hwnd = item.data(ROLE)
        if hwnd not in self.windows:
            return
        item.setBackground(QBrush())
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            return  # Shift+클릭은 고르기만
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            self.toggle_timer([hwnd])
        else:
            activate(hwnd)

    def selected_thumbs(self) -> list[int]:
        return [it.data(ROLE) for it in self.thumbs.selectedItems()
                if it.data(ROLE) in self.windows and not it.isHidden()]

    def on_thumb_selection(self):
        n = len(self.selected_thumbs())
        self.thumb_count.setText(f"고른 창 {n}개" if n else "미리보기를 드래그해 여러 개 고를 수 있습니다")
        self.close_thumbs_button.setEnabled(bool(n))

    def toggle_timer(self, hwnds: list[int], on: bool | None = None):
        for hwnd in hwnds:
            st = self.windows[hwnd]
            start = (not st["deadline"]) if on is None else on
            st["deadline"] = time.time() + self.timer_spin.value() * 60 if start else None
        self.monitor()

    def toggle_watch(self, hwnds: list[int], on: bool | None = None):
        for hwnd in hwnds:
            st = self.windows[hwnd]
            st["watch"] = (not st["watch"]) if on is None else on
            st["last_change"] = time.time()
            st["alerted"] = False
        self.monitor()

    def thumb_menu(self, pos):
        item = self.thumbs.itemAt(pos)
        if not item or item.data(ROLE) not in self.windows:
            return
        if not item.isSelected():  # 고른 묶음 밖을 누르면 그 창 하나만
            self.thumbs.clearSelection()
            item.setSelected(True)
        hwnds = self.selected_thumbs()
        idle, minutes = self.idle_spin.value(), self.timer_spin.value()
        menu = QMenu(self)
        if len(hwnds) == 1:
            hwnd = hwnds[0]
            st = self.windows[hwnd]
            menu.addAction("창 앞으로", lambda: activate(hwnd))
            menu.addAction(f"변화 감시 {'끄기' if st['watch'] else '켜기'} ({idle}초)",
                           lambda: self.toggle_watch(hwnds))
            menu.addAction(f"타이머 {'취소' if st['deadline'] else '시작'} ({minutes}분)",
                           lambda: self.toggle_timer(hwnds))
            wkey = st["key"]
            if wkey in self.cfg["work"]:
                menu.addAction(f"작업 시간 멈춤 ({fmt_long(time.time() - self.cfg['work'][wkey]['start'])} 지남)",
                               lambda: self.stop_work(wkey))
            else:
                menu.addAction("이 프로필 작업 시간 재기 시작", lambda: self.start_work(wkey))
            if self.sid(wkey) in self.pauses:
                menu.addAction(f"다시 쓸 시각 지우기 ({self.pause_text(wkey, datetime.now())})",
                               lambda: self.clear_pause(wkey))
            else:
                menu.addAction("다시 쓸 시각 직접 적기…", lambda: self.set_pause_by_hand(wkey))
            menu.addAction("이 창에 입력", lambda: self.broadcast(targets=hwnds))
            menu.addAction("이 창 사이트 이동", lambda: self.go_to_site(targets=hwnds))
            menu.addAction("글자 감시…" + (" (켜짐)" if st["text_watch"] else ""), lambda: self.set_text_watch(hwnds))
            menu.addAction("문구 찾아 누르기…", lambda: self.click_phrase(hwnds))
            menu.addAction("프로젝트 지침 바꾸기(claude.ai)…", lambda: self.replace_instructions(targets=hwnds))
            tab_sub = menu.addMenu("탭 정리")
            for mode, name in TAB_MODES.items():
                tab_sub.addAction(f"{name} 닫기", lambda m=mode: self.close_tabs_bulk(m, targets=hwnds))
        else:
            n = len(hwnds)
            menu.addAction(f"변화 감시 켜기 ({n}개, {idle}초)", lambda: self.toggle_watch(hwnds, True))
            menu.addAction(f"변화 감시 끄기 ({n}개)", lambda: self.toggle_watch(hwnds, False))
            menu.addAction(f"타이머 시작 ({n}개, {minutes}분)", lambda: self.toggle_timer(hwnds, True))
            menu.addAction(f"타이머 취소 ({n}개)", lambda: self.toggle_timer(hwnds, False))
            menu.addAction(f"고른 창 {n}개에 일괄 입력", lambda: self.broadcast(targets=hwnds))
            menu.addAction(f"고른 창 {n}개 사이트 이동", lambda: self.go_to_site(targets=hwnds))
            menu.addAction(f"고른 창 {n}개 글자 감시…", lambda: self.set_text_watch(hwnds))
            menu.addAction(f"고른 창 {n}개에서 문구 찾아 누르기…", lambda: self.click_phrase(hwnds))
            menu.addAction(f"고른 창 {n}개 프로젝트 지침 일괄 바꾸기(claude.ai)…",
                           lambda: self.replace_instructions(targets=hwnds))
            tab_sub = menu.addMenu(f"고른 창 {n}개 탭 정리")
            for mode, name in TAB_MODES.items():
                tab_sub.addAction(f"{name} 닫기", lambda m=mode: self.close_tabs_bulk(m, targets=hwnds))
        menu.addAction("알림 표시 지우기",
                       lambda: [self.windows[h]["item"].setBackground(QBrush()) for h in hwnds if h in self.windows])
        menu.addSeparator()
        menu.addAction("이 창 닫기" if len(hwnds) == 1 else f"고른 창 {len(hwnds)}개 닫기",
                       lambda: self.close_selected_thumbs(ask=len(hwnds) > 1))
        menu.exec(self.thumbs.viewport().mapToGlobal(pos))

    # ───── 일괄 닫기 ─────
    def confirm_close(self, targets: list[int], scope: str) -> None:
        if not targets:
            QMessageBox.information(self, "닫기", "닫을 창이 없습니다.")
            return
        names = [self.label(h) for h in sorted(targets, key=self.sort_key)]
        counted = {n: names.count(n) for n in dict.fromkeys(names)}
        lines = [f"{n} ×{c}" if c > 1 else n for n, c in counted.items()]
        shown = "\n".join(lines[:12]) + (f"\n… 외 {len(lines) - 12}개" if len(lines) > 12 else "")
        answer = QMessageBox.question(
            self, "닫기", f"{scope} {len(targets)}개를 닫을까요?\n\n{shown}\n\n"
                          "(닫은 탭은 그 프로필 창에서 Ctrl+Shift+T 로 되살릴 수 있습니다)")
        if answer == QMessageBox.StandardButton.Yes:
            self.close_now(targets)

    def close_now(self, targets: list[int]) -> None:
        for hwnd in targets:
            close_window(hwnd)
        self.statusBar().showMessage(f"창 {len(targets)}개에 닫기를 보냈습니다.", 10000)

    def close_windows(self, *_):
        """왼쪽 '일괄 닫기': 트리에서 고른 프로필·그룹 기준."""
        chosen = set(self.selected_profiles())
        if chosen:
            targets = [h for h, st in self.windows.items() if st["key"] in chosen]
        else:  # 아무것도 안 고르면 프로필 창 전체(기타 창 제외)
            targets = [h for h, st in self.windows.items() if st["folder"]]
        self.confirm_close(targets, "고른 프로필의 창" if chosen else "모든 프로필 창")

    def close_selected_thumbs(self, *_, ask: bool = True):
        """오른쪽 미리보기에서 고른 창 닫기(Del 키, 버튼, 오른쪽 클릭)."""
        targets = self.selected_thumbs()
        if ask or len(targets) > 1:
            self.confirm_close(targets, "고른 창")
        elif targets:
            self.close_now(targets)

    # ───── 일괄 입력 ─────
    def broadcast(self, *_, targets: list[int] | None = None):
        if targets is None:
            chosen = set(self.selected_profiles())
            targets = [h for h in sorted(self.windows, key=self.sort_key)
                       if (not chosen or self.windows[h]["key"] in chosen)]
        targets = [h for h in targets if h in self.windows]
        if not targets:
            QMessageBox.information(self, "일괄 입력", "열려 있는 대상 창이 없습니다.")
            return
        dialog = BroadcastDialog(self, len(targets), self.last_broadcast,
                                 self.cfg.get("input_mode", "find"), self.cfg.get("input_hint", ""))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        text = dialog.edit.toPlainText()
        steps = parse_macro(text)
        if not steps:
            return
        self.last_broadcast = text   # 이 창이 켜져 있는 동안만 기억(파일에 남기지 않음)
        self.cfg["input_mode"] = "find" if dialog.find_box.isChecked() else "cursor"
        self.cfg["input_hint"] = dialog.hint.text().strip()
        self.save()
        if dialog.find_box.isChecked():  # 창마다 먼저 입력칸을 찾아 초점을 준다
            steps = [("focus_input", self.cfg["input_hint"])] + steps
        if any(s[0] == "keys" and s[2] == win32con.VK_RETURN for s in steps):
            answer = QMessageBox.question(
                self, "일괄 입력",
                f"Enter 가 들어 있어 창 {len(targets)}개에서 보내기·제출이 될 수 있습니다.\n\n"
                f"순서: {describe_macro(steps)}\n\n진행할까요?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.run_steps(targets, steps, "넣었습니다")

    def progress(self, title: str, total: int) -> QProgressDialog:
        dialog = QProgressDialog(title, "멈추기", 0, max(total, 1), self)
        dialog.setWindowTitle("진행 중")
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setValue(0)
        QApplication.processEvents()
        return dialog

    @staticmethod
    def pump(dialog: QProgressDialog, value: int | None = None) -> bool:
        """화면을 살려 두고(응답 없음 방지) '멈추기'를 눌렀는지 본다. 계속해도 되면 True."""
        if value is not None:
            dialog.setValue(value)
        QApplication.processEvents()
        return not dialog.wasCanceled()

    def run_steps(self, targets: list[int], steps: list[tuple], verb: str) -> None:
        """창을 하나씩 앞으로 가져와 steps(글·특수 키·대기·주소창 확인)를 차례로 보낸다.
        키를 누르기 바로 전마다 맨 앞 창을 확인하고, 아니면 그 창은 거기서 멈춘다."""
        targets = [h for h in targets if h in self.windows and win32gui.IsWindow(h)]  # 그새 닫힌 창 빼기
        old_clip = get_clipboard()
        failed, stopped, no_address, no_input = [], [], [], []
        done, cancelled = 0, False
        progress = self.progress(f"창 {len(targets)}개에 차례로 넣는 중… (멈추려면 '멈추기')", len(targets))
        try:
            for index, hwnd in enumerate(targets):
                if not self.pump(progress, index):
                    cancelled = True
                    break
                label = self.label(hwnd)
                if not win32gui.IsWindow(hwnd) or not activate(hwnd):  # 엉뚱한 창에 넣지 않게 건너뛴다
                    failed.append(label)
                    continue
                time.sleep(0.25)
                ok = True
                for step in steps:
                    if win32gui.GetForegroundWindow() != hwnd:  # 중간에 다른 창이 앞으로 오면 그 창은 멈춤
                        stopped.append(label)
                        ok = False
                        break
                    if step[0] == "text":
                        set_clipboard(step[1])
                        if win32gui.GetForegroundWindow() != hwnd:
                            stopped.append(label)
                            ok = False
                            break
                        press_ctrl_v()
                        time.sleep(0.2)
                    elif step[0] == "keys":
                        press_keys(step[1], step[2])
                        time.sleep(0.1)
                    elif step[0] == "focus_input":
                        try:
                            hit = find_input(hwnd, step[1])
                        except Exception:
                            hit = None
                        if not hit or not focus_input(hwnd, hit[0]):  # 칸을 못 찾으면 그 창은 아무것도 안 넣음
                            no_input.append(label)
                            ok = False
                            break
                    elif step[0] == "check_address":
                        time.sleep(0.15)
                        if not focus_in_browser_ui(hwnd):  # 주소창이 없는 창(앱 창 등): 페이지 칸에 주소가 들어가지 않게
                            no_address.append(label)
                            ok = False
                            break
                    else:  # 대기
                        end = time.time() + step[1]
                        while time.time() < end and not cancelled:
                            time.sleep(0.1)
                            cancelled = not self.pump(progress)
                        if cancelled:
                            ok = False
                            break
                if ok:
                    done += 1
                time.sleep(0.15)
                if cancelled:
                    break
        finally:
            progress.close()
            time.sleep(0.2)
            if old_clip is not None:
                set_clipboard(old_clip)
            activate(int(self.winId()))
        note = ""
        if failed:
            note += f" / 앞으로 못 가져와 건너뜀: {', '.join(failed)}"
        if stopped:
            note += f" / 도중에 다른 창이 앞에 와서 멈춤: {', '.join(stopped)}"
        if no_address:
            note += f" / 주소창이 없어 건너뜀: {', '.join(no_address)}"
        if no_input:
            note += f" / 입력칸을 못 찾아 건너뜀: {', '.join(no_input)}"
        if cancelled:
            note += " / 멈추기로 중단"
        self.statusBar().showMessage(f"{done}개 창에 {verb}.{note}", 20000)

    # ───── 페이지 글: 사용량 일시 중지 시각 · 글자 감시 · 문구 찾아 누르기 ─────
    def start_scan(self):
        if self.pause_box.isChecked():
            hwnds = list(self.windows)
        else:
            hwnds = [h for h, st in self.windows.items() if st["text_watch"]]
        self.scanner.start(hwnds)

    def save_pauses(self):
        write_json_atomic(self.pause_path, self.pauses)
        self.pause_mtime = self.pause_path.stat().st_mtime

    def reload_pauses(self, force: bool = False):
        """다른 곳(usage_pause.py --text 등)에서 고친 것을 놓치지 않게 파일이 바뀌었으면 다시 읽는다."""
        try:
            mtime = self.pause_path.stat().st_mtime
        except OSError:
            mtime = None
        if force or mtime != getattr(self, "pause_mtime", None):
            loaded = usage_pause.load(self.pause_path)
            self.pauses = {k: v for k, v in loaded.items() if isinstance(v, dict)}
            self.pause_mtime = mtime

    def pause_of(self, key: str) -> datetime | None:
        try:
            return datetime.fromisoformat(self.pauses[self.sid(key)]["resume"])
        except (KeyError, ValueError):
            return None

    def record_pause(self, key: str, line: str, announce: bool = True) -> datetime | None:
        resume = usage_pause.record(self.pause_path, self.sid(key), line)
        self.reload_pauses(force=True)
        if resume and announce:
            label = self.work_label(key)
            message = f"{resume:%H:%M} 부터 다시 쓸 수 있습니다 — 그때 알려 드릴게요."
            self.tray.showMessage(f"⏸ {label}", message)
            self.popup.show_text(f"⏸ {label}\n{message}", 8)
        return resume

    def on_texts(self, results: dict):
        """다른 스레드가 읽어 온 페이지 글 처리(이 함수는 화면 스레드에서 돈다)."""
        for hwnd, text in results.items():
            st = self.windows.get(hwnd)
            if not st or text is None:
                continue
            key = st["key"]
            if self.pause_box.isChecked():
                line = find_pause_line(text)
                norm = " ".join(line.split())[:120] if line else None
                already = self.pauses.get(self.sid(key), {}).get("text")
                if line and norm != already and norm != self.cfg["pause_done"].get(self.sid(key)):
                    self.record_pause(key, line)
            if st["text_watch"]:
                lowered = text.lower()
                now_seen = {p for p in st["text_watch"] if p.lower() in lowered}
                for phrase in now_seen - st["text_seen"]:  # 새로 나타난 것만 알림
                    self.alert(hwnd, f"'{phrase}' 글자가 보입니다.")
                st["text_seen"] = now_seen

    def check_pauses(self, now_dt: datetime):
        self.reload_pauses()
        for name, resume, ok in usage_pause.due(self.pauses, now_dt):
            if not ok:
                continue
            label = self.work_label(self.local_key(name) or name)
            message = f"{resume:%H:%M} 이 됐습니다. 이제 다시 쓸 수 있어요."
            self.tray.showMessage(f"▶ {label}", message)
            self.popup.show_text(f"▶ {label}\n{message}", 15)
            QApplication.beep()
            for st in self.windows.values():
                if self.sid(st["key"]) == name:
                    st["item"].setBackground(ALERT_BG)
            self.cfg["pause_done"][name] = self.pauses[name].get("text", "")
            del self.pauses[name]
            self.save_pauses()
            self.save()

    def pause_text(self, key: str, now_dt: datetime) -> str | None:
        resume = self.pause_of(key)
        if not resume:
            return None
        return f"⏸ {resume:%H:%M}까지 ({fmt_long((resume - now_dt).total_seconds())})"

    def set_pause_by_hand(self, key: str):
        text, ok = QInputDialog.getText(self, "다시 쓸 시각 적기",
                                        "창에 뜬 안내를 붙여 넣거나 시각만 적으세요\n(예: 오후 12:10 / 2시간 후 / 3:30 PM):")
        if not ok or not text.strip():
            return
        line = text if usage_pause.PAUSE_WORDS.search(text) else f"다시 사용 {text}"
        if not self.record_pause(key, line):
            QMessageBox.information(self, "다시 쓸 시각", "시각을 못 읽었어요. '오후 12:10', '14:20', '2시간 후' 처럼 적어 주세요.")

    def clear_pause(self, key: str):
        self.reload_pauses(force=True)
        name = self.sid(key)
        if name in self.pauses:
            self.cfg["pause_done"][name] = self.pauses[name].get("text", "")
            del self.pauses[name]
            self.save_pauses()
            self.save()

    def set_text_watch(self, hwnds: list[int]):
        current = ", ".join(self.windows[hwnds[0]]["text_watch"])
        text, ok = QInputDialog.getText(
            self, "글자 감시", f"창 {len(hwnds)}개에서 이 글이 나타나면 알립니다(여러 개는 쉼표로, 비우면 끔).\n"
                             "20초마다 지금 보이는 탭의 페이지 글을 확인합니다.", text=current)
        if not ok:
            return
        phrases = [p.strip() for p in text.split(",") if p.strip()]
        for hwnd in hwnds:
            self.windows[hwnd]["text_watch"] = phrases
            self.windows[hwnd]["text_seen"] = set()
        if phrases:
            self.start_scan()

    def click_phrase(self, hwnds: list[int]):
        phrase, ok = QInputDialog.getText(
            self, "문구 찾아 누르기",
            f"창 {len(hwnds)}개에서 이 글이 적힌 단추·링크를 찾아 누릅니다.\n(먼저 찾은 것을 보여 주고 한 번 더 묻습니다)",
            text=self.cfg.get("last_click", ""))
        phrase = phrase.strip()
        if not ok or not phrase:
            return
        self.cfg["last_click"] = phrase
        self.save()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        found, missing = [], []
        try:
            for hwnd in hwnds:
                try:
                    hit = find_clickable(hwnd, phrase)
                except Exception:
                    hit = None
                (found.append((hwnd, *hit)) if hit else missing.append(self.label(hwnd)))
        finally:
            QApplication.restoreOverrideCursor()
        if not found:
            QMessageBox.information(self, "문구 찾아 누르기", f"'{phrase}' 단추·링크를 찾지 못했습니다.")
            return
        lines = [f"{self.label(h)} — {desc}" for h, _, desc in found][:12]
        note = f"\n\n못 찾음: {', '.join(missing)}" if missing else ""
        if QMessageBox.question(self, "문구 찾아 누르기",
                                f"찾았습니다. 누를까요?\n\n" + "\n".join(lines) + note) != QMessageBox.StandardButton.Yes:
            return
        done = []
        for hwnd, control, _ in found:
            try:
                done.append(press_control(control, hwnd))
            except Exception:
                missing.append(self.label(hwnd))
        self.statusBar().showMessage(f"'{phrase}' {len(done)}곳을 눌렀습니다." +
                                     (f" / 못 누름·못 찾음: {', '.join(missing)}" if missing else ""), 15000)

    # ───── 작업 시간 ─────
    def work_key(self, item: QTreeWidgetItem) -> str | None:
        if item is None or item is self.other_group:
            return None
        return item.data(0, ROLE) or f"group:{item.text(0)}"

    def work_label(self, wkey: str) -> str:
        if wkey.startswith("group:"):
            return f"그룹 {wkey[6:]}"
        if wkey.startswith("@"):
            return f"기타 · {self.other_name(wkey[1:])}"
        if "acct:" in wkey and wkey not in self.profiles:   # 이 PC 에 없는 계정
            return wkey.replace("edge:acct:", "Edge · ").replace("acct:", "")
        return self.profiles.get(wkey, wkey)

    def group_of(self, key: str) -> str | None:
        for item in self.profile_items():
            if item.data(0, ROLE) == key and item.parent() and item.parent() is not self.other_group:
                return item.parent().text(0)
        return None

    def start_work(self, wkey: str, alert_hours: float | None = None):
        hours = self.work_spin.value() if alert_hours is None else alert_hours
        self.cfg["work"][wkey] = {"start": time.time(), "alert_min": round(hours * 60), "alerted": False}
        self.save()
        self.refresh_work(time.time())
        alert = f"\n{fmt_long(hours * 3600)} 뒤에 알립니다." if hours else ""
        self.popup.show_text(f"⏱ {self.work_label(wkey)}\n작업 시간 재기 시작 ({time.strftime('%H:%M')}){alert}")

    def stop_work(self, wkey: str):
        work = self.cfg["work"].pop(wkey, None)
        self.save()
        self.refresh_work(time.time())
        if work:
            try:   # 기록이 안 남아도 멈추는 일은 그대로(이름·그룹만 남기고 창 글자는 남기지 않음)
                group = wkey[6:] if wkey.startswith("group:") else (self.group_of(wkey) or "")
                work_log.append(work_log.store_path(), self.work_label(wkey), group, work["start"], time.time())
            except Exception:
                pass
            self.popup.show_text(f"⏹ {self.work_label(wkey)}\n{fmt_long(time.time() - work['start'])} 작업하고 멈췄습니다.")

    def set_work_alert(self, wkey: str, hours: float):
        work = self.cfg["work"].get(wkey)
        if work:
            work.update(alert_min=round(hours * 60), alerted=False)
            self.save()
            self.refresh_work(time.time())

    def ask_alert_hours(self) -> float | None:
        hours, ok = QInputDialog.getDouble(self, "작업 알림", "몇 시간 뒤에 알릴까요? (0 = 알림 없음)",
                                           self.work_spin.value() or 5, 0, 24, 1)
        return hours if ok else None

    def work_text(self, wkey: str, now: float) -> str:
        work = self.cfg["work"][wkey]
        text = f"{self.work_label(wkey)}: {fmt_long(now - work['start'])} (시작 {time.strftime('%H:%M', time.localtime(work['start']))})"
        if work.get("alert_min"):
            left = work["alert_min"] * 60 - (now - work["start"])
            text += f" · 알림 {fmt_hm(work['alert_min'] * 60)}" + (" 지남" if left <= 0 else f"까지 {fmt_long(left)}")
        return text

    def refresh_work(self, now: float):
        """트리 '작업' 칸을 고치고, 정한 시간이 지난 작업은 한 번 알린다."""
        work = self.cfg["work"]
        for wkey, w in work.items():
            if w.get("alert_min") and not w.get("alerted") and now - w["start"] >= w["alert_min"] * 60:
                w["alerted"] = True
                self.save()
                message = f"작업 시작한 지 {fmt_long(now - w['start'])} 지났습니다."
                self.tray.showMessage(f"⏱ {self.work_label(wkey)}", message)
                self.popup.show_text(f"⏱ {self.work_label(wkey)}\n{message}", 15)
                QApplication.beep()
        self.building = True
        try:
            items = [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
            for item in items + self.profile_items():
                wkey = self.work_key(item)
                w = work.get(wkey) if wkey else None
                pause = self.pause_text(wkey, datetime.now()) if wkey and not wkey.startswith("group:") else None
                item.setText(2, " ".join(t for t in (fmt_hm(now - w["start"]) if w else "",
                                                     f"⏸{self.pause_of(wkey):%H:%M}" if pause else "") if t))
                item.setToolTip(2, "\n".join(t for t in (self.work_text(wkey, now) if w else "", pause or "") if t))
                item.setForeground(2, QBrush(WORK_ALERT_COLOR) if w and w.get("alerted") else QBrush())
        finally:
            self.building = False

    def tree_menu(self, pos):
        item = self.tree.itemAt(pos)
        wkey = self.work_key(item)
        if not wkey:
            return
        menu = QMenu(self)
        now = time.time()
        if wkey in self.cfg["work"]:
            info = menu.addAction(self.work_text(wkey, now))
            info.setEnabled(False)
            menu.addAction("작업 시간 멈춤", lambda: self.stop_work(wkey))
            menu.addAction("0부터 다시 재기", lambda: self.start_work(wkey, self.cfg["work"][wkey].get("alert_min", 0) / 60))
            sub = menu.addMenu("알림 바꾸기")
        else:
            hours = self.work_spin.value()
            menu.addAction(f"작업 시간 재기 시작" + (f" ({fmt_long(hours * 3600)} 뒤 알림)" if hours else ""),
                           lambda: self.start_work(wkey))
            sub = menu.addMenu("작업 시간 재기 시작 + 알림")
        apply = (lambda h: self.set_work_alert(wkey, h)) if wkey in self.cfg["work"] else (lambda h: self.start_work(wkey, h))
        for hours in (1, 2, 3, 4, 5, 6, 8):
            sub.addAction(f"{hours}시간 뒤", lambda h=hours: apply(h))
        sub.addAction("알림 없음", lambda: apply(0))
        sub.addAction("직접 입력…", lambda: (lambda h: h is not None and apply(h))(self.ask_alert_hours()))
        if item.data(0, ROLE):
            menu.addSeparator()
            menu.addAction("열기", lambda: self.open_profiles([item.data(0, ROLE)]))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # ───── 어디서든 쓰는 단축키(RegisterHotKey) ─────
    def register_hotkeys(self):
        hwnd = int(self.winId())
        failed = []
        for name, hid in HOTKEY_IDS.items():
            text = self.cfg["hotkeys"][name]
            try:
                mods, vk = parse_hotkey(text)
                if not _user32.RegisterHotKey(hwnd, hid, mods, vk):
                    failed.append(text)
            except (ValueError, KeyError):
                failed.append(text)
        if failed:
            self.statusBar().showMessage(f"단축키를 못 잡았습니다(다른 프로그램이 쓰는 중이거나 형식 오류): {', '.join(failed)}"
                                         " — config.json 의 hotkeys 에서 바꿀 수 있습니다", 30000)

    def nativeEvent(self, event_type, message):
        kind = event_type.data() if hasattr(event_type, "data") else event_type
        if bytes(kind) == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam in HOTKEY_IDS.values():  # WM_HOTKEY
                QTimer.singleShot(0, lambda w=msg.wParam: self.on_hotkey(w))
                return True, 0
        return super().nativeEvent(event_type, message)

    def foreground_key(self) -> str | None:
        """지금 맨 앞 창이 Chrome·Edge 창이면 그 프로필 키."""
        fg = _user32.GetAncestor(win32gui.GetForegroundWindow(), 2)  # GA_ROOT
        if fg and fg not in self.windows:
            self.sync_windows(time.time())
        st = self.windows.get(fg)
        return st["key"] if st else None

    def on_hotkey(self, hid: int):
        now = time.time()
        key = self.foreground_key()
        if hid == HOTKEY_IDS["toggle"]:
            if not key:
                self.popup.show_text("Chrome·Edge 창을 앞에 두고 누르세요.\n그 창 프로필의 작업 시간을 시작하거나 멈춥니다.", 4)
            elif key in self.cfg["work"]:
                self.stop_work(key)
            else:
                self.start_work(key)
            return
        lines = []
        if key:
            group = self.group_of(key)
            mine = [k for k in (key, f"group:{group}" if group else None) if k and k in self.cfg["work"]]
            lines.append(f"지금 창: {self.work_label(key)}")
            lines += [f"  ⏱ {self.work_text(k, now)}" for k in mine] or ["  (재고 있는 작업 시간 없음)"]
        others = [k for k in sorted(self.cfg["work"], key=lambda k: self.cfg["work"][k]["start"])
                  if not (key and k in (key, f"group:{self.group_of(key)}"))]
        if others:
            lines.append("재고 있는 작업:" if not lines else "\n다른 작업:")
            lines += [f"  ⏱ {self.work_text(k, now)}" for k in others]
        if self.pauses:
            now_dt = datetime.now()
            lines.append("\n다시 쓸 시각:" if lines else "다시 쓸 시각:")
            for name, resume, ok in usage_pause.due(self.pauses, now_dt):
                left = "지금 가능" if ok else f"{fmt_long((resume - now_dt).total_seconds())} 남음"
                lines.append(f"  {'▶' if ok else '⏸'} {self.work_label(self.local_key(name) or name)}  {resume:%H:%M} ({left})")
        if not lines:
            lines = ["재고 있는 작업 시간이 없습니다.",
                     f"Chrome 창에서 {self.cfg['hotkeys']['toggle']} 또는 매니저 트리 오른쪽 클릭으로 시작합니다."]
        self.popup.show_text("\n".join(lines), 8)

    # ───── 자동화 ─────
    def automation_menu(self, *_):
        menu = QMenu(self)
        menu.addAction("프로젝트 지침 일괄 바꾸기 (claude.ai, 맨 위 이름 줄은 두고)…", self.replace_instructions)
        button = self.sender()
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()) if button else QCursor.pos())

    def replace_instructions(self, *_, targets: list[int] | None = None):
        windows, scope = self.target_windows(targets)
        if not windows:
            QMessageBox.information(self, "프로젝트 지침", "대상 창이 없습니다.")
            return
        dialog = InstructionsDialog(self, scope)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        body, keep = dialog.final_body(), dialog.keep.value()
        only_bracket, preview_only = dialog.only_bracket.isChecked(), dialog.preview_only.isChecked()

        # 1) 읽기: 창마다 편집 창을 열어 지금 지침을 읽고 취소로 닫는다(바꾸지 않음)
        plans, skipped = [], []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for hwnd in windows:
                label = self.label(hwnd)
                try:
                    url = page_url(hwnd) or ""
                    if "claude.ai/project/" not in url:
                        skipped.append(f"{label} — 프로젝트 페이지가 아님")
                        continue
                    field = open_instructions(hwnd)
                    if not field:
                        skipped.append(f"{label} — '지침 편집'을 못 엶")
                        continue
                    current = field_value(field)
                    close_instructions(hwnd, save=False)
                except Exception as e:
                    skipped.append(f"{label} — 읽기 오류 {e.__class__.__name__}")
                    continue
                first = current.split("\n", 1)[0].strip()
                if only_bracket and not first.startswith("["):
                    skipped.append(f"{label} — 첫 줄이 [ 로 시작하지 않음: {first[:30]}")
                    continue
                new = compose_instructions(current, body, keep)
                if new.strip() == current.strip():
                    skipped.append(f"{label} — 이미 같은 지침")
                    continue
                plans.append((hwnd, label, current, new, url))
        finally:
            QApplication.restoreOverrideCursor()
        if not plans:
            QMessageBox.information(self, "프로젝트 지침", "바꿀 창이 없습니다.\n\n" + "\n".join(skipped[:15]))
            return
        lines = [f"{label}\n    남김: {current.split(chr(10), 1)[0][:50]}\n    {len(current)}자 → {len(new)}자"
                 for _, label, current, new, _url in plans]
        what = "미리보기(글칸에 넣고 확인한 뒤 취소, 저장 안 함)" if preview_only else "바꾸고 '지침 저장'"
        message = (f"창 {len(plans)}개의 프로젝트 지침을 {what} 할까요?\n\n" + "\n".join(lines[:10]) +
                   (f"\n… 외 {len(lines) - 10}개" if len(lines) > 10 else "") +
                   (f"\n\n건너뜀:\n" + "\n".join(skipped[:10]) if skipped else "") +
                   "\n\n창이 하나씩 앞으로 와서 글칸에 붙여 넣습니다. 그동안 마우스·키보드를 쓰지 마세요.")
        if QMessageBox.question(self, "프로젝트 지침", message) != QMessageBox.StandardButton.Yes:
            return

        # 2) 바꾸기: 페이지·지금 지침이 1단계와 같은지 다시 확인 → 글칸 전체 선택 → 붙여넣기 → 글칸 확인
        #    → 저장(또는 원래 글로 되돌리고 취소) → 새로 고쳐 다시 읽어 확인
        old_clip = get_clipboard()
        done, failed = [], []
        progress = self.progress(f"창 {len(plans)}개의 지침을 바꾸는 중… (멈추려면 '멈추기')", len(plans))
        try:
            for index, (hwnd, label, current, new, url) in enumerate(plans):
                if not self.pump(progress, index):
                    failed.append("(멈추기로 나머지는 안 함)")
                    break
                try:
                    if not win32gui.IsWindow(hwnd):
                        failed.append(f"{label} — 창이 닫힘")
                        continue
                    if (page_url(hwnd) or "") != url:
                        failed.append(f"{label} — 그새 다른 페이지로 바뀜, 건너뜀")
                        continue
                    field = open_instructions(hwnd)
                    if not field:
                        failed.append(f"{label} — 편집 창을 못 엶")
                        continue
                    if field_value(field).strip() != current.strip():
                        close_instructions(hwnd, save=False)
                        failed.append(f"{label} — 지침이 1단계에서 읽은 것과 달라 건너뜀(다시 해 주세요)")
                        continue
                    if not activate(hwnd):
                        close_instructions(hwnd, save=False)
                        failed.append(f"{label} — 창을 앞으로 못 가져옴")
                        continue
                    time.sleep(0.2)
                    ok = fill_field(hwnd, field, new)
                    if not ok or preview_only:
                        if preview_only and ok:
                            time.sleep(0.8)  # 눈으로 볼 틈
                        # claude.ai 는 취소해도 쓴 글이 그 페이지에 남아 있다가 다음 저장 때 들어갈 수 있어, 원래 글로 되돌리고 취소
                        restored = field_value(field).strip() == current.strip() or fill_field(hwnd, field, current)
                        close_instructions(hwnd, save=False)
                        if ok:
                            done.append(label if restored else f"{label} (원래 글 되돌리기 확인 못 함 — 그 창은 새로 고침 권장)")
                        else:
                            failed.append(f"{label} — 글칸에 제대로 안 들어가서 원래대로 두고 취소함(저장 안 함)"
                                          + ("" if restored else " — 그 창은 새로 고침 권장"))
                        continue
                    if not close_instructions(hwnd, save=True):
                        failed.append(f"{label} — '지침 저장' 뒤 편집 창이 안 닫힘(확인 필요)")
                        continue
                    saved = reload_and_read_instructions(hwnd)
                    if saved is not None and saved.strip() == new.strip():
                        done.append(label)
                    else:
                        failed.append(f"{label} — 저장 뒤 새로 고쳐 읽은 글이 다름(확인 필요)")
                except Exception as e:
                    failed.append(f"{label} — 오류 {e.__class__.__name__}")
        finally:
            progress.close()
            time.sleep(0.2)
            if old_clip is not None:
                set_clipboard(old_clip)
            activate(int(self.winId()))
        verb = "미리보기했습니다(저장 안 함)" if preview_only else "바꾸고 저장해 확인했습니다"
        QMessageBox.information(self, "프로젝트 지침",
                                f"{len(done)}개 창의 지침을 {verb}." +
                                (f"\n\n안 된 곳:\n" + "\n".join(failed) if failed else ""))

    # ───── 탭 정리 ─────
    def tab_menu(self, *_):
        menu = QMenu(self)
        for mode, name in TAB_MODES.items():
            menu.addAction(f"{name} 닫기", lambda m=mode: self.close_tabs_bulk(m))
        button = self.sender()
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()) if button else self.cursor().pos())

    def target_windows(self, targets: list[int] | None) -> tuple[list[int], str]:
        """미리보기에서 고른 창 → 트리에서 고른 프로필의 창 → 열린 프로필 창 전체(기타 창 제외)."""
        if targets is not None:
            windows = [h for h in targets if h in self.windows]
            return windows, f"고른 창 {len(windows)}개"
        chosen = set(self.selected_profiles())
        ordered = sorted(self.windows, key=self.sort_key)
        if chosen:
            windows = [h for h in ordered if self.windows[h]["key"] in chosen]
            return windows, f"고른 프로필의 창 {len(windows)}개"
        windows = [h for h in ordered if self.windows[h]["folder"]]
        return windows, f"열린 프로필 창 전체 {len(windows)}개"

    def close_tabs_bulk(self, mode: str, targets: list[int] | None = None):
        windows, scope = self.target_windows(targets)
        if not windows:
            QMessageBox.information(self, "탭 정리", "대상 창이 없습니다.")
            return
        try:
            import uiautomation  # noqa: F401
        except ImportError:
            QMessageBox.warning(self, "탭 정리", "uiautomation 패키지가 없습니다.\n실행.bat 으로 다시 켜면 설치됩니다.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        plan, unreadable = [], []
        try:
            for hwnd in windows:
                try:
                    found = tabs_to_close(browser_tabs(hwnd), mode)
                except Exception:
                    unreadable.append(self.label(hwnd))
                    continue
                if found:
                    plan.append((hwnd, found))
        finally:
            QApplication.restoreOverrideCursor()
        total = sum(len(found) for _, found in plan)
        name = TAB_MODES[mode]
        if not total:
            note = f"\n(탭을 못 읽은 창: {', '.join(unreadable)})" if unreadable else ""
            QMessageBox.information(self, "탭 정리", f"{scope}에서 닫을 {name}이 없습니다.{note}")
            return
        lines = [f"{self.label(h)} — {len(found)}개" for h, found in plan]
        shown = "\n".join(lines[:12]) + (f"\n… 외 {len(lines) - 12}개 창" if len(lines) > 12 else "")
        answer = QMessageBox.question(
            self, "탭 정리",
            f"{scope}에서 지금 보는 탭 기준 {name} {total}개를 닫을까요?\n\n{shown}\n\n"
            "(닫은 탭은 그 창에서 Ctrl+Shift+T 로 되살릴 수 있습니다)")
        if answer != QMessageBox.StandardButton.Yes:
            return
        closed = failed = 0
        changed = []
        for hwnd, found in plan:
            try:
                fresh = tabs_to_close(browser_tabs(hwnd), mode)
            except Exception:
                fresh = []
            if [t["name"] for t in fresh] != [t["name"] for t in found]:   # 그새 탭을 바꿨으면 그 창은 안 닫음
                changed.append(self.label(hwnd))
                continue
            c, f = close_tabs(fresh)
            closed, failed = closed + c, failed + f
        if changed:
            unreadable += [f"{n}(그새 탭이 바뀌어 건너뜀)" for n in changed]
        note = f" / 못 닫음 {failed}개" if failed else ""
        note += f" / 탭을 못 읽은 창: {', '.join(unreadable)}" if unreadable else ""
        self.statusBar().showMessage(f"{name} {closed}개를 닫았습니다.{note}", 15000)

    # ───── 사이트 이동 ─────
    def go_to_site(self, *_, targets: list[int] | None = None):
        """targets(미리보기에서 고른 창)가 없으면 트리 기준: 고른 프로필, 안 고르면 열린 프로필 창 전체."""
        if targets is not None:
            windows = [h for h in targets if h in self.windows]
            keys = list(dict.fromkeys(self.windows[h]["key"] for h in windows))
            scope = f"고른 창 {len(windows)}개"
        else:
            chosen = self.selected_profiles()
            if chosen:
                windows = [h for h in sorted(self.windows, key=self.sort_key) if self.windows[h]["key"] in chosen]
                keys = chosen
                scope = f"고른 프로필 {len(keys)}개 (열린 창 {len(windows)}개)"
            else:
                windows = [h for h in sorted(self.windows, key=self.sort_key) if self.windows[h]["folder"]]
                keys = list(dict.fromkeys(self.windows[h]["key"] for h in windows))
                scope = f"열린 프로필 창 전체 {len(windows)}개"
        launchable = [k for k in keys if k in self.profile_info]
        if not windows and not launchable:
            QMessageBox.information(self, "사이트 이동", "대상이 없습니다.")
            return
        dialog = GotoDialog(self, scope, self.cfg.get("recent_urls", []),
                            self.cfg.get("goto_mode", "tab"), bool(windows), bool(launchable))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        url = normalize_url(dialog.url.currentText())
        if not url:
            return
        mode = "new" if dialog.new_tab.isChecked() else "tab"
        self.cfg["recent_urls"] = [url] + [u for u in self.cfg.get("recent_urls", []) if u != url][:9]
        self.cfg["goto_mode"] = mode
        self.save()
        if mode == "new":
            for key in launchable:
                self.launch_queue.append((key, url, False))
            self.launch_next()
            skipped = len(keys) - len(launchable)
            note = f" / 기타 창 {skipped}개는 새 탭으로 열 수 없어 건너뜀" if skipped else ""
            self.statusBar().showMessage(f"프로필 {len(launchable)}개에 새 탭으로 엽니다.{note}", 15000)
        else:
            steps = [("keys", [win32con.VK_CONTROL], ord("L"), "Ctrl+L"), ("check_address",), ("text", url),
                     ("keys", [], win32con.VK_RETURN, "Enter")]
            self.run_steps(windows, steps, "주소를 넣었습니다")

    def closeEvent(self, event):
        self.save()
        for hid in HOTKEY_IDS.values():
            _user32.UnregisterHotKey(int(self.winId()), hid)
        self.popup.hide()
        self.tray.hide()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)

    def log_exception(kind, value, tb):  # pythonw 는 콘솔이 없어 오류가 안 보이므로 파일과 상태 표시줄에 남긴다
        import traceback
        text = "".join(traceback.format_exception(kind, value, tb))
        try:
            with open(data_dir(SKILL) / "error.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}]\n{text}")
        except OSError:
            pass
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, Manager):
                widget.statusBar().showMessage(f"오류가 있었습니다: {value} — error.log 에 적음", 30000)

    sys.excepthook = log_exception
    window = Manager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:  # pythonw 는 콘솔이 없어 오류가 안 보이므로 창과 파일로 남긴다
        import traceback
        log = data_dir(SKILL) / "error.log"
        log.write_text(traceback.format_exc(), encoding="utf-8")
        _user32.MessageBoxW(0, f"시작하지 못했습니다.\n\n{traceback.format_exc()[-800:]}\n\n기록: {log}",
                            "Chrome·Edge 프로필 매니저", 0x10)
        raise
