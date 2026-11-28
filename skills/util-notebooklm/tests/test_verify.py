"""답의 인용 대조(verify, ISSUE-004) 시험 — 가짜 쪽 글만 쓰고 PyMuPDF·Gemini·네트워크는 쓰지 않는다.

    python -m unittest discover -s tests      (util-notebooklm 폴더에서)
"""
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("MY_SKILLS_DATA_DIR", tempfile.mkdtemp(prefix="nlm_verify_data_"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import nlm  # noqa: E402

PAGES = [
    "모둠 활동은 네 명이 한 모둠을 이룬다.",
    "분수의 덧셈은 통분한 뒤\n분자끼리 더한다. 마지막에 약분한다.",
    "Fraction Addition needs common denominators.",
]


def status(answer, pages=PAGES):
    return [r["status"] for r in nlm.verify_quotes(answer, pages)]


class QuoteLinesTests(unittest.TestCase):
    def test_takes_lines_with_page_marks_and_strips_bullets_and_quotes(self):
        rows = nlm.quote_lines('- [p.1] "모둠 활동은 네 명이다."\n[p.2-3] 분수의 덧셈')
        self.assertEqual(rows, [([1], "모둠 활동은 네 명이다."), ([2, 3], "분수의 덧셈")])

    def test_skips_summary_line_none_and_header_comment(self):
        ans = "<!-- 원본: a [p.1] | 찾을 내용: b -->\n없음\n쪽: 1, 2\n쪽 : [p.3]"
        self.assertEqual(nlm.quote_lines(ans), [])

    def test_skips_marks_without_text(self):
        self.assertEqual(nlm.quote_lines("[p.4]\n- [p.5] -"), [])

    def test_lines_without_marks_are_not_quotes(self):
        self.assertEqual(nlm.quote_lines("그냥 설명하는 줄입니다 길게 길게"), [])

    def test_pdf_file_page_phrase_counts_as_mark(self):
        self.assertEqual(nlm.quote_lines("PDF 파일 2쪽 분수의 덧셈은 통분한다")[0][0], [2])


class FragmentTests(unittest.TestCase):
    def test_ellipsis_splits_and_short_fragments_drop(self):
        self.assertEqual(nlm.quote_fragments("분수의 덧셈은 통분한 뒤 … 분자끼리 더한다 마지막에 … 끝"),
                         [nlm.squash("분수의 덧셈은 통분한 뒤"), nlm.squash("분자끼리 더한다 마지막에")])
        self.assertEqual(nlm.quote_fragments("일곱글자만 … 끝"), [])  # 8글자(정리 후) 미만은 뺌

    def test_three_dots_and_jungryak(self):
        self.assertEqual(len(nlm.quote_fragments("앞부분 문장이 이렇게 길다... 뒷부분 문장도 이렇게 길다")), 2)
        self.assertEqual(len(nlm.quote_fragments("앞부분 문장이 이렇게 길다 [중략] 뒷부분 문장도 이렇게 길다")), 2)

    def test_too_short_gives_no_fragments(self):
        self.assertEqual(nlm.quote_fragments("짧음"), [])

    def test_squash_ignores_spaces_punctuation_and_case(self):
        self.assertEqual(nlm.squash("A b, “C”.​ 가-나"), "abc가나")


class VerifyTests(unittest.TestCase):
    def test_exact_quote_on_cited_page_is_ok(self):
        self.assertEqual(status("[p.1] 모둠 활동은 네 명이 한 모둠을 이룬다."), ["ok"])

    def test_line_breaks_spaces_and_quotes_do_not_matter(self):
        self.assertEqual(status('[p.2] "분수의 덧셈은  통분한 뒤 분자끼리 더한다."'), ["ok"])

    def test_english_case_insensitive(self):
        self.assertEqual(status("[p.3] fraction addition NEEDS common denominators"), ["ok"])

    def test_quote_on_other_page_reports_where(self):
        r = nlm.verify_quotes("[p.1] 분수의 덧셈은 통분한 뒤 분자끼리 더한다.", PAGES)[0]
        self.assertEqual((r["status"], r["found"]), ("elsewhere", [2]))

    def test_other_page_search_includes_the_first_page(self):
        r = nlm.verify_quotes("[p.2] 모둠 활동은 네 명이 한 모둠을 이룬다.", PAGES)[0]
        self.assertEqual((r["status"], r["found"]), ("elsewhere", [1]))

    def test_invented_quote_is_missing(self):
        self.assertEqual(status("[p.2] 소수의 곱셈은 자연수처럼 계산한다."), ["missing"])

    def test_page_range_accepts_quote_on_any_page_in_range(self):
        self.assertEqual(status("[p.1-2] 분수의 덧셈은 통분한 뒤 분자끼리 더한다."), ["ok"])

    def test_every_fragment_must_be_found_on_cited_pages(self):
        self.assertEqual(status("[p.2] 분수의 덧셈은 통분한 뒤 … 분자끼리 더한다"), ["ok"])
        self.assertEqual(status("[p.2] 분수의 덧셈은 통분한 뒤 … 소수의 곱셈은 어렵다"), ["missing"])

    def test_page_number_beyond_pdf_is_out_of_range_even_if_text_exists(self):
        self.assertEqual(status("[p.9] 분수의 덧셈은 통분한 뒤 분자끼리 더한다."), ["out_of_range"])

    def test_partly_valid_range_still_checks_the_valid_pages(self):
        self.assertEqual(status("[p.2-9] 분수의 덧셈은 통분한 뒤 분자끼리 더한다."), ["ok"])

    def test_short_quote_not_judged(self):
        self.assertEqual(status("[p.1] 모둠 활동"), ["short"])

    def test_empty_answer_and_none_answer(self):
        self.assertEqual(nlm.verify_quotes("", PAGES), [])
        self.assertEqual(nlm.verify_quotes("없음", PAGES), [])

    def test_does_not_change_pages(self):
        pages = list(PAGES)
        nlm.verify_quotes("[p.1] 모둠 활동은 네 명이 한 모둠을 이룬다.", pages)
        self.assertEqual(pages, PAGES)


class ReportTests(unittest.TestCase):
    def test_no_quotes_message(self):
        self.assertIn("대조할 인용", nlm.verify_report([]))

    def test_counts_and_warning_lines(self):
        ans = ("[p.1] 모둠 활동은 네 명이 한 모둠을 이룬다.\n"
               "[p.1] 분수의 덧셈은 통분한 뒤 분자끼리 더한다.\n"
               "[p.2] 소수의 곱셈은 자연수처럼 계산한다.\n"
               "[p.9] 없는 쪽을 가리키는 긴 문장입니다 정말로\n"
               "[p.2] 짧음")
        text = nlm.verify_report(nlm.verify_quotes(ans, PAGES))
        self.assertIn("인용 5개 — 맞음 1 · 다른 쪽에 있음 1 · 원문에 없음 1 · 대조 안 함(너무 짧음) 1 · 없는 쪽 1", text)
        self.assertIn("⚠ 쪽이 달라요 [1] → 실제 2쪽", text)
        self.assertIn("⚠ 원문에서 못 찾음 [2]", text)
        self.assertIn("⚠ PDF 에 없는 쪽 [9]", text)

    def test_long_quote_is_cut_in_report(self):
        long = "소수의 곱셈은 " + "아주 " * 40
        self.assertIn("…", nlm.verify_report(nlm.verify_quotes(f"[p.2] {long}", PAGES)))


class FakeDoc:
    def __init__(self, texts):
        self._t = texts
        self.page_count = len(texts)

    def __getitem__(self, i):
        return type("P", (), {"get_text": lambda s, t=self._t[i]: t})()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class CmdVerifyTests(unittest.TestCase):
    def run_cmd(self, answer):
        tmp = pathlib.Path(tempfile.mkdtemp())
        md = tmp / "답.md"
        md.write_text(answer, encoding="utf-8")
        fake = type("F", (), {"open": staticmethod(lambda path: FakeDoc(PAGES))})
        args = type("A", (), {"pdf": str(tmp / "x.pdf"), "answer": str(md)})
        with patch.object(nlm, "fitz", lambda: fake):
            nlm.cmd_verify(args)

    def test_all_ok_exits_normally(self):
        self.run_cmd("[p.1] 모둠 활동은 네 명이 한 모둠을 이룬다.")

    def test_wrong_page_only_is_a_warning_not_failure(self):
        self.run_cmd("[p.1] 분수의 덧셈은 통분한 뒤 분자끼리 더한다.")

    def test_invented_quote_exits_with_code_1(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_cmd("[p.2] 소수의 곱셈은 자연수처럼 계산한다.")
        self.assertEqual(ctx.exception.code, 1)

    def test_page_beyond_pdf_exits_with_code_1(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_cmd("[p.9] 분수의 덧셈은 통분한 뒤 분자끼리 더한다.")
        self.assertEqual(ctx.exception.code, 1)

    def test_reads_bom_answer_file(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        md = tmp / "답.md"
        md.write_bytes("﻿[p.1] 모둠 활동은 네 명이 한 모둠을 이룬다.".encode("utf-8"))
        fake = type("F", (), {"open": staticmethod(lambda path: FakeDoc(PAGES))})
        with patch.object(nlm, "fitz", lambda: fake):
            nlm.cmd_verify(type("A", (), {"pdf": "x.pdf", "answer": str(md)}))


if __name__ == "__main__":
    unittest.main()
