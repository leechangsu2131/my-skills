"""
PKM 속성 관리 도구 (Obsidian Vault용) v10
=========================================
- 절대 삭제 없음: 모든 작업은 추가/수정만 함
- 되돌리기: 모든 변경 전 백업 자동 생성
- 파일명 검색 / 내용(본문) 검색 / Obsidian 경로 붙여넣기
- domain / engine / topic / type 속성 일괄 추가·제거
- 리스트 속성: [a, b] 인라인 배열 형식으로 통일 저장
- v10: PARA 소배치 검토 / 1단계 YAML 적용 / 2단계 이동 추가
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
from pathlib import Path
from datetime import datetime
from pkm_batch_tools import (
    DEFAULT_BATCH_SIZE,
    MAX_BATCH_SIZE,
    MIN_BATCH_SIZE,
    apply_stage1_yaml,
    list_para_source_folders,
    move_stage2_items,
    review_para_batch,
)
from pkm_core import (
    DOMAIN_VALUES,
    ENGINE_VALUES,
    PROP_DESCRIPTIONS,
    TYPE_VALUES,
    apply_props_to_file,
    get_current_props,
    match_index,
    parse_obsidian_paths,
    read_text_file,
    remove_props_from_file,
    restore_backup,
    search_in_content,
)


# ─── 메인 GUI ─────────────────────────────────

class PKMManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PKM 속성 관리 도구 v10")
        self.geometry("1260x860")
        self.configure(bg="#1e1e2e")

        self.vault_path = tk.StringVar()
        self.all_files = []
        self.filtered_files = []
        self.batch_source_var = tk.StringVar()
        self.batch_size_var = tk.IntVar(value=DEFAULT_BATCH_SIZE)
        self.batch_results = {}
        self.current_batch_source = None
        self.current_batch_report = None

        self._build_ui()
        # 초기 검색 버튼 상태 (파일명 모드 = 실시간, 버튼 불필요)
        self.search_btn.config(state="normal")
        self.search_hint.config(text="Enter 또는 [검색] 클릭")

    # ── UI 구성 ──────────────────────────────

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel",    background="#1e1e2e", foreground="#cdd6f4")
        style.configure("TFrame",    background="#1e1e2e")
        style.configure("TButton",   background="#313244", foreground="#cdd6f4",
                         padding=6, relief="flat")
        style.map("TButton", background=[("active", "#45475a")])
        style.configure("Accent.TButton", background="#89b4fa", foreground="#1e1e2e",
                         font=("", 10, "bold"))
        style.configure("TEntry",    fieldbackground="#313244", foreground="#cdd6f4",
                         insertcolor="#cdd6f4")
        style.configure("TCombobox", fieldbackground="#313244", foreground="#cdd6f4")

        # ── 상단: Vault 선택 ──
        top = ttk.Frame(self)
        top.pack(fill="x", padx=12, pady=8)
        ttk.Label(top, text="📂 Vault 경로:").pack(side="left")
        ttk.Entry(top, textvariable=self.vault_path, width=60).pack(side="left", padx=6)
        ttk.Button(top, text="폴더 선택", command=self._choose_vault).pack(side="left")
        ttk.Button(top, text="파일 불러오기 ▶", style="Accent.TButton",
                   command=self._load_files).pack(side="left", padx=8)

        # ── 메인 3열 ──
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=12, pady=4)
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.columnconfigure(2, weight=2)
        main.rowconfigure(0, weight=1)

        self._build_file_panel(main)
        self._build_prop_panel(main)
        self._build_log_panel(main)

    def _build_file_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="📄 파일 목록", padding=6)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        frame.rowconfigure(4, weight=1)
        frame.columnconfigure(0, weight=1)

        # ── 검색 탭 (파일명 / 내용) ──
        tab_frame = ttk.Frame(frame)
        tab_frame.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        self.search_mode = tk.StringVar(value="name")   # "name" | "content"

        rb_name = ttk.Radiobutton(tab_frame, text="📝 파일명 검색",
                                   variable=self.search_mode, value="name",
                                   command=self._on_search_mode_change)
        rb_name.pack(side="left", padx=(0, 8))
        rb_content = ttk.Radiobutton(tab_frame, text="🔎 내용 검색",
                                      variable=self.search_mode, value="content",
                                      command=self._on_search_mode_change)
        rb_content.pack(side="left")

        # 검색 입력란
        sf = ttk.Frame(frame)
        sf.grid(row=1, column=0, sticky="ew", pady=(0, 2))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(sf, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.search_entry.bind("<Return>", lambda _: self._trigger_search())
        self.search_btn = ttk.Button(sf, text="검색", width=6,
                                      command=self._trigger_search)
        self.search_btn.pack(side="left")
        self.search_hint = ttk.Label(sf, text="", foreground="#a6adc8")
        self.search_hint.pack(side="left", padx=4)

        # 필터 행 1: domain / engine
        ff1 = ttk.Frame(frame)
        ff1.grid(row=2, column=0, sticky="ew", pady=(0, 2))
        ttk.Label(ff1, text="domain:").pack(side="left")
        self.domain_filter = ttk.Combobox(ff1, values=["(전체)"] + DOMAIN_VALUES + ["(없음)"], width=10)
        self.domain_filter.set("(전체)")
        self.domain_filter.pack(side="left", padx=(2, 6))
        ttk.Label(ff1, text="engine:").pack(side="left")
        self.engine_filter = ttk.Combobox(ff1, values=["(전체)"] + ENGINE_VALUES + ["(없음)"], width=11)
        self.engine_filter.set("(전체)")
        self.engine_filter.pack(side="left", padx=(2, 0))

        # 필터 행 2: topic / status / 속성없음 / 조회
        ff2 = ttk.Frame(frame)
        ff2.grid(row=3, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(ff2, text="topic:").pack(side="left")
        self.topic_filter_var = tk.StringVar()
        ttk.Entry(ff2, textvariable=self.topic_filter_var, width=10).pack(side="left", padx=(2, 6))
        ttk.Label(ff2, text="(없음) 입력시 미설정 파일만", foreground="#a6adc8",
                  font=("", 8)).pack(side="left", padx=(0, 6))
        ttk.Label(ff2, text="status:").pack(side="left")
        self.status_filter_var = tk.StringVar()
        status_combo = ttk.Combobox(ff2, textvariable=self.status_filter_var,
                                     values=["(전체)", "완료", "초안", "진행중", "확인됨", "반증됨", "철회", "(없음)"],
                                     width=8)
        status_combo.set("(전체)")
        status_combo.pack(side="left", padx=(2, 6))
        # 속성 없는 파일만 필터 (자동 조회 없음)
        self.no_props_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ff2, text="속성없음만",
                         variable=self.no_props_var).pack(side="left", padx=(0, 4))
        ttk.Button(ff2, text="조회", width=5,
                   command=self._filter_files).pack(side="left", padx=2)

        # Listbox
        lb_frame = ttk.Frame(frame)
        lb_frame.grid(row=4, column=0, sticky="nsew")
        lb_frame.rowconfigure(0, weight=1)
        lb_frame.columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            lb_frame, selectmode="extended",
            bg="#313244", fg="#cdd6f4", selectbackground="#89b4fa",
            selectforeground="#1e1e2e", activestyle="none",
            font=("Consolas", 10), relief="flat", borderwidth=0,
            exportselection=0,
        )
        sb = ttk.Scrollbar(lb_frame, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self.listbox.bind("<Double-Button-1>", self._preview_file)

        # 하단 버튼 행 1
        bf1 = ttk.Frame(frame)
        bf1.grid(row=5, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(bf1, text="전체 선택", command=self._select_all).pack(side="left", padx=2)
        ttk.Button(bf1, text="선택 해제", command=self._deselect_all).pack(side="left", padx=2)
        ttk.Button(bf1, text="인덱스 자동 추천 ✨",
                   command=self._auto_suggest).pack(side="left", padx=4)
        self.sel_label = ttk.Label(bf1, text="선택: 0개")
        self.sel_label.pack(side="right")

        # 하단 버튼 행 2 — Obsidian 경로 붙여넣기 / 목록 초기화
        bf2 = ttk.Frame(frame)
        bf2.grid(row=6, column=0, sticky="ew", pady=(2, 0))
        ttk.Button(bf2, text="📋 Obsidian 경로 붙여넣기",
                   command=self._paste_obsidian_paths,
                   style="Accent.TButton").pack(side="left", padx=2)
        ttk.Button(bf2, text="🔄 목록 초기화",
                   command=self._reset_list).pack(side="left", padx=4)
        ttk.Label(bf2,
                  text="Obsidian 검색 후 '복사' → 여기 붙여넣기",
                  foreground="#a6adc8").pack(side="left", padx=4)

    def _build_prop_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="🏷 속성 설정", padding=8)
        frame.grid(row=0, column=1, sticky="nsew", padx=(0, 6))

        # domain
        self._prop_row(frame, 0, "domain", DOMAIN_VALUES, combo=True)
        # engine
        self._prop_row(frame, 1, "engine", ENGINE_VALUES, combo=True)
        # type
        self._prop_row(frame, 2, "type", TYPE_VALUES, combo=True)
        # topic
        self._prop_row(frame, 3, "topic", [], combo=False)
        # status
        self._prop_row(frame, 4, "status",
                       ["완료", "초안", "진행중", "확인됨", "반증됨", "철회"], combo=True)
        # 관련종목 (리스트 입력 — 쉼표로 구분)
        self._prop_row(frame, 5, "관련종목", [], combo=False,
                       hint="쉼표로 구분 → [a, b] 리스트로 저장")
        # 상태 (거시예측용)
        self._prop_row(frame, 6, "상태",
                       ["진행중", "확인됨", "반증됨", "철회"], combo=True)
        # 날짜 (시장일지용)
        self._prop_row(frame, 7, "날짜", [], combo=False, hint="예: 2025-10")

        # 덮어쓰기 옵션
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="기존 값 덮어쓰기 (체크 안 하면 빈 값만 채움)",
                         variable=self.overwrite_var).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=8)

        # 속성 설명
        desc_frame = ttk.LabelFrame(frame, text="ℹ 속성 설명", padding=6)
        desc_frame.grid(row=9, column=0, columnspan=2, sticky="ew", pady=4)
        self.desc_label = tk.Label(desc_frame, text="속성을 선택하면 설명이 나타납니다.",
                                    bg="#1e1e2e", fg="#a6adc8", justify="left",
                                    wraplength=280, anchor="w")
        self.desc_label.pack(fill="x")

        # 액션 버튼들
        ttk.Separator(frame, orient="horizontal").grid(
            row=10, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Button(frame, text="✅ 선택 파일에 속성 추가/수정",
                   style="Accent.TButton",
                   command=self._apply_props).grid(
            row=11, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(frame, text="🗑 선택 파일에서 속성 제거",
                   command=self._remove_props).grid(
            row=12, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(frame, text="⏪ 선택 파일 되돌리기 (최근 백업 복원)",
                   command=self._restore).grid(
            row=13, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(frame, text="👁 선택 파일 현재 속성 보기",
                   command=self._show_current_props).grid(
            row=14, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(frame, text="🧹 백업 파일 전체 삭제 (_PKM_BACKUP 폴더 비우기)",
                   command=self._delete_all_backups).grid(
            row=15, column=0, columnspan=2, sticky="ew", pady=2)

        ttk.Separator(frame, orient="horizontal").grid(
            row=16, column=0, columnspan=2, sticky="ew", pady=8)

        batch_frame = ttk.LabelFrame(frame, text="🚚 PARA 소배치 이관", padding=6)
        batch_frame.grid(row=17, column=0, columnspan=2, sticky="ew", pady=4)
        batch_frame.columnconfigure(1, weight=1)

        ttk.Label(batch_frame, text="source:").grid(row=0, column=0, sticky="w", pady=2)
        self.batch_source_combo = ttk.Combobox(
            batch_frame,
            textvariable=self.batch_source_var,
            values=[],
            width=28,
            state="readonly",
        )
        self.batch_source_combo.grid(row=0, column=1, sticky="ew", pady=2, padx=(4, 0))

        ttk.Label(batch_frame, text="batch size:").grid(row=1, column=0, sticky="w", pady=2)
        self.batch_size_spin = tk.Spinbox(
            batch_frame,
            from_=MIN_BATCH_SIZE,
            to=MAX_BATCH_SIZE,
            textvariable=self.batch_size_var,
            width=6,
        )
        self.batch_size_spin.grid(row=1, column=1, sticky="w", pady=2, padx=(4, 0))

        ttk.Button(
            batch_frame,
            text="🔎 배치 검토",
            style="Accent.TButton",
            command=self._run_para_batch_review,
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(
            batch_frame,
            text="1단계 YAML 적용",
            command=self._apply_batch_stage1,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(
            batch_frame,
            text="2단계 이동",
            command=self._move_batch_stage2,
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=2)

        filter_row = ttk.Frame(batch_frame)
        filter_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(
            filter_row,
            text="⚠ 충돌/링크 민감만",
            command=self._show_batch_blocked_only,
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            filter_row,
            text="📋 배치 전체",
            command=self._show_batch_all,
        ).pack(side="left")

        self.batch_summary_label = ttk.Label(
            batch_frame,
            text="배치 미실행",
            foreground="#a6adc8",
            wraplength=280,
            justify="left",
        )
        self.batch_summary_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))

        frame.columnconfigure(1, weight=1)

    def _prop_row(self, parent, row, name, values, combo=True, hint=""):
        label_text = f"{name}:"
        ttk.Label(parent, text=label_text, width=8).grid(
            row=row, column=0, sticky="w", pady=3)
        var = tk.StringVar()
        setattr(self, f"prop_{name}", var)
        if combo and values:
            w = ttk.Combobox(parent, textvariable=var,
                             values=["(설정 안 함)"] + values, width=20)
            w.set("(설정 안 함)")
        else:
            w = ttk.Entry(parent, textvariable=var, width=22)
            if hint:
                w.insert(0, "")
                # placeholder 힌트를 툴팁처럼 표시
                w.bind("<FocusIn>",  lambda e, h=hint, v=var: None)
        w.grid(row=row, column=1, sticky="ew", pady=3)
        w.bind("<FocusIn>", lambda e, n=name: self._show_desc(n))

    def _build_log_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="📋 작업 로그", padding=6)
        frame.grid(row=0, column=2, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.log = scrolledtext.ScrolledText(
            frame, bg="#181825", fg="#a6e3a1",
            font=("Consolas", 9), state="disabled",
            relief="flat", borderwidth=0,
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        ttk.Button(frame, text="로그 지우기",
                   command=self._clear_log).grid(row=1, column=0, sticky="e", pady=4)

    # ── 이벤트 핸들러 ────────────────────────

    def _choose_vault(self):
        path = filedialog.askdirectory(title="Obsidian Vault 폴더 선택")
        if path:
            self.vault_path.set(path)
            self._refresh_batch_sources()

    def _load_files(self):
        vault = self.vault_path.get().strip()
        if not vault or not os.path.isdir(vault):
            messagebox.showerror("오류", "유효한 Vault 폴더를 선택하세요.")
            return
        self.all_files = sorted(Path(vault).rglob("*.md"))
        # _PKM_BACKUP 폴더 내 .md.bak 파일 제외
        self.all_files = [f for f in self.all_files if "_PKM_BACKUP" not in str(f)]
        self._clear_batch_state()
        self._refresh_batch_sources()
        self.search_var.set("")
        self._filter_files()
        self._log(f"✅ {len(self.all_files)}개 .md 파일 로드 완료")

    def _clear_batch_state(self):
        self.batch_results = {}
        self.current_batch_source = None
        self.current_batch_report = None
        if hasattr(self, "batch_summary_label"):
            self.batch_summary_label.config(text="배치 미실행")

    def _refresh_batch_sources(self):
        vault = self.vault_path.get().strip()
        if not vault or not os.path.isdir(vault):
            self.batch_source_combo["values"] = []
            self.batch_source_var.set("")
            return

        sources = list_para_source_folders(Path(vault))
        self.batch_source_combo["values"] = sources
        if sources:
            if self.batch_source_var.get() not in sources:
                self.batch_source_var.set(sources[0])
        else:
            self.batch_source_var.set("")

    def _set_batch_view(self, items):
        self.filtered_files = [item.source_path for item in items]
        self._refresh_listbox()
        if self.filtered_files:
            self.listbox.select_set(0, "end")
        self._on_select()

    def _selected_batch_items(self):
        selected_items = []
        for idx in self.listbox.curselection():
            if idx < len(self.filtered_files):
                item = self.batch_results.get(self.filtered_files[idx])
                if item:
                    selected_items.append(item)
        return selected_items

    def _run_para_batch_review(self):
        vault = self.vault_path.get().strip()
        if not vault or not os.path.isdir(vault):
            messagebox.showerror("오류", "먼저 유효한 Vault 폴더를 선택하세요.")
            return
        if not self.all_files:
            self._load_files()
        source_folder = self.batch_source_var.get().strip() or None
        batch_size = self.batch_size_var.get() or DEFAULT_BATCH_SIZE
        try:
            review = review_para_batch(
                vault_path=Path(vault),
                source_folder=source_folder,
                batch_size=batch_size,
            )
        except Exception as exc:
            messagebox.showerror("배치 검토 오류", str(exc))
            return

        self.batch_results = {item.source_path: item for item in review.items}
        self.current_batch_source = review.source_folder
        self.current_batch_report = review.report_path
        self.batch_source_var.set(review.source_folder)
        self._set_batch_view(review.items)
        self.batch_summary_label.config(
            text=(
                f"source: {review.source_folder}\n"
                f"ready {review.status_counts.get('ready', 0)} / "
                f"needs_review {review.status_counts.get('needs_review', 0)} / "
                f"link_sensitive {review.status_counts.get('link_sensitive', 0)} / "
                f"conflict {review.status_counts.get('conflict', 0)}"
            )
        )
        self._log(
            f"🚚 배치 검토 완료: {len(review.items)}개 선택, 보고서 저장 → {review.report_path}"
        )

    def _apply_batch_stage1(self):
        items = self._selected_batch_items()
        if not items:
            messagebox.showinfo("안내", "배치에서 적용할 파일을 먼저 선택하세요.")
            return
        if not messagebox.askyesno(
            "1단계 적용 확인",
            f"선택한 {len(items)}개 파일에 추천 YAML을 적용합니다.\n원본 위치는 그대로 유지됩니다.",
        ):
            return
        summary = apply_stage1_yaml(items)
        self._log(
            "🧩 1단계 YAML 적용 완료: 성공 {ok} / 스킵 {skipped} / 오류 {error}".format(
                **summary
            )
        )
        self._run_para_batch_review()

    def _move_batch_stage2(self):
        items = self._selected_batch_items()
        if not items:
            messagebox.showinfo("안내", "배치에서 이동할 파일을 먼저 선택하세요.")
            return
        if not messagebox.askyesno(
            "2단계 이동 확인",
            f"선택한 {len(items)}개 파일을 PKM 폴더로 이동합니다.\n이동 전 백업이 생성됩니다.",
        ):
            return

        vault = self.vault_path.get().strip()
        summary = move_stage2_items(Path(vault), items)
        self._log(
            "📦 2단계 이동 완료: 이동 {moved} / 스킵 {skipped} / 충돌 {conflict} / 오류 {error}".format(
                **summary
            )
        )
        self._load_files()
        if self.batch_source_var.get().strip():
            self._run_para_batch_review()

    def _show_batch_blocked_only(self):
        if not self.batch_results:
            messagebox.showinfo("안내", "먼저 배치 검토를 실행하세요.")
            return
        blocked = [
            item
            for item in self.batch_results.values()
            if item.review_status in {"conflict", "link_sensitive"}
        ]
        self._set_batch_view(blocked)
        self._log(f"⚠ 충돌/링크 민감 파일 {len(blocked)}개 표시")

    def _show_batch_all(self):
        if not self.batch_results:
            messagebox.showinfo("안내", "먼저 배치 검토를 실행하세요.")
            return
        ordered = sorted(
            self.batch_results.values(),
            key=lambda item: item.source_rel.lower(),
        )
        self._set_batch_view(ordered)
        self._log(f"📋 현재 배치 전체 {len(ordered)}개 표시")

    def _on_search_mode_change(self):
        """파일명/내용 검색 모드 전환"""
        mode = self.search_mode.get()
        if mode == "name":
            self.search_hint.config(text="Enter 또는 [검색] 클릭")
        else:
            self.search_hint.config(text="Enter 또는 [검색] 클릭")
        self.search_var.set("")
        self._filter_files()

    def _trigger_search(self):
        """엔터 또는 포커스아웃 시 — 파일명/내용 모드 공통 진입점"""
        if self.search_mode.get() == "name":
            self._filter_files()
        else:
            self._do_search()

    def _on_search_changed(self):
        """(호환성 유지용 — 실시간 필터 제거됨, 현재 미사용)"""
        pass

    def _do_search(self):
        """내용 검색 실행"""
        query = self.search_var.get().strip()
        if not query:
            self._filter_files()
            return
        if not self.all_files:
            messagebox.showinfo("안내", "먼저 Vault를 불러오세요.")
            return
        self._log(f"🔎 내용 검색 중: '{query}' ...")
        self.update_idletasks()  # UI 반응성 유지

        # 먼저 파일명/속성 필터 적용 후 그 결과 안에서 내용 검색
        base = self._get_base_filtered()
        matched = search_in_content(base, query)

        self.filtered_files = matched
        self._refresh_listbox()
        self._log(f"🔎 내용 검색 결과: {len(matched)}개 파일에서 '{query}' 발견")

    def _get_base_filtered(self) -> list:
        """domain/engine/topic/status/속성없음 필터 적용한 기본 파일 목록 반환
        (없음) 선택 시 해당 속성이 없는 파일만 / 값 선택 시 정확히 일치하는 파일만"""
        d_filter = self.domain_filter.get()
        e_filter = self.engine_filter.get()
        t_filter = self.topic_filter_var.get().strip().lower()
        s_filter = self.status_filter_var.get().strip()
        no_props = self.no_props_var.get()

        need_props = (d_filter != "(전체)" or e_filter != "(전체)" or
                      t_filter or s_filter not in ("", "(전체)") or no_props)

        result = []
        for f in self.all_files:
            if need_props:
                props = get_current_props(f)

                # domain
                if d_filter == "(없음)":
                    if props.get("domain", ""):
                        continue
                elif d_filter != "(전체)":
                    if props.get("domain", "") != d_filter:
                        continue

                # engine
                if e_filter == "(없음)":
                    if props.get("engine", ""):
                        continue
                elif e_filter != "(전체)":
                    if props.get("engine", "") != e_filter:
                        continue

                # topic
                if t_filter == "(없음)":
                    if str(props.get("topic", "")).strip():
                        continue
                elif t_filter:
                    val = str(props.get("topic", "")).lower()
                    if t_filter not in val:
                        continue

                # status
                if s_filter == "(없음)":
                    if props.get("status", ""):
                        continue
                elif s_filter and s_filter != "(전체)":
                    if props.get("status", "") != s_filter:
                        continue

                if no_props and props:
                    continue
            result.append(f)
        return result

    def _filter_files(self):
        """파일명 검색 + domain/engine/속성없음 필터 (기존 선택 유지)"""
        # 현재 선택된 파일 경로 저장
        prev_selected = {self.filtered_files[i] for i in self.listbox.curselection()} \
            if hasattr(self, 'filtered_files') else set()

        query = self.search_var.get().lower()
        base = self._get_base_filtered()

        if self.search_mode.get() == "name" and query:
            result = [f for f in base if query in f.stem.lower()]
        else:
            result = base

        self.filtered_files = result
        self._refresh_listbox_keep_selection(prev_selected)
        self._log(f"🔍 필터 결과: {len(result)}개")

    def _display_label_for_file(self, file_path):
        item = self.batch_results.get(file_path)
        if item:
            status_tag = {
                "ready": "[ready]",
                "needs_review": "[review]",
                "link_sensitive": "[link]",
                "conflict": "[conflict]",
            }.get(item.review_status, "[batch]")
            return f"{file_path.stem} {status_tag}"
        return file_path.stem

    def _refresh_listbox(self):
        """listbox를 filtered_files 기준으로 갱신 (스크롤 위치 유지)"""
        scroll_pos = self.listbox.yview()[0]
        self.listbox.delete(0, "end")
        for f in self.filtered_files:
            self.listbox.insert("end", self._display_label_for_file(f))
        self._apply_listbox_colors()
        self.listbox.yview_moveto(scroll_pos)

    def _refresh_listbox_keep_selection(self, prev_selected: set):
        """listbox 갱신 후 이전 선택 파일 복원 (스크롤 위치 유지)"""
        scroll_pos = self.listbox.yview()[0]
        self.listbox.delete(0, "end")
        for f in self.filtered_files:
            self.listbox.insert("end", self._display_label_for_file(f))
        self._apply_listbox_colors()
        for i, f in enumerate(self.filtered_files):
            if f in prev_selected:
                self.listbox.select_set(i)
        self.listbox.yview_moveto(scroll_pos)
        self._on_select()

    def _apply_listbox_colors(self):
        """속성 없는 파일은 주황색으로 표시"""
        for i, f in enumerate(self.filtered_files):
            try:
                batch_item = self.batch_results.get(f)
                if batch_item:
                    color = {
                        "ready": "#a6e3a1",
                        "needs_review": "#fab387",
                        "link_sensitive": "#cba6f7",
                        "conflict": "#f38ba8",
                    }.get(batch_item.review_status, "#cdd6f4")
                    self.listbox.itemconfig(i, fg=color)
                    continue
                props = get_current_props(f)
                if not props:
                    self.listbox.itemconfig(i, fg="#fab387")   # 주황 (속성 없음)
                else:
                    self.listbox.itemconfig(i, fg="#cdd6f4")   # 기본 흰색
            except Exception:
                pass

    def _paste_obsidian_paths(self):
        """
        Obsidian 검색결과 복사 형식의 경로를 붙여넣어
        해당 파일들을 목록에서 선택 상태로 만듦.
        팝업 텍스트창에서 입력받는 방식.
        """
        vault = self.vault_path.get().strip()
        if not vault or not os.path.isdir(vault):
            messagebox.showerror("오류", "먼저 Vault 폴더를 선택하고 파일을 불러오세요.")
            return

        # 입력 팝업
        win = tk.Toplevel(self)
        win.title("📋 Obsidian 검색결과 경로 붙여넣기")
        win.geometry("700x420")
        win.configure(bg="#1e1e2e")
        win.grab_set()  # 모달

        ttk.Label(win,
                  text="Obsidian에서 검색 후 결과 복사(Ctrl+C) → 아래에 붙여넣기(Ctrl+V)",
                  background="#1e1e2e", foreground="#cdd6f4").pack(pady=(10, 4), padx=12, anchor="w")
        ttk.Label(win,
                  text="예)  4 ARCHIVE(보관함, 끝남)/감상문/원칙 - 레이달리오.md",
                  background="#1e1e2e", foreground="#a6adc8",
                  font=("Consolas", 9)).pack(padx=12, anchor="w")

        txt = scrolledtext.ScrolledText(win, bg="#313244", fg="#cdd6f4",
                                         font=("Consolas", 10), height=14)
        txt.pack(fill="both", expand=True, padx=12, pady=8)
        txt.focus()

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        def _apply():
            raw = txt.get("1.0", "end")
            vault_p = Path(vault)
            found, not_found = parse_obsidian_paths(raw, vault_p)

            if not found:
                messagebox.showwarning("결과 없음",
                    "매칭된 파일이 없습니다.\nVault 경로가 올바른지, 파일이 존재하는지 확인하세요.")
                return

            # 기존 목록 초기화 후 found 파일만 표시
            self._clear_batch_state()
            self.filtered_files = found
            self._refresh_listbox()

            # 모두 선택 상태로
            self.listbox.select_set(0, "end")

            self._on_select()
            msg = f"✅ {len(found)}개 파일 로드 및 선택됨"
            if not_found:
                msg += f"\n⚠ {len(not_found)}개 경로를 찾지 못함:\n" + "\n".join(not_found[:5])
                if len(not_found) > 5:
                    msg += f"\n  ... 외 {len(not_found)-5}개"
            self._log(msg)
            win.destroy()

        ttk.Button(btn_frame, text="✅ 적용",
                   style="Accent.TButton", command=_apply).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="취소", command=win.destroy).pack(side="left")

    def _on_select(self, _=None):
        n = len(self.listbox.curselection())
        self.sel_label.config(text=f"선택: {n}개")

    def _select_all(self):
        self.listbox.select_set(0, "end")
        self._on_select()

    def _deselect_all(self):
        self.listbox.select_clear(0, "end")
        self._on_select()

    def _reset_list(self):
        """목록 초기화 — 조회 결과를 비워 아무것도 없는 상태로"""
        self._clear_batch_state()
        self.filtered_files = []
        self.listbox.delete(0, "end")
        self._on_select()
        self._log("🔄 목록 초기화")

    def _preview_file(self, _=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        f = self.filtered_files[sel[0]]
        props = get_current_props(f)
        win = tk.Toplevel(self)
        win.title(f.stem)
        win.geometry("500x400")
        win.configure(bg="#1e1e2e")
        txt = scrolledtext.ScrolledText(win, bg="#313244", fg="#cdd6f4",
                                         font=("Consolas", 10))
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("end", f"파일: {f}\n\n현재 속성:\n")
        if props:
            for k, v in props.items():
                txt.insert("end", f"  {k}: {v}\n")
        else:
            txt.insert("end", "  (속성 없음)\n")
        try:
            content = read_text_file(f)
            txt.insert("end", f"\n--- 내용 미리보기 ---\n{content[:800]}")
        except:
            pass
        txt.configure(state="disabled")

    def _show_desc(self, name):
        desc = PROP_DESCRIPTIONS.get(name, "")
        self.desc_label.config(text=desc or "설명 없음")

    def _auto_suggest(self):
        """선택된 파일에 인덱스 매핑 자동 추천 → 속성 필드 채우기"""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("안내", "파일을 먼저 선택하세요.")
            return
        if len(sel) == 1:
            f = self.filtered_files[sel[0]]
            mapping = match_index(f.stem)
            if mapping:
                for k in ["domain", "engine"]:
                    if k in mapping:
                        getattr(self, f"prop_{k}").set(mapping[k])
                self._log(f"✨ [{f.stem}] 자동 추천: {mapping}")
            else:
                self._log(f"⚠ [{f.stem}] 인덱스 매핑 없음 — 수동 입력 필요")
        else:
            self._log("ℹ 여러 파일 선택 시 자동 추천은 개별 적용됩니다. [속성 추가] 시 인덱스 참조 적용.")

    def _get_props_to_apply(self) -> dict:
        props = {}
        for name in ["domain", "engine", "type", "topic", "status", "상태", "날짜"]:
            v = getattr(self, f"prop_{name}").get().strip()
            if v and v != "(설정 안 함)":
                props[name] = v
        # 관련종목: 쉼표 구분 입력 → 리스트로 변환
        v = getattr(self, "prop_관련종목").get().strip()
        if v and v != "(설정 안 함)":
            items = [item.strip() for item in v.split(",") if item.strip()]
            props["관련종목"] = items if len(items) > 1 else items[0] if items else v
        return props

    def _apply_props(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("안내", "파일을 먼저 선택하세요.")
            return
        manual_props = self._get_props_to_apply()
        overwrite = self.overwrite_var.get()
        ok = skip = err = 0
        remove_indices = []   # 성공한 파일 인덱스 (목록에서 제거할 것)
        for idx in sel:
            f = self.filtered_files[idx]
            mapping = match_index(f.stem)
            props = {**mapping, **manual_props}
            if not props:
                self._log(f"⚠ [{f.stem}] 적용할 속성 없음")
                skip += 1
                continue
            result = apply_props_to_file(f, props, overwrite=overwrite)
            if result == "ok":
                self._log(f"✅ [{f.stem}] {props}")
                ok += 1
                remove_indices.append(idx)
            elif result == "skipped":
                self._log(f"➖ [{f.stem}] 변경 없음 (이미 값 있음)")
                skip += 1
            else:
                self._log(f"❌ [{f.stem}] {result}", error=True)
                err += 1
        self._log(f"── 완료: 성공 {ok} / 스킵 {skip} / 오류 {err} ──")
        if self.batch_results and self.batch_source_var.get().strip():
            self._run_para_batch_review()
            return
        # 성공한 파일만 목록에서 제거 (나머지는 유지)
        if remove_indices:
            remove_set = set(remove_indices)
            self.filtered_files = [f for i, f in enumerate(self.filtered_files)
                                   if i not in remove_set]
            self._refresh_listbox()

    def _remove_props(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("안내", "파일을 먼저 선택하세요.")
            return
        keys = []
        for name in ["domain", "engine", "type", "topic", "status", "관련종목", "상태", "날짜"]:
            v = getattr(self, f"prop_{name}").get().strip()
            if v and v != "(설정 안 함)":
                keys.append(name)
        if not keys:
            messagebox.showinfo("안내", "제거할 속성을 콤보박스에서 선택하세요.")
            return
        if not messagebox.askyesno("확인",
            f"선택한 {len(sel)}개 파일에서 속성 {keys}를 제거합니다.\n(백업이 자동 생성됩니다)"):
            return
        ok = skip = err = 0
        remove_indices = []
        for idx in sel:
            f = self.filtered_files[idx]
            result = remove_props_from_file(f, keys)
            if result == "ok":
                self._log(f"🗑 [{f.stem}] {keys} 제거됨")
                ok += 1
                remove_indices.append(idx)
            elif result == "skipped":
                self._log(f"➖ [{f.stem}] 해당 속성 없음")
                skip += 1
            else:
                self._log(f"❌ [{f.stem}] {result}", error=True)
                err += 1
        self._log(f"── 제거 완료: {ok} / 스킵 {skip} / 오류 {err} ──")
        if self.batch_results and self.batch_source_var.get().strip():
            self._run_para_batch_review()
            return
        # 성공한 파일만 목록에서 제거
        if remove_indices:
            remove_set = set(remove_indices)
            self.filtered_files = [f for i, f in enumerate(self.filtered_files)
                                   if i not in remove_set]
            self._refresh_listbox()

    def _restore(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("안내", "파일을 먼저 선택하세요.")
            return
        if not messagebox.askyesno("확인",
            f"선택한 {len(sel)}개 파일을 최근 백업으로 복원합니다.\n현재 파일이 덮어써집니다."):
            return
        for idx in sel:
            f = self.filtered_files[idx]
            result = restore_backup(f)
            if result.startswith("restored"):
                self._log(f"⏪ [{f.stem}] {result}")
            else:
                self._log(f"⚠ [{f.stem}] 백업 없음", error=True)
        if self.batch_results and self.batch_source_var.get().strip():
            self._run_para_batch_review()

    def _show_current_props(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo("안내", "파일을 먼저 선택하세요.")
            return
        lines = []
        for idx in sel:
            f = self.filtered_files[idx]
            props = get_current_props(f)
            prop_str = ", ".join(f"{k}={v}" for k, v in props.items()) if props else "(없음)"
            lines.append(f"{f.stem}: {prop_str}")
        win = tk.Toplevel(self)
        win.title("현재 속성")
        win.geometry("600x400")
        win.configure(bg="#1e1e2e")
        txt = scrolledtext.ScrolledText(win, bg="#313244", fg="#cdd6f4",
                                         font=("Consolas", 10))
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("end", "\n".join(lines))
        txt.configure(state="disabled")

    def _delete_all_backups(self):
        """Vault 내 모든 _PKM_BACKUP 폴더의 백업 파일 삭제"""
        vault = self.vault_path.get().strip()
        if not vault or not os.path.isdir(vault):
            messagebox.showerror("오류", "먼저 Vault 폴더를 선택하세요.")
            return
        bak_dirs = list(Path(vault).rglob("_PKM_BACKUP"))
        if not bak_dirs:
            messagebox.showinfo("안내", "백업 폴더(_PKM_BACKUP)가 없습니다.")
            return
        total_files = sum(len(list(d.glob("*.bak"))) for d in bak_dirs)
        if total_files == 0:
            messagebox.showinfo("안내", "삭제할 백업 파일이 없습니다.")
            return
        if not messagebox.askyesno("백업 삭제 확인",
            f"모든 _PKM_BACKUP 폴더의 백업 파일 {total_files}개를 삭제합니다.\n"
            f"이 작업은 되돌릴 수 없습니다. 계속하시겠습니까?"):
            return
        deleted = 0
        errors = 0
        for bak_dir in bak_dirs:
            for bak_file in bak_dir.glob("*.bak"):
                try:
                    bak_file.unlink()
                    deleted += 1
                except Exception as e:
                    self._log(f"❌ 삭제 실패: {bak_file.name} — {e}", error=True)
                    errors += 1
        self._log(f"🧹 백업 삭제 완료: {deleted}개 삭제 / 오류 {errors}개")

    def _log(self, msg: str, error=False):
        self.log.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        color = "#f38ba8" if error else "#a6e3a1"
        self.log.insert("end", f"[{ts}] {msg}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")


if __name__ == "__main__":
    app = PKMManager()
    app.mainloop()
