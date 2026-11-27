"""scripts/split_by_lesson_headers.py 시험 (S1): 쪽 머리의 '12차시 3' 표시로 차시 시작 쪽 찾기, 계획 표에서 차시 제목 읽기,
저장 흐름(groups.json·pdf_splits 파일 이름·단원 개관·미리보기).

    python -m unittest discover -s tests      (splitter 폴더에서)

PDF 라이브러리(fitz)는 가짜 문서로 바꿔서, 쪽별 글을 직접 넣어 본다. 임시 폴더만 쓰고 실제 지도서·학생 정보는 쓰지 않는다.
소스(split_by_lesson_headers.py)는 고치지 않는다.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import fitz  # noqa: F401
except ImportError:  # 이 환경처럼 PyMuPDF 가 없을 때만 가짜로 대신한다
    sys.modules["fitz"] = types.ModuleType("fitz")

from scripts import split_by_lesson_headers as sp  # noqa: E402


class FakePage:
    def __init__(self, text):
        self.text = text

    def get_text(self):
        return self.text


class FakeDoc:
    def __init__(self, pages):
        self.pages = list(pages)
        self.page_count = len(self.pages)
        self.closed = False

    def __getitem__(self, i):
        return FakePage(self.pages[i])

    def close(self):
        self.closed = True


class FakePart:
    """fitz.open() (인자 없음) 로 만든 새 PDF — 넣은 쪽을 기록하고 save 하면 파일로 남긴다."""

    def __init__(self):
        self.inserted = []

    def insert_pdf(self, doc, from_page, to_page):
        self.inserted.append((from_page, to_page))

    def save(self, path):
        Path(path).write_text(json.dumps(self.inserted), encoding="utf-8")

    def close(self):
        pass


def fake_fitz(docs):
    """파일 이름 → 쪽 글 목록."""
    def open_(arg=None):
        return FakePart() if arg is None else FakeDoc(docs[Path(arg).name])
    return types.SimpleNamespace(open=open_)


def starts(*pages):
    return sp.lesson_starts(FakeDoc(pages))


class LessonStartsTests(unittest.TestCase):
    def test_total_then_number_form(self):  # "12차시 3"
        total, found = starts("개관", "12차시 1 도입", "내용", "12차시 2 전개", "12차시 3 정리")
        self.assertEqual((total, found), (12, {1: (1, 1), 2: (3, 1), 3: (4, 1)}))

    def test_range_form_covers_several_lessons(self):  # "2~3 9차시"
        total, found = starts("2~3 9차시 활동", "9차시 4 다음")
        self.assertEqual((total, found), (9, {2: (0, 2), 4: (1, 1)}))

    def test_number_then_total_form(self):  # "10 12차시"
        self.assertEqual(starts("10 12차시 정리"), (12, {10: (0, 1)}))

    def test_project_header_found_a_little_later_in_page(self):
        self.assertEqual(starts("프로젝트 활동 4차시 1 도입"), (4, {1: (0, 1)}))

    def test_lesson_inside_a_covered_range_and_duplicates_are_ignored(self):
        total, found = starts("2~3 9차시 가", "9차시 3 겹침", "9차시 2 또", "9차시 4 나")
        self.assertEqual(found, {2: (0, 2), 4: (3, 1)})

    def test_number_larger_than_total_is_ignored(self):
        self.assertEqual(starts("12차시 13 이상함"), (0, {}))

    def test_most_common_total_wins_and_larger_numbers_are_dropped(self):
        # 9차시로 적힌 쪽이 2개, 12차시로 적힌 쪽이 1개 → 전체 9차시. 10 은 버려진다.
        total, found = starts("2~3 9차시 가", "10 12차시 나", "9차시 4 다")
        self.assertEqual((total, found), (9, {2: (0, 2), 4: (2, 1)}))

    def test_no_headers_or_no_pages(self):
        self.assertEqual(starts("표지", "본문"), (0, {}))
        self.assertEqual(starts(), (0, {}))

    def test_control_characters_and_line_breaks_are_normalized(self):
        self.assertEqual(starts("12차시\x00\n 1  도입"), (12, {1: (0, 1)}))


class TitleTests(unittest.TestCase):
    def plan(self, text, first=1):
        return sp.plan_titles(FakeDoc([text, "본문 쪽"]), first)

    def test_bullet_style_plan_rows(self):
        got = self.plan("• 1차시 분수 알아보기 『수학』 • 2차시 크기 비교")
        self.assertEqual(got, {1: "분수 알아보기", 2: "크기 비교"})

    def test_table_style_plan_rows_with_symbols_fixed(self):
        got = self.plan("1차시 수 10~11쪽 익 8~9쪽 곱셈 Ö 나눗셈 2~3차시 수 12쪽 두 번째")
        self.assertEqual(got, {1: "곱셈 ÷ 나눗셈", 2: "두 번째"})

    def test_only_pages_before_first_lesson_are_read(self):
        doc = FakeDoc(["• 1차시 가 제목", "• 2차시 본문 속 글"])
        self.assertEqual(sp.plan_titles(doc, 1), {1: "가 제목"})

    def test_no_plan_gives_empty_dict(self):
        self.assertEqual(self.plan("표지"), {})

    def test_clean_title_fixes_spacing_symbols_and_length(self):
        self.assertEqual(sp.clean_title("  자 리  수 볼 까요  "), "자리 수 볼까요")
        self.assertEqual(sp.clean_title("몇십 몇 알아볼 까요"), "몇십몇 알아볼까요")
        self.assertEqual(sp.clean_title("2_3 Ö 4"), "2×3 ÷ 4")
        self.assertEqual(len(sp.clean_title("가" * 80)), 60)

    def test_safe_replaces_forbidden_characters_and_cuts_at_50(self):
        self.assertEqual(sp.safe('a/b:c*d?'), "a_b_c_d_")
        self.assertEqual(len(sp.safe("가" * 80)), 50)


class MainTests(unittest.TestCase):
    UNIT1 = ["표지", "• 1차시 분수 • 2차시 크기 비교", "12차시 1 도입", "내용", "12차시 2 전개", "마무리"]
    UNIT2 = ["10차시 1 시작", "10차시 2 끝"]            # 개관 없음(첫 쪽부터 차시)
    NOHDR = ["머리 표시가 없는 PDF", "본문"]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "수학 3-2"
        self.folder.mkdir()

    def run_main(self, docs, *extra):
        for name in docs:
            (self.folder / name).write_bytes(b"%PDF-fake")
        argv = ["split_by_lesson_headers.py", "--dir", str(self.folder), "--glob", "*단원.pdf", *extra]
        out = io.StringIO()
        with patch.object(sys, "argv", argv), patch.object(sp, "fitz", fake_fitz(docs)), contextlib.redirect_stdout(out):
            sp.main()
        return out.getvalue()

    def groups(self):
        return json.loads((self.folder / "groups.json").read_text(encoding="utf-8"))["groups"]

    def test_dry_run_prints_but_writes_nothing(self):
        out = self.run_main({"지도서_1단원.pdf": self.UNIT1}, "--dry-run")
        self.assertIn("[지도서_1단원] 지도서_1단원.pdf: 12차시, 빠짐", out)   # 단원 이름을 안 주면 파일 이름
        self.assertIn("[미리보기]", out)
        self.assertFalse((self.folder / "groups.json").exists())
        self.assertFalse((self.folder / "pdf_splits").exists())

    def test_save_writes_groups_with_overview_then_lessons(self):
        self.run_main({"지도서_1단원.pdf": self.UNIT1}, "--units", "분수")
        g = self.groups()
        self.assertEqual([x["title"] for x in g], ["단원 개관", "분수", "크기 비교"])
        self.assertEqual([x["detected_level"] for x in g], ["plan", "lesson", "lesson"])
        self.assertEqual([(x["start_page"], x["end_page"]) for x in g], [(1, 2), (3, 4), (5, 6)])   # 1부터, 마지막은 끝 쪽까지
        self.assertEqual([x["lesson_no"] for x in g], [None, 1, 2])
        self.assertEqual(g[0]["lesson_span"], None)
        self.assertEqual(g[1]["parent_unit_title"], "1. 분수")
        self.assertEqual([x["index"] for x in g], [1, 2, 3])
        self.assertTrue(all(x["method"] == "lesson_header" for x in g))

    def test_pdf_splits_file_names_and_pages(self):
        self.run_main({"지도서_1단원.pdf": self.UNIT1}, "--units", "분수")
        files = sorted(p.name for p in (self.folder / "pdf_splits").glob("*.pdf"))
        self.assertEqual(files, [
            "[수학 3-2]_subunit_01_1. 분수_단원 개관_p1-2.pdf",
            "[수학 3-2]_subunit_02_1. 분수_분수_p3-4.pdf",
            "[수학 3-2]_subunit_03_1. 분수_크기 비교_p5-6.pdf",
        ])
        first = json.loads((self.folder / "pdf_splits" / files[0]).read_text(encoding="utf-8"))
        self.assertEqual(first, [[0, 1]])                           # 0부터 쪽 번호로 잘랐다

    def test_unit_without_overview_pages_has_no_plan_group(self):
        self.run_main({"지도서_1단원.pdf": self.UNIT2})
        g = self.groups()
        self.assertEqual([x["detected_level"] for x in g], ["lesson", "lesson"])
        self.assertEqual([x["title"] for x in g], ["1차시", "2차시"])    # 계획 표가 없으면 'N차시'
        self.assertEqual(g[0]["parent_unit_title"], "지도서_1단원")        # 단원 이름을 안 주면 파일 이름

    def test_files_are_ordered_by_unit_number_not_alphabetically(self):
        docs = {"지도서_10단원.pdf": self.UNIT2, "지도서_2단원.pdf": self.UNIT2, "지도서_1단원.pdf": self.UNIT2}
        self.run_main(docs, "--units", "가,나,다")
        self.assertEqual([x["source_pdf"] for x in self.groups()][::2],
                         ["지도서_1단원.pdf", "지도서_2단원.pdf", "지도서_10단원.pdf"])
        self.assertEqual([x["index"] for x in self.groups()], [1, 2, 3, 4, 5, 6])   # 단원이 바뀌어도 번호는 이어진다

    def test_pdf_without_headers_is_skipped_but_still_counts_as_a_unit_number(self):
        out = self.run_main({"지도서_1단원.pdf": self.NOHDR, "지도서_2단원.pdf": self.UNIT2}, "--units", "가,나")
        self.assertIn("[건너뜀] 지도서_1단원.pdf", out)
        self.assertEqual({x["source_pdf"] for x in self.groups()}, {"지도서_2단원.pdf"})
        self.assertEqual(self.groups()[0]["parent_unit_title"], "2. 나")      # 건너뛴 파일도 단원 번호를 차지한다

    def test_missing_lessons_are_reported(self):
        out = self.run_main({"지도서_1단원.pdf": ["12차시 1 a", "12차시 2 b"]})
        self.assertIn("12차시, 빠짐 [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]", out)

    def test_range_lesson_span_is_recorded(self):
        self.run_main({"지도서_1단원.pdf": ["2~3 9차시 가", "9차시 4 나"]})
        g = self.groups()
        self.assertEqual([(x["lesson_no"], x["lesson_span"]) for x in g], [(2, 2), (4, 1)])


if __name__ == "__main__":
    unittest.main()
