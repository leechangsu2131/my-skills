#!/usr/bin/env python3
from __future__ import annotations

import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from scripts.split_subunits_from_plan_table import (
    build_run_directory_name,
    split_subunits_from_plan_table,
)

SPLIT_LEVEL_LABELS = {
    "unit": "단원 단위만 분할",
    "detail": "차시/세부 제재까지 분할",
}
SPLIT_LEVEL_CHOICES = tuple(SPLIT_LEVEL_LABELS.values())
SPLIT_LEVEL_BY_LABEL = {label: key for key, label in SPLIT_LEVEL_LABELS.items()}


class SplitterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("지도서 PDF 분할기")
        self.root.geometry("900x680")
        self.root.minsize(820, 560)

        self.pdf_path = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "output"))
        self.scan_pages = tk.IntVar(value=60)
        self.page_offset = tk.IntVar(value=0)
        self.guide_column = tk.StringVar(value="")
        self.split_level_label = tk.StringVar(value=SPLIT_LEVEL_LABELS["unit"])
        self.status_text = tk.StringVar(value="PDF를 선택해 주세요.")
        self.is_running = False

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

        ttk.Label(frame, text="입력 PDF").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(frame, textvariable=self.pdf_path).grid(
            row=0, column=1, sticky="ew", padx=(8, 8), pady=(0, 8)
        )
        ttk.Button(frame, text="찾아보기", command=self.choose_pdf).grid(
            row=0, column=2, sticky="ew", pady=(0, 8)
        )

        ttk.Label(frame, text="출력 폴더").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(frame, textvariable=self.output_dir).grid(
            row=1, column=1, sticky="ew", padx=(8, 8), pady=(0, 8)
        )
        ttk.Button(frame, text="선택", command=self.choose_output_dir).grid(
            row=1, column=2, sticky="ew", pady=(0, 8)
        )

        options = ttk.LabelFrame(frame, text="옵션", padding=12)
        options.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 12))
        options.columnconfigure(1, weight=1)
        options.columnconfigure(3, weight=1)

        ttk.Label(options, text="탐색 페이지 수").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(options, from_=1, to=1000, textvariable=self.scan_pages, width=10).grid(
            row=0, column=1, sticky="w", padx=(8, 20)
        )
        ttk.Label(options, text="페이지 오프셋").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(options, from_=-500, to=500, textvariable=self.page_offset, width=10).grid(
            row=0, column=3, sticky="w", padx=(8, 0)
        )

        ttk.Label(options, text="분할 수준").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Combobox(
            options,
            textvariable=self.split_level_label,
            values=SPLIT_LEVEL_CHOICES,
            state="readonly",
            width=24,
        ).grid(row=1, column=1, sticky="w", padx=(8, 20), pady=(10, 0))
        ttk.Label(
            options,
            text="단원만 자르거나 더 세부적인 제재/차시 수준까지 나눌 수 있습니다.",
        ).grid(row=1, column=2, columnspan=2, sticky="w", pady=(10, 0))

        ttk.Label(options, text="지도서 쪽수 열 인덱스").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(options, textvariable=self.guide_column, width=12).grid(
            row=2, column=1, sticky="w", padx=(8, 20), pady=(10, 0)
        )
        ttk.Label(
            options,
            text="비우면 자동 탐지, 숫자를 넣으면 0부터 시작하는 열 번호를 고정합니다.",
        ).grid(row=2, column=2, columnspan=2, sticky="w", pady=(10, 0))

        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self.preview_button = ttk.Button(actions, text="미리보기", command=self.preview_split)
        self.preview_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.save_button = ttk.Button(actions, text="분할 저장", command=self.save_split)
        self.save_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ttk.Label(frame, text="분할 결과").grid(row=4, column=0, columnspan=3, sticky="w")
        self.result_box = tk.Text(frame, wrap="word", height=18)
        self.result_box.grid(row=5, column=0, columnspan=3, sticky="nsew")
        self.result_box.configure(state="disabled")

        status_bar = ttk.Label(frame, textvariable=self.status_text, relief="sunken", anchor="w")
        status_bar.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(12, 0))

    def choose_pdf(self) -> None:
        chosen = filedialog.askopenfilename(
            title="지도서 PDF 선택",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if chosen:
            self.pdf_path.set(chosen)

    def choose_output_dir(self) -> None:
        chosen = filedialog.askdirectory(title="출력 폴더 선택")
        if chosen:
            self.output_dir.set(chosen)

    def preview_split(self) -> None:
        self.run_split(save=False)

    def save_split(self) -> None:
        self.run_split(save=True)

    def run_split(self, *, save: bool) -> None:
        if self.is_running:
            return

        pdf_path = Path(self.pdf_path.get().strip())
        output_dir = Path(self.output_dir.get().strip())
        guide_column_text = self.guide_column.get().strip()
        split_level = SPLIT_LEVEL_BY_LABEL.get(self.split_level_label.get(), "unit")

        if not pdf_path:
            messagebox.showwarning("확인", "먼저 PDF 파일을 선택해 주세요.")
            return
        if not pdf_path.exists():
            messagebox.showerror("오류", "선택한 PDF 파일을 찾을 수 없습니다.")
            return
        if not output_dir:
            messagebox.showwarning("확인", "출력 폴더를 입력해 주세요.")
            return

        z_col = None
        if guide_column_text:
            try:
                z_col = int(guide_column_text)
            except ValueError:
                messagebox.showerror("오류", "열 인덱스는 숫자로 입력해 주세요.")
                return

        self.set_running(True, "PDF를 분석 중입니다...")
        self.write_result("")

        worker = threading.Thread(
            target=self._run_split_worker,
            kwargs={
                "pdf_path": pdf_path,
                "output_dir": output_dir,
                "save": save,
                "z_col": z_col,
                "split_level": split_level,
            },
            daemon=True,
        )
        worker.start()

    def _run_split_worker(
        self,
        *,
        pdf_path: Path,
        output_dir: Path,
        save: bool,
        z_col: int | None,
        split_level: str,
    ) -> None:
        try:
            groups = split_subunits_from_plan_table(
                pdf_path=pdf_path,
                out_dir=output_dir,
                dry_run=not save,
                save=save,
                scan_pages=self.scan_pages.get(),
                page_offset=self.page_offset.get(),
                z_col=z_col,
                split_level=split_level,
            )
            self.root.after(
                0,
                lambda: self.on_success(pdf_path, output_dir, groups, save, split_level),
            )
        except Exception as exc:
            details = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            self.root.after(0, lambda: self.on_error(details))

    def on_success(
        self,
        pdf_path: Path,
        output_dir: Path,
        groups: list[dict],
        save: bool,
        split_level: str,
    ) -> None:
        run_dir = output_dir / build_run_directory_name(pdf_path)
        lines = [
            f"입력 파일: {pdf_path}",
            f"출력 위치: {run_dir}",
            f"분할 수준: {SPLIT_LEVEL_LABELS.get(split_level, split_level)}",
            f"감지된 그룹 수: {len(groups)}",
            "",
        ]
        for group in groups:
            lines.append(
                f"{group['index']:02d}. {group['title']}  "
                f"p.{group['start_page']}-{group['end_page']}  "
                f"({group['method']})"
            )

        if save:
            lines.extend(
                [
                    "",
                    "분할 PDF 저장이 완료되었습니다.",
                    f"저장 폴더: {run_dir / 'pdf_splits'}",
                ]
            )
            self.status_text.set("분할 저장이 완료되었습니다.")
        else:
            lines.extend(
                [
                    "",
                    "미리보기만 완료되었습니다.",
                    "실제 PDF를 만들려면 '분할 저장'을 눌러 주세요.",
                ]
            )
            self.status_text.set("미리보기가 완료되었습니다.")

        self.write_result("\n".join(lines))
        self.set_running(False, self.status_text.get())

    def on_error(self, details: str) -> None:
        self.write_result(f"작업 중 오류가 발생했습니다.\n\n{details}")
        self.set_running(False, "오류가 발생했습니다.")
        messagebox.showerror("오류", details)

    def set_running(self, running: bool, status: str) -> None:
        self.is_running = running
        self.status_text.set(status)
        state = "disabled" if running else "normal"
        self.preview_button.configure(state=state)
        self.save_button.configure(state=state)

    def write_result(self, text: str) -> None:
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    ttk.Style().theme_use("clam")
    SplitterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
