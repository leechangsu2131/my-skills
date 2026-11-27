"""scripts/apply_annual_plan.py 시험 (S1): 연간지도계획 글에서 차시 목록 뽑기, groups.json 에 제목·차시 입히기.

    python -m unittest discover -s tests      (splitter 폴더에서)

PDF 라이브러리(fitz)는 가짜로 바꿔서, 계획 글을 직접 넣어 본다. 임시 폴더만 쓰고 실제 지도서·학생 정보는 쓰지 않는다.
소스(apply_annual_plan.py)는 고치지 않는다.
"""
from __future__ import annotations

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

from scripts import apply_annual_plan as plan  # noqa: E402


class FakePage:
    def __init__(self, text):
        self.text = text

    def get_text(self):
        return self.text


def with_plan_text(*page_texts):
    """plan_entries 가 읽을 PDF 를 쪽별 글로 대신한다."""
    return patch.object(plan.fitz, "open", create=True, return_value=[FakePage(t) for t in page_texts])


def entries(*page_texts):
    with with_plan_text(*page_texts):
        return plan.plan_entries(Path("계획.pdf"))


class PlanEntriesTests(unittest.TestCase):
    def test_single_lesson_entry(self):
        self.assertEqual(entries("1 사회 변화와 다양한 문화 10~13"),
                         [{"from": 1, "to": 1, "title": "사회 변화와 다양한 문화", "textbook_pages": "10~13"}])

    def test_range_lesson_entry_repeated_number_is_one_entry(self):
        # "5~6 5~6 제목 40~45": 차시 번호가 두 번 적힌 표
        self.assertEqual(entries("5~6 5~6 직업의 세계 40~45"),
                         [{"from": 5, "to": 6, "title": "직업의 세계", "textbook_pages": "40~45"}])

    def test_entries_are_sorted_by_lesson_even_if_text_order_differs(self):
        got = entries("3 다 제목 20~22 1 가 제목 10~11 2 나 제목 12~19")
        self.assertEqual([e["from"] for e in got], [1, 2, 3])

    def test_text_is_joined_across_pages_and_spaces_normalized(self):
        got = entries("1 가   제목\n이어짐", " 10~11  2 나 제목 12~13")
        self.assertEqual([(e["from"], e["title"]) for e in got], [(1, "가 제목 이어짐"), (2, "나 제목")])

    def test_control_characters_are_blanked(self):
        got = entries("1 가\x00나 제목​다 10~11")
        self.assertEqual(got[0]["title"], "가 나 제목 다")

    def test_duplicate_lesson_number_keeps_first(self):
        got = entries("1 가 제목 10~11 2 나 제목 12~13 2 중복 제목 14~15")
        self.assertEqual([(e["from"], e["title"]) for e in got], [(1, "가 제목"), (2, "나 제목")])

    def test_reversed_range_is_skipped(self):
        got = entries("4~3 역전 30~31 7 정상 32~33")
        self.assertEqual([e["from"] for e in got], [7])

    def test_extra_heading_after_title_is_cut(self):
        got = entries("3 다 제목 할 수 있어요 20~22 4 라 제목 풍덩 사회 속으로 23~24")
        self.assertEqual([e["title"] for e in got], ["다 제목", "라 제목"])

    def test_title_starting_with_header_words_is_skipped(self):
        got = entries("1 연간 지도 계획 안내 2~3 2 나 제목 12~13")
        self.assertEqual([e["from"] for e in got], [2])

    def test_numbers_glued_to_other_digits_are_not_entries(self):
        self.assertEqual(entries("2026.11 가 제목 10~11"), [])

    def test_no_entries_in_empty_or_unrelated_text(self):
        self.assertEqual(entries(""), [])
        self.assertEqual(entries("표지 목차 머리말"), [])


