"""personal-carrot 순수 함수 시험 (폰·Appium·구글시트·네트워크 없이, 가짜 자료만 사용).

- collector/models.py: parse_price, Product
- collector/extractor.py: 표 만들기, JSON·CSV 저장, 합치기
- storage/sqlite_db.py: 임시 폴더의 SQLite 로 중복 확인·통계·정리
- collector/daangn_app.py: 화면 글 → 상품 만들기, 걸러내기 (appium·selenium 은 가짜 모듈로 대신)
- main.py: get_keywords, parse_args

소스는 고치지 않는다. 현재 동작과 다르게 기대하는 것은 xfail 로 표시하고 이유를 적었다.
"""
import importlib
import importlib.util
import json
import sqlite3
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_DIR))

from collector.models import Product, parse_price  # noqa: E402
from collector import extractor  # noqa: E402
from storage.sqlite_db import DaangnDB  # noqa: E402


def make_product(title="레고 세트", price=10000, **kw):
    base = dict(
        title=title,
        price=price,
        price_text=f"{price:,}원",
        location="동구",
        time_text="3시간 전",
        keyword="레고",
    )
    base.update(kw)
    return Product(**base)


# ── parse_price ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "text, expected",
    [
        ("150,000원", 150000),
        ("150000", 150000),
        ("15만원", 150000),
        ("15만", 150000),
        ("1.5만원", 15000),
        ("1,500원", 1500),
        ("나눔", 0),
        ("무료나눔", 0),
        ("무료", 0),
        ("0원", 0),
        ("  20 000 원 ", 20000),
        ("가격미정", -1),
        ("", -1),
        (None, -1),
        ("만원", -1),
    ],
)
def test_parse_price(text, expected):
    assert parse_price(text) == expected


@pytest.mark.xfail(reason="'10만5천원' 에서 '10만' 만 읽어 100000 이 된다(5천을 놓침).", strict=False)
def test_parse_price_man_and_cheon():
    assert parse_price("10만5천원") == 105000


@pytest.mark.xfail(reason="'3천원' 은 숫자만 모아 3 이 된다(천 단위를 못 읽음).", strict=False)
def test_parse_price_cheon():
    assert parse_price("3천원") == 3000


@pytest.mark.xfail(reason="'1.2.3만원' 처럼 점이 여러 개면 float() 에서 ValueError 로 멈춘다.", strict=False)
def test_parse_price_malformed_number_does_not_crash():
    assert isinstance(parse_price("1.2.3만원"), int)  # 멈추지만 않으면 됨


# ── Product ────────────────────────────────────────────────────

def test_product_row_matches_header_length():
    p = make_product()
    assert len(p.to_sheet_row()) == len(Product.sheet_header())


def test_product_to_dict_keys():
    d = make_product().to_dict()
    assert set(d) == {
        "title", "price", "price_text", "location", "time_text",
        "url", "keyword", "status", "collected_at",
    }


def test_product_defaults():
    p = make_product()
    assert p.status == "판매중"
    assert p.url == ""
    datetime.fromisoformat(p.collected_at)  # 날짜 형식이면 통과


def test_product_sheet_row_order():
    p = make_product(title="제목", price=5000, url="https://example.com/1", status="예약중")
    row = p.to_sheet_row()
    assert row[1] == "레고"  # 키워드
    assert row[2] == "제목"
    assert row[3] == 5000
    assert row[7] == "https://example.com/1"
    assert row[8] == "예약중"


# ── extractor ──────────────────────────────────────────────────

def test_products_to_dataframe_column_order():
    df = extractor.products_to_dataframe([make_product()])
    assert list(df.columns) == [
        "collected_at", "keyword", "title", "price",
        "price_text", "location", "time_text", "url", "status",
    ]
    assert len(df) == 1


def test_products_to_dataframe_empty_has_no_rows():
    assert len(extractor.products_to_dataframe([])) == 0


@pytest.mark.xfail(
    reason="빈 목록의 열 이름은 한글 머리글(Product.sheet_header), 값이 있을 때는 영어 열 이름이라 서로 다르다.",
    strict=False,
)
def test_products_to_dataframe_empty_and_nonempty_columns_match():
    empty = extractor.products_to_dataframe([])
    full = extractor.products_to_dataframe([make_product()])
    assert list(empty.columns) == list(full.columns)


