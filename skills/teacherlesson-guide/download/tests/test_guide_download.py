"""guide_download.py 의 순수 부분 시험 (S1): 파일 이름 만들기, ZIP 이름 복구, 부분 받기, 미래엔 주소 캐시, 파일 받기.

    python -m unittest discover -s tests      (download 폴더에서)

크롬·selenium·수업 비서 서버·네트워크 없이 돈다. 불러올 때 필요한 모듈은 가짜(stub)로 대신하고,
HTTP 는 가짜 urlopen 으로 바꾼다. 내 문서·진짜 .env·D:\\지도서 는 건드리지 않는다. 소스는 고치지 않는다.
"""

import io
import json
import pathlib
import sys
import tempfile
import types
import unittest
import zipfile
from unittest.mock import patch

# ── 불러오기 전에 가짜 모듈을 끼워 넣는다(진짜가 있으면 selenium 은 그대로 둔다) ──
_app = types.ModuleType("assistant_server")
_app.DATA = pathlib.Path(tempfile.mkdtemp(prefix="gd_test_"))
_store = {}
_app.read_json = lambda path, default=None: json.loads(json.dumps(_store.get(str(path), default)))
_app.write_json = lambda path, value: _store.__setitem__(str(path), json.loads(json.dumps(value)))
sys.modules["assistant_server"] = _app
try:
    import selenium  # noqa: F401
except ImportError:
    _sel = types.ModuleType("selenium")
    _wd = types.ModuleType("selenium.webdriver")
    _by = types.ModuleType("selenium.webdriver.common.by")
    _by.By = type("By", (), {})
    _common = types.ModuleType("selenium.webdriver.common")
    _exc = types.ModuleType("selenium.common.exceptions")
    _exc.WebDriverException = type("WebDriverException", (Exception,), {})
    _sel_common = types.ModuleType("selenium.common")
    _wd.common = _common
    for name, mod in {
        "selenium": _sel, "selenium.webdriver": _wd, "selenium.webdriver.common": _common,
        "selenium.webdriver.common.by": _by, "selenium.common": _sel_common,
        "selenium.common.exceptions": _exc,
    }.items():
        sys.modules[name] = mod
    _sel.webdriver = _wd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import guide_download as gd  # noqa: E402


class FakeResponse:
    def __init__(self, body=b"", status=200, headers=None):
        self._body, self.status, self.headers = io.BytesIO(body), status, headers or {}

    def read(self, n=-1):
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def make_server(blob: bytes, *, partial=True, short=False):
    """URL 하나를 흉내 내는 가짜 urlopen. HEAD 는 길이, Range 요청은 해당 구간을 준다."""
    calls = []

    def urlopen(req, timeout=None):
        calls.append(req)
        if isinstance(req, str):                      # urlopen("주소") 처럼 문자열로 부르는 경우(전체 받기)
            return FakeResponse(blob, 200, {"Content-Length": str(len(blob))})
        if req.get_method() == "HEAD":
            return FakeResponse(headers={"Content-Length": str(len(blob))})
        rng = req.headers.get("Range")
        if rng:
            a, b = (int(x) for x in rng.removeprefix("bytes=").split("-"))
            body = blob[a:b + 1]
            if short:
                body = body[:-1]
            return FakeResponse(body, 206 if partial else 200)
        return FakeResponse(blob, 200, {"Content-Length": str(len(blob))})

    return urlopen, calls


