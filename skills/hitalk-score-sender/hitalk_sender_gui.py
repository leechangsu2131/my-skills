import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

from hitalk_sender import build_message, is_placeholder_spreadsheet_id


SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
CLI_PATH = SCRIPT_DIR / "hitalk_sender.py"
CHROME_BAT_PATH = SCRIPT_DIR / "launch_chrome_hiclass.bat"
DEFAULT_MESSAGE_FILE_PATH = SCRIPT_DIR / "custom_message_template.txt"
PREVIEW_PATH = SCRIPT_DIR / "preview.txt"
REHEARSAL_LOG_PATH = SCRIPT_DIR / "rehearsal_log.txt"


class HiTalkSenderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HiTalk Sender")
        self.geometry("1120x860")
        self.minsize(980, 760)
        self.configure(bg="#f4efe6")

        self.log_queue = queue.Queue()
        self.process = None
        self.worker_thread = None
        self.preview_refresh_thread = None

        self.subject_var = tk.StringVar()
        self.spreadsheet_var = tk.StringVar()
        self.range_var = tk.StringVar()
        self.message_file_var = tk.StringVar(value=str(DEFAULT_MESSAGE_FILE_PATH))
        self.status_var = tk.StringVar(value="준비됨")
        self.current_config = {}
        self.preview_students = []
        self.preview_total_count = 0

        self._configure_style()
        self._build_ui()
        self.subject_var.trace_add("write", self._refresh_live_preview)
        self._load_config()
        self.after(150, self._drain_log_queue)

    def _configure_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f4efe6")
        style.configure("Card.TFrame", background="#fffaf2")
        style.configure("TLabel", background="#f4efe6", foreground="#2b241c")
        style.configure("Muted.TLabel", background="#f4efe6", foreground="#6a5c4d")
        style.configure(
            "TButton",
            background="#d7c7b3",
            foreground="#2b241c",
            padding=8,
            relief="flat",
        )
        style.map("TButton", background=[("active", "#cdb89e")])
        style.configure(
            "Accent.TButton",
            background="#2f6f5e",
            foreground="#f9f5ef",
            padding=9,
            font=("", 10, "bold"),
        )
        style.map("Accent.TButton", background=[("active", "#275b4d")])
        style.configure(
            "Warn.TButton",
            background="#9a5a3a",
            foreground="#fffaf2",
            padding=9,
            font=("", 10, "bold"),
        )
        style.map("Warn.TButton", background=[("active", "#7d472c")])
        style.configure(
            "TEntry",
            fieldbackground="#fffaf2",
            foreground="#2b241c",
            insertcolor="#2b241c",
        )

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=18, pady=(16, 10))

        ttk.Label(
            header,
            text="HiTalk Sender",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="하이톡 공지/점수 전송을 창에서 관리합니다. 긴 문구는 파일로 저장해 두고 dry-run → rehearsal → send 순서로 진행하세요.",
            style="Muted.TLabel",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=3)
        main.rowconfigure(1, weight=2)

        self._build_message_panel(main)
        self._build_settings_panel(main)
        self._build_log_panel(main)

    def _build_message_panel(self, parent):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=14)
        frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(5, weight=3)
        frame.rowconfigure(7, weight=2)

        ttk.Label(frame, text="메시지 템플릿", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            frame,
            text="치환값: [학생], [과목], [점수], [코멘트]",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 8))

        path_row = ttk.Frame(frame)
        path_row.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        path_row.columnconfigure(1, weight=1)
        ttk.Label(path_row, text="템플릿 파일").grid(row=0, column=0, sticky="w")
        self.message_file_entry = ttk.Entry(
            path_row,
            textvariable=self.message_file_var,
        )
        self.message_file_entry.grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(path_row, text="불러오기", command=self._load_message_file).grid(
            row=0, column=2, padx=(0, 6)
        )
        ttk.Button(path_row, text="저장", command=self._save_message_file).grid(
            row=0, column=3
        )

        helper = ttk.Label(
            frame,
            text="예: 안녕하세요? [학생]부모님",
            style="Muted.TLabel",
        )
        helper.grid(row=3, column=0, sticky="w")

        self.message_text = scrolledtext.ScrolledText(
            frame,
            wrap="word",
            font=("맑은 고딕", 11),
            bg="#fffdf8",
            fg="#2b241c",
            insertbackground="#2b241c",
            relief="flat",
            borderwidth=0,
        )
        self.message_text.grid(row=5, column=0, sticky="nsew", pady=(8, 12))
        self.message_text.bind("<<Modified>>", self._on_message_modified)

        preview_row = ttk.Frame(frame)
        preview_row.grid(row=6, column=0, sticky="ew", pady=(0, 8))
        preview_row.columnconfigure(0, weight=1)
        ttk.Label(preview_row, text="실제 미리보기", font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            preview_row,
            text="시트에서 읽은 실제 학생 1~2명 기준으로 보여줍니다.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.preview_refresh_button = ttk.Button(
            preview_row,
            text="실제 예시 새로고침",
            command=self._refresh_preview_students,
        )
        self.preview_refresh_button.grid(row=0, column=1, sticky="e", padx=(10, 6))
        ttk.Button(
            preview_row,
            text="마지막 dry-run 불러오기",
            command=self._load_dry_run_preview,
        ).grid(row=0, column=2, sticky="e")

        preview_notebook = ttk.Notebook(frame)
        preview_notebook.grid(row=7, column=0, sticky="nsew", pady=(0, 12))

        live_tab = ttk.Frame(preview_notebook)
        live_tab.columnconfigure(0, weight=1)
        live_tab.rowconfigure(0, weight=1)
        self.live_preview_text = scrolledtext.ScrolledText(
            live_tab,
            wrap="word",
            font=("맑은 고딕", 10),
            bg="#f7f1e7",
            fg="#2b241c",
            insertbackground="#2b241c",
            relief="flat",
            borderwidth=0,
            state="disabled",
        )
        self.live_preview_text.grid(row=0, column=0, sticky="nsew")
        preview_notebook.add(live_tab, text="실제 예시 1~2건")

        dry_run_tab = ttk.Frame(preview_notebook)
        dry_run_tab.columnconfigure(0, weight=1)
        dry_run_tab.rowconfigure(0, weight=1)
        self.dry_run_preview_text = scrolledtext.ScrolledText(
            dry_run_tab,
            wrap="word",
            font=("맑은 고딕", 10),
            bg="#f9f5ef",
            fg="#2b241c",
            insertbackground="#2b241c",
            relief="flat",
            borderwidth=0,
            state="disabled",
        )
        self.dry_run_preview_text.grid(row=0, column=0, sticky="nsew")
        preview_notebook.add(dry_run_tab, text="마지막 dry-run 전체")

        button_row = ttk.Frame(frame)
        button_row.grid(row=8, column=0, sticky="ew")
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        button_row.columnconfigure(2, weight=1)
        button_row.columnconfigure(3, weight=1)

        self.chrome_button = ttk.Button(
            button_row,
            text="크롬 열기",
            command=self._open_chrome,
        )
        self.chrome_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.dry_run_button = ttk.Button(
            button_row,
            text="Dry Run",
            command=lambda: self._run_cli("dry_run"),
        )
        self.dry_run_button.grid(row=0, column=1, sticky="ew", padx=6)

        self.rehearsal_button = ttk.Button(
            button_row,
            text="Rehearsal",
            style="Accent.TButton",
            command=lambda: self._run_cli("rehearsal"),
        )
        self.rehearsal_button.grid(row=0, column=2, sticky="ew", padx=6)

        self.send_button = ttk.Button(
            button_row,
            text="실제 전송",
            style="Warn.TButton",
            command=lambda: self._run_cli("send"),
        )
        self.send_button.grid(row=0, column=3, sticky="ew", padx=(6, 0))

    def _build_settings_panel(self, parent):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=14)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="설정", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(frame, text="과목명").grid(row=1, column=0, sticky="w", pady=(12, 6))
        ttk.Entry(frame, textvariable=self.subject_var).grid(
            row=1, column=1, sticky="ew", pady=(12, 6)
        )

        ttk.Label(frame, text="시트 ID").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.spreadsheet_var).grid(
            row=2, column=1, sticky="ew", pady=6
        )

        ttk.Label(frame, text="범위").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self.range_var).grid(
            row=3, column=1, sticky="ew", pady=6
        )

        ttk.Label(frame, text="상태").grid(row=4, column=0, sticky="w", pady=(12, 6))
        ttk.Label(
            frame,
            textvariable=self.status_var,
            style="Muted.TLabel",
        ).grid(row=4, column=1, sticky="w", pady=(12, 6))

        action_row = ttk.Frame(frame)
        action_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)

        ttk.Button(action_row, text="설정 저장", command=self._save_config).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(
            action_row,
            text="설정 다시 읽기",
            command=self._load_config,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        file_row = ttk.Frame(frame)
        file_row.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        file_row.columnconfigure(0, weight=1)
        file_row.columnconfigure(1, weight=1)

        ttk.Button(
            file_row,
            text="dry-run 결과 열기",
            command=lambda: self._open_file(PREVIEW_PATH),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            file_row,
            text="rehearsal 로그 열기",
            command=lambda: self._open_file(REHEARSAL_LOG_PATH),
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_log_panel(self, parent):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=14)
        frame.grid(row=1, column=1, sticky="nsew", pady=(10, 0))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(frame, text="실행 로그", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        self.log_text = scrolledtext.ScrolledText(
            frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#f9f5ef",
            fg="#2b241c",
            insertbackground="#2b241c",
            relief="flat",
            borderwidth=0,
            state="disabled",
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(8, 12))

        bottom = ttk.Frame(frame)
        bottom.grid(row=2, column=0, sticky="ew")
        ttk.Button(bottom, text="로그 지우기", command=self._clear_log).pack(
            side="left"
        )

    def _load_config(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        self.current_config = config

        self.subject_var.set(config.get("subject", ""))
        self.spreadsheet_var.set(config.get("spreadsheet_id", ""))
        self.range_var.set(config.get("range", ""))

        message_file = config.get("custom_message_file") or DEFAULT_MESSAGE_FILE_PATH.name
        message_path = (
            Path(message_file)
            if os.path.isabs(message_file)
            else SCRIPT_DIR / message_file
        )
        self.message_file_var.set(str(message_path))
        self._load_message_file(silent=True)
        self._load_dry_run_preview(silent=True)
        self.status_var.set("설정 불러옴")
        self._append_log(f"[GUI] 설정 로드 완료: {CONFIG_PATH}")
        self._refresh_live_preview()
        self._refresh_preview_students()

    def _save_config(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        config["subject"] = self.subject_var.get().strip()
        config["spreadsheet_id"] = self.spreadsheet_var.get().strip()
        config["range"] = self.range_var.get().strip()

        message_path = Path(self.message_file_var.get().strip() or DEFAULT_MESSAGE_FILE_PATH)
        try:
            relative_message_path = message_path.relative_to(SCRIPT_DIR)
            config["custom_message_file"] = str(relative_message_path)
        except ValueError:
            config["custom_message_file"] = str(message_path)

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            f.write("\n")

        self.current_config = config
        self.status_var.set("설정 저장 완료")
        self._append_log("[GUI] config.json 저장 완료")
        self._refresh_live_preview()

    def _load_message_file(self, silent=False):
        path = Path(self.message_file_var.get().strip() or DEFAULT_MESSAGE_FILE_PATH)
        if not path.exists():
            if not silent:
                messagebox.showerror("파일 없음", f"메시지 파일을 찾을 수 없습니다.\n{path}")
            return

        self.message_text.delete("1.0", "end")
        self.message_text.insert("1.0", path.read_text(encoding="utf-8"))
        self.message_text.edit_modified(False)
        self.status_var.set("메시지 불러옴")
        if not silent:
            self._append_log(f"[GUI] 메시지 파일 불러옴: {path}")
        self._refresh_live_preview()

    def _save_message_file(self):
        path = Path(self.message_file_var.get().strip() or DEFAULT_MESSAGE_FILE_PATH)
        path.write_text(self.message_text.get("1.0", "end-1c").rstrip() + "\n", encoding="utf-8")
        self.status_var.set("메시지 저장 완료")
        self._append_log(f"[GUI] 메시지 파일 저장 완료: {path}")
        self._refresh_live_preview()

    def _on_message_modified(self, _event=None):
        if self.message_text.edit_modified():
            self.message_text.edit_modified(False)
            self._refresh_live_preview()

    def _build_preview_config(self):
        config = dict(self.current_config)
        config["subject"] = self.subject_var.get().strip()
        config["spreadsheet_id"] = self.spreadsheet_var.get().strip()
        config["range"] = self.range_var.get().strip()
        return config

    def _set_readonly_text(self, widget, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _fetch_preview_students_from_sheet(self, config):
        spreadsheet_id = (config.get("spreadsheet_id") or "").strip()
        range_name = (config.get("range") or "").strip()

        if is_placeholder_spreadsheet_id(spreadsheet_id):
            raise RuntimeError("시트 ID를 먼저 올바르게 입력해 주세요.")
        if not range_name:
            raise RuntimeError("시트 범위를 먼저 입력해 주세요.")

        candidates = ["gws.cmd", "gws"] if os.name == "nt" else ["gws"]
        gws_executable = next((shutil.which(candidate) for candidate in candidates if shutil.which(candidate)), None)
        if not gws_executable:
            raise RuntimeError("gws CLI를 찾지 못했습니다. 먼저 전역 설치가 필요합니다.")

        params_json = json.dumps(
            {"spreadsheetId": spreadsheet_id, "range": range_name},
            ensure_ascii=False,
        )
        result = subprocess.run(
            [
                gws_executable,
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
            errors="replace",
            cwd=str(SCRIPT_DIR),
        )
        if result.returncode != 0:
            error_text = (result.stderr or "").strip() or "구글시트 읽기에 실패했습니다."
            raise RuntimeError(error_text)

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"gws 출력 파싱에 실패했습니다: {exc}") from exc

        values = data.get("values", [])
        if len(values) < 2:
            raise RuntimeError("시트에 학생 데이터가 없습니다.")

        name_col = config.get("name_column", 1)
        score_col = config.get("score_column", 2)
        students = []
        for row in values[1:]:
            if len(row) <= max(name_col, score_col):
                continue
            name = str(row[name_col]).strip()
            score = str(row[score_col]).strip()
            if name and score:
                students.append({"name": name, "score": score})

        if not students:
            raise RuntimeError("이름과 점수가 모두 있는 학생이 없습니다.")
        return students

    def _refresh_preview_students(self):
        if self.preview_refresh_thread and self.preview_refresh_thread.is_alive():
            return

        config = self._build_preview_config()
        self.preview_refresh_button.configure(state="disabled")
        self.status_var.set("실제 예시 불러오는 중")
        self._append_log("[GUI] 실제 예시 학생 미리보기 불러오는 중")

        self.preview_refresh_thread = threading.Thread(
            target=self._refresh_preview_students_worker,
            args=(config,),
            daemon=True,
        )
        self.preview_refresh_thread.start()

    def _refresh_preview_students_worker(self, config):
        try:
            students = self._fetch_preview_students_from_sheet(config)
            self.log_queue.put(
                (
                    "preview_samples",
                    {
                        "students": students[:2],
                        "total_count": len(students),
                    },
                )
            )
        except Exception as exc:
            self.log_queue.put(("preview_error", str(exc)))

    def _refresh_live_preview(self, *_args):
        template = self.message_text.get("1.0", "end-1c").strip()
        if not template:
            rendered = "메시지 템플릿을 입력하면 여기에 실제 예시가 표시됩니다."
        elif not self.preview_students:
            rendered = (
                "실제 예시가 아직 없습니다.\n"
                "오른쪽 위의 '실제 예시 새로고침'을 누르면 현재 시트 기준 학생 1~2명의 메시지를 보여줍니다."
            )
        else:
            config = self._build_preview_config()
            lines = []
            header = f"현재 시트 기준 실제 예시 {len(self.preview_students)}건"
            if self.preview_total_count > len(self.preview_students):
                header += f" (전체 {self.preview_total_count}명 중 앞의 {len(self.preview_students)}명)"
            lines.append(header)
            lines.append("=" * 56)

            for index, student in enumerate(self.preview_students, 1):
                try:
                    message = build_message(
                        student["name"],
                        student["score"],
                        config,
                        custom_message=template,
                    )
                except Exception as exc:
                    message = f"[미리보기 오류] {exc}\n\n원본 템플릿:\n{template}"

                lines.append(f"[예시 {index}] {student['name']} ({student['score']}점)")
                lines.append(message)
                if index < len(self.preview_students):
                    lines.append("─" * 50)

            rendered = "\n".join(lines)

        self._set_readonly_text(self.live_preview_text, rendered)

    def _load_dry_run_preview(self, silent=False):
        if PREVIEW_PATH.exists():
            text = PREVIEW_PATH.read_text(encoding="utf-8").strip()
            rendered = text or "preview.txt가 비어 있습니다."
            if not silent:
                self._append_log(f"[GUI] dry-run 결과 불러옴: {PREVIEW_PATH}")
        else:
            rendered = (
                "아직 dry-run 결과가 없습니다.\n"
                "Dry Run을 한 번 실행하면 전체 학생 메시지가 이 탭에 그대로 표시됩니다."
            )
            if not silent:
                self._append_log("[GUI] 아직 dry-run 결과 파일이 없습니다.")

        self._set_readonly_text(self.dry_run_preview_text, rendered)

    def _open_chrome(self):
        try:
            os.startfile(CHROME_BAT_PATH)
            self._append_log("[GUI] 하이톡 크롬 실행기 열기")
        except OSError as exc:
            messagebox.showerror("실행 실패", str(exc))

    def _open_file(self, path: Path):
        if not path.exists():
            messagebox.showinfo("파일 없음", f"아직 파일이 없습니다.\n{path}")
            return
        os.startfile(path)

    def _set_running(self, is_running: bool, status_text: str):
        state = "disabled" if is_running else "normal"
        for widget in (
            self.chrome_button,
            self.dry_run_button,
            self.rehearsal_button,
            self.send_button,
            self.message_file_entry,
            self.preview_refresh_button,
        ):
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass
        self.status_var.set(status_text)

    def _build_command(self, mode: str):
        command = [sys.executable, str(CLI_PATH)]
        message_path = Path(self.message_file_var.get().strip() or DEFAULT_MESSAGE_FILE_PATH)
        command.extend(["--message-file", str(message_path)])

        if mode == "dry_run":
            command.append("--dry-run")
        elif mode == "rehearsal":
            command.append("--rehearsal")
        return command

    def _run_cli(self, mode: str):
        if self.process and self.process.poll() is None:
            messagebox.showinfo("실행 중", "이미 다른 작업이 실행 중입니다.")
            return

        self._save_config()
        self._save_message_file()

        if mode == "send":
            confirmed = messagebox.askyesno(
                "실제 전송 확인",
                "실제 발송을 진행합니다.\n하이톡 탭이 1개인지 다시 확인했나요?",
            )
            if not confirmed:
                return

        command = self._build_command(mode)
        self._append_log(f"[GUI] 실행: {' '.join(command)}")
        self._set_running(True, f"{mode} 실행 중")

        self.worker_thread = threading.Thread(
            target=self._execute_process,
            args=(command, mode),
            daemon=True,
        )
        self.worker_thread.start()

    def _execute_process(self, command, mode):
        try:
            self.process = subprocess.Popen(
                command,
                cwd=str(SCRIPT_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if mode == "send" and self.process.stdin:
                self.process.stdin.write("y\nn\n")
                self.process.stdin.flush()
                self.process.stdin.close()

            if self.process.stdout:
                for line in self.process.stdout:
                    self.log_queue.put(("log", line.rstrip("\n")))

            return_code = self.process.wait()
            self.log_queue.put(("done", (mode, return_code)))
        except Exception as exc:
            self.log_queue.put(("error", str(exc)))

    def _drain_log_queue(self):
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "done":
                    mode, return_code = payload
                    status = "완료" if return_code == 0 else f"실패({return_code})"
                    self._append_log(f"[GUI] {mode} 종료: {status}")
                    self._set_running(False, f"{mode} {status}")
                    if mode == "dry_run" and return_code == 0:
                        self._load_dry_run_preview(silent=True)
                        self._append_log("[GUI] 마지막 dry-run 탭 갱신 완료")
                    self.process = None
                elif kind == "preview_samples":
                    self.preview_students = payload["students"]
                    self.preview_total_count = payload["total_count"]
                    self.preview_refresh_button.configure(state="normal")
                    self.status_var.set("실제 예시 갱신 완료")
                    self._append_log(
                        f"[GUI] 실제 예시 {len(self.preview_students)}건 갱신 완료 "
                        f"(전체 {self.preview_total_count}명)"
                    )
                    self._refresh_live_preview()
                elif kind == "preview_error":
                    self.preview_students = []
                    self.preview_total_count = 0
                    self.preview_refresh_button.configure(state="normal")
                    self.status_var.set("실제 예시 불러오기 실패")
                    self._append_log(f"[GUI] 실제 예시 불러오기 실패: {payload}")
                    self._refresh_live_preview()
                elif kind == "error":
                    self._append_log(f"[GUI] 오류: {payload}")
                    self._set_running(False, "오류 발생")
                    self.process = None
        except queue.Empty:
            pass
        finally:
            self.after(150, self._drain_log_queue)

    def _append_log(self, line: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


if __name__ == "__main__":
    app = HiTalkSenderGUI()
    app.mainloop()
