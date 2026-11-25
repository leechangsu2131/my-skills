"""personal-library-search 순수 함수 시험 (네트워크·비밀값·실제 사이트 없이).

각 스크립트는 불러올 때 중앙 .env 를 읽고 requests 를 바꿔 놓는다(verify=False).
시험에서는 가짜 skill_env 로 .env 읽기를 막고, 시험이 끝나면 requests 를 되돌린다.
소스는 고치지 않는다. 현재 동작과 다르게 기대하는 것은 xfail 로 표시하고 이유를 적었다.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest
import requests

SKILL_DIR = Path(__file__).resolve().parents[1]


def _load(module_name, filename, monkeypatch):
    stub = types.ModuleType("skill_env")
    stub.load_env = lambda *a, **k: None
    stub.data_dir = lambda *a, **k: SKILL_DIR
    monkeypatch.setitem(sys.modules, "skill_env", stub)
    # 스크립트가 requests.Session.request 를 바꾸므로 시험 뒤에 원래대로
    monkeypatch.setattr(requests.Session, "request", requests.Session.request)
    spec = importlib.util.spec_from_file_location(module_name, SKILL_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def sync_books(monkeypatch):
    return _load("t_add_and_sync_books", "add_and_sync_books.py", monkeypatch)


@pytest.fixture
def lib_sync(monkeypatch):
    return _load("t_library_notion_sync", "library_notion_sync.py", monkeypatch)


@pytest.fixture
def import_books(monkeypatch):
    return _load("t_import_books", "import_books.py", monkeypatch)


@pytest.fixture
def request_books(monkeypatch):
    return _load("t_request_books", "request_books.py", monkeypatch)


# ── add_and_sync_books: _normalize / _title_score ──────────────

def test_normalize_removes_spaces_and_marks_and_lowercases(sync_books):
    assert sync_books._normalize("The Book: Part-1 (개정판)") == "thebookpart1개정판"


def test_normalize_empty(sync_books):
    assert sync_books._normalize("") == ""


def test_title_score_exact_match_ignores_spaces_and_case(sync_books):
    assert sync_books._title_score("Hello World", "hello-world") == 1.0


def test_title_score_contains(sync_books):
    assert sync_books._title_score("어린왕자", "어린왕자 (특별판)") == 0.8
    assert sync_books._title_score("어린왕자 (특별판)", "어린왕자") == 0.8


def test_title_score_empty_is_zero(sync_books):
    assert sync_books._title_score("", "어린왕자") == 0.0
    assert sync_books._title_score("어린왕자", "") == 0.0
    assert sync_books._title_score("()", "어린왕자") == 0.0  # 정규화하면 빈 글


def test_title_score_common_letter_ratio(sync_books):
    # 'abcd' 와 'abxy': 공통 글자 a,b → 2/4
    assert sync_books._title_score("abcd", "abxy") == pytest.approx(0.5)


def test_title_score_in_range(sync_books):
    s = sync_books._title_score("전혀 다른 제목", "xyz")
    assert 0.0 <= s <= 1.0


@pytest.mark.xfail(
    reason="공통 글자 비율이 순서·개수를 보지 않아 글자만 같고 순서가 다른 제목('abcabc' 와 'cbacba')도 1.0 이 된다. "
    "낱글자 비교 방식의 한계.",
    strict=False,
)
def test_title_score_same_letters_different_order_is_not_perfect(sync_books):
    assert sync_books._title_score("abcabc", "cbacba") < 1.0


# ── extract_text_from_property (add_and_sync_books / request_books) ──

@pytest.mark.parametrize("fixture_name", ["sync_books", "request_books"])
def test_extract_text_title_and_rich_text(fixture_name, request):
    mod = request.getfixturevalue(fixture_name)
    title = {"type": "title", "title": [{"plain_text": " 학생"}, {"plain_text": "A의 책 "}]}
    rich = {"type": "rich_text", "rich_text": [{"plain_text": "저자"}, {"plain_text": "X"}]}
    assert mod.extract_text_from_property(title) == "학생A의 책"
    assert mod.extract_text_from_property(rich) == "저자X"


@pytest.mark.parametrize("fixture_name", ["sync_books", "request_books"])
def test_extract_text_empty_and_unknown_type(fixture_name, request):
    mod = request.getfixturevalue(fixture_name)
    assert mod.extract_text_from_property(None) == ""
    assert mod.extract_text_from_property({}) == ""
    assert mod.extract_text_from_property({"type": "number", "number": 3}) == ""
    assert mod.extract_text_from_property({"type": "title", "title": []}) == ""


def test_extract_text_url_only_in_sync_books(sync_books):
    assert sync_books.extract_text_from_property({"type": "url", "url": "https://example.com/a"}) == "https://example.com/a"
    assert sync_books.extract_text_from_property({"type": "url", "url": None}) == ""


# ── library_notion_sync.extract_library_tags ───────────────────

def test_library_tags_mapping(lib_sync):
    names = ["경주시립 단석도서관", "송화도서관", "전자도서관", "오디오북 서비스", "중앙도서관"]
    tags = lib_sync.extract_library_tags(names)
    assert tags == [{"name": "단석"}, {"name": "송화"}, {"name": "전자"}, {"name": "시립"}]


def test_library_tags_dedup_keeps_first_order(lib_sync):
    tags = lib_sync.extract_library_tags(["전자책", "웹진", "송화", "송화 어린이"])
    assert tags == [{"name": "전자"}, {"name": "송화"}]


def test_library_tags_empty(lib_sync):
    assert lib_sync.extract_library_tags([]) == []


def test_library_tags_dansuk_wins_over_other_words(lib_sync):
    # '단석' 이 먼저 검사되므로 '전자' 가 같이 있어도 단석
    assert lib_sync.extract_library_tags(["단석 전자자료실"]) == [{"name": "단석"}]


# ── import_books.parse_text_file ───────────────────────────────

def _write(tmp_path, text):
    p = tmp_path / "books.txt"
    p.write_text(text, encoding="utf-8")
    return p


def test_parse_text_file_basic(import_books, tmp_path):
    p = _write(tmp_path, "책 제목 하나\n저자A\nhttps://example.com/a\n책 제목 둘\nlink.coupang.com/xyz\n")
    books = import_books.parse_text_file(str(p))
    assert len(books) == 2
    assert books[0]["raw_text"] == "책 제목 하나 저자A"
    assert books[0]["url"] == "https://example.com/a"
    assert books[0]["author"] == ""
    assert books[1]["raw_text"] == "책 제목 둘"
    assert books[1]["url"] == "link.coupang.com/xyz"


def test_parse_text_file_removes_stock_notice_and_blank_lines(import_books, tmp_path):
    p = _write(tmp_path, "\n책 제목\n\n재고 한정\nhttps://example.com/b\n")
    books = import_books.parse_text_file(str(p))
    assert [b["raw_text"] for b in books] == ["책 제목"]


def test_parse_text_file_text_without_url_is_dropped(import_books, tmp_path):
    p = _write(tmp_path, "주소 없는 책\n")
    assert import_books.parse_text_file(str(p)) == []


def test_parse_text_file_empty_file(import_books, tmp_path):
    assert import_books.parse_text_file(str(_write(tmp_path, ""))) == []


@pytest.mark.xfail(
    reason="줄 안에 '제목 + URL' 이 같이 있으면 그 앞 글은 버려지고 이전에 모은 글만 제목이 된다(제목이 비어 나옴).",
    strict=False,
)
def test_parse_text_file_title_and_url_on_same_line(import_books, tmp_path):
    p = _write(tmp_path, "책 제목 https://example.com/c\n")
    books = import_books.parse_text_file(str(p))
    assert books and "책 제목" in books[0]["raw_text"]


# ── request_books.load_library_accounts / get_books_to_request ──

def test_load_library_accounts_reads_numbered_env(request_books, monkeypatch):
    for i in range(1, 11):
        monkeypatch.delenv(f"LIBRARY_ACCOUNT_{i}_ID", raising=False)
        monkeypatch.delenv(f"LIBRARY_ACCOUNT_{i}_PW", raising=False)
    monkeypatch.setenv("LIBRARY_ACCOUNT_1_ID", "idA")
    monkeypatch.setenv("LIBRARY_ACCOUNT_1_PW", "pwA")
    monkeypatch.setenv("LIBRARY_ACCOUNT_2_ID", "idB")  # 비밀번호 없음 → 건너뜀
    monkeypatch.setenv("LIBRARY_ACCOUNT_3_ID", "idC")
    monkeypatch.setenv("LIBRARY_ACCOUNT_3_PW", "pwC")
    assert request_books.load_library_accounts() == [
        {"id": "idA", "pw": "pwA"},
        {"id": "idC", "pw": "pwC"},
    ]


def test_load_library_accounts_none(request_books, monkeypatch):
    for i in range(1, 11):
        monkeypatch.delenv(f"LIBRARY_ACCOUNT_{i}_ID", raising=False)
        monkeypatch.delenv(f"LIBRARY_ACCOUNT_{i}_PW", raising=False)
    assert request_books.load_library_accounts() == []


def _page(pid, title, author="저자", isbn="000"):
    def t(text):
        return {"type": "title", "title": [{"plain_text": text}]}
    def r(text):
        return {"type": "rich_text", "rich_text": [{"plain_text": text}]}
    return {"id": pid, "properties": {"제목": t(title), "저자": r(author), "ISBN": r(isbn)}}


def test_get_books_to_request_pages_and_skips_untitled(request_books, monkeypatch):
    calls = []
    responses = [
        {"results": [_page("p1", "책1"), _page("p2", "")], "has_more": True, "next_cursor": "c2"},
        {"results": [_page("p3", "책3")], "has_more": False},
    ]

    def fake_api(method, endpoint, payload=None):
        calls.append((method, endpoint, dict(payload or {})))
        return responses[len(calls) - 1]

    monkeypatch.setattr(request_books, "call_notion_api", fake_api)
    books = request_books.get_books_to_request()
    assert [b["page_id"] for b in books] == ["p1", "p3"]
    assert calls[0][2]["filter"]["multi_select"]["contains"] == "미소장"
    assert calls[1][2]["start_cursor"] == "c2"


def test_get_books_to_request_title_filter_has_no_notion_filter(request_books, monkeypatch):
    seen = {}

    def fake_api(method, endpoint, payload=None):
        seen.update(payload)
        return {"results": [_page("p1", "Python 책"), _page("p2", "다른 책")], "has_more": False}

    monkeypatch.setattr(request_books, "call_notion_api", fake_api)
    books = request_books.get_books_to_request(title_filter="python")
    assert "filter" not in seen
    assert [b["title"] for b in books] == ["Python 책"]


def test_get_books_to_request_stops_when_api_returns_nothing(request_books, monkeypatch):
    monkeypatch.setattr(request_books, "call_notion_api", lambda *a, **k: None)
    assert request_books.get_books_to_request() == []
