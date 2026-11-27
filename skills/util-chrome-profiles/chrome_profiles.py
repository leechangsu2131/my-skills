"""Chrome 프로필 매니저 (Windows / Python 3.10+)

설치: pip install -r requirements.txt
실행: 실행.bat 더블클릭, 또는 pythonw chrome_profiles.py
점검: python chrome_profiles.py --check   (프로필·열린 창 목록만 출력하고 끝냄)

Chrome 을 평소처럼 실행하고(로그인 상태 유지) Windows API 로 창을 다룬다.
창이 어느 프로필인지는 Chrome 이 창마다 붙이는 작업표시줄 앱 ID(AppUserModelID)로 알아낸다.
  기본 프로필 → "Chrome",  Profile 4 → "Chrome.UserData.Profile4"
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

USER_DATA = Path(os.path.expandvars(os.environ.get("CHROME_USER_DATA_DIR", "")) or
                 Path(os.environ["LOCALAPPDATA"]) / "Google" / "Chrome" / "User Data")
CONFIG = data_dir(SKILL) / "config.json"
UNGROUPED = "미분류"
CHANGE_THRESHOLD = 2.0   # 32x32 흑백 축소본의 평균 밝기 차이. 클수록 둔감하다.
CAPTURE_BUDGET = 0.15    # 1초마다 캡처에 쓰는 최대 시간(초). 창이 많으면 돌아가며 찍는다.
THUMB_W, THUMB_H = 240, 150


# ───────────────────────── Chrome / Windows 유틸 ─────────────────────────
def find_chrome() -> str:
    for base in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        p = Path(os.environ.get(base, "")) / "Google" / "Chrome" / "Application" / "chrome.exe"
        if p.exists():
            return str(p)
    raise FileNotFoundError("chrome.exe 를 찾지 못했습니다.")


def load_profiles() -> dict[str, str]:
    """Local State 에서 {폴더명: 표시 이름(이메일)} 을 읽는다."""
    data = json.loads((USER_DATA / "Local State").read_text(encoding="utf-8"))
    out = {}
    for folder, info in data["profile"]["info_cache"].items():
        name = info.get("name") or folder
        email = info.get("user_name")
        out[folder] = f"{name} ({email})" if email else name
    return dict(sorted(out.items(), key=lambda kv: _natural(kv[0])))


def _natural(text: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]


def _aumid_part(text: str) -> str:
    """Chrome 이 앱 ID 를 만들 때처럼 영문·숫자·점만 남긴다."""
    return re.sub(r"[^A-Za-z0-9.]", "", text)


def aumid_table(folders) -> dict[str, str]:
    """{창의 앱 ID: 프로필 폴더명}"""
    prefix = "Chrome." + _aumid_part(USER_DATA.name) + "."
    table = {prefix + _aumid_part(f): f for f in folders}
    if "Default" in folders:
        table["Chrome"] = "Default"
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
            _exe_cache[pid] = exe.lower().endswith("\\chrome.exe")
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
    """보이는 Chrome 브라우저 창(대화상자·팝업 제외)."""
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
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    win32api.keybd_event(ord("V"), 0, 0, 0)
    win32api.keybd_event(ord("V"), 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)


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
    print(f"User Data: {USER_DATA}")
    print(f"설정 파일: {CONFIG}")
    print(f"프로필 {len(profiles)}개")
    for folder, name in profiles.items():
        print(f"  {folder:12} {name}")
    print("열린 Chrome 창")
    for hwnd in chrome_windows():
        aumid = window_aumid(hwnd)
        folder = table.get(aumid or "", "?")
        print(f"  {hwnd:>10}  {folder:12} {aumid!s:32} {win32gui.GetWindowText(hwnd)[:40]}")


if __name__ == "__main__" and "--check" in sys.argv:
    sys.stdout.reconfigure(encoding="utf-8")
    check()
    sys.exit(0)


# ───────────────────────── 화면 ─────────────────────────
from PySide6.QtCore import QSize, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QIcon, QImage, QPixmap  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractItemView, QApplication, QCheckBox, QHBoxLayout, QInputDialog, QLabel, QListView,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QSpinBox, QSplitter,
    QStyle, QSystemTrayIcon, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

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
        root = self.invisibleRootItem()
        root.setFlags(root.flags() & ~DROP)  # 프로필은 그룹 안으로만 떨어진다.

    def dropEvent(self, event):
        super().dropEvent(event)
        self.on_drop()


class Manager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chrome 프로필 매니저")
        self.resize(1200, 720)
        self.chrome = find_chrome()
        self.profiles = load_profiles()
        self.aumids = aumid_table(self.profiles)
        try:
            self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            self.cfg = {}
        self.cfg.setdefault("start_url", {})
        self.windows: dict[int, dict] = {}   # hwnd → 창 상태
        self.capture_order: list[int] = []
        self.launch_queue: list[str] = []
        self.building = False

        # 왼쪽: 그룹 트리
        self.tree = Tree(self.after_drop)
        self.tree.itemDoubleClicked.connect(self.on_double_click)
        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.itemSelectionChanged.connect(self.apply_filter)

        buttons = QHBoxLayout()
        for label, slot, tip in (
            ("열기", self.open_selected, "고른 프로필(그룹이면 그룹 전체)을 연다. 이미 열려 있으면 앞으로 가져온다. Shift 를 누르고 누르면 늘 새 창."),
            ("그룹 추가", self.add_group, "새 그룹. 이름은 그룹을 고르고 F2 로 바꾼다."),
            ("그룹 삭제", self.remove_group, "고른 그룹을 지우고 안의 프로필은 미분류로 옮긴다."),
            ("시작 URL", self.set_start_url, "고른 프로필들의 시작 URL 을 한 번에 바꾼다(비우면 해제)."),
            ("일괄 입력", self.broadcast, "열린 창(고른 프로필이 있으면 그 창들)의 커서 위치에 같은 글을 붙여 넣는다."),
            ("일괄 닫기", self.close_windows, "고른 프로필(그룹이면 그룹 전체)의 창을 모두 닫는다. 아무것도 안 고르면 프로필 창 전체. '기타 Chrome 창'은 닫지 않는다."),
        ):
            button = QPushButton(label)
            button.setToolTip(tip)
            button.clicked.connect(slot)
            buttons.addWidget(button)

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

        help_text = QLabel("미리보기: 클릭=창 앞으로 · Ctrl+클릭=타이머 시작/취소 · 오른쪽 클릭=변화 감시 등")
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
        self.thumbs.itemClicked.connect(self.on_thumb_click)
        self.thumbs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.thumbs.customContextMenuRequested.connect(self.thumb_menu)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(self.thumbs)
        splitter.setSizes([500, 700])
        self.setCentralWidget(splitter)

        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Chrome 프로필 매니저")
        self.tray.activated.connect(lambda *_: (self.showNormal(), self.raise_(), self.activateWindow()))
        self.tray.show()

        self.build_tree()
        self.monitor()
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.monitor)
        self.monitor_timer.start(1000)

    # ───── 그룹 / 프로필 트리 ─────
    def group_item(self, name: str) -> QTreeWidgetItem:
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if not item.data(0, ROLE) and item.text(0) == name:
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

    def on_item_changed(self, item, column):
        if not self.building and column == 0 and not item.data(0, ROLE):
            self.save()

    def selected_profiles(self) -> list[str]:
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
        groups = [it for it in self.tree.selectedItems() if not it.data(0, ROLE) and it.text(0) != UNGROUPED]
        for group in groups:
            children = group.takeChildren()
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(group))
            self.group_item(UNGROUPED).addChildren(children)
        if groups:
            self.save()

    def set_start_url(self, *_):
        folders = self.selected_profiles()
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
            existing = [h for h, st in self.windows.items() if st["folder"] == folder]
            if existing and not force_new:
                activate(existing[-1])
            else:
                self.launch_queue.append(folder)
        self.launch_next()

    def launch_next(self):
        """여러 개를 한꺼번에 띄우면 Chrome 이 버벅이므로 0.4초 간격으로 하나씩."""
        if not self.launch_queue:
            return
        folder = self.launch_queue.pop(0)
        args = [self.chrome, f"--profile-directory={folder}", "--new-window"]
        if self.cfg["start_url"].get(folder):
            args.append(self.cfg["start_url"][folder])
        subprocess.Popen(args)
        if self.launch_queue:
            QTimer.singleShot(400, self.launch_next)

    # ───── 미리보기 / 감시 / 알림 ─────
    def label_of(self, folder: str | None, aumid: str | None) -> str:
        if folder:
            return self.profiles[folder]
        return f"기타 Chrome 창 ({aumid})" if aumid else "기타 Chrome 창"

    def sort_key(self, hwnd: int):
        order = {item.data(0, ROLE): i for i, item in enumerate(self.profile_items())}
        return (order.get(self.windows[hwnd]["folder"], 10_000), hwnd)

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
            st["item"].setHidden(bool(chosen) and st["folder"] not in chosen)

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
            item = QListWidgetItem(self.label_of(folder, aumid))
            item.setData(ROLE, hwnd)
            item.setSizeHint(QSize(THUMB_W + 16, THUMB_H + 64))
            self.windows[hwnd] = {"folder": folder, "aumid": aumid, "item": item, "sig": None,
                                  "last_change": now, "watch": False, "alerted": False,
                                  "deadline": None}
            changed = True
        if changed:
            self.reorder_thumbs()
            counts = {}
            for st in self.windows.values():
                counts[st["folder"]] = counts.get(st["folder"], 0) + 1
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
            lines = [self.label_of(st["folder"], st["aumid"]), win32gui.GetWindowText(hwnd)[:34]]
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
        self.tray.showMessage(self.label_of(st["folder"], st["aumid"]), message)
        QApplication.beep()

    def on_thumb_click(self, item):
        hwnd = item.data(ROLE)
        if hwnd not in self.windows:
            return
        item.setBackground(QBrush())
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
            self.toggle_timer(hwnd)
        else:
            activate(hwnd)

    def toggle_timer(self, hwnd: int):
        st = self.windows[hwnd]
        st["deadline"] = None if st["deadline"] else time.time() + self.timer_spin.value() * 60
        self.monitor()

    def toggle_watch(self, hwnd: int):
        st = self.windows[hwnd]
        st["watch"] = not st["watch"]
        st["last_change"] = time.time()
        st["alerted"] = False
        self.monitor()

    def thumb_menu(self, pos):
        item = self.thumbs.itemAt(pos)
        if not item or item.data(ROLE) not in self.windows:
            return
        hwnd = item.data(ROLE)
        st = self.windows[hwnd]
        menu = QMenu(self)
        menu.addAction("창 앞으로", lambda: activate(hwnd))
        menu.addAction(f"변화 감시 {'끄기' if st['watch'] else '켜기'} ({self.idle_spin.value()}초)",
                       lambda: self.toggle_watch(hwnd))
        menu.addAction(f"타이머 {'취소' if st['deadline'] else '시작'} ({self.timer_spin.value()}분)",
                       lambda: self.toggle_timer(hwnd))
        menu.addAction("알림 표시 지우기", lambda: item.setBackground(QBrush()))
        menu.addSeparator()
        menu.addAction("이 창 닫기", lambda: close_window(hwnd))
        menu.exec(self.thumbs.viewport().mapToGlobal(pos))

    # ───── 일괄 닫기 ─────
    def close_windows(self, *_):
        chosen = set(self.selected_profiles())
        targets = [h for h, st in self.windows.items()
                   if st["folder"] and (not chosen or st["folder"] in chosen)]
        if not targets:
            QMessageBox.information(self, "일괄 닫기", "닫을 창이 없습니다.")
            return
        names = sorted({self.profiles[self.windows[h]["folder"]] for h in targets})
        shown = "\n".join(names[:12]) + (f"\n… 외 {len(names) - 12}개 프로필" if len(names) > 12 else "")
        scope = "고른 프로필" if chosen else "모든 프로필"
        answer = QMessageBox.question(
            self, "일괄 닫기",
            f"{scope}의 창 {len(targets)}개를 닫을까요?\n\n{shown}\n\n"
            "(닫은 탭은 그 프로필 창에서 Ctrl+Shift+T 로 되살릴 수 있습니다)")
        if answer == QMessageBox.StandardButton.Yes:
            for hwnd in targets:
                close_window(hwnd)
            self.statusBar().showMessage(f"창 {len(targets)}개에 닫기를 보냈습니다.", 10000)

    # ───── 일괄 입력 ─────
    def broadcast(self, *_):
        chosen = set(self.selected_profiles())
        targets = [h for h in sorted(self.windows, key=self.sort_key)
                   if (not chosen or self.windows[h]["folder"] in chosen)]
        if not targets:
            QMessageBox.information(self, "일괄 입력", "열려 있는 대상 창이 없습니다.")
            return
        text, ok = QInputDialog.getMultiLineText(
            self, "일괄 입력",
            f"창 {len(targets)}개의 현재 커서 위치에 붙여 넣을 내용\n(창이 하나씩 앞으로 오며 붙여 넣습니다. 그동안 마우스·키보드를 쓰지 마세요):")
        if not ok or not text:
            return
        old_clip = get_clipboard()
        set_clipboard(text)
        failed = []
        for hwnd in targets:
            if activate(hwnd):
                time.sleep(0.25)
                press_ctrl_v()
                time.sleep(0.2)
            else:  # 엉뚱한 창에 붙지 않게 건너뛴다
                st = self.windows[hwnd]
                failed.append(self.label_of(st["folder"], st["aumid"]))
        time.sleep(0.2)
        if old_clip is not None:
            set_clipboard(old_clip)
        activate(int(self.winId()))
        note = f" / 앞으로 못 가져와 건너뜀: {', '.join(failed)}" if failed else ""
        self.statusBar().showMessage(f"{len(targets) - len(failed)}개 창에 넣었습니다.{note}", 15000)

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
                            "Chrome 프로필 매니저", 0x10)
        raise
