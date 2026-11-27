"""nlm.py 의 순수 함수·노트북 목록·Gemini 호출 순서 시험 (S1).

    python -m unittest discover -s tests      (util-notebooklm 폴더에서)

PyMuPDF(fitz)·Gemini CLI·네트워크·실제 .env 없이 돈다.
데이터 폴더는 임시 폴더로 바꿔서(MY_SKILLS_DATA_DIR) 내 문서를 건드리지 않는다. 소스(nlm.py)는 고치지 않는다.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

_TMP_DATA = tempfile.mkdtemp(prefix="nlm_test_data_")
os.environ["MY_SKILLS_DATA_DIR"] = _TMP_DATA  # nlm 을 불러오기 전에 정한다(DATA 가 그때 만들어짐)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import nlm  # noqa: E402


class FakePage:
    def __init__(self, text):
        self._text = text

    def get_text(self):
        return self._text


class PageRefsTests(unittest.TestCase):
    def test_single_and_range_forms(self):
        self.assertEqual(nlm.page_refs("[p.3] 본문 [p.5-7] 본문"), [3, 5, 6, 7])

    def test_spaces_and_tilde_ranges(self):
        self.assertEqual(nlm.page_refs("[p. 7 ~ 9]"), [7, 8, 9])
        self.assertEqual(nlm.page_refs("[p 4]"), [4])

    def test_pdf_page_phrases(self):
        self.assertEqual(nlm.page_refs("PDF 파일 12쪽, PDF 5쪽"), [5, 12])

    def test_duplicates_removed_and_sorted(self):
        self.assertEqual(nlm.page_refs("[p.9] [p.2] [p.9] [p.2-3]"), [2, 3, 9])

    def test_no_refs_gives_empty_list(self):
        self.assertEqual(nlm.page_refs("관련 없음"), [])
        self.assertEqual(nlm.page_refs(""), [])

    def test_reversed_range_keeps_only_first_number(self):
        # 지금 동작: [p.9-7] 은 9쪽만(끝이 앞서면 시작 쪽 하나로 본다).
        self.assertEqual(nlm.page_refs("[p.9-7]"), [9])

    def test_page_zero_is_ignored(self):
        self.assertEqual(nlm.page_refs("[p.0] [p.1]"), [1])


class ParsePagesTests(unittest.TestCase):
    def test_commas_ranges_and_spaces(self):
        self.assertEqual(nlm.parse_pages("4,7-8"), [4, 7, 8])
        self.assertEqual(nlm.parse_pages(" 4  7-8 "), [4, 7, 8])

    def test_duplicates_merged(self):
        self.assertEqual(nlm.parse_pages("3,3,2-4"), [2, 3, 4])

    def test_empty_spec_gives_empty_list(self):
        self.assertEqual(nlm.parse_pages(""), [])

    def test_not_a_number_raises(self):
        with self.assertRaises(ValueError):
            nlm.parse_pages("가")

    def test_reversed_range_gives_nothing(self):
        # 지금 동작: 8-7 은 빈 범위.
        self.assertEqual(nlm.parse_pages("8-7"), [])


class CompactTests(unittest.TestCase):
    def test_runs_are_joined(self):
        self.assertEqual(nlm.compact([1, 2, 3, 5, 7, 8]), "1-3,5,7-8")

    def test_single_page(self):
        self.assertEqual(nlm.compact([4]), "4")

    def test_long_result_is_cut_to_60_chars(self):
        pages = list(range(1, 400, 2))  # 1,3,5,… 전부 떨어진 쪽
        self.assertEqual(len(nlm.compact(pages)), 60)


class SplitTextTests(unittest.TestCase):
    TEXT = "머리말은 버려진다\n# 가\n가 본문\n## 나\n나 본문 1\n나 본문 2\n**다**\n다 본문\n"

    def test_splits_at_each_heading_and_drops_text_before_first(self):
        parts = nlm.split_text(self.TEXT)
        self.assertEqual([p[1] for p in parts], ["# 가", "## 나", "**다**"])
        self.assertTrue(all("머리말" not in p[2] for p in parts))
        self.assertEqual(parts[1][2], "## 나\n나 본문 1\n나 본문 2")

    def test_empty_or_no_heading_gives_empty_list(self):
        self.assertEqual(nlm.split_text(""), [])
        self.assertEqual(nlm.split_text("제목 없는 글\n둘째 줄"), [])

    def test_pattern_cuts_only_at_matching_headings(self):
        text = "# 1단원 (p.3)\n a\n## 소제목\n b\n# 2단원 (p.9)\n c\n"
        parts = nlm.split_text(text, r"\(p\.(\d+)\)")
        self.assertEqual([p[1] for p in parts], ["# 1단원 (p.3)", "# 2단원 (p.9)"])
        self.assertEqual(parts[0][0].group(1), "3")
        self.assertIn("## 소제목", parts[0][2])  # 표시가 없는 제목은 앞 구간 안에 남는다

    def test_compiled_pattern_is_accepted(self):
        import re
        parts = nlm.split_text("# A\nx\n# B\ny", re.compile("B"))
        self.assertEqual([p[1] for p in parts], ["# B"])


class TextHelperTests(unittest.TestCase):
    def test_low_text_boundaries(self):
        self.assertTrue(nlm.is_low_text("가" * 39))
        self.assertFalse(nlm.is_low_text("가" * 40))
        self.assertFalse(nlm.is_low_text(" ".join(["word"] * 40)))
        self.assertTrue(nlm.is_low_text(""))

    def test_page_text_cleans_lines(self):
        raw = "첫   줄\x00\x01\n\n#제목처럼 보이는 줄\n●● 중복 기호\n   \n끝"
        text = nlm.page_text(FakePage(raw))
        self.assertEqual(text.splitlines(), ["첫 줄", "\\#제목처럼 보이는 줄", "● 중복 기호", "끝"])


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = pathlib.Path(self.tmp.name) / "sub" / "notebooks.json"
        patcher = patch.object(nlm, "REGISTRY", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def args(self, **kw):
        base = dict(action="list", topic=None, url=None, note=None, q=None)
        base.update(kw)
        return MagicMock(**base)

    def test_missing_or_broken_file_gives_empty_registry(self):
        self.assertEqual(nlm.load_registry(), {})
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{깨진", encoding="utf-8")
        self.assertEqual(nlm.load_registry(), {})
        self.assertEqual(nlm.notebook_url("없는주제"), "")

    def test_add_then_lookup(self):
        nlm.cmd_nb(self.args(action="add", topic="수학", url="https://notebooklm.google.com/notebook/abc", note="3-2"))
        self.assertEqual(nlm.notebook_url("수학"), "https://notebooklm.google.com/notebook/abc")
        saved = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(saved["수학"]["note"], "3-2")

    def test_add_rejects_other_sites_and_missing_parts(self):
        for kw in (
            dict(topic="수학", url="https://example.com/x"),
            dict(topic="수학", url=None),
            dict(topic=None, url="https://notebooklm.google.com/a"),
        ):
            with self.subTest(kw=kw), self.assertRaises(SystemExit):
                nlm.cmd_nb(self.args(action="add", **kw))
        self.assertFalse(self.path.exists())

    def test_open_unknown_topic_exits(self):
        with self.assertRaises(SystemExit):
            nlm.cmd_nb(self.args(action="open", topic="없음"))

    def test_open_copies_question_and_opens_url(self):
        nlm.save_registry({"사회": {"url": "https://notebooklm.google.com/notebook/s"}})
        with patch.object(nlm, "copy_to_clipboard") as copy, \
                patch.object(nlm.os, "startfile", create=True) as start:
            nlm.cmd_nb(self.args(action="open", topic="사회", q="3단원 활동"))
        copy.assert_called_once()
        self.assertIn("3단원 활동", copy.call_args[0][0])
        start.assert_called_once_with("https://notebooklm.google.com/notebook/s")


class GeminiCommandTests(unittest.TestCase):
    def test_not_installed_raises(self):
        with patch.object(nlm.shutil, "which", return_value=None):
            with self.assertRaises(RuntimeError):
                nlm.gemini_command()

    def test_cmd_shim_without_bundle_raises(self):
        def which(name):
            return {"gemini.cmd": "C:/x/gemini.cmd", "node": "C:/x/node"}.get(name)
        with patch.object(nlm.shutil, "which", side_effect=which):
            with self.assertRaises(RuntimeError):
                nlm.gemini_command()

    def test_runs_bundle_with_node_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            js = pathlib.Path(tmp) / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"
            js.parent.mkdir(parents=True)
            js.write_text("", encoding="utf-8")
            shim = pathlib.Path(tmp) / "gemini.cmd"

            def which(name):
                return {"gemini.cmd": str(shim), "node": "/usr/bin/node"}.get(name)
            with patch.object(nlm.shutil, "which", side_effect=which):
                self.assertEqual(nlm.gemini_command(), ["/usr/bin/node", str(js)])

    def test_plain_executable_without_node_is_used_directly(self):
        def which(name):
            return {"gemini": "/usr/local/bin/gemini"}.get(name)
        with patch.object(nlm.shutil, "which", side_effect=which):
            self.assertEqual(nlm.gemini_command(), ["/usr/local/bin/gemini"])


def completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class GeminiAskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = pathlib.Path(self.tmp.name)
        self.pdf = root / "지도서 샘플.pdf"
        self.pdf.write_bytes(b"%PDF-1.4 fake")
        self.work = root / "work"
        for p in (
            patch.object(nlm, "gemini_command", return_value=["node", "gemini.js"]),
            patch.object(nlm, "env_values", return_value={}),
        ):
            p.start()
            self.addCleanup(p.stop)

    def ask(self, run, **kw):
        with patch.object(nlm.subprocess, "run", side_effect=run) as mocked:
            result = nlm.gemini_ask(self.pdf, "질문 {file}", work=self.work, **kw)
        return result, mocked

    def test_first_model_answers(self):
        result, mocked = self.ask([completed(stdout=" 답 [p.3] \n")])
        self.assertEqual(result, ("답 [p.3]", nlm.DEFAULT_MODEL))
        self.assertEqual(mocked.call_count, 1)

    def test_prompt_gets_fixed_local_file_name_and_pdf_is_copied(self):
        _, mocked = self.ask([completed(stdout="ok")])
        cmd = mocked.call_args[0][0]
        self.assertEqual(cmd[:4], ["node", "gemini.js", "-e", "none"])
        self.assertEqual(cmd[-1], "질문 doc.pdf")
        self.assertEqual((self.work / "doc.pdf").read_bytes(), b"%PDF-1.4 fake")

    def test_falls_back_in_order_when_busy_or_failed(self):
        run = [completed(1, "", "Error: quota exceeded"), subprocess.TimeoutExpired("gemini", 60), completed(stdout="third")]
        result, mocked = self.ask(run)
        chain = [nlm.DEFAULT_MODEL, *nlm.FALLBACK_MODELS]
        self.assertEqual(result, ("third", chain[2]))
        used = [c[0][0][c[0][0].index("-m") + 1] for c in mocked.call_args_list]
        self.assertEqual(used, chain[:3])

    def test_empty_output_counts_as_failure(self):
        result, _ = self.ask([completed(0, "   \n", ""), completed(stdout="둘째")])
        self.assertEqual(result[1], nlm.FALLBACK_MODELS[0])

    def test_all_models_fail_raises_with_every_reason(self):
        total = 1 + len(nlm.FALLBACK_MODELS)
        run = [completed(2, "", "Error: boom")] * total
        with patch.object(nlm.subprocess, "run", side_effect=run):
            with self.assertRaises(RuntimeError) as ctx:
                nlm.gemini_ask(self.pdf, "q", work=self.work)
        message = str(ctx.exception)
        for model in (nlm.DEFAULT_MODEL, *nlm.FALLBACK_MODELS):
            self.assertIn(model, message)

    def test_chosen_model_is_tried_first_without_duplicates(self):
        chosen = nlm.FALLBACK_MODELS[1]
        run = [completed(1, "", "x")] * len(nlm.FALLBACK_MODELS)
        with patch.object(nlm.subprocess, "run", side_effect=run + [completed(stdout="ok")]) as mocked:
            with self.assertRaises(RuntimeError):
                nlm.gemini_ask(self.pdf, "q", model=chosen, work=self.work)
        used = [c[0][0][c[0][0].index("-m") + 1] for c in mocked.call_args_list]
        self.assertEqual(used[0], chosen)
        self.assertEqual(len(used), len(set(used)))
        self.assertEqual(len(used), 1 + len(nlm.FALLBACK_MODELS) - 1)

    def test_timeouts(self):
        _, mocked = self.ask([completed(stdout="a")], timeout=300)
        self.assertEqual(mocked.call_args.kwargs["timeout"], 120)  # 기본은 최대 120초
        _, mocked = self.ask([completed(stdout="a")], timeout=30)
        self.assertEqual(mocked.call_args.kwargs["timeout"], 60)   # 최소 60초
        _, mocked = self.ask([completed(stdout="a")], model_timeout=45)
        self.assertEqual(mocked.call_args.kwargs["timeout"], 45)

    def test_api_key_goes_to_work_folder_only(self):
        with patch.object(nlm, "env_values", return_value={"GEMINI_API_KEY": "가짜키-테스트"}):
            _, mocked = self.ask([completed(stdout="ok")])
        settings = json.loads((self.work / ".gemini" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings["security"]["auth"]["selectedType"], "gemini-api-key")
        self.assertEqual(mocked.call_args.kwargs["env"]["GEMINI_API_KEY"], "가짜키-테스트")
        self.assertEqual(mocked.call_args.kwargs["cwd"], self.work)

    def test_key_priority_follows_key_names(self):
        values = {"GEMINI_API_KEY": "일반", "UTIL_NOTEBOOKLM__GEMINI_API_KEY": "전용"}
        with patch.object(nlm, "env_values", return_value=values):
            _, mocked = self.ask([completed(stdout="ok")])
        self.assertEqual(mocked.call_args.kwargs["env"]["GEMINI_API_KEY"], "전용")

    def test_without_key_old_settings_file_is_removed(self):
        settings = self.work / ".gemini" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("{}", encoding="utf-8")
        self.ask([completed(stdout="ok")])
        self.assertFalse(settings.exists())

    def test_gemini_find_uses_find_prompt_and_returns_model(self):
        with patch.object(nlm, "gemini_ask", return_value=("답", "m")) as ask:
            self.assertEqual(nlm.gemini_find(self.pdf, "분수 활동", model_timeout=30), ("답", "m"))
        prompt = ask.call_args[0][1]
        self.assertIn("분수 활동", prompt)
        self.assertIn("{file}", prompt)
        self.assertEqual(ask.call_args.kwargs["model_timeout"], 30)


if __name__ == "__main__":
    unittest.main()
