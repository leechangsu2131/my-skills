"""transcribe.py 의 받아쓰기 사전(자주 쓰는 말·고쳐 쓰기) 시험 (T111).

가짜 faster_whisper 와 임시 폴더만 쓴다. 학생 이름은 '학생A'.
"""
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import transcribe as tr  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]


class ApplyFixes(unittest.TestCase):
    def test_longest_first(self):
        self.assertEqual(tr.apply_fixes("모둠 활동지", {"모둠": "모둠A", "모둠 활동지": "모둠 활동지(학습지)"}),
                         "모둠 활동지(학습지)")

    def test_no_chain(self):
        # 바꾼 결과가 다시 바뀌지 않는다(한 번에 훑기)
        self.assertEqual(tr.apply_fixes("가 나", {"가": "나", "나": "다"}), "나 다")

    def test_word_boundary(self):
        fx = {"에이": "A"}
        self.assertEqual(tr.apply_fixes("학생에이", fx), "학생에이")      # 앞이 글자 → 그대로
        self.assertEqual(tr.apply_fixes("에이들", fx), "에이들")          # 뒤가 글자 → 그대로
        self.assertEqual(tr.apply_fixes("에이 반", fx), "A 반")
        self.assertEqual(tr.apply_fixes("에이, 비", fx), "A, 비")

    def test_particle_allowed(self):
        self.assertEqual(tr.apply_fixes("학생에이가 말했다", {"학생에이": "학생A"}), "학생A가 말했다")
        self.assertEqual(tr.apply_fixes("학생에이에게", {"학생에이": "학생A"}), "학생A에게")

    def test_regex_chars_are_literal(self):
        self.assertEqual(tr.apply_fixes("1+1 은 2", {"1+1": "일 더하기 일"}), "일 더하기 일 은 2")

    def test_empty_inputs(self):
        self.assertEqual(tr.apply_fixes("글", {}), "글")
        self.assertEqual(tr.apply_fixes("", {"a": "b"}), "")
        self.assertEqual(tr.apply_fixes("글", {"": "x"}), "글")


class BuildHint(unittest.TestCase):
    def test_join_and_dedupe(self):
        self.assertEqual(tr.build_hint(["알림장", "알림장", "모둠"]), "알림장, 모둠")

    def test_cut_at_word_boundary_within_limit(self):
        out = tr.build_hint(["가" * 100, "나" * 90, "다" * 30])
        self.assertLessEqual(len(out), tr.HINT_LIMIT)
        self.assertEqual(out, "가" * 100 + ", " + "나" * 90)

    def test_first_word_too_long_gives_empty(self):
        self.assertEqual(tr.build_hint(["가" * 300]), "")

    def test_empty(self):
        self.assertEqual(tr.build_hint([]), "")


class LoadWords(unittest.TestCase):
    def test_example_file_is_valid_and_fake(self):
        hints, fixes = tr.load_words(HERE / "stt_words.example.json")
        self.assertTrue(hints and fixes)
        self.assertIn("학생A", hints)

    def test_missing_or_broken_is_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "w.json"
            self.assertEqual(tr.load_words(p), ([], {}))
            p.write_text("{깨짐", encoding="utf-8")
            self.assertEqual(tr.load_words(p), ([], {}))
            p.write_text(json.dumps(["목록"]), encoding="utf-8")
            self.assertEqual(tr.load_words(p), ([], {}))

    def test_bad_entries_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "w.json"
            p.write_text(json.dumps({"자주 쓰는 말": ["a", 3, " ", None, " b "], "고쳐 쓰기": {"x": "y", "": "z", "q": 1}}),
                         encoding="utf-8")
            self.assertEqual(tr.load_words(p), (["a", "b"], {"x": "y"}))


class Transcriber(unittest.TestCase):
    def fake_module(self, calls):
        class Seg:
            def __init__(self, text):
                self.start, self.end, self.text = 0.0, 1.0, text

        class Model:
            def __init__(self, *a, **k):
                pass

            def transcribe(self, path, **kw):
                calls.append(kw)
                return iter([Seg(" 학생에이가 알림 장을 봤다 ")]), None
        return types.SimpleNamespace(WhisperModel=Model)

    def test_hint_passed_and_fixes_applied(self):
        calls = []
        with mock.patch.dict(sys.modules, {"faster_whisper": self.fake_module(calls)}):
            run = tr.load_transcriber("small", words=(["알림장", "학생A"], {"학생에이": "학생A", "알림 장": "알림장"}))
            out = run("x.webm")
        self.assertEqual(calls[0]["initial_prompt"], "알림장, 학생A")
        self.assertEqual(out[0]["text"], "학생A가 알림장을 봤다")

    def test_no_words_no_prompt(self):
        calls = []
        with mock.patch.dict(sys.modules, {"faster_whisper": self.fake_module(calls)}):
            out = tr.load_transcriber("small", words=([], {}))("x.webm")
        self.assertNotIn("initial_prompt", calls[0])
        self.assertEqual(out[0]["text"], "학생에이가 알림 장을 봤다")


if __name__ == "__main__":
    unittest.main()
