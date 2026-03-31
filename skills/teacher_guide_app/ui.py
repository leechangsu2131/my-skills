"""
CLI 인터페이스: 교사용 지도서 관리 시스템의 메인 UI
"""

import os
import sys
import re
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from cache_manager import CacheManager
from indexer import PDFIndexer
from extractor import PDFExtractor
from analyzer import LessonAnalyzer


console = Console() if HAS_RICH else None


def cprint(text, style=""):
    if HAS_RICH and console:
        console.print(text, style=style)
    else:
        print(text)


class CLI:
    def __init__(self):
        self.cache = CacheManager()
        self.extractor = PDFExtractor()
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.analyzer = LessonAnalyzer(api_key=self.api_key)

    def run(self):
        """메인 실행 루프"""
        self._print_banner()

        if len(sys.argv) > 1:
            # 명령행 인자 처리
            self._handle_args(sys.argv[1:])
        else:
            # 대화형 모드
            self._interactive_mode()

    def _print_banner(self):
        banner = """
╔══════════════════════════════════════════════════╗
║       📚 교사용 지도서 PDF 관리 시스템            ║
║       Teacher's Guide PDF Cache System           ║
╚══════════════════════════════════════════════════╝
"""
        print(banner)

    def _handle_args(self, args):
        cmd = args[0].lower()

        if cmd == "add":
            # python app.py add 파일.pdf 국어 3
            if len(args) < 4:
                print("사용법: python app.py add [PDF파일] [교과] [학년]")
                print("예시:   python app.py add 국어지도서.pdf 국어 3")
                return
            self._cmd_add(args[1], args[2], int(args[3]))

        elif cmd == "get":
            # python app.py get 국어 3 1 2  → 국어 3학년 1단원 2차시
            if len(args) < 5:
                print("사용법: python app.py get [교과] [학년] [단원] [차시]")
                print("예시:   python app.py get 국어 3 1 2")
                return
            self._cmd_get(args[1], int(args[2]), int(args[3]), int(args[4]))

        elif cmd == "list":
            self._cmd_list()

        elif cmd == "show":
            # python app.py show 국어 3  → 차시 목록 보기
            if len(args) < 3:
                print("사용법: python app.py show [교과] [학년]")
                return
            self._cmd_show(args[1], int(args[2]))

        elif cmd == "search":
            # python app.py search 국어 3 덧셈
            if len(args) < 4:
                print("사용법: python app.py search [교과] [학년] [키워드]")
                return
            self._cmd_search(args[1], int(args[2]), args[3])

        elif cmd == "analyze":
            # python app.py analyze 국어 3 1 2
            if len(args) < 5:
                print("사용법: python app.py analyze [교과] [학년] [단원] [차시]")
                return
            self._cmd_analyze(args[1], int(args[2]), int(args[3]), int(args[4]))

        elif cmd == "edit":
            # python app.py edit 국어 3
            if len(args) < 3:
                print("사용법: python app.py edit [교과] [학년]")
                return
            self._cmd_edit(args[1], int(args[2]))

        elif cmd == "help" or cmd == "-h" or cmd == "--help":
            self._print_help()

        else:
            # 자유 형식 입력: "국어 3학년 1단원 2차시"
            self._parse_free_input(" ".join(args))

    def _interactive_mode(self):
        """대화형 모드"""
        self._print_help_short()

        while True:
            try:
                print()
                user_input = input("📖 명령 입력 > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["q", "quit", "exit", "종료"]:
                    print("👋 종료합니다.")
                    break
                self._parse_free_input(user_input)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 종료합니다.")
                break

    def _parse_free_input(self, text: str):
        """자유 형식 입력 파싱"""
        text = text.strip()

        # 명령 처리
        if text.startswith("추가 ") or text.startswith("add "):
            parts = text.split()
            if len(parts) >= 4:
                self._cmd_add(parts[1], parts[2], int(parts[3]))
                return

        if text in ["목록", "list", "ls"]:
            self._cmd_list()
            return

        if text in ["도움말", "help", "?"]:
            self._print_help()
            return

        # 차시 추출: "국어 3학년 1단원 2차시" 또는 "국어 3 1 2"
        lesson_info = self._parse_lesson_query(text)
        if lesson_info:
            subject, grade, unit, lesson = lesson_info
            self._cmd_get(subject, grade, unit, lesson)
            return

        # show 처리: "국어 3" 또는 "국어 3학년 목록"
        show_info = self._parse_show_query(text)
        if show_info:
            subject, grade = show_info
            self._cmd_show(subject, grade)
            return

        print(f"  ❓ 이해하지 못했습니다: '{text}'")
        print(f"  예시: 국어 3학년 1단원 2차시")
        print(f"  예시: 국어 3 1 2")
        print(f"  예시: 목록  (등록된 교과서 보기)")
        self._print_help_short()

    def _parse_lesson_query(self, text: str):
        """차시 쿼리 파싱"""
        # 패턴 1: "국어 3학년 1단원 2차시"
        m = re.search(
            r'([가-힣]+)\s*(\d+)\s*학년\s*(\d+)\s*단원\s*(\d+)\s*차시',
            text
        )
        if m:
            return m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))

        # 패턴 2: "국어 3 1 2" (숫자만)
        m = re.match(r'([가-힣]+)\s+(\d+)\s+(\d+)\s+(\d+)$', text)
        if m:
            return m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))

        # 패턴 3: "국어3 1단원 2차시"
        m = re.search(
            r'([가-힣]+)(\d+)\s*[,\s]\s*(\d+)\s*단원\s*(\d+)\s*차시',
            text
        )
        if m:
            return m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))

        return None

    def _parse_show_query(self, text: str):
        """교과서 목차 조회 파싱"""
        m = re.search(r'([가-힣]+)\s*(\d+)\s*학년', text)
        if m:
            return m.group(1), int(m.group(2))
        m = re.match(r'([가-힣]+)\s+(\d+)$', text)
        if m:
            return m.group(1), int(m.group(2))
        return None

    # ─── 명령 실행 ──────────────────────────────────────────

    def _cmd_add(self, pdf_path: str, subject: str, grade: int):
        """PDF 등록 및 인덱싱"""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            print(f"  ❌ 파일을 찾을 수 없습니다: {pdf_path}")
            return

        print(f"\n  📁 등록 중: {subject} {grade}학년 지도서")
        print(f"  📄 파일: {pdf_path.name}")

        # PDF 캐시에 등록
        cached_path = self.cache.register_pdf(subject, grade, pdf_path)
        print(f"  💾 캐시에 저장됨")

        # 인덱싱
        indexer = PDFIndexer(api_key=self.api_key)
        meta = indexer.index_pdf(str(cached_path), subject, grade)

        # 메타데이터 저장
        self.cache.save_meta(subject, grade, meta)

        # 결과 출력
        total_lessons = sum(len(u.get("lessons", [])) for u in meta.get("units", []))
        unit_count = len(meta.get("units", []))
        method = meta.get("method", "unknown")
        method_kr = {"bookmarks": "북마크", "pattern": "패턴 매칭", "ai": "AI 분석", "manual": "수동 입력"}.get(method, method)

        print(f"\n  ✅ 등록 완료!")
        print(f"  📊 {unit_count}개 단원 / {total_lessons}개 차시 ({method_kr})")
        print(f"\n  차시 목록 보기: python app.py show {subject} {grade}")
        print(f"  차시 추출하기: python app.py get {subject} {grade} [단원번호] [차시번호]")

    def _cmd_get(self, subject: str, grade: int, unit_no: int, lesson_no: int):
        """차시 추출"""
        subject = self.cache.normalize_subject(subject)

        if not self.cache.is_registered(subject, grade):
            print(f"\n  ❌ {subject} {grade}학년 지도서가 등록되지 않았습니다.")
            print(f"  등록: python app.py add [PDF파일] {subject} {grade}")
            return

        lesson = self.cache.find_lesson(subject, grade, unit_no, lesson_no)
        if not lesson:
            print(f"\n  ❌ {subject} {grade}학년 {unit_no}단원 {lesson_no}차시를 찾을 수 없습니다.")
            print(f"  차시 목록: python app.py show {subject} {grade}")
            return

        pdf_path = self.cache.get_pdf_path(subject, grade)
        if not pdf_path:
            print(f"\n  ❌ PDF 파일이 없습니다. 다시 등록해주세요.")
            return

        pages = lesson["pages"]
        print(f"\n  📖 {subject} {grade}학년 {unit_no}단원 {lesson_no}차시")
        print(f"  📌 {lesson['unit_title']} > {lesson['lesson_title']}")
        print(f"  📄 페이지 {pages[0]} ~ {pages[1]} ({pages[1]-pages[0]+1}페이지)")
        print(f"  🔄 추출 중...")

        output_path = self.extractor.extract_lesson(str(pdf_path), lesson)

        print(f"\n  ✅ 저장 완료!")
        print(f"  📂 {output_path}")

        # 수업 내용 분석 여부 묻기
        print()
        if self.api_key:
            analyze_it = input("  🤖 수업 내용 AI 요약을 볼까요? [Y/n]: ").strip().lower()
        else:
            analyze_it = input("  📋 차시 텍스트 추출 결과를 볼까요? [y/N]: ").strip().lower()
            analyze_it = "y" if analyze_it == "y" else "n"

        if analyze_it != "n":
            print()
            if self.api_key:
                print("  🤖 Claude가 수업 내용을 분석하고 있습니다...")
            result = self.analyzer.analyze(str(pdf_path), lesson)
            print("\n" + "═" * 55)
            print(result)
            print("═" * 55)

            # 분석 결과를 텍스트 파일로도 저장할지
            save_analysis = input("\n  분석 결과를 텍스트 파일로 저장할까요? [y/N]: ").strip().lower()
            if save_analysis == "y":
                txt_path = output_path.with_suffix(".txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"{subject} {grade}학년 {unit_no}단원 {lesson_no}차시\n")
                    f.write(f"{lesson['unit_title']} > {lesson['lesson_title']}\n")
                    f.write(f"페이지: {pages[0]}~{pages[1]}\n\n")
                    f.write(result)
                print(f"  💾 저장됨: {txt_path}")

        # PDF 열기
        open_it = input("\n  PDF 파일을 열까요? [Y/n]: ").strip().lower()
        if open_it != "n":
            self.extractor.open_file(output_path)

    def _cmd_list(self):
        """등록된 교과서 목록"""
        books = self.cache.list_registered()
        if not books:
            print("\n  📭 등록된 교과서가 없습니다.")
            print("  등록: python app.py add [PDF파일] [교과] [학년]")
            return

        print("\n  📚 등록된 교과서 목록")
        print("  " + "─" * 50)
        print(f"  {'교과':<8} {'학년':<6} {'단원수':<8} {'상태':<10}")
        print("  " + "─" * 50)
        for book in books:
            status = "✅ 인덱싱됨" if book.get("indexed") else "⚠️  미인덱싱"
            units = book.get("unit_count", "?")
            print(f"  {book['subject']:<8} {book['grade']}학년   {units:<8} {status}")
        print("  " + "─" * 50)

    def _cmd_show(self, subject: str, grade: int):
        """특정 교과서의 차시 목록"""
        subject = self.cache.normalize_subject(subject)
        meta = self.cache.load_meta(subject, grade)
        if not meta:
            print(f"\n  ❌ {subject} {grade}학년 인덱스가 없습니다.")
            print(f"  등록: python app.py add [PDF파일] {subject} {grade}")
            return

        method = meta.get("method", "")
        method_kr = {"bookmarks":"북마크","toc_page":"목차 페이지","body_headers":"본문 헤더",
                     "ai":"AI 분석","manual":"수동 입력"}.get(method, method)
        total = meta.get("total_pages", "?")
        print(f"\n  📚 {subject} {grade}학년 차시 목록  [{method_kr} / 총 {total}페이지]")

        for unit in meta.get("units", []):
            print(f"\n  【{unit['unit_no']}단원】 {unit['title']}")
            for lesson in unit.get("lessons", []):
                pages = lesson.get("pages", [0, 0])
                no    = lesson.get("lesson_no", "?")
                no_end = lesson.get("lesson_no_end", no)
                if no == no_end:
                    no_str = f"{no:>2}차시"
                else:
                    no_str = f"{no}~{no_end}차시"
                print(f"    {no_str:<8}  {lesson['title']:<35}  p.{pages[0]}~{pages[1]}")

    def _cmd_search(self, subject: str, grade: int, keyword: str):
        """키워드로 차시 검색"""
        subject = self.cache.normalize_subject(subject)
        results = self.cache.search_lessons(subject, grade, keyword)
        if not results:
            print(f"\n  🔍 '{keyword}' 검색 결과 없음")
            return

        print(f"\n  🔍 '{keyword}' 검색 결과: {len(results)}건")
        for r in results:
            pages = r.get("pages", [0, 0])
            print(f"  {r['unit_no']}단원 {r['lesson_no']}차시  {r['lesson_title']}  (p.{pages[0]}~{pages[1]})")

    def _cmd_analyze(self, subject: str, grade: int, unit_no: int, lesson_no: int):
        """차시 내용 AI 분석 (PDF 추출 없이 바로 분석)"""
        subject = self.cache.normalize_subject(subject)

        if not self.cache.is_registered(subject, grade):
            print(f"\n  ❌ {subject} {grade}학년 지도서가 등록되지 않았습니다.")
            return

        lesson = self.cache.find_lesson(subject, grade, unit_no, lesson_no)
        if not lesson:
            print(f"\n  ❌ {subject} {grade}학년 {unit_no}단원 {lesson_no}차시를 찾을 수 없습니다.")
            return

        pdf_path = self.cache.get_pdf_path(subject, grade)
        pages = lesson["pages"]

        print(f"\n  📖 {subject} {grade}학년 {unit_no}단원 {lesson_no}차시 분석")
        print(f"  📌 {lesson['unit_title']} > {lesson['lesson_title']}")
        print(f"  📄 페이지 {pages[0]}~{pages[1]}")

        if self.api_key:
            print(f"\n  🤖 Claude가 수업 내용을 분석 중입니다...")
        else:
            print(f"\n  📋 텍스트 추출 중...")

        result = self.analyzer.analyze(str(pdf_path), lesson)

        print("\n" + "═" * 55)
        print(result)
        print("═" * 55)

        save = input("\n  텍스트 파일로 저장할까요? [y/N]: ").strip().lower()
        if save == "y":
            out_dir = Path(__file__).parent / "output"
            out_dir.mkdir(exist_ok=True)
            fname = f"{subject}{grade}학년_{unit_no}단원_{lesson_no}차시_분석.txt"
            fpath = out_dir / fname
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(f"{subject} {grade}학년 {unit_no}단원 {lesson_no}차시\n")
                f.write(f"{lesson['unit_title']} > {lesson['lesson_title']}\n\n")
                f.write(result)
            print(f"  💾 저장됨: {fpath}")

    def _cmd_edit(self, subject: str, grade: int):
        """인덱스 수동 편집"""
        import json
        subject = self.cache.normalize_subject(subject)
        meta = self.cache.load_meta(subject, grade)
        if not meta:
            print(f"  ❌ {subject} {grade}학년 인덱스 없음")
            return

        cache_dir = self.cache.get_cache_dir(subject, grade)
        meta_path = cache_dir / "meta.json"
        print(f"  📝 인덱스 파일: {meta_path}")
        print(f"  직접 편집하려면 위 파일을 텍스트 편집기로 여세요.")

        # 간단한 페이지 범위 수정
        print(f"\n  빠른 수정 - 차시 페이지 범위 변경")
        print(f"  형식: [단원번호] [차시번호] [시작페이지] [끝페이지]")
        print(f"  (비워두면 종료)")

        while True:
            inp = input("  입력: ").strip()
            if not inp:
                break
            parts = inp.split()
            if len(parts) == 4:
                try:
                    u, l, s, e = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
                    for unit in meta["units"]:
                        if unit["unit_no"] == u:
                            for lesson in unit["lessons"]:
                                if lesson["lesson_no"] == l:
                                    lesson["pages"] = [s, e]
                                    print(f"  ✅ {u}단원 {l}차시 → p.{s}~{e}")
                except:
                    print("  ❌ 형식 오류")

        self.cache.save_meta(subject, grade, meta)
        print(f"  💾 저장됨")

    def _print_help(self):
        print("""
  ═══════════════════════════════════════════════
  📚 교사용 지도서 PDF 관리 시스템 - 도움말
  ═══════════════════════════════════════════════

  ▶ PDF 등록 (최초 1회)
    python app.py add 국어지도서.pdf 국어 3
    python app.py add 수학지도서.pdf 수학 4

  ▶ 차시 추출 (매일 사용)
    python app.py get 국어 3 1 2      ← 국어 3학년 1단원 2차시 (추출 + 선택적 분석)
    python app.py get 수학 4 3 1      ← 수학 4학년 3단원 1차시

  ▶ 수업 내용 AI 요약 (API 키 필요)
    python app.py analyze 국어 3 1 2  ← 학습목표·수업흐름·핵심내용 자동 정리

  ▶ 자유 형식 입력 (대화형 모드)
    python app.py
    > 국어 3학년 1단원 2차시
    > 수학 4 3 1

  ▶ 목록/조회
    python app.py list                ← 등록된 교과서 목록
    python app.py show 국어 3         ← 차시 목록 보기
    python app.py search 국어 3 받아올림  ← 키워드 검색

  ▶ 수정
    python app.py edit 국어 3         ← 페이지 범위 수정

  ▶ 지원 교과: 국어, 수학, 과학, 사회, 영어, 도덕, 음악, 미술, 체육, 실과
  ═══════════════════════════════════════════════
""")

    def _print_help_short(self):
        print("  💡 사용법: '교과 학년 단원 차시'  예) 국어 3 1 2")
        print("  💡 목록보기: list    도움말: help    종료: q")