def test_save_to_json_roundtrip_and_name(tmp_path):
    path = extractor.save_to_json([make_product(title="한글 제목")], str(tmp_path), keyword="레고 스파이크")
    assert path.parent == tmp_path
    assert path.name.startswith("daangn_레고스파이크_") and path.suffix == ".json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["title"] == "한글 제목"
    assert "한글 제목" in path.read_text(encoding="utf-8")  # \u 로 깨지지 않음


def test_save_to_json_without_keyword_uses_all(tmp_path):
    path = extractor.save_to_json([], str(tmp_path))
    assert path.name.startswith("daangn_all_")
    assert json.loads(path.read_text(encoding="utf-8")) == []


def test_save_to_json_creates_missing_dir(tmp_path):
    out = tmp_path / "a" / "b"
    extractor.save_to_json([make_product()], str(out))
    assert out.is_dir()


def test_save_to_csv_utf8_sig_and_rows(tmp_path):
    path = extractor.save_to_csv([make_product(title="한글"), make_product(title="둘")], str(tmp_path), "레고")
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # 엑셀에서 한글이 깨지지 않게 BOM
    text = raw.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("collected_at,keyword,title")
    assert len(text.splitlines()) == 3


def _write_json(dirpath, name, items):
    (dirpath / name).write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def test_merge_json_files_missing_dir(tmp_path):
    assert extractor.merge_json_files(str(tmp_path / "없음")) == []


def test_merge_json_files_dedup_by_url_then_title_price(tmp_path):
    _write_json(tmp_path, "daangn_a_1.json", [
        {"title": "A", "price": 1, "url": "https://example.com/1"},
        {"title": "B", "price": 2, "url": ""},
    ])
    _write_json(tmp_path, "daangn_b_2.json", [
        {"title": "A다시", "price": 1, "url": "https://example.com/1"},  # 같은 URL
        {"title": "B", "price": 2, "url": ""},                            # 같은 제목+가격
        {"title": "B", "price": 3, "url": ""},                            # 가격 다름
    ])
    _write_json(tmp_path, "other.json", [{"title": "무시", "price": 0, "url": ""}])  # 이름이 daangn_ 이 아님
    merged = extractor.merge_json_files(str(tmp_path))
    assert [(m["title"], m["price"]) for m in merged] == [("A", 1), ("B", 2), ("B", 3)]


def test_print_summary_runs_for_empty_and_normal(capsys):
    extractor.print_summary([])
    assert "0건" in capsys.readouterr().out
    extractor.print_summary([make_product(price=10000), make_product(price=30000, keyword="마이크로비트")])
    out = capsys.readouterr().out
    assert "총 매물 수: 2건" in out
    assert "10,000원" in out and "30,000원" in out


def test_print_summary_free_items_only_does_not_crash(capsys):
    extractor.print_summary([make_product(price=0), make_product(price=-1)])
    assert "총 매물 수: 2건" in capsys.readouterr().out


# ── DaangnDB (SQLite, 임시 폴더) ──────────────────────────────

@pytest.fixture
def db(tmp_path):
    d = DaangnDB(str(tmp_path / "sub" / "t.db"))
    yield d
    d.close()


def test_db_creates_parent_dir_and_tables(db):
    names = {r[0] for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"products", "collection_logs"} <= names


def test_db_insert_dedup_by_url(db):
    a = make_product(url="https://example.com/1")
    b = make_product(title="다른 제목", url="https://example.com/1")
    assert db.insert_products([a, b]) == 1
    assert db.is_duplicate(b) is True


def test_db_dedup_without_url_uses_title_price_location(db):
    a = make_product(title="같은 글", price=5000, location="동구")
    assert db.insert_products([a]) == 1
    assert db.is_duplicate(make_product(title="같은 글", price=5000, location="동구")) is True
    assert db.is_duplicate(make_product(title="같은 글", price=6000, location="동구")) is False
    assert db.is_duplicate(make_product(title="같은 글", price=5000, location="서구")) is False


def test_db_filter_new_keeps_only_new(db, capsys):
    old = make_product(title="이미 있음")
    db.insert_products([old])
    new = make_product(title="새 것")
    result = db.filter_new([old, new])
    assert [p.title for p in result] == ["새 것"]
    assert "1건 스킵" in capsys.readouterr().out


def test_db_get_stats(db):
    db.insert_products([
        make_product(title="a", keyword="레고"),
        make_product(title="b", keyword="레고"),
        make_product(title="c", keyword="마이크로비트"),
    ])
    stats = db.get_stats()
    assert stats["total"] == 3
    assert stats["by_keyword"] == {"레고": 2, "마이크로비트": 1}
    assert stats["last_collected"]