class SafeAndNiceNameTests(unittest.TestCase):
    def test_safe_replaces_forbidden_characters_and_trims(self):
        self.assertEqual(gd.safe('  a/b\\c:d*e?f"g<h>i|j  '), "a_b_c_d_e_f_g_h_i_j")
        self.assertEqual(gd.safe("그대로"), "그대로")
        self.assertEqual(gd.safe("a//b"), "a_b")  # 이어진 금지 문자는 밑줄 하나

    def test_nice_name_for_teacher_guide_units(self):
        item = {"label": "교사용 지도서", "file": "math_jido_3-2-4.pdf"}
        self.assertEqual(gd.nice_name("수학", "3학년2학기", item), "[수학]3-2_지도서_4단원.pdf")

    def test_nice_name_for_other_labels_has_no_unit_suffix(self):
        item = {"label": "연간지도계획", "file": "math_plan_3-2-0.pdf"}
        self.assertEqual(gd.nice_name("수학", "3학년2학기", item), "[수학]3-2_연간지도계획_0.pdf")

    def test_nice_name_label_is_made_safe(self):
        item = {"label": "평가/자료", "file": "x_3-1-2.pdf"}
        self.assertEqual(gd.nice_name("사회", "3학년1학기", item), "[사회]3-1_평가_자료_2.pdf")

    def test_nice_name_without_pattern_falls_back_to_term_and_file(self):
        item = {"label": "교사용 지도서", "file": "국어/가 지도서.pdf"}
        self.assertEqual(gd.nice_name("국어", "3학년1학기", item), "[국어]3학년1학기_국어_가 지도서.pdf")


class ZipNameTests(unittest.TestCase):
    def test_utf8_flag_name_is_kept(self):
        info = zipfile.ZipInfo("지도서/pdf/국어.pdf")
        info.flag_bits |= 0x800
        self.assertEqual(gd._zip_name(info), "지도서/pdf/국어.pdf")

    def test_cp949_name_is_restored(self):
        raw = "지도서/pdf/국어.pdf".encode("cp949").decode("cp437")  # 윈도우 압축 프로그램이 쓰는 방식
        self.assertEqual(gd._zip_name(zipfile.ZipInfo(raw)), "지도서/pdf/국어.pdf")

    def test_ascii_name_is_unchanged(self):
        self.assertEqual(gd._zip_name(zipfile.ZipInfo("a/b.pdf")), "a/b.pdf")

    def test_undecodable_name_is_kept_as_is(self):
        info = zipfile.ZipInfo("ü")  # cp437 로 만들 수 없는 글자는 그대로
        self.assertEqual(gd._zip_name(info), "ü")


class HttpRangeFileTests(unittest.TestCase):
    BLOB = bytes(range(256)) * 4  # 1024바이트

    def open_file(self, **kw):
        urlopen, calls = make_server(self.BLOB, **kw)
        with patch.object(gd.urllib.request, "urlopen", urlopen):
            f = gd.HttpRangeFile("https://example.com/한글 파일.zip")
            return f, calls, urlopen

    def test_url_is_quoted_and_size_comes_from_head(self):
        f, calls, _ = self.open_file()
        self.assertEqual(f.size, 1024)
        self.assertNotIn(" ", f.url)
        self.assertIn("%ED%95%9C", f.url)
        self.assertEqual(calls[0].get_method(), "HEAD")

    def test_read_asks_for_the_exact_range_and_advances(self):
        f, calls, urlopen = self.open_file()
        with patch.object(gd.urllib.request, "urlopen", urlopen):
            self.assertEqual(f.read(10), self.BLOB[:10])
            self.assertEqual(f.tell(), 10)
            self.assertEqual(f.read(5), self.BLOB[10:15])
        self.assertEqual(calls[1].headers["Range"], "bytes=0-9")
        self.assertEqual(calls[2].headers["Range"], "bytes=10-14")

    def test_seek_modes(self):
        f, _, _ = self.open_file()
        self.assertEqual(f.seek(100), 100)
        self.assertEqual(f.seek(20, 1), 120)
        self.assertEqual(f.seek(-24, 2), 1000)

    def test_read_past_end_returns_empty_without_request(self):
        f, calls, urlopen = self.open_file()
        f.seek(0, 2)
        before = len(calls)
        with patch.object(gd.urllib.request, "urlopen", urlopen):
            self.assertEqual(f.read(10), b"")
            self.assertEqual(f.read(0), b"")
        self.assertEqual(len(calls), before)

    def test_read_is_cut_at_end_and_read_all_works(self):
        f, _, urlopen = self.open_file()
        f.seek(1020)
        with patch.object(gd.urllib.request, "urlopen", urlopen):
            self.assertEqual(f.read(100), self.BLOB[1020:])
            f.seek(0)
            self.assertEqual(f.read(), self.BLOB)

    def test_server_without_partial_support_is_rejected(self):
        urlopen, _ = make_server(self.BLOB, partial=False)
        with patch.object(gd.urllib.request, "urlopen", urlopen):
            f = gd.HttpRangeFile("https://example.com/a.zip")
            with self.assertRaisesRegex(RuntimeError, "부분 받기"):
                f.read(10)

    def test_wrong_length_is_rejected(self):
        urlopen, _ = make_server(self.BLOB, short=True)
        with patch.object(gd.urllib.request, "urlopen", urlopen):
            f = gd.HttpRangeFile("https://example.com/a.zip")
            with self.assertRaisesRegex(RuntimeError, "길이"):
                f.read(10)

    def test_readinto_fills_buffer(self):
        f, _, urlopen = self.open_file()
        buf = bytearray(8)
        with patch.object(gd.urllib.request, "urlopen", urlopen):
            self.assertEqual(f.readinto(buf), 8)
        self.assertEqual(bytes(buf), self.BLOB[:8])