class MainTests(unittest.TestCase):
    PLAN = "1 가 제목 10~11 2~3 2~3 나 제목 12~15 4 다 제목 16~17 5 라 제목 18~19"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.groups = Path(self.tmp.name) / "groups.json"
        self.backup = self.groups.with_name("groups.orig.json")

    def write_groups(self, groups):
        self.groups.write_text(json.dumps({"groups": groups, "extra": "그대로"}, ensure_ascii=False), encoding="utf-8")

    def run_main(self, lessons="1-4", dry=False, text=None):
        argv = ["apply_annual_plan.py", "--groups", str(self.groups), "--plan", "계획.pdf",
                "--lessons", lessons, "--unit", "1. 사회 변화"]
        if dry:
            argv.append("--dry-run")
        with patch.object(sys, "argv", argv), with_plan_text(text or self.PLAN):
            plan.main()

    def three_groups(self):
        return [
            {"start_page": 3, "end_page": 4, "title": "깨진 제목1", "detected_level": "lesson"},
            {"start_page": 5, "end_page": 8, "title": "깨진 제목2", "detected_level": "lesson"},
            {"start_page": 9, "end_page": 10, "title": "깨진 제목3", "detected_level": "lesson"},
        ]

    def test_pairs_in_order_and_fills_titles_and_lesson_info(self):
        self.write_groups(self.three_groups())
        self.run_main()
        data = json.loads(self.groups.read_text(encoding="utf-8"))
        g1, g2, g3 = data["groups"]
        self.assertEqual((g1["title"], g1["lesson_span"], g1["lesson_range"], g1["textbook_pages"]),
                         ("가 제목", 1, "1", "10~11"))
        self.assertEqual((g2["title"], g2["lesson_span"], g2["lesson_range"], g2["textbook_pages"]),
                         ("나 제목", 2, "2~3", "12~15"))
        self.assertEqual(g3["lesson_range"], "4")
        self.assertEqual(g2["source_title"], "깨진 제목2")          # 원래 제목은 남긴다
        self.assertTrue(all(g["parent_unit_title"] == "1. 사회 변화" for g in data["groups"]))
        self.assertEqual(g2["start_page"], 5)                       # 쪽 범위는 안 건드림
        self.assertEqual(data["extra"], "그대로")                    # 다른 키도 그대로

    def test_dry_run_changes_nothing(self):
        self.write_groups(self.three_groups())
        before = self.groups.read_text(encoding="utf-8")
        self.run_main(dry=True)
        self.assertEqual(self.groups.read_text(encoding="utf-8"), before)
        self.assertFalse(self.backup.exists())

    def test_original_is_backed_up_once_and_never_overwritten(self):
        self.write_groups(self.three_groups())
        original = self.groups.read_text(encoding="utf-8")
        self.run_main()
        self.assertEqual(self.backup.read_text(encoding="utf-8"), original)
        self.run_main()                                              # 두 번째 실행
        self.assertEqual(self.backup.read_text(encoding="utf-8"), original)

    def test_second_run_overwrites_source_title_with_first_run_title(self):
        # 지금 동작(참고용): 다시 돌리면 source_title 이 "처음 깨진 제목" 이 아니라 첫 실행에서 넣은 제목이 된다.
        # 진짜 원본은 groups.orig.json 에만 남는다. 고치게 되면 이 시험을 바꾼다.
        self.write_groups(self.three_groups())
        self.run_main()
        self.run_main()
        data = json.loads(self.groups.read_text(encoding="utf-8"))
        self.assertEqual(data["groups"][0]["source_title"], "가 제목")
        orig = json.loads(self.backup.read_text(encoding="utf-8"))
        self.assertEqual(orig["groups"][0]["title"], "깨진 제목1")

    def test_count_mismatch_stops_without_touching_files(self):
        self.write_groups(self.three_groups()[:2])                   # 계획 3개 vs 묶음 2개
        before = self.groups.read_text(encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            self.run_main()
        self.assertIn("개수가 달라", str(ctx.exception))
        self.assertEqual(self.groups.read_text(encoding="utf-8"), before)
        self.assertFalse(self.backup.exists())

    def test_section_and_plan_groups_are_not_counted(self):
        groups = self.three_groups()
        groups.insert(0, {"start_page": 1, "end_page": 2, "title": "단원 개관", "detected_level": "Section"})
        groups.append({"start_page": 11, "end_page": 12, "title": "연간계획", "detected_level": "PLAN"})
        self.write_groups(groups)
        self.run_main()
        data = json.loads(self.groups.read_text(encoding="utf-8"))
        self.assertNotIn("lesson_span", data["groups"][0])           # 개관은 그대로
        self.assertNotIn("lesson_span", data["groups"][-1])
        self.assertEqual(data["groups"][1]["title"], "가 제목")

    def test_lessons_range_filters_plan_entries(self):
        self.write_groups(self.three_groups()[:2])
        self.run_main(lessons="2-4")                                 # 2~3차시, 4차시만 → 묶음 2개와 같음
        data = json.loads(self.groups.read_text(encoding="utf-8"))
        self.assertEqual([g["title"] for g in data["groups"]], ["나 제목", "다 제목"])

    def test_groups_without_level_are_counted(self):
        groups = [{"start_page": 1, "end_page": 2}, {"start_page": 3, "end_page": 4},
                  {"start_page": 5, "end_page": 6}]
        self.write_groups(groups)
        self.run_main()
        data = json.loads(self.groups.read_text(encoding="utf-8"))
        self.assertEqual(data["groups"][0]["source_title"], "")      # 제목이 없던 묶음도 빈 글로 남김


if __name__ == "__main__":
    unittest.main()
