"""util-pdf-translator scripts/*.py 순수 함수·흐름 시험 (T08)

- 네트워크·비밀값·실제 PDF·실제 Discord 없이 가짜(mock)로만 시험한다.
- PyMuPDF(fitz)·requests 는 가짜 모듈로 바꿔 끼운다(설치되어 있지 않아도 돈다).
- 스크립트 이름이 숫자로 시작해서(01_…, 03_…) importlib 로 파일 경로에서 불러온다.
- 불러올 때 중앙 .env 읽기(load_env)는 꺼 둔다 → 교사 PC 의 실제 키가 시험에 섞이지 않는다.
- 소스는 고치지 않는다. 버그로 보이는 것은 xfail(strict) 로 남기고 ISSUES.md 에 적었다.

실행: python -m pytest skills/util-pdf-translator/tests -q
"""

from __future__ import annotations

import builtins
import importlib.util
import json
import re
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
SHARED = SKILL_DIR.parent / "_shared"

FAKE_WEBHOOK = "https://example.invalid/webhook"


# ───────── 불러오기 도우미 ─────────

def _load_script(filename: str, module_name: str):
    """scripts/<filename> 을 불러온다. 중앙 .env 읽기(load_env)는 빈 함수로 바꿔 둔다."""
    if str(SHARED) not in sys.path:
        sys.path.insert(0, str(SHARED))
    import skill_env

    original = skill_env.load_env
    skill_env.load_env = lambda *args, **kwargs: None
    try:
        spec = importlib.util.spec_from_file_location(module_name, SCRIPTS / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        skill_env.load_env = original
    return module


def _ensure_requests_stub():
    """requests 가 없으면 빈 가짜 모듈을 넣는다(03_send_discord.py 가 import 함)."""
    try:
        import requests  # noqa: F401
    except ImportError:
        sys.modules["requests"] = types.ModuleType("requests")
    import requests as module

    return module


@pytest.fixture(scope="module")
def toc_mod():
    return _load_script("01_setup_toc.py", "pdf_setup_toc")


@pytest.fixture(scope="module")
def extract_mod():
    return _load_script("extract_chapter.py", "pdf_extract_chapter")


@pytest.fixture(scope="module")
def discord_mod():
    _ensure_requests_stub()
    return _load_script("03_send_discord.py", "pdf_send_discord")


@pytest.fixture(scope="module")
def daily_mod():
    return _load_script("run_daily.py", "pdf_run_daily")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """시험 중에는 실제 설정값이 새어 들어오지 않게 비운다."""
    for key in ("PDF_PATH", "DISCORD_WEBHOOK_URL", "CHAPTER_EMOJI", "GEMS_URL"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    """어떤 시험도 진짜 requests.post 를 부를 수 없게 막는다."""
    requests_mod = _ensure_requests_stub()

    def _blocked(*args, **kwargs):
        raise AssertionError("시험에서 실제 네트워크 요청을 하면 안 됨")

    monkeypatch.setattr(requests_mod, "post", _blocked, raising=False)


# ───────── 가짜 PyMuPDF(fitz) ─────────

class FakePage:
    def __init__(self, text: str = "", blocks: list | None = None):
        self._text = text
        self._blocks = blocks or []

    def get_text(self, mode: str):
        if mode == "dict":
            return {"blocks": self._blocks}
        return self._text


class FakeDoc:
    def __init__(self, pages: list[FakePage]):
        self.pages = pages
        self.closed = False

    def __len__(self):
        return len(self.pages)

    def __getitem__(self, index):
        return self.pages[index]

    def close(self):
        self.closed = True


def install_fake_fitz(monkeypatch, pages: list[FakePage]) -> list[FakeDoc]:
    """sys.modules['fitz'] 를 가짜로 바꾼다. 열린 문서 목록을 돌려준다."""
    opened: list[FakeDoc] = []
    module = types.ModuleType("fitz")

    def fake_open(path):
        doc = FakeDoc(pages)
        doc.path = path
        opened.append(doc)
        return doc

    module.open = fake_open
    monkeypatch.setitem(sys.modules, "fitz", module)
    return opened


def text_block(text: str, size: float) -> dict:
    return {"type": 0, "lines": [{"spans": [{"text": text, "size": size}]}]}


def image_block() -> dict:
    return {"type": 1, "lines": [{"spans": [{"text": "Chapter 9", "size": 40}]}]}


def feed_input(monkeypatch, answers: list[str]):
    """input() 에 미리 정한 답을 차례로 넣는다. 답이 모자라면 시험 실패."""
    queue = list(answers)

    def fake_input(prompt=""):
        if not queue:
            raise AssertionError(f"입력이 모자람: {prompt!r}")
        return queue.pop(0)

    monkeypatch.setattr(builtins, "input", fake_input)
    return queue


def no_input(monkeypatch):
    def fail(prompt=""):
        raise AssertionError(f"입력을 물으면 안 되는 상황: {prompt!r}")

    monkeypatch.setattr(builtins, "input", fail)


def run_main(module, monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["script", *argv])
    module.main()


# ═════════════════ 01_setup_toc.py ═════════════════

def _matches_any_pattern(toc_mod, text: str) -> bool:
    return any(re.match(p, text, re.IGNORECASE) for p in toc_mod.CHAPTER_PATTERNS)


@pytest.mark.parametrize("text", [
    "Chapter 1", "CHAPTER 12", "chapter 3: Foo", "챕터 5", "Part 2", "PART 4",
    "1. Introduction", "12. Results", "Section 7",
])
def test_챕터_제목_모양은_감지한다(toc_mod, text):
    assert _matches_any_pattern(toc_mod, text)


@pytest.mark.parametrize("text", [
    "Chapter One",      # 숫자를 영어 낱말로 쓰면 감지 못 함(현재 동작)
    "Chapters 1", "Chapter", "Introduction", "챕터5", "1.Introduction",
    "Appendix 1", "Page 5", "",
])
def test_챕터_제목이_아닌_모양은_감지하지_않는다(toc_mod, text):
    assert not _matches_any_pattern(toc_mod, text)


def test_detect_chapters_auto_폰트14이상_패턴_맞는_것만_모은다(toc_mod, monkeypatch):
    pages = [
        FakePage(blocks=[text_block("Chapter 1", 20), image_block()]),   # 1쪽: 이미지 블록은 무시
        FakePage(blocks=[text_block("Chapter 2", 13.9)]),                # 2쪽: 폰트가 작아서 제외
        FakePage(blocks=[text_block("2. Methods", 14)]),                 # 3쪽: 정확히 14 는 포함
        FakePage(blocks=[text_block("  Part 3  ", 16.04)]),              # 4쪽: 앞뒤 공백 제거
        FakePage(blocks=[text_block("Introduction", 30)]),               # 5쪽: 패턴 아님
    ]
    opened = install_fake_fitz(monkeypatch, pages)

    found = toc_mod.detect_chapters_auto("book.pdf")

    assert found == [
        {"page": 1, "text": "Chapter 1", "font_size": 20},
        {"page": 3, "text": "2. Methods", "font_size": 14},
        {"page": 4, "text": "Part 3", "font_size": 16.0},
    ]
    assert opened[0].closed is True


def test_detect_chapters_auto_PyMuPDF가_없으면_안내하고_종료(toc_mod, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "fitz", None)  # import fitz → ImportError
    with pytest.raises(SystemExit) as exc:
        toc_mod.detect_chapters_auto("book.pdf")
    assert exc.value.code == 1
    assert "PyMuPDF" in capsys.readouterr().out


def test_save_toc_load_toc_한글_그대로_저장하고_다시_읽는다(toc_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    chapters = [{"chapter": 1, "title": "서문", "start_page": 3, "end_page": 20}]
    toc_mod.save_toc(chapters)
    raw = (tmp_path / "toc.json").read_text(encoding="utf-8")
    assert "서문" in raw and "\\u" not in raw  # ensure_ascii=False
    assert toc_mod.load_toc() == chapters


def test_load_toc_파일이_없으면_빈_목록(toc_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "없음.json")
    assert toc_mod.load_toc() == []


def test_show_toc_비어_있으면_안내(toc_mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    toc_mod.show_toc()
    assert "toc.json이 없거나 비어있습니다" in capsys.readouterr().out


def test_show_toc_끝쪽_항목이_없으면_물음표(toc_mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    toc_mod.save_toc([
        {"chapter": 1, "title": "첫째", "start_page": 5, "end_page": 9},
        {"chapter": 3, "title": "셋째", "start_page": 20},
    ])
    capsys.readouterr()
    toc_mod.show_toc()
    out = capsys.readouterr().out
    assert "첫째" in out and "셋째" in out
    assert out.count("?") == 1


def test_show_toc_끝쪽이_null_이어도_물음표로_보여야_한다(toc_mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    toc_mod.save_toc([{"chapter": 2, "title": "둘째", "start_page": 10, "end_page": None}])
    capsys.readouterr()
    toc_mod.show_toc()
    out = capsys.readouterr().out
    assert "None" not in out and "?" in out


def _six_page_book(monkeypatch):
    """제목이 1·3·5쪽에 있는 6쪽짜리 가짜 책."""
    pages = [
        FakePage(blocks=[text_block("Chapter 1", 20)]),
        FakePage(),
        FakePage(blocks=[text_block("Chapter 2", 20)]),
        FakePage(),
        FakePage(blocks=[text_block("Chapter 3", 20)]),
        FakePage(),
    ]
    return install_fake_fitz(monkeypatch, pages)


def test_auto_mode_후보가_없으면_저장하지_않고_수동_안내(toc_mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    install_fake_fitz(monkeypatch, [FakePage(blocks=[text_block("본문", 10)])])
    no_input(monkeypatch)
    toc_mod.auto_mode("book.pdf")
    assert not (tmp_path / "toc.json").exists()
    assert "--manual" in capsys.readouterr().out


def test_auto_mode_all_은_끝쪽을_다음_챕터_시작_앞쪽으로(toc_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    _six_page_book(monkeypatch)
    feed_input(monkeypatch, ["all"])
    toc_mod.auto_mode("book.pdf")
    assert toc_mod.load_toc() == [
        {"chapter": 1, "title": "Chapter 1", "start_page": 1, "end_page": 2},
        {"chapter": 2, "title": "Chapter 2", "start_page": 3, "end_page": 4},
        {"chapter": 3, "title": "Chapter 3", "start_page": 5, "end_page": 6},
    ]


def test_auto_mode_번호를_골라_쓰면_번호를_다시_매긴다(toc_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    _six_page_book(monkeypatch)
    feed_input(monkeypatch, ["1, 3"])
    toc_mod.auto_mode("book.pdf")
    assert toc_mod.load_toc() == [
        {"chapter": 1, "title": "Chapter 1", "start_page": 1, "end_page": 4},
        {"chapter": 2, "title": "Chapter 3", "start_page": 5, "end_page": 6},
    ]


@pytest.mark.parametrize("answer", ["skip", "SKIP", "abc", "1,x"])
def test_auto_mode_취소하거나_잘못된_입력이면_저장하지_않는다(toc_mod, monkeypatch, tmp_path, answer):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    _six_page_book(monkeypatch)
    feed_input(monkeypatch, [answer])
    toc_mod.auto_mode("book.pdf")
    assert not (tmp_path / "toc.json").exists()


def test_auto_mode_범위_밖_번호만_골라도_기존_목차를_지우지_않아야_한다(toc_mod, monkeypatch, tmp_path):
    toc_path = tmp_path / "toc.json"
    monkeypatch.setattr(toc_mod, "TOC_PATH", toc_path)
    existing = [{"chapter": 1, "title": "기존", "start_page": 1, "end_page": 9}]
    toc_path.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
    _six_page_book(monkeypatch)
    feed_input(monkeypatch, ["9"])  # 후보는 3개뿐
    toc_mod.auto_mode("book.pdf")
    assert json.loads(toc_path.read_text(encoding="utf-8")) == existing


def test_manual_mode_끝쪽을_비우면_다음_챕터_시작_앞쪽으로_채운다(toc_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    feed_input(monkeypatch, ["첫째", "1", "", "둘째", "10", "20", ""])
    toc_mod.manual_mode()
    assert toc_mod.load_toc() == [
        {"chapter": 1, "title": "첫째", "start_page": 1, "end_page": 9},
        {"chapter": 2, "title": "둘째", "start_page": 10, "end_page": 20},
    ]


def test_manual_mode_시작쪽이_숫자가_아니면_다시_묻는다(toc_mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    feed_input(monkeypatch, ["첫째", "x", "5", "7", ""])
    toc_mod.manual_mode()
    assert "숫자를 입력해주세요" in capsys.readouterr().out
    assert toc_mod.load_toc() == [{"chapter": 1, "title": "첫째", "start_page": 5, "end_page": 7}]


def test_manual_mode_PDF_쪽수를_알면_마지막_끝쪽을_채운다(toc_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-fake")
    monkeypatch.setenv("PDF_PATH", str(pdf))
    install_fake_fitz(monkeypatch, [FakePage() for _ in range(30)])
    feed_input(monkeypatch, ["첫째", "3", "", ""])
    toc_mod.manual_mode()
    assert toc_mod.load_toc() == [{"chapter": 1, "title": "첫째", "start_page": 3, "end_page": 30}]


def test_manual_mode_PDF_쪽수를_모르면_마지막_끝쪽은_비워_둔다(toc_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    feed_input(monkeypatch, ["첫째", "3", "", ""])
    toc_mod.manual_mode()
    assert toc_mod.load_toc() == [{"chapter": 1, "title": "첫째", "start_page": 3, "end_page": None}]


def _existing_two_chapters(toc_mod, tmp_path):
    toc_path = tmp_path / "toc.json"
    existing = [
        {"chapter": 1, "title": "하나", "start_page": 1, "end_page": 9},
        {"chapter": 2, "title": "둘", "start_page": 10, "end_page": 19},
    ]
    toc_path.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")
    return toc_path, existing


def test_manual_mode_이어서_추가하면_번호가_이어진다(toc_mod, monkeypatch, tmp_path):
    toc_path, existing = _existing_two_chapters(toc_mod, tmp_path)
    monkeypatch.setattr(toc_mod, "TOC_PATH", toc_path)
    feed_input(monkeypatch, ["y", "셋", "20", "29", ""])
    toc_mod.manual_mode()
    saved = json.loads(toc_path.read_text(encoding="utf-8"))
    assert saved[:2] == existing
    assert saved[2] == {"chapter": 3, "title": "셋", "start_page": 20, "end_page": 29}


def test_manual_mode_이어서_추가인데_새로_입력이_없으면_그대로(toc_mod, monkeypatch, tmp_path, capsys):
    toc_path, existing = _existing_two_chapters(toc_mod, tmp_path)
    monkeypatch.setattr(toc_mod, "TOC_PATH", toc_path)
    feed_input(monkeypatch, ["y", ""])
    toc_mod.manual_mode()
    assert "변경사항이 없습니다" in capsys.readouterr().out
    assert json.loads(toc_path.read_text(encoding="utf-8")) == existing


def test_manual_mode_처음부터_다시_입력하면_새_목차로_바뀐다(toc_mod, monkeypatch, tmp_path):
    """기존보다 많은 챕터를 새로 입력하면 새 목차로 저장된다(이 경우는 잘 동작)."""
    toc_path, _ = _existing_two_chapters(toc_mod, tmp_path)
    monkeypatch.setattr(toc_mod, "TOC_PATH", toc_path)
    feed_input(monkeypatch, ["n", "가", "1", "5", "나", "6", "9", "다", "10", "12", ""])
    toc_mod.manual_mode()
    saved = json.loads(toc_path.read_text(encoding="utf-8"))
    assert [c["title"] for c in saved] == ["가", "나", "다"]
    assert [c["chapter"] for c in saved] == [1, 2, 3]


def test_manual_mode_처음부터_다시_입력한_챕터가_기존보다_적어도_저장되어야_한다(toc_mod, monkeypatch, tmp_path):
    toc_path, _ = _existing_two_chapters(toc_mod, tmp_path)
    monkeypatch.setattr(toc_mod, "TOC_PATH", toc_path)
    feed_input(monkeypatch, ["n", "새로", "1", "30", ""])
    toc_mod.manual_mode()
    saved = json.loads(toc_path.read_text(encoding="utf-8"))
    assert [c["title"] for c in saved] == ["새로"]


def test_toc_main_show_는_목차를_출력(toc_mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(toc_mod, "TOC_PATH", tmp_path / "toc.json")
    toc_mod.save_toc([{"chapter": 1, "title": "서문", "start_page": 1, "end_page": 2}])
    capsys.readouterr()
    run_main(toc_mod, monkeypatch, "--show")
    assert "서문" in capsys.readouterr().out


def test_toc_main_auto_인데_PDF_경로가_없으면_종료(toc_mod, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run_main(toc_mod, monkeypatch, "--auto")
    assert exc.value.code == 1
    assert "PDF 경로가 필요" in capsys.readouterr().out


def test_toc_main_auto_인데_PDF_파일이_없으면_종료(toc_mod, monkeypatch, tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        run_main(toc_mod, monkeypatch, "--auto", "--pdf", str(tmp_path / "없는.pdf"))
    assert exc.value.code == 1
    assert "찾을 수 없습니다" in capsys.readouterr().out


def test_toc_main_auto_는_pdf옵션이_환경변수보다_먼저(toc_mod, monkeypatch, tmp_path):
    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    first.write_bytes(b"x")
    second.write_bytes(b"x")
    monkeypatch.setenv("PDF_PATH", str(second))
    seen = []
    monkeypatch.setattr(toc_mod, "auto_mode", lambda path: seen.append(path))
    run_main(toc_mod, monkeypatch, "--auto", "--pdf", str(first))
    run_main(toc_mod, monkeypatch, "--auto")
    assert seen == [str(first), str(second)]


def test_toc_main_옵션을_안_주거나_겹쳐_주면_argparse_오류(toc_mod, monkeypatch):
    for argv in ([], ["--auto", "--manual"]):
        with pytest.raises(SystemExit) as exc:
            run_main(toc_mod, monkeypatch, *argv)
        assert exc.value.code == 2


# ═════════════════ extract_chapter.py ═════════════════

def test_extract_load_toc_없으면_안내하고_종료(extract_mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(extract_mod, "TOC_PATH", tmp_path / "toc.json")
    with pytest.raises(SystemExit) as exc:
        extract_mod.load_toc()
    assert exc.value.code == 1
    assert "01_setup_toc.py" in capsys.readouterr().out


def test_extract_load_toc_읽기(extract_mod, monkeypatch, tmp_path):
    toc = [{"chapter": 1, "title": "서문", "start_page": 1, "end_page": 3}]
    (tmp_path / "toc.json").write_text(json.dumps(toc, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(extract_mod, "TOC_PATH", tmp_path / "toc.json")
    assert extract_mod.load_toc() == toc


def _pages(*texts):
    return [FakePage(text=t) for t in texts]


def test_extract_chapter_text_쪽번호는_1부터_끝쪽도_포함(extract_mod, monkeypatch):
    opened = install_fake_fitz(monkeypatch, _pages("p1", "p2", "p3", "p4"))
    assert extract_mod.extract_chapter_text("book.pdf", 2, 3) == "p2\np3"
    assert extract_mod.extract_chapter_text("book.pdf", 1, 1) == "p1"
    assert all(doc.closed for doc in opened)


def test_extract_chapter_text_끝쪽이_책보다_크면_마지막_쪽까지(extract_mod, monkeypatch):
    install_fake_fitz(monkeypatch, _pages("p1", "p2", "p3", "p4"))
    assert extract_mod.extract_chapter_text("book.pdf", 3, 99) == "p3\np4"


def test_extract_chapter_text_시작쪽이_책보다_크면_빈_글(extract_mod, monkeypatch):
    install_fake_fitz(monkeypatch, _pages("p1", "p2"))
    assert extract_mod.extract_chapter_text("book.pdf", 9, 12) == ""


def test_extract_chapter_text_PyMuPDF가_없으면_안내하고_종료(extract_mod, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "fitz", None)
    with pytest.raises(SystemExit) as exc:
        extract_mod.extract_chapter_text("book.pdf", 1, 2)
    assert exc.value.code == 1
    assert "PyMuPDF" in capsys.readouterr().out


@pytest.mark.parametrize("number, expected_name", [
    (1, "chapter_01.txt"), (9, "chapter_09.txt"), (12, "chapter_12.txt"), (123, "chapter_123.txt"),
])
def test_save_chapter_파일_이름은_두_자리로_채운다(extract_mod, monkeypatch, tmp_path, number, expected_name):
    monkeypatch.setattr(extract_mod, "OUTPUT_DIR", tmp_path / "output")
    out = extract_mod.save_chapter(number, "내용")
    assert out == tmp_path / "output" / expected_name
    assert out.read_text(encoding="utf-8") == "내용"


def test_save_chapter_폴더를_만들고_다시_쓰면_덮어쓴다(extract_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(extract_mod, "OUTPUT_DIR", tmp_path / "a" / "b" / "output")
    extract_mod.save_chapter(1, "처음")
    out = extract_mod.save_chapter(1, "나중")
    assert out.read_text(encoding="utf-8") == "나중"


@pytest.mark.parametrize("chapter, expected_range", [
    ({"chapter": 1, "title": "t", "start_page": 5, "end_page": 9}, (5, 9)),
    ({"chapter": 1, "title": "t", "start_page": 5, "end_page": None}, (5, 55)),   # 끝쪽 없음 → 시작+50
    ({"chapter": 1, "title": "t", "start_page": 5}, (5, 55)),
])
def test_process_chapter_끝쪽이_없으면_시작쪽에_50을_더한다(extract_mod, monkeypatch, tmp_path, chapter, expected_range):
    monkeypatch.setattr(extract_mod, "OUTPUT_DIR", tmp_path / "output")
    calls = []

    def fake_extract(pdf_path, start, end):
        calls.append((pdf_path, start, end))
        return "본문"

    monkeypatch.setattr(extract_mod, "extract_chapter_text", fake_extract)
    extract_mod.process_chapter(chapter, "book.pdf")
    assert calls == [("book.pdf", *expected_range)]
    assert (tmp_path / "output" / "chapter_01.txt").read_text(encoding="utf-8") == "본문"


def _extract_setup(extract_mod, monkeypatch, tmp_path):
    toc = [
        {"chapter": 1, "title": "하나", "start_page": 1, "end_page": 5},
        {"chapter": 2, "title": "둘", "start_page": 6, "end_page": 9},
    ]
    (tmp_path / "toc.json").write_text(json.dumps(toc, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(extract_mod, "TOC_PATH", tmp_path / "toc.json")
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-fake")
    done = []
    monkeypatch.setattr(extract_mod, "process_chapter", lambda chapter, pdf_path: done.append((chapter["chapter"], pdf_path)))
    return pdf, done


def test_extract_main_PDF를_못_찾으면_종료(extract_mod, monkeypatch, tmp_path, capsys):
    _extract_setup(extract_mod, monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        run_main(extract_mod, monkeypatch, "--chapter", "1")
    assert exc.value.code == 1
    assert "PDF 파일을 찾을 수 없습니다" in capsys.readouterr().out


def test_extract_main_챕터_하나(extract_mod, monkeypatch, tmp_path):
    pdf, done = _extract_setup(extract_mod, monkeypatch, tmp_path)
    run_main(extract_mod, monkeypatch, "--chapter", "2", "--pdf", str(pdf))
    assert done == [(2, str(pdf))]


@pytest.mark.parametrize("word", ["all", "ALL", "All"])
def test_extract_main_all_은_전체_챕터(extract_mod, monkeypatch, tmp_path, word):
    pdf, done = _extract_setup(extract_mod, monkeypatch, tmp_path)
    monkeypatch.setenv("PDF_PATH", str(pdf))
    run_main(extract_mod, monkeypatch, "--chapter", word)
    assert [num for num, _ in done] == [1, 2]


def test_extract_main_목차에_없는_챕터면_종료(extract_mod, monkeypatch, tmp_path, capsys):
    pdf, done = _extract_setup(extract_mod, monkeypatch, tmp_path)
    with pytest.raises(SystemExit) as exc:
        run_main(extract_mod, monkeypatch, "--chapter", "7", "--pdf", str(pdf))
    assert exc.value.code == 1
    assert done == []
    assert "챕터 7을 찾을 수 없습니다" in capsys.readouterr().out


# ═════════════════ 03_send_discord.py ═════════════════

def test_split_message_짧은_글은_한_덩어리(discord_mod):
    assert discord_mod.split_message("안녕하세요\n반갑습니다") == ["안녕하세요\n반갑습니다"]


@pytest.mark.parametrize("text", ["", "\n\n  \n", "   "])
def test_split_message_빈_글은_빈_목록(discord_mod, text):
    assert discord_mod.split_message(text) == []


def test_split_message_줄_단위로_나누고_한도를_넘지_않는다(discord_mod):
    line = "a" * 10
    chunks = discord_mod.split_message("\n".join([line] * 5), max_len=25)
    assert chunks == [f"{line}\n{line}", f"{line}\n{line}", line]
    assert all(len(c) <= 25 for c in chunks)


def test_split_message_기본_한도는_1900자(discord_mod):
    assert discord_mod.DISCORD_MAX_LEN == 1900
    text = "\n".join("가" * 50 for _ in range(200))
    chunks = discord_mod.split_message(text)
    assert len(chunks) > 1
    assert all(len(c) <= 1900 for c in chunks)


def test_split_message_글자_순서와_내용이_보존된다(discord_mod):
    text = "\n".join(f"문단{i}\n\n내용{i}" for i in range(60))
    chunks = discord_mod.split_message(text, max_len=80)
    original = [l for l in text.splitlines() if l.strip()]
    rebuilt = [l for c in chunks for l in c.splitlines() if l.strip()]
    assert rebuilt == original


def test_split_message_한도와_딱_맞는_한_줄(discord_mod):
    chunks = discord_mod.split_message("b" * 1900)
    assert chunks == ["b" * 1900]


def test_split_message_한도보다_긴_한_줄도_나눠야_한다(discord_mod):
    chunks = discord_mod.split_message("c" * 50, max_len=20)
    assert all(len(c) <= 20 for c in chunks)


def test_split_message_긴_줄은_낱말_사이에서_자르고_내용을_보존한다(discord_mod):
    line = " ".join(["가나다라"] * 30)
    chunks = discord_mod.split_message("머리\n" + line + "\n꼬리", max_len=23)
    assert all(0 < len(c) <= 23 for c in chunks)
    assert " ".join(chunks).split() == ["머리", *line.split(), "꼬리"]


class FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


def _patch_post(discord_mod, monkeypatch, status, text=""):
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse(status, text)

    monkeypatch.setattr(discord_mod.requests, "post", fake_post)
    return calls


@pytest.mark.parametrize("status", [200, 204])
def test_send_to_discord_성공_코드(discord_mod, monkeypatch, status):
    calls = _patch_post(discord_mod, monkeypatch, status)
    assert discord_mod.send_to_discord(FAKE_WEBHOOK, "안녕") is True
    assert calls == [{"url": FAKE_WEBHOOK, "json": {"content": "안녕"}, "timeout": 10}]


@pytest.mark.parametrize("status", [400, 404, 429, 500])
def test_send_to_discord_실패_코드는_False(discord_mod, monkeypatch, capsys, status):
    _patch_post(discord_mod, monkeypatch, status, "오류 내용")
    assert discord_mod.send_to_discord(FAKE_WEBHOOK, "안녕") is False
    out = capsys.readouterr().out
    assert f"HTTP {status}" in out and "오류 내용" in out


def test_discord_load_toc_없으면_빈_목록_있으면_읽는다(discord_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(discord_mod, "TOC_PATH", tmp_path / "toc.json")
    assert discord_mod.load_toc() == []
    toc = [{"chapter": 1, "title": "서문", "start_page": 1}]
    (tmp_path / "toc.json").write_text(json.dumps(toc, ensure_ascii=False), encoding="utf-8")
    assert discord_mod.load_toc() == toc


@pytest.mark.parametrize("number, name", [(1, "chapter_01_translated.txt"), (12, "chapter_12_translated.txt")])
def test_load_translated_text_두_자리_파일_이름(discord_mod, monkeypatch, tmp_path, number, name):
    monkeypatch.setattr(discord_mod, "OUTPUT_DIR", tmp_path)
    (tmp_path / name).write_text("번역문 한글", encoding="utf-8")
    assert discord_mod.load_translated_text(number) == "번역문 한글"


def test_load_translated_text_없으면_안내하고_종료(discord_mod, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(discord_mod, "OUTPUT_DIR", tmp_path)
    with pytest.raises(SystemExit) as exc:
        discord_mod.load_translated_text(3)
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "chapter_03_translated.txt" in out and "02_gems_translate.js" in out


def _chapter_files(discord_mod, monkeypatch, tmp_path, lines=200):
    toc = [{"chapter": 3, "title": "시험 제목", "start_page": 1, "end_page": 9}]
    (tmp_path / "toc.json").write_text(json.dumps(toc, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "chapter_03_translated.txt").write_text(
        "\n".join("가" * 50 for _ in range(lines)), encoding="utf-8")
    monkeypatch.setattr(discord_mod, "TOC_PATH", tmp_path / "toc.json")
    monkeypatch.setattr(discord_mod, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(discord_mod.time, "sleep", lambda *_: None)
    sent = []

    def fake_send(webhook_url, content):
        sent.append((webhook_url, content))
        return True

    monkeypatch.setattr(discord_mod, "send_to_discord", fake_send)
    return sent


def test_send_chapter_머리글_다음_본문_덩어리_순서로_보낸다(discord_mod, monkeypatch, tmp_path):
    sent = _chapter_files(discord_mod, monkeypatch, tmp_path)
    discord_mod.send_chapter(3, FAKE_WEBHOOK)
    assert all(url == FAKE_WEBHOOK for url, _ in sent)
    header = sent[0][1]
    assert header.startswith("📖 **챕터 3: 시험 제목**")
    body = [content for _, content in sent[1:]]
    assert len(body) > 1
    assert all(len(c) <= 1900 for c in body)


def test_send_chapter_이모지는_환경변수로_바꾼다(discord_mod, monkeypatch, tmp_path):
    sent = _chapter_files(discord_mod, monkeypatch, tmp_path, lines=3)
    monkeypatch.setenv("CHAPTER_EMOJI", "📚")
    discord_mod.send_chapter(3, FAKE_WEBHOOK)
    assert sent[0][1].startswith("📚 **챕터 3")


def test_send_chapter_목차에_없으면_제목을_Chapter_번호로(discord_mod, monkeypatch, tmp_path):
    sent = _chapter_files(discord_mod, monkeypatch, tmp_path, lines=3)
    (tmp_path / "chapter_05_translated.txt").write_text("본문", encoding="utf-8")
    discord_mod.send_chapter(5, FAKE_WEBHOOK)
    assert "챕터 5: Chapter 5" in sent[0][1]


def test_send_chapter_일부_전송이_실패해도_나머지를_계속_보낸다(discord_mod, monkeypatch, tmp_path, capsys):
    _chapter_files(discord_mod, monkeypatch, tmp_path)
    results = []

    def flaky_send(webhook_url, content):
        results.append(content)
        return len(results) != 2  # 두 번째(본문 첫 덩어리)만 실패

    monkeypatch.setattr(discord_mod, "send_to_discord", flaky_send)
    discord_mod.send_chapter(3, FAKE_WEBHOOK)
    out = capsys.readouterr().out
    assert "❌ 1/" in out
    assert len(results) > 2  # 실패 뒤에도 계속 보냄


def test_send_chapter_번역_파일이_없으면_머리글도_보내지_않고_종료(discord_mod, monkeypatch, tmp_path):
    sent = _chapter_files(discord_mod, monkeypatch, tmp_path)
    (tmp_path / "chapter_03_translated.txt").unlink()
    with pytest.raises(SystemExit):
        discord_mod.send_chapter(3, FAKE_WEBHOOK)
    assert sent == []


def test_discord_main_웹훅이_없으면_종료(discord_mod, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run_main(discord_mod, monkeypatch, "--chapter", "1")
    assert exc.value.code == 1
    assert "DISCORD_WEBHOOK_URL" in capsys.readouterr().out


def test_discord_main_웹훅은_webhook옵션이_환경변수보다_먼저(discord_mod, monkeypatch):
    seen = []
    monkeypatch.setattr(discord_mod, "send_chapter", lambda num, url: seen.append((num, url)))
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.invalid/from-env")
    run_main(discord_mod, monkeypatch, "--chapter", "4")
    run_main(discord_mod, monkeypatch, "--chapter", "5", "--webhook", FAKE_WEBHOOK)
    assert seen == [(4, "https://example.invalid/from-env"), (5, FAKE_WEBHOOK)]


def test_discord_main_chapter_는_필수(discord_mod, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        run_main(discord_mod, monkeypatch)
    assert exc.value.code == 2


# ═════════════════ run_daily.py ═════════════════

@pytest.mark.parametrize("code, expected", [(0, True), (1, False), (2, False)])
def test_run_종료_코드로_성공_실패를_알린다(daily_mod, monkeypatch, code, expected):
    seen = {}

    def fake_run(cmd, cwd=None):
        seen["cmd"], seen["cwd"] = cmd, cwd
        return SimpleNamespace(returncode=code)

    monkeypatch.setattr(daily_mod.subprocess, "run", fake_run)
    assert daily_mod.run(["echo", "x"], "설명") is expected
    assert seen == {"cmd": ["echo", "x"], "cwd": daily_mod.SCRIPT_DIR}


def _record_steps(daily_mod, monkeypatch, fail_at=None):
    steps = []

    def fake_run(cmd, desc):
        steps.append(cmd)
        return fail_at is None or len(steps) != fail_at

    monkeypatch.setattr(daily_mod, "run", fake_run)
    return steps


def test_run_daily_기본은_추출_번역_전송_세_단계(daily_mod, monkeypatch):
    steps = _record_steps(daily_mod, monkeypatch)
    run_main(daily_mod, monkeypatch, "--chapter", "4")
    assert steps == [
        [sys.executable, "extract_chapter.py", "--chapter", "4"],
        ["node", "02_gems_translate.js", "--chapter", "4"],
        [sys.executable, "03_send_discord.py", "--chapter", "4"],
    ]


def test_run_daily_건너뛰기_옵션(daily_mod, monkeypatch):
    steps = _record_steps(daily_mod, monkeypatch)
    run_main(daily_mod, monkeypatch, "--chapter", "1", "--skip-extract")
    assert [s[1] for s in steps] == ["02_gems_translate.js", "03_send_discord.py"]

    steps.clear()
    run_main(daily_mod, monkeypatch, "--chapter", "1", "--skip-translate")
    assert [s[1] for s in steps] == ["extract_chapter.py", "03_send_discord.py"]

    steps.clear()
    run_main(daily_mod, monkeypatch, "--chapter", "1", "--skip-extract", "--skip-translate")
    assert [s[1] for s in steps] == ["03_send_discord.py"]


@pytest.mark.parametrize("fail_at, expected_steps", [(1, 1), (2, 2), (3, 3)])
def test_run_daily_단계가_실패하면_그_뒤는_하지_않고_종료코드_1(daily_mod, monkeypatch, fail_at, expected_steps):
    steps = _record_steps(daily_mod, monkeypatch, fail_at=fail_at)
    with pytest.raises(SystemExit) as exc:
        run_main(daily_mod, monkeypatch, "--chapter", "2")
    assert exc.value.code == 1
    assert len(steps) == expected_steps


def test_run_daily_chapter_는_필수이고_숫자여야_한다(daily_mod, monkeypatch):
    for argv in ([], ["--chapter", "abc"]):
        with pytest.raises(SystemExit) as exc:
            run_main(daily_mod, monkeypatch, *argv)
        assert exc.value.code == 2
