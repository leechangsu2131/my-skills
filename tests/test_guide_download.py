"""skills/teacherlesson-guide/download/guide_download.py 의 순수 함수 시험 (S1).

크롬·사이트에 접속하지 않는다. 파일 이름 만들기(safe·nice_name), ZIP 파일 이름 글자 복원(_zip_name),
미래엔 주소 기억(cache_miraen_url·cached_miraen_url), ZIP 안 PDF 꺼내기(download — 가짜 ZIP)를 시험한다.
이 PC 에 selenium 이 없으면 가짜 모듈로 대신해서 불러온다(시험에서 쓰지 않음).
"""
import io
import json
import pathlib
import sys
import types
import zipfile

import pytest

# selenium·urllib3 가 없는 환경에서도 모듈을 불러올 수 있게 가짜로 채운다(있으면 진짜를 쓴다).
for _name, _attrs in {
    "selenium": {"webdriver": types.SimpleNamespace()},
    "selenium.webdriver": {},
    "selenium.webdriver.common": {},
    "selenium.webdriver.common.by": {"By": object},
    "selenium.common": {},
    "selenium.common.exceptions": {"WebDriverException": Exception},
    "urllib3": {},
    "urllib3.exceptions": {"ReadTimeoutError": Exception},
}.items():
    try:
        __import__(_name)
    except ImportError:
        _mod = types.ModuleType(_name)
        _mod.__dict__.update(_attrs)
        sys.modules[_name] = _mod

DOWNLOAD_DIR = pathlib.Path(__file__).resolve().parent.parent / "skills" / "teacherlesson-guide" / "download"
sys.path.insert(0, str(DOWNLOAD_DIR))
import guide_download as gd  # noqa: E402


# ── safe ──
def test_safe_replaces_forbidden_filename_characters():
    assert gd.safe('수학: 3/2 "지도서"?') == '수학_ 3_2 _지도서_'.strip()


def test_safe_collapses_runs_and_strips():
    assert gd.safe("  a<>|b  ") == "a_b"
    assert gd.safe("a\\/b") == "a_b"


def test_safe_keeps_normal_korean_and_spaces():
    assert gd.safe("연간 지도 계획") == "연간 지도 계획"


# ── nice_name ──
def test_nice_name_teacher_guide_with_unit_number():
    item = {"file": "math_jido_3-2-4.pdf", "label": "교사용 지도서"}
    assert gd.nice_name("수학", "3학년2학기", item) == "[수학]3-2_지도서_4단원.pdf"


def test_nice_name_other_label_uses_label_and_plain_number():
    item = {"file": "soc_plan_3-1-12.pdf", "label": "연간지도계획"}
    assert gd.nice_name("사회", "3학년1학기", item) == "[사회]3-1_연간지도계획_12.pdf"


def test_nice_name_label_is_made_filename_safe():
    item = {"file": "x_3-1-2.pdf", "label": "평가/자료"}
    assert gd.nice_name("국어", "t", item) == "[국어]3-1_평가_자료_2.pdf"


def test_nice_name_without_number_falls_back_to_term_and_file():
    item = {"file": "교사용:지도서.pdf", "label": "교사용 지도서"}
    assert gd.nice_name("국어", "3학년1학기", item) == "[국어]3학년1학기_교사용_지도서.pdf"


def test_nice_name_matches_only_at_end_of_file_name():
    item = {"file": "3-2-4.pdf.bak.pdf", "label": "교사용 지도서"}
    assert gd.nice_name("수학", "t", item) == "[수학]t_3-2-4.pdf.bak.pdf"


# ── _zip_name ──
def test_zip_name_utf8_flag_returned_as_is():
    info = zipfile.ZipInfo("지도서/pdf/a.pdf")
    info.flag_bits |= 0x800
    assert gd._zip_name(info) == "지도서/pdf/a.pdf"


def test_zip_name_utf8_flag_wins_even_if_name_looks_like_cp949_bytes():
    looks_like_cp949 = "가".encode("cp949").decode("cp437")      # 'в' 처럼 cp437 글자 둘
    info = zipfile.ZipInfo(looks_like_cp949)
    info.flag_bits |= 0x800
    assert gd._zip_name(info) == looks_like_cp949


def test_zip_name_restores_cp949_names_stored_as_cp437():
    real = "지도서/pdf/국어_3-2_1.pdf"
    info = zipfile.ZipInfo(real.encode("cp949").decode("cp437"))
    assert gd._zip_name(info) == real


def test_zip_name_unrepresentable_name_is_returned_unchanged():
    info = zipfile.ZipInfo("é.pdf")          # cp437 로 못 돌려놓는 글자
    assert gd._zip_name(info) == "é.pdf"