def test_db_get_stats_empty(db):
    assert db.get_stats() == {"total": 0, "by_keyword": {}, "last_collected": None}


def test_db_log_collection(db):
    db.log_collection("레고", 7)
    row = db.conn.execute("SELECT keyword, count FROM collection_logs").fetchone()
    assert row == ("레고", 7)


def test_db_cleanup_old_removes_only_old(db):
    old_time = (datetime.now() - timedelta(days=60)).isoformat(timespec="seconds")
    new_time = datetime.now().isoformat(timespec="seconds")
    db.insert_products([
        make_product(title="오래됨", collected_at=old_time),
        make_product(title="최근", collected_at=new_time),
    ])
    assert db.cleanup_old(days=30) == 1
    titles = [r[0] for r in db.conn.execute("SELECT title FROM products")]
    assert titles == ["최근"]


def test_db_reopen_keeps_data(tmp_path):
    path = str(tmp_path / "r.db")
    d1 = DaangnDB(path)
    d1.insert_products([make_product(url="https://example.com/9")])
    d1.close()
    d2 = DaangnDB(path)
    try:
        assert d2.is_duplicate(make_product(url="https://example.com/9"))
    finally:
        d2.close()


def test_db_use_after_close_raises(tmp_path):
    d = DaangnDB(str(tmp_path / "c.db"))
    d.close()
    with pytest.raises(sqlite3.ProgrammingError):
        d.get_stats()


# ── DaangnApp / main (appium·selenium 가짜 모듈) ───────────────

def _fake_modules():
    def mod(name, **attrs):
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        return m

    class AppiumBy:
        ACCESSIBILITY_ID = "accessibility id"
        CLASS_NAME = "class name"
        XPATH = "xpath"

    class WebDriverWait:
        def __init__(self, *a, **k):
            pass

    class _Err(Exception):
        pass

    class TimeoutException(_Err): ...
    class NoSuchElementException(_Err): ...
    class StaleElementReferenceException(_Err): ...

    appium = mod("appium")
    a_webdriver = mod("appium.webdriver", Remote=object)
    a_common = mod("appium.webdriver.common")
    a_by = mod("appium.webdriver.common.appiumby", AppiumBy=AppiumBy)
    a_options = mod("appium.options")
    a_android = mod("appium.options.android", UiAutomator2Options=object)
    appium.webdriver = a_webdriver
    appium.options = a_options
    a_webdriver.common = a_common
    a_common.appiumby = a_by
    a_options.android = a_android

    selenium = mod("selenium")
    s_webdriver = mod("selenium.webdriver")
    s_support = mod("selenium.webdriver.support")
    s_ui = mod("selenium.webdriver.support.ui", WebDriverWait=WebDriverWait)
    s_ec = mod("selenium.webdriver.support.expected_conditions")
    s_common = mod("selenium.common")
    s_exc = mod(
        "selenium.common.exceptions",
        TimeoutException=TimeoutException,
        NoSuchElementException=NoSuchElementException,
        StaleElementReferenceException=StaleElementReferenceException,
    )
    selenium.webdriver = s_webdriver
    selenium.common = s_common
    s_webdriver.support = s_support
    s_support.ui = s_ui
    s_support.expected_conditions = s_ec
    s_common.exceptions = s_exc

    return {m.__name__: m for m in [
        appium, a_webdriver, a_common, a_by, a_options, a_android,
        selenium, s_webdriver, s_support, s_ui, s_ec, s_common, s_exc,
    ]}


