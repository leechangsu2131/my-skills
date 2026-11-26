"""douclass_probe.py · scan_music_pdf_header.py 의 명령줄 시험(T95).

    python -m unittest test_douclass_scripts -v      (이 폴더에서)

진짜 PDF·크롬·selenium 은 쓰지 않는다. PDF 는 쪽 글만 돌려주는 가짜 fitz 로, 크롬 붙기는 아예 시도하지 않는다.
"""
import contextlib
import io
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import douclass_probe
import scan_music_pdf_header as scan

HERE = pathlib.Path(__file__).resolve().parent


class FakeDoc:
    def __init__(self, pages):
        self.pages = pages

    def __len__(self):
        return len(self.pages)

    def __getitem__(self, i):
        return mock.Mock(get_text=lambda: self.pages[i])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def run(main, argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exc:  # argparse 의 --help·오류
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class NoUserPathTests(unittest.TestCase):
    def test_scripts_have_no_hardcoded_user_paths(self):
        for name in ("douclass_probe.py", "scan_music_pdf_header.py"):
            text = (HERE / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?i)[a-z]:[\\/]+users[\\/]", name)


class ScanHeaderTests(unittest.TestCase):
    def test_header_flags_look_only_at_first_200_chars_ignoring_symbols_and_spaces(self):
        self.assertEqual(scan.header_flags("1. 단 원 계 획\n내용"), {"is_plan": True, "is_appendix": False, "is_toc": False})
        self.assertTrue(scan.header_flags("차 례")["is_toc"])
        self.assertTrue(scan.header_flags("[부록] 악보")["is_appendix"])
        self.assertFalse(any(scan.header_flags("가" * 250 + "계획 부록 차례").values()))

    def test_scan_marks_lesson_pages_and_skips_plan_pages(self):
        doc = FakeDoc(["표지", "단원 계획 길고 짧은 음, 높고 낮은 음", "길고 짧은 음, 높고 낮은 음 수업 내용", "다른 쪽"])
        got = scan.scan(doc, scan.DEFAULT_TARGET)
        self.assertEqual([(p, ok) for p, _, ok in got], [(2, False), (3, True)])

    def test_main_prints_one_result_pair_per_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = pathlib.Path(tmp) / "a.pdf"
            pdf.write_bytes(b"x")
            fake_fitz = mock.Mock(open=lambda path: FakeDoc(["부록 길고짧은음높고낮은음", "길고 짧은 음 높고 낮은 음"]))
            with mock.patch.dict(sys.modules, {"fitz": fake_fitz}):
                code, out, _ = run(scan.main, [str(pdf)])
        self.assertEqual(code, 0)
        self.assertIn("Scanning for: 길고짧은음높고낮은음", out)
        self.assertIn("Page 1: is_plan=False, is_appendix=True, is_toc=False", out)
        self.assertIn("SKIPPED due to header markers", out)
        self.assertIn("Page 2:", out)
        self.assertIn("MATCH! This must be the actual lesson.", out)

    def test_custom_target_is_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = pathlib.Path(tmp) / "a.pdf"
            pdf.write_bytes(b"x")
            fake_fitz = mock.Mock(open=lambda path: FakeDoc(["새 친구들, 함께"]))
            with mock.patch.dict(sys.modules, {"fitz": fake_fitz}):
                code, out, _ = run(scan.main, [str(pdf), "--target", "새 친구들"])
        self.assertEqual(code, 0)
        self.assertIn("Scanning for: 새친구들", out)
        self.assertIn("Page 1:", out)

    def test_without_path_prints_usage_and_exits_2(self):
        code, out, err = run(scan.main, [])
        self.assertEqual(code, 2)
        self.assertIn("usage:", err)
        self.assertIn("경로를 적어 주세요", err)
        self.assertEqual(out, "")

    def test_missing_file_exits_2(self):
        code, _, err = run(scan.main, ["/없는/폴더/music.pdf"])
        self.assertEqual(code, 2)
        self.assertIn("파일을 찾을 수 없어요", err)

    def test_missing_pymupdf_exits_2_with_install_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = pathlib.Path(tmp) / "a.pdf"
            pdf.write_bytes(b"x")
            with mock.patch.dict(sys.modules, {"fitz": None}):
                code, _, err = run(scan.main, [str(pdf)])
        self.assertEqual(code, 2)
        self.assertIn("pip install PyMuPDF", err)

    def test_help_exits_0_without_pymupdf(self):
        with mock.patch.dict(sys.modules, {"fitz": None}):
            code, out, _ = run(scan.main, ["--help"])
        self.assertEqual(code, 0)
        self.assertIn("--target", out)


class ProbeTests(unittest.TestCase):
    def test_help_exits_0_without_selenium(self):
        with mock.patch.dict(sys.modules, {"selenium": None, "selenium.webdriver": None, "selenium.webdriver.common.by": None}):
            code, out, _ = run(douclass_probe.main, ["--help"])
        self.assertEqual(code, 0)
        self.assertIn("--port", out)
        self.assertIn("--lesson", out)

    def test_missing_selenium_exits_2_with_install_hint(self):
        with mock.patch.dict(sys.modules, {"selenium": None, "selenium.webdriver": None, "selenium.webdriver.common.by": None}):
            code, _, err = run(douclass_probe.main, [])
        self.assertEqual(code, 2)
        self.assertIn("pip install selenium", err)

    def test_options_reach_attach_and_failed_attach_exits_1(self):
        fake_by = mock.Mock(CLASS_NAME="c", XPATH="x")
        modules = {"selenium": mock.Mock(), "selenium.webdriver": mock.Mock(), "selenium.webdriver.common": mock.Mock(),
                   "selenium.webdriver.common.by": mock.Mock(By=fake_by)}
        with mock.patch.dict(sys.modules, modules), mock.patch.object(douclass_probe, "attach", return_value=None) as attach:
            code, _, _ = run(douclass_probe.main, ["--port", "9333"])
        self.assertEqual(code, 1)
        attach.assert_called_once_with(9333)

    def test_defaults_keep_old_behaviour(self):
        self.assertEqual((douclass_probe.REMOTE_PORT, douclass_probe.TARGET_LESSON), (9222, "1~2차시"))


if __name__ == "__main__":
    unittest.main()