def test_zip_name_ascii_name_unchanged():
    assert gd._zip_name(zipfile.ZipInfo("a/b.pdf")) == "a/b.pdf"


# ── 미래엔 주소 기억 ──
@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    path = tmp_path / "guide_download_candidates.json"
    monkeypatch.setattr(gd, "MIRAEN_CACHE", path)
    return path


def test_cache_then_read_back_same_grade_term(cache_file):
    gd.cache_miraen_url("국어", "3-2", "3학년2학기", [{"url": "https://x/dvd.zip"}])
    assert gd.cached_miraen_url("국어", "3-2") == "https://x/dvd.zip"
    saved = json.loads(cache_file.read_text(encoding="utf-8"))["국어"]
    assert saved["grade_term"] == "3-2" and saved["term"] == "3학년2학기" and saved["at"]


def test_cached_url_is_ignored_for_a_different_grade_term(cache_file):
    gd.cache_miraen_url("국어", "3-2", "3학년2학기", [{"url": "https://x/dvd.zip"}])
    assert gd.cached_miraen_url("국어", "3-1") == ""


def test_cached_url_missing_file_or_subject_is_empty(cache_file):
    assert gd.cached_miraen_url("국어", "3-2") == ""
    gd.cache_miraen_url("국어", "3-2", "t", [{"url": "u"}])
    assert gd.cached_miraen_url("수학", "3-2") == ""


def test_cache_uses_first_item_that_has_a_url(cache_file):
    gd.cache_miraen_url("국어", "3-2", "t", [{"file": "a"}, {"url": ""}, {"url": "https://x/1"}, {"url": "https://x/2"}])
    assert gd.cached_miraen_url("국어", "3-2") == "https://x/1"


def test_cache_without_any_url_writes_nothing(cache_file):
    gd.cache_miraen_url("국어", "3-2", "t", [{"file": "a"}, {"url": ""}])
    assert not cache_file.exists()


def test_cache_keeps_other_subjects(cache_file):
    gd.cache_miraen_url("국어", "3-2", "t", [{"url": "https://x/k"}])
    gd.cache_miraen_url("도덕", "3-2", "t", [{"url": "https://x/d"}])
    assert gd.cached_miraen_url("국어", "3-2") == "https://x/k"
    assert gd.cached_miraen_url("도덕", "3-2") == "https://x/d"


def test_corrupt_cache_file_is_replaced_not_crashing(cache_file):
    cache_file.write_text('["이상한", "모양"]', encoding="utf-8")
    assert gd.cached_miraen_url("국어", "3-2") == ""
    gd.cache_miraen_url("국어", "3-2", "t", [{"url": "https://x/k"}])
    assert gd.cached_miraen_url("국어", "3-2") == "https://x/k"


# ── download (ZIP 안의 파일 꺼내기) ──
def zip_item(content: bytes, name="지도서/pdf/a.pdf"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, content)
    archive = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    info = archive.infolist()[0]
    return {"member": info, "archive": archive, "size": info.file_size}


PDF = b"%PDF-1.7\n" + b"x" * 2048


def test_download_extracts_pdf_member(tmp_path):
    dest = tmp_path / "a.pdf"
    msg = gd.download(zip_item(PDF), dest)
    assert msg.startswith("받음")
    assert dest.read_bytes() == PDF
    assert not dest.with_suffix(".part").exists()


def test_download_skips_when_same_size_already_there(tmp_path):
    dest = tmp_path / "a.pdf"
    dest.write_bytes(PDF)
    assert gd.download(zip_item(PDF), dest) == "이미 있음"


def test_download_replaces_a_file_whose_size_differs(tmp_path):
    dest = tmp_path / "a.pdf"
    dest.write_bytes(b"%PDF-old")
    assert gd.download(zip_item(PDF), dest).startswith("받음")
    assert dest.read_bytes() == PDF


def test_download_rejects_non_pdf_and_leaves_nothing_behind(tmp_path):
    dest = tmp_path / "a.pdf"
    with pytest.raises(RuntimeError, match="PDF가 아닌"):
        gd.download(zip_item("<html>로그인하세요</html>".encode("utf-8")), dest)
    assert not dest.exists()
    assert not dest.with_suffix(".part").exists()


def test_download_non_pdf_does_not_overwrite_an_existing_good_file(tmp_path):
    dest = tmp_path / "a.pdf"
    dest.write_bytes(PDF)
    with pytest.raises(RuntimeError):
        gd.download(zip_item(b"<html>x</html>"), dest)
    assert dest.read_bytes() == PDF
