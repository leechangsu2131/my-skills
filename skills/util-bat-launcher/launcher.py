"""스킬 실행기 — my-skills 의 모든 .bat/.cmd 를 한 창에 모아 더블클릭으로 실행한다.

실행: 실행.bat 더블클릭 (처음 한 번 '바탕화면 바로가기' 를 눌러 두면 다음부터는 바탕화면에서)
목록: python launcher.py --list   (화면 없이 찾은 파일만 출력)

분야 → 스킬 → 실행 파일 순서로 보이고, 즐겨찾기·최근 실행은 맨 위에 따로 모인다.
실행은 탐색기에서 더블클릭한 것과 같다(그 bat 이 있는 폴더에서 실행).
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents
                            if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # noqa: E402

SKILL = "util-bat-launcher"
SKILLS = Path(__file__).resolve().parents[1]          # my-skills/skills
CONFIG = data_dir(SKILL) / "config.json"
SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "scratch", "dist", "build", ".next"}
CATEGORY_ORDER = ["학교 행정", "학생 기록·평가", "수업·교사 도구", "홈페이지", "개인·생활", "공통 유틸"]
RECENT_MAX = 8


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


def skill_meta(skill_dir: Path) -> dict:
    """SKILL.md 앞머리에서 category·summary·status 만 간단히 읽는다."""
    meta = {"category": "기타", "summary": "", "status": ""}
    md = skill_dir / "SKILL.md"
    if md.is_file():
        head = read_text(md).split("\n---", 2)[0]
        for key in meta:
            m = re.search(rf"^\s*{key}:\s*(.+)$", head, re.M)
            if m:
                meta[key] = m.group(1).split("  #")[0].strip()
    return meta


def _useful(text: str) -> bool:
    """구분선(====, ───)·오류 안내·진행 표시가 아닌, 글자가 있는 설명인지."""
    text = text.strip().strip('"')
    letters = re.findall(r"[A-Za-z가-힣]", text)
    if len(letters) < 3 or text.startswith(("[", "(", "%")):
        return False
    return not re.search(r"(?i)error|fail|오류|실패|install|please|press any key|not found|찾지 못", text)


def bat_note(path: Path) -> str:
    """bat 안 첫 설명 줄을 짧게. title → rem/:: → echo 순서로 본다."""
    try:
        lines = [ln.strip().lstrip("@") for ln in read_text(path).splitlines()[:25]]
    except OSError:
        return ""
    patterns = (r"(?i)^title\s+(.+)", r"(?i)^(?:rem|::)\s*(.+)", r"(?i)^echo\s+(?!(?:off|on)\s*$)(.+)")
    for pattern in patterns:
        for line in lines:
            m = re.match(pattern, line)
            if m and _useful(m.group(1)):
                return m.group(1).replace("^", "").strip().strip('"').strip("─-= ")[:80]
    return ""


def scan() -> list[dict]:
    """[{"rel": 'skills 기준 경로', "skill": 스킬, "name": 스킬 안 경로, "note": 설명, "meta": {...}}]"""
    found = []
    for skill_dir in sorted(SKILLS.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith(("_", ".")):
            continue
        meta = None
        for root, dirs, files in os.walk(skill_dir):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
            for name in sorted(files):
                if not name.lower().endswith((".bat", ".cmd")):
                    continue
                path = Path(root) / name
                meta = meta or skill_meta(skill_dir)
                found.append({"rel": path.relative_to(SKILLS).as_posix(), "skill": skill_dir.name,
                              "name": path.relative_to(skill_dir).as_posix(), "note": bat_note(path),
                              "meta": meta})
    return found


if __name__ == "__main__" and "--list" in sys.argv:
    sys.stdout.reconfigure(encoding="utf-8")
    for entry in scan():
        print(f"{entry['rel']:70} {entry['note']}")
    sys.exit(0)


# ───────────────────────── 화면 ─────────────────────────
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QBrush, QColor, QFont, QGuiApplication  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QHBoxLayout, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QStyle,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

ROLE = Qt.ItemDataRole.UserRole


class Launcher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("스킬 실행기")
        self.resize(900, 760)
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        try:
            self.cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            self.cfg = {}
        self.cfg.setdefault("favorites", [])
        self.cfg.setdefault("recent", [])
        self.cfg.setdefault("ran", [])   # 한 번이라도 실행한 파일(처음 실행 확인을 다시 묻지 않음)

        self.search = QLineEdit()
        self.search.setPlaceholderText("찾기: 스킬·파일 이름·설명 (예: 나이스, 인쇄, 실행)")
        self.search.textChanged.connect(self.rebuild)
        refresh = QPushButton("새로 고침")
        refresh.clicked.connect(self.reload)
        shortcut = QPushButton("바탕화면 바로가기")
        shortcut.setToolTip("바탕화면에 '스킬 실행기' 바로가기를 만든다.")
        shortcut.clicked.connect(self.make_shortcut)
        top = QHBoxLayout()
        top.addWidget(self.search, 1)
        top.addWidget(refresh)
        top.addWidget(shortcut)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["실행 파일", "설명"])
        self.tree.setColumnWidth(0, 380)
        self.tree.itemActivated.connect(self.on_activate)   # 더블클릭·Enter
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.menu)

        box = QVBoxLayout()
        box.addLayout(top)
        box.addWidget(self.tree)
        central = QWidget()
        central.setLayout(box)
        self.setCentralWidget(central)
        self.statusBar().showMessage("더블클릭(또는 Enter)으로 실행 · 오른쪽 클릭: 즐겨찾기·폴더 열기·내용 보기")
        self.reload()
        self.search.setFocus()

    # ───── 목록 ─────
    def reload(self, *_):
        self.entries = {e["rel"]: e for e in scan()}
        self.rebuild()

    def matches(self, entry: dict, words: list[str]) -> bool:
        hay = " ".join([entry["rel"], entry["note"], entry["meta"]["summary"], entry["meta"]["category"]]).lower()
        return all(w in hay for w in words)

    def bat_item(self, entry: dict, label: str | None = None) -> QTreeWidgetItem:
        item = QTreeWidgetItem([label or entry["name"], entry["note"]])
        item.setData(0, ROLE, entry["rel"])
        item.setToolTip(0, str(SKILLS / entry["rel"]))
        if entry["rel"] in self.cfg["favorites"]:
            item.setText(0, "★ " + item.text(0))
        return item

    def header(self, text: str, note: str = "") -> QTreeWidgetItem:
        item = QTreeWidgetItem([text, note])
        font = QFont()
        font.setBold(True)
        item.setFont(0, font)
        return item

    def rebuild(self, *_):
        words = self.search.text().lower().split()
        shown = [e for e in self.entries.values() if self.matches(e, words)]
        self.tree.clear()

        def pinned(title: str, rels: list[str]):
            items = [self.bat_item(self.entries[r], f"{self.entries[r]['skill']} / {self.entries[r]['name']}")
                     for r in rels if r in self.entries and self.entries[r] in shown]
            if items:
                group = self.header(title)
                group.addChildren(items)
                self.tree.addTopLevelItem(group)

        pinned("★ 즐겨찾기", self.cfg["favorites"])
        pinned("🕘 최근 실행", [r for r in self.cfg["recent"] if r not in self.cfg["favorites"]])

        by_category: dict[str, dict[str, list[dict]]] = {}
        for entry in shown:
            by_category.setdefault(entry["meta"]["category"], {}).setdefault(entry["skill"], []).append(entry)
        order = CATEGORY_ORDER + sorted(c for c in by_category if c not in CATEGORY_ORDER)
        for category in order:
            if category not in by_category:
                continue
            skills = by_category[category]
            cat_item = self.header(f"{category}  ({sum(len(v) for v in skills.values())})")
            for skill, entries in sorted(skills.items()):
                meta = entries[0]["meta"]
                skill_item = QTreeWidgetItem([skill, meta["summary"]])
                skill_item.setToolTip(1, meta["summary"])
                if meta["status"] in ("보관",):
                    skill_item.setForeground(0, QBrush(QColor("gray")))
                skill_item.addChildren([self.bat_item(e) for e in entries])
                cat_item.addChild(skill_item)
            self.tree.addTopLevelItem(cat_item)
        self.tree.expandAll()
        self.setWindowTitle(f"스킬 실행기 — 실행 파일 {len(shown)}개")

    # ───── 실행·메뉴 ─────
    def on_activate(self, item, _column=0):
        rel = item.data(0, ROLE)
        if rel:
            self.run(rel)

    def run(self, rel: str):
        path = SKILLS / rel
        if not path.is_file():
            QMessageBox.warning(self, "스킬 실행기", f"파일이 없습니다:\n{path}")
            self.reload()
            return
        if rel not in self.cfg["ran"]:  # 처음 실행하는 파일은 한 번 묻는다(크롬 강제 종료·프린터 초기화 같은 것도 섞여 있음)
            box = QMessageBox(QMessageBox.Icon.Question, "스킬 실행기",
                              f"처음 실행하는 파일입니다.\n\n{rel}\n{self.entries.get(rel, {}).get('note', '')}\n\n실행할까요?",
                              parent=self)
            run = box.addButton("실행", QMessageBox.ButtonRole.AcceptRole)
            look = box.addButton("내용 먼저 보기", QMessageBox.ButtonRole.ActionRole)
            box.addButton("취소", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is look:
                self.show_file(path)
                return
            if box.clickedButton() is not run:
                return
            self.cfg["ran"].append(rel)
        try:
            os.startfile(str(path), cwd=str(path.parent))  # 탐색기 더블클릭과 같게, 그 폴더에서
        except OSError as e:
            QMessageBox.warning(self, "스킬 실행기", f"실행하지 못했습니다:\n{path}\n\n{e}")
            return
        self.cfg["recent"] = [rel] + [r for r in self.cfg["recent"] if r != rel][:RECENT_MAX - 1]
        self.save()
        self.statusBar().showMessage(f"실행: {rel}", 8000)
        scroll = self.tree.verticalScrollBar().value()   # 목록을 새로 그려도 보던 자리 유지
        self.rebuild()
        self.tree.verticalScrollBar().setValue(scroll)

    def show_file(self, path: Path):
        try:
            os.startfile("notepad.exe", arguments=f'"{path}"')
        except OSError as e:
            QMessageBox.warning(self, "스킬 실행기", f"메모장을 열지 못했습니다:\n{e}")

    def toggle_favorite(self, rel: str):
        favs = self.cfg["favorites"]
        favs.remove(rel) if rel in favs else favs.append(rel)
        self.save()
        self.rebuild()

    def menu(self, pos):
        item = self.tree.itemAt(pos)
        rel = item.data(0, ROLE) if item else None
        if not rel:
            return
        path = SKILLS / rel
        menu = QMenu(self)
        menu.addAction("실행", lambda: self.run(rel))
        menu.addAction("즐겨찾기 빼기" if rel in self.cfg["favorites"] else "즐겨찾기 추가",
                       lambda: self.toggle_favorite(rel))
        menu.addSeparator()
        menu.addAction("폴더 열기", lambda: os.startfile(str(path.parent)))
        menu.addAction("내용 보기(메모장)", lambda: self.show_file(path))
        menu.addAction("경로 복사", lambda: QGuiApplication.clipboard().setText(str(path)))
        if rel in self.cfg["recent"]:
            menu.addAction("최근 실행에서 지우기", lambda: (self.cfg["recent"].remove(rel), self.save(), self.rebuild()))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def save(self):
        CONFIG.write_text(json.dumps(self.cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    def make_shortcut(self, *_):
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = Path(shell.SpecialFolders("Desktop"))
        link = shell.CreateShortCut(str(desktop / "스킬 실행기.lnk"))
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        link.TargetPath = str(pythonw if pythonw.exists() else sys.executable)
        link.Arguments = f'"{Path(__file__).resolve()}"'
        link.WorkingDirectory = str(Path(__file__).resolve().parent)
        link.Description = "my-skills 의 bat 파일을 모아 실행"
        link.save()
        self.statusBar().showMessage(f"바탕화면에 만들었습니다: {desktop / '스킬 실행기.lnk'}", 10000)


def main():
    app = QApplication(sys.argv)
    window = Launcher()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:  # pythonw 는 콘솔이 없어 오류가 안 보이므로 창과 파일로 남긴다
        import ctypes
        import traceback
        log = data_dir(SKILL) / "error.log"
        log.write_text(traceback.format_exc(), encoding="utf-8")
        ctypes.windll.user32.MessageBoxW(0, f"시작하지 못했습니다.\n\n{traceback.format_exc()[-800:]}\n\n기록: {log}",
                                         "스킬 실행기", 0x10)
        raise