def build_zip(members: dict[str, bytes], cp949=True) -> bytes:
    """윈도우 압축 프로그램처럼 이름을 cp949 로 넣은 ZIP(UTF-8 표시 없음).
    파이썬은 한글 이름에 UTF-8 표시를 자동으로 붙이므로, 같은 길이의 영문 자리표시자로 만든 뒤 바이트를 바꿔 끼운다."""
    out = io.BytesIO()
    swaps = []
    with zipfile.ZipFile(out, "w") as z:
        for i, (name, data) in enumerate(members.items()):
            if not cp949:
                z.writestr(name, data)
                continue
            raw = name.encode("cp949")
            holder = (f"m{i:03d}_" + "x" * len(raw))[:len(raw)].encode("ascii")
            assert len(holder) == len(raw) and len(raw) >= 5, "이름이 너무 짧아요"
            swaps.append((holder, raw))
            z.writestr(holder.decode("ascii"), data)
    blob = out.getvalue()
    for holder, raw in swaps:
        assert blob.count(holder) == 2           # 지역 머리 + 중앙 목록
        blob = blob.replace(holder, raw)
    return blob


class MiraenTests(unittest.TestCase):
    def test_items_from_url_keeps_only_guide_pdfs(self):
        blob = build_zip({
            "미래엔/지도서/pdf/국어3-1.pdf": b"%PDF-1",
            "미래엔/지도서/pdf/국어3-2.pdf": b"%PDF-2",
            "미래엔/지도서/hwp/국어3-1.hwp": b"x",
            "미래엔/교과서/pdf/국어.pdf": b"%PDF-3",
        })
        urlopen, _ = make_server(blob)
        with patch.object(gd.urllib.request, "urlopen", urlopen):
            term, items = gd.miraen_items_from_url("국어", "3-2", "https://example.com/dvd.zip")
        self.assertEqual(term, "3학년2학기")
        self.assertEqual([i["file"] for i in items], ["국어3-1.pdf", "국어3-2.pdf"])
        self.assertTrue(all(i["label"] == "교사용 지도서" for i in items))
        self.assertEqual(items[0]["size"], len(b"%PDF-1"))

    def test_unknown_subject_is_rejected_before_any_request(self):
        with patch.object(gd.urllib.request, "urlopen", side_effect=AssertionError("요청하면 안 됨")):
            with self.assertRaisesRegex(RuntimeError, "아직 몰라요"):
                gd.miraen_items_from_url("수학", "3-1", "https://example.com/dvd.zip")

    def test_cache_round_trip_matches_grade_term_only(self):
        _store.clear()
        self.assertEqual(gd.cached_miraen_url("국어", "3-1"), "")
        gd.cache_miraen_url("국어", "3-1", "3학년1학기", [{"url": ""}, {"url": "https://example.com/a.zip"}])
        self.assertEqual(gd.cached_miraen_url("국어", "3-1"), "https://example.com/a.zip")
        self.assertEqual(gd.cached_miraen_url("국어", "3-2"), "")   # 다른 학기는 못 씀
        self.assertEqual(gd.cached_miraen_url("수학", "3-1"), "")

    def test_cache_skips_when_no_url_and_survives_broken_file(self):
        _store.clear()
        gd.cache_miraen_url("국어", "3-1", "3학년1학기", [{"label": "x"}])
        self.assertEqual(_store, {})
        _store[str(gd.MIRAEN_CACHE)] = ["깨진", "모양"]            # dict 가 아닌 파일
        self.assertEqual(gd.cached_miraen_url("국어", "3-1"), "")
        gd.cache_miraen_url("국어", "3-1", "3학년1학기", [{"url": "https://example.com/b.zip"}])
        self.assertEqual(gd.cached_miraen_url("국어", "3-1"), "https://example.com/b.zip")


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dest = pathlib.Path(self.tmp.name) / "out.pdf"

    def zip_item(self, data: bytes):
        blob = build_zip({"지도서/pdf/a.pdf": data}, cp949=False)
        archive = zipfile.ZipFile(io.BytesIO(blob))
        info = archive.infolist()[0]
        return {"member": info, "archive": archive, "size": info.file_size}

    def test_zip_member_is_extracted(self):
        item = self.zip_item(b"%PDF-1.4 hello")
        self.assertTrue(gd.download(item, self.dest).startswith("받음"))
        self.assertEqual(self.dest.read_bytes(), b"%PDF-1.4 hello")
        self.assertFalse(self.dest.with_suffix(".part").exists())

    def test_same_size_file_is_skipped(self):
        item = self.zip_item(b"%PDF-1.4 hello")
        self.dest.write_bytes(b"x" * item["size"])
        self.assertEqual(gd.download(item, self.dest), "이미 있음")
        self.assertEqual(self.dest.read_bytes(), b"x" * item["size"])   # 건드리지 않음

    def test_different_size_file_is_replaced(self):
        item = self.zip_item(b"%PDF-1.4 hello")
        self.dest.write_bytes(b"old")
        gd.download(item, self.dest)
        self.assertEqual(self.dest.read_bytes(), b"%PDF-1.4 hello")

    def test_larger_existing_file_is_also_replaced(self):
        item = self.zip_item(b"%PDF-1.4 hello")
        self.dest.write_bytes(b"z" * (item["size"] + 50))      # 중간에 끊긴 게 아니라 더 큰 파일도 같은 크기가 아니면 다시 받는다
        self.assertTrue(gd.download(item, self.dest).startswith("받음"))
        self.assertEqual(self.dest.read_bytes(), b"%PDF-1.4 hello")

    def test_non_pdf_is_rejected_and_part_file_removed(self):
        item = self.zip_item("<html>로그인 필요</html>".encode("utf-8"))
        with self.assertRaisesRegex(RuntimeError, "PDF가 아닌"):
            gd.download(item, self.dest)
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.dest.with_suffix(".part").exists())

    def test_url_item_uses_head_size_then_downloads(self):
        blob = b"%PDF-1.7 " + b"y" * 100
        urlopen, calls = make_server(blob)
        with patch.object(gd.urllib.request, "urlopen", urlopen):
            msg = gd.download({"url": "https://example.com/a.pdf"}, self.dest)
        self.assertTrue(msg.startswith("받음"))
        self.assertEqual(self.dest.read_bytes(), blob)
        self.assertEqual(calls[0].get_method(), "HEAD")
        self.assertIsInstance(calls[1], str)

    def test_url_item_with_same_size_is_skipped_without_get(self):
        blob = b"%PDF-1.7 " + b"y" * 100
        self.dest.write_bytes(blob)
        urlopen, calls = make_server(blob)
        with patch.object(gd.urllib.request, "urlopen", urlopen):
            self.assertEqual(gd.download({"url": "https://example.com/a.pdf"}, self.dest), "이미 있음")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].get_method(), "HEAD")


class PublishersTests(unittest.TestCase):
    def test_supported_publishers(self):
        self.assertEqual(set(gd.PUBLISHERS), {"아이스크림", "미래엔", "천재교육"})
        for url, func in gd.PUBLISHERS.values():
            self.assertTrue(url.startswith("https://"))
            self.assertTrue(callable(func))


if __name__ == "__main__":
    unittest.main()