@pytest.fixture
def stubbed(monkeypatch):
    """appium·selenium 을 가짜 모듈로 바꾸고 collector.daangn_app 을 불러온다."""
    for name, m in _fake_modules().items():
        monkeypatch.setitem(sys.modules, name, m)
    for name in ("collector.daangn_app", "collector.appium_driver"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    yield
    for name in ("collector.daangn_app", "collector.appium_driver"):
        sys.modules.pop(name, None)


@pytest.fixture
def app_cls(stubbed):
    return importlib.import_module("collector.daangn_app").DaangnApp


def make_app(app_cls, **collection):
    return app_cls(driver=object(), config={"collection": collection})


def test_app_reads_collection_config(app_cls):
    app = make_app(app_cls, max_scroll_count=9, exclude_sold=False, exclude_keywords=["구합니다"])
    assert app.max_scroll == 9
    assert app.exclude_sold is False
    assert app.exclude_kw == ["구합니다"]


def test_app_default_config_values(app_cls):
    app = app_cls(driver=object(), config={})
    assert app.max_scroll == 5 and app.exclude_sold is True and app.exclude_kw == []


@pytest.mark.parametrize(
    "text, expected",
    [
        ("150,000원", True), ("15만원", True), ("나눔", True), ("무료나눔", True),
        ("가격미정", True), ("1,500", True), ("100", True),
        ("12", False), ("", False), (None, False),
        ("3시간 전", False), ("부산진구 · 3시간 전", False), ("레고 스파이크", False),
    ],
)
def test_looks_like_price(app_cls, text, expected):
    assert app_cls._looks_like_price(text) is expected


@pytest.mark.xfail(
    reason="'원' 한 글자만 보므로 '수원시 · 3시간 전' 이나 '원피스 팝니다' 처럼 '원'이 든 지역·제목도 가격으로 읽는다.",
    strict=False,
)
@pytest.mark.parametrize("text", ["수원시 · 3시간 전", "원피스 팝니다"])
def test_looks_like_price_word_containing_won_is_not_price(app_cls, text):
    assert app_cls._looks_like_price(text) is False


def test_parse_product_texts_two_products(app_cls):
    app = make_app(app_cls)
    texts = [
        "레고 스파이크 프라임", "동구 · 1시간 전", "150,000원",
        "마이크로비트 세트", "서구 · 2시간 전", "나눔",
    ]
    products = app._parse_product_texts(texts, "레고")
    assert [(p.title, p.price, p.location, p.time_text) for p in products] == [
        ("레고 스파이크 프라임", 150000, "동구", "1시간 전"),
        ("마이크로비트 세트", 0, "서구", "2시간 전"),
    ]
    assert all(p.keyword == "레고" and p.status == "판매중" for p in products)


def test_parse_product_texts_picks_status_badge(app_cls):
    app = make_app(app_cls)
    texts = ["3D프린터 팝니다", "예약중", "남구 · 5분 전", "200,000원"]
    (p,) = app._parse_product_texts(texts, "3D프린터")
    assert p.status == "예약중" and p.title == "3D프린터 팝니다" and p.location == "남구"


def test_parse_product_texts_price_without_title_is_skipped(app_cls):
    app = make_app(app_cls)
    assert app._parse_product_texts(["10,000원"], "x") == []
    assert app._parse_product_texts([], "x") == []


def test_parse_product_texts_ignores_tab_names_and_short_text(app_cls):
    app = make_app(app_cls)
    # 위쪽 글이 탭 이름이거나 두 글자 이하면 제목으로 쓰지 않는다
    assert app._parse_product_texts(["중고거래", "10,000원"], "x") == []
    assert app._parse_product_texts(["ab", "10,000원"], "x") == []


def test_try_build_product_location_without_time(app_cls):
    app = make_app(app_cls)
    p = app._try_build_product(["제목이에요", "동구 ·", "5,000원"], 2, "k")
    assert p.location == "동구" and p.time_text == ""


def test_filter_products_excludes_sold_and_keywords(app_cls, capsys):
    app = make_app(app_cls, exclude_sold=True, exclude_keywords=["구합니다", "삽니다"])
    products = [
        make_product(title="좋은 상품"),
        make_product(title="판매 끝", status="판매완료"),
        make_product(title="레고 구합니다"),
        make_product(title="예약된 상품", status="예약중"),
    ]
    kept = app._filter_products(products)
    assert [p.title for p in kept] == ["좋은 상품", "예약된 상품"]
    assert "2건 제외" in capsys.readouterr().out


def test_filter_products_keeps_sold_when_disabled(app_cls):
    app = make_app(app_cls, exclude_sold=False)
    kept = app._filter_products([make_product(status="판매완료")])
    assert len(kept) == 1


@pytest.fixture
def main_mod(stubbed):
    spec = importlib.util.spec_from_file_location("t_carrot_main", SKILL_DIR / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_get_keywords_override_wins(main_mod):
    assert main_mod.get_keywords({"keywords": ["a", "b"]}, override="레고") == ["레고"]


def test_get_keywords_from_config_and_missing(main_mod):
    assert main_mod.get_keywords({"keywords": ["a", "b"]}) == ["a", "b"]
    assert main_mod.get_keywords({}) == []


def test_parse_args_flags(main_mod, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "-k", "레고", "--local-only", "--dry-run", "--no-db"])
    args = main_mod.parse_args()
    assert args.keyword == "레고" and args.local_only and args.dry_run and args.no_db


def test_parse_args_defaults(main_mod, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py"])
    args = main_mod.parse_args()
    assert args.keyword is None and not args.local_only and not args.dry_run and not args.no_db
