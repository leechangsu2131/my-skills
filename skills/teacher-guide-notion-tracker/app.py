#!/usr/bin/env python3
"""교사용 지도서 진도표 → Notion 업로더 GUI."""
from __future__ import annotations

import json
import threading
import traceback
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from scripts.notion_uploader import (
    create_tracker_database,
    extract_page_id,
    parse_groups_json,
)

CONFIG_PATH = Path.home() / ".notion_tracker_config.json"
DEFAULT_PAGE_URL = "https://www.notion.so/32addde1e1df816da429fac735e3898e"


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_config(data: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class TrackerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("지도서 진도표 → 노션 업로더")
        self.root.geometry("920x700")
        self.root.minsize(820, 580)

        config = _load_config()

        self.json_path = tk.StringVar()
        self.notion_token = tk.StringVar(value=config.get("notion_token", ""))
        self.page_url = tk.StringVar(
            value=config.get("page_url", DEFAULT_PAGE_URL)
        )
        self.db_title = tk.StringVar()
        self.status_text = tk.StringVar(value="groups.json 파일을 선택해 주세요.")
        self.is_running = False

        self._build_ui()

    # ── UI 구성 ────────────────────────────────────────────
    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

        row = 0
        # groups.json 선택
        ttk.Label(frame, text="groups.json").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(frame, textvariable=self.json_path).grid(
            row=row, column=1, sticky="ew", padx=(8, 8), pady=(0, 8)
        )
        ttk.Button(frame, text="찾아보기", command=self._choose_json).grid(
            row=row, column=2, sticky="ew", pady=(0, 8)
        )

        row += 1
        # Notion API 키
        ttk.Label(frame, text="Notion API 키").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(frame, textvariable=self.notion_token, show="•").grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(0, 8)
        )

        row += 1
        # 페이지 URL
        ttk.Label(frame, text="노션 페이지 URL").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        ttk.Entry(frame, textvariable=self.page_url).grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(0, 8)
        )

        row += 1
        # DB 제목
        ttk.Label(frame, text="DB 제목 (선택)").grid(
            row=row, column=0, sticky="w", pady=(0, 8)
        )
        title_entry = ttk.Entry(frame, textvariable=self.db_title)
        title_entry.grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=(8, 0), pady=(0, 8)
        )

        row += 1
        # 버튼
        actions = ttk.Frame(frame)
        actions.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self.preview_btn = ttk.Button(
            actions, text="미리보기", command=self._preview
        )
        self.preview_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.upload_btn = ttk.Button(
            actions, text="노션에 업로드", command=self._upload
        )
        self.upload_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        row += 1
        # 결과 표시
        ttk.Label(frame, text="결과").grid(
            row=row, column=0, columnspan=3, sticky="w"
        )
        row += 1
        self.result_box = tk.Text(frame, wrap="word", height=18)
        self.result_box.grid(row=row, column=0, columnspan=3, sticky="nsew")
        self.result_box.configure(state="disabled")

        # 진행 바
        row += 1
        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=(8, 0)
        )

        # 상태 바
        row += 1
        status_bar = ttk.Label(
            frame, textvariable=self.status_text, relief="sunken", anchor="w"
        )
        status_bar.grid(
            row=row, column=0, columnspan=3, sticky="ew", pady=(8, 0)
        )

    # ── 파일 선택 ──────────────────────────────────────────
    def _choose_json(self) -> None:
        chosen = filedialog.askopenfilename(
            title="groups.json 선택",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if chosen:
            self.json_path.set(chosen)

    # ── 미리보기 ───────────────────────────────────────────
    def _preview(self) -> None:
        json_path = self.json_path.get().strip()
        if not json_path:
            messagebox.showwarning("확인", "먼저 groups.json 파일을 선택해 주세요.")
            return
        if not Path(json_path).exists():
            messagebox.showerror("오류", "선택한 파일을 찾을 수 없습니다.")
            return

        try:
            data = parse_groups_json(json_path)
        except Exception as exc:
            messagebox.showerror("파싱 오류", str(exc))
            return

        lines = [
            f"출처 PDF: {data['pdf']}",
            f"분할 수준: {data['split_level']}",
            f"총 항목 수: {len(data['entries'])}",
            "",
            "─" * 60,
        ]
        for e in data["entries"]:
            unit_tag = f"  [{e['unit']}]" if e["unit"] else ""
            lines.append(
                f"  {e['index']:02d}. {e['title']}"
                f"  {e['page_range']}{unit_tag}"
            )

        # DB 제목 자동 채우기
        if not self.db_title.get().strip():
            pdf_stem = Path(data["pdf"]).stem
            self.db_title.set(f"📚 {pdf_stem} 진도표")

        self._write_result("\n".join(lines))
        self.status_text.set(f"미리보기 완료 — {len(data['entries'])}개 항목")

    # ── 업로드 ─────────────────────────────────────────────
    def _upload(self) -> None:
        if self.is_running:
            return

        json_path = self.json_path.get().strip()
        token = self.notion_token.get().strip()
        page_url = self.page_url.get().strip()
        db_title = self.db_title.get().strip()

        if not json_path:
            messagebox.showwarning("확인", "groups.json 파일을 선택해 주세요.")
            return
        if not Path(json_path).exists():
            messagebox.showerror("오류", "선택한 파일을 찾을 수 없습니다.")
            return
        if not token:
            messagebox.showwarning("확인", "Notion API 키를 입력해 주세요.")
            return
        if not page_url:
            messagebox.showwarning("확인", "노션 페이지 URL을 입력해 주세요.")
            return

        try:
            page_id = extract_page_id(page_url)
        except ValueError as exc:
            messagebox.showerror("오류", str(exc))
            return

        try:
            data = parse_groups_json(json_path)
        except Exception as exc:
            messagebox.showerror("파싱 오류", str(exc))
            return

        if not db_title:
            pdf_stem = Path(data["pdf"]).stem
            db_title = f"📚 {pdf_stem} 진도표"

        # 설정 저장
        _save_config({"notion_token": token, "page_url": page_url})

        self._set_running(True, "노션에 업로드하는 중...")
        self._write_result("")
        self.progress["value"] = 0
        self.progress["maximum"] = len(data["entries"])

        worker = threading.Thread(
            target=self._upload_worker,
            kwargs={
                "token": token,
                "page_id": page_id,
                "db_title": db_title,
                "data": data,
            },
            daemon=True,
        )
        worker.start()

    def _upload_worker(
        self, *, token: str, page_id: str, db_title: str, data: dict
    ) -> None:
        def on_progress(current: int, total: int, msg: str) -> None:
            self.root.after(0, lambda: self._update_progress(current, total, msg))

        try:
            db_url = create_tracker_database(
                notion_token=token,
                page_id=page_id,
                db_title=db_title,
                groups_data=data,
                on_progress=on_progress,
            )
            self.root.after(0, lambda: self._on_success(db_url, data))
        except Exception as exc:
            details = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.root.after(0, lambda: self._on_error(details))

    def _on_success(self, db_url: str, data: dict) -> None:
        lines = [
            "✅ 노션 진도표 업로드 완료!",
            "",
            f"데이터베이스 URL: {db_url}",
            f"삽입된 항목 수: {len(data['entries'])}",
            "",
            "노션에서 확인해 보세요. 보드 뷰 / 캘린더 뷰를 추가하면",
            "수업 진행 상황을 더 직관적으로 관리할 수 있습니다.",
        ]
        self._write_result("\n".join(lines))
        self._set_running(False, "업로드 완료!")

        if messagebox.askyesno("완료", "노션 페이지를 브라우저에서 열까요?"):
            webbrowser.open(db_url)

    def _on_error(self, details: str) -> None:
        self._write_result(f"업로드 중 오류가 발생했습니다.\n\n{details}")
        self._set_running(False, "오류가 발생했습니다.")
        messagebox.showerror("오류", details)

    # ── 유틸 ───────────────────────────────────────────────
    def _update_progress(self, current: int, total: int, msg: str) -> None:
        self.progress["value"] = current
        self.progress["maximum"] = total
        self.status_text.set(msg)

    def _set_running(self, running: bool, status: str) -> None:
        self.is_running = running
        self.status_text.set(status)
        state = "disabled" if running else "normal"
        self.preview_btn.configure(state=state)
        self.upload_btn.configure(state=state)

    def _write_result(self, text: str) -> None:
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    ttk.Style().theme_use("clam")
    TrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
