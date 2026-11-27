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
import json
import os
import pathlib
import re
import subprocess
import sys
import time
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
    {키: {"name": 표시 이름, "folder": 폴더명, "exe": 실행 파일, "browser": 브라우저 정보}}"""
    out = {}
    for browser in BROWSERS:
        exe, state = find_exe(browser), browser["user_data"] / "Local State"
        if not exe or not state.is_file():
            continue
        cache = json.loads(state.read_text(encoding="utf-8"))["profile"]["info_cache"]
        for folder in sorted(cache, key=_natural):
            info = cache[folder]
            name = info.get("name") or folder
            email = info.get("user_name")
            name = f"{name} ({email})" if email else name
            if browser["prefix"]:
                name = f"{browser['label']} · {name}"
            out[browser["prefix"] + folder] = {"name": name, "folder": folder, "exe": exe, "browser": browser}
    if not out:
        raise FileNotFoundError("Chrome·Edge 를 찾지 못했습니다.")
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
        print(f"  {key:16} {info['name']}")
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
from PySide6.QtCore import QSize, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QIcon, QImage, QKeySequence, QPixmap, QShortcut  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QGridLayout,
    QHBoxLayout, QInputDialog, QLabel, QListView, QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QSpinBox, QSplitter, QStyle,
    QSystemTrayIcon, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)


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
        note = QLabel("기타 브라우저 창은 '지금 탭' 방식만 됩니다. 지금 탭 방식은 그동안 마우스·키보드를 쓰지 마세요.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray")
        box.addWidget(note)
        box.addWidget(buttons)


class BroadcastDialog(QDialog):
    """일괄 입력 창: 글 + 특수 키 단추. 단추를 누르면 커서 자리에 {Enter} 같은 표시가 들어간다."""
    KEY_BUTTONS = ["Enter", "Shift+Enter", "Ctrl+Enter", "Tab", "Esc", "Backspace",
                   "Ctrl+A", "Ctrl+V", "Up", "Down", "F5", "대기 1"]

    def __init__(self, parent, count: int, last_text: str):
        super().__init__(parent)
        self.setWindowTitle("일괄 입력")
        self.resize(560, 420)
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
        self.setHeaderLabels(["그룹 / 프로필", "창", "시작 URL"])
        self.setColumnWidth(0, 260)
        self.setColumnWidth(1, 34)
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
        try:
            self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            self.cfg = {}
        self.cfg.setdefault("start_url", {})
        self.cfg.setdefault("aliases", {})   # 기타 Chrome 창 앱 ID → 사용자가 붙인 이름
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
             ("시작 URL", self.set_start_url, "고른 프로필들의 시작 URL 을 한 번에 바꾼다(비우면 해제).")),
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

        settings = QHBoxLayout()
        settings.addWidget(QLabel("변화 감시(초)"))
        settings.addWidget(self.idle_spin)
        settings.addWidget(QLabel("타이머(분)"))
        settings.addWidget(self.timer_spin)
        settings.addStretch()

        help_text = QLabel("미리보기: 클릭=창 앞으로 · 드래그/Shift+클릭=여러 개 고르기 · Del=고른 창 닫기\n"
                           "Ctrl+클릭=타이머 시작/취소 · 오른쪽 클릭=변화 감시·닫기 등 · 기타 창 이름은 F2")
        help_text.setStyleSheet("color: gray")

        left = QWidget()
        box = QVBoxLayout(left)
        box.addLayout(buttons)
        box.addWidget(self.tree)
        box.addLayout(settings)
        box.addWidget(self.filter_box)
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
        flags = (item.flags() | DROP) & ~DRAG
        item.setFlags(flags & ~EDIT if name == UNGROUPED else flags | EDIT)
        self.tree.addTopLevelItem(item)
        item.setExpanded(True)
        return item

    def profile_item(self, folder: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([self.profiles[folder], "", self.cfg["start_url"].get(folder, "")])
        item.setData(0, ROLE, folder)
        item.setToolTip(0, folder)
        item.setFlags((item.flags() | DRAG) & ~DROP & ~EDIT)
        return item

    def build_tree(self):
        self.building = True
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
                item = QTreeWidgetItem([self.other_name(key[1:]), "", ""])
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
        elif not key:
            self.save()

    def selected_profiles(self) -> list[str]:
        """트리에서 고른 키 목록(그룹이면 그 안 전체). 기타 창은 '@앱ID'."""
        result = []
        for item in self.tree.selectedItems():
            children = [item] if item.data(0, ROLE) else [item.child(i) for i in range(item.childCount())]
            result += [c.data(0, ROLE) for c in children if c.data(0, ROLE) not in result]
        return result

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
                        timer_min=self.timer_spin.value(), filter=self.filter_box.isChecked())
        CONFIG.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=2), encoding="utf-8")

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
                item.setText(2, url)
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
        st = self.windows[hwnd]
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
                                  "alerted": False, "deadline": None}
            changed = True
        if changed:
            self.building = True
            self.refresh_other_group()
            self.building = False
            self.reorder_thumbs()
            counts = {}
            for st in self.windows.values():
                counts[st["key"]] = counts.get(st["key"], 0) + 1
            self.building = True
            for item in self.profile_items():
                n = counts.get(item.data(0, ROLE), 0)
                item.setText(1, str(n) if n else "")
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
            menu.addAction("이 창에 입력", lambda: self.broadcast(targets=hwnds))
            menu.addAction("이 창 사이트 이동", lambda: self.go_to_site(targets=hwnds))
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
        dialog = BroadcastDialog(self, len(targets), self.cfg.get("last_broadcast", ""))
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        text = dialog.edit.toPlainText()
        steps = parse_macro(text)
        if not steps:
            return
        self.cfg["last_broadcast"] = text
        self.save()
        if any(s[0] == "keys" and s[2] == win32con.VK_RETURN for s in steps):
            answer = QMessageBox.question(
                self, "일괄 입력",
                f"Enter 가 들어 있어 창 {len(targets)}개에서 보내기·제출이 될 수 있습니다.\n\n"
                f"순서: {describe_macro(steps)}\n\n진행할까요?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.run_steps(targets, steps, "넣었습니다")

    def run_steps(self, targets: list[int], steps: list[tuple], verb: str) -> None:
        """창을 하나씩 앞으로 가져와 steps(글·특수 키·대기)를 차례로 보낸다."""
        old_clip = get_clipboard()
        failed, stopped = [], []
        for hwnd in targets:
            if not activate(hwnd):  # 엉뚱한 창에 넣지 않게 건너뛴다
                failed.append(self.label(hwnd))
                continue
            time.sleep(0.25)
            for step in steps:
                if win32gui.GetForegroundWindow() != hwnd:  # 중간에 다른 창이 앞으로 오면 그 창은 멈춤
                    stopped.append(self.label(hwnd))
                    break
                if step[0] == "text":
                    set_clipboard(step[1])
                    press_ctrl_v()
                    time.sleep(0.2)
                elif step[0] == "keys":
                    press_keys(step[1], step[2])
                    time.sleep(0.1)
                else:
                    time.sleep(step[1])
            time.sleep(0.15)
        time.sleep(0.2)
        if old_clip is not None:
            set_clipboard(old_clip)
        activate(int(self.winId()))
        note = ""
        if failed:
            note += f" / 앞으로 못 가져와 건너뜀: {', '.join(failed)}"
        if stopped:
            note += f" / 도중에 다른 창이 앞에 와서 멈춤: {', '.join(stopped)}"
        done = len(targets) - len(failed) - len(stopped)
        self.statusBar().showMessage(f"{done}개 창에 {verb}.{note}", 20000)

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
        for _, found in plan:
            c, f = close_tabs(found)
            closed, failed = closed + c, failed + f
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
            steps = [("keys", [win32con.VK_CONTROL], ord("L"), "Ctrl+L"), ("text", url),
                     ("keys", [], win32con.VK_RETURN, "Enter")]
            self.run_steps(windows, steps, "주소를 넣었습니다")

    def closeEvent(self, event):
        self.save()
        self.tray.hide()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
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
