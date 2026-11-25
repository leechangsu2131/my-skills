"""skills/util-notebooklm/nlm.py 순수 함수 시험.

Gemini CLI 는 subprocess.run 을 가짜로 바꿔 부르지 않는다. PDF 는 PyMuPDF 로 시험용을 만든다.
"""
import json
import pathlib
import subprocess
import warnings

import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    fitz = pytest.importorskip("fitz")

import nlm  # noqa: E402

LONG_KO = "분수의 덧셈을 배우는 시간입니다. " * 6   # 한글 40자 이상 → 글자 있는 쪽


# ──────────────────────────── split_text ────────────────────────────

SAMPLE = """앞에 붙은 설명은 버린다
# 첫째
본문 1
## [수학 1단원] 1차시 덧셈
덧셈 본문
**굵은 제목**
굵은 본문
## 둘째 (표시 없음)
끝 본문
"""


def test_split_text_without_pattern_cuts_at_every_heading():
    parts = nlm.split_text(SAMPLE)
    assert [head for _, head, _ in parts] == [
        "# 첫째", "## [수학 1단원] 1차시 덧셈", "**굵은 제목**", "## 둘째 (표시 없음)"]
    assert all(m is None for m, _, _ in parts)            # 표시 없이 자를 때는 match 가 없다
    assert parts[0][2] == "# 첫째\n본문 1"                # 본문은 제목 줄부터, 앞뒤 공백 없음
    assert "앞에 붙은 설명" not in "".join(body for _, _, body in parts)


def test_split_text_with_pattern_keeps_other_headings_in_the_body():
    parts = nlm.split_text(SAMPLE, r"\[수학 \d단원\]\s*\d+차시")
    assert len(parts) == 1
    match, head, body = parts[0]
    assert match.group(0) == "[수학 1단원] 1차시" and head.startswith("## [수학")
    assert "**굵은 제목**" in body and "## 둘째" in body and body.endswith("끝 본문")


def test_split_text_accepts_compiled_pattern_and_returns_empty_when_nothing_matches():
    import re
    assert len(nlm.split_text(SAMPLE, re.compile("둘째"))) == 1
    assert nlm.split_text(SAMPLE, "없는표시") == []


def test_split_text_requires_space_after_hashes_and_ignores_empty_text():
    assert nlm.split_text("#해시태그만\n본문") == []
    assert nlm.split_text("") == []
    assert nlm.split_text("   # 들여쓴 제목\n글")[0][1] == "   # 들여쓴 제목"   # 앞 공백은 허용


# ──────────────────────────── page_refs ────────────────────────────

@pytest.mark.parametrize("text, expected", [
    ("근거 [p.3] 입니다", [3]),
    ("[p. 7]", [7]),
    ("[P.2]", []),                                   # 대문자 P 는 표시로 보지 않는다
    ("[p.3-5] 와 [p.9]", [3, 4, 5, 9]),
    ("[p.3~5]", [3, 4, 5]),
    ("[p.3∼5]", [3, 4, 5]),                          # 물결 모양이 다른 문자(∼)
    ("[p.4 - 6]", [4, 5, 6]),
    ("PDF 파일 12쪽에 있음", [12]),
    ("PDF 8쪽", [8]),
    ("[p.5] [p.5] PDF 5쪽", [5]),                    # 중복은 하나로
    ("[p.10] [p.2]", [2, 10]),                       # 오름차순
    ("[p.5-3]", [5]),                                # 거꾸로 쓴 범위는 시작 쪽만
    ("[p.0] [p.0-2]", [1, 2]),                       # 0쪽 이하는 버림
    ("없음", []),
    ("", []),
])
def test_page_refs(text, expected):
    assert nlm.page_refs(text) == expected


# ──────────────────────────── parse_pages ────────────────────────────

@pytest.mark.parametrize("spec, expected", [
    ("4,7-8", [4, 7, 8]),
    ("1-3, 5", [1, 2, 3, 5]),
    ("3 1 2", [1, 2, 3]),                            # 공백 구분
    ("5,5,4-6", [4, 5, 6]),                          # 중복 제거·정렬
    ("  9  ", [9]),
    ("3-", [3]),
    ("", []),
    ("8-4", []),                                     # 거꾸로 쓴 범위는 빈 목록
])
def test_parse_pages(spec, expected):
    assert nlm.parse_pages(spec) == expected


def test_parse_pages_rejects_non_numbers():
    with pytest.raises(ValueError):
        nlm.parse_pages("a-b")


# ──────────────────────────── compact ────────────────────────────

@pytest.mark.parametrize("pages, expected", [
    ([4], "4"),
    ([1, 2, 3], "1-3"),
    ([1, 2, 3, 5, 7, 8], "1-3,5,7-8"),
    ([2, 4, 6], "2,4,6"),
])
def test_compact(pages, expected):
    assert nlm.compact(pages) == expected


def test_compact_caps_length_for_file_names():
    assert len(nlm.compact(list(range(1, 400, 2)))) == 60


def test_compact_round_trips_with_parse_pages():
    pages = [1, 2, 3, 9, 11, 12, 40]
    assert nlm.parse_pages(nlm.compact(pages)) == pages


# ──────────────────────────── write_source (시험용 PDF) ────────────────────────────

def make_pdf(path: pathlib.Path, pages: list[tuple[str, tuple[float, float]]]) -> pathlib.Path:
    doc = fitz.open()
    for text, (w, h) in pages:
        page = doc.new_page(width=w, height=h)
        if text:
            page.insert_textbox(fitz.Rect(40, 40, w - 40, h - 40), text, fontname="korea", fontsize=11)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def guide_pdf(tmp_path):
    """1쪽: 글 많음(+ '#' 로 시작하는 줄·겹친 기호), 2쪽: 글 거의 없음(작은 종이), 3쪽: 글 많음."""
    first = "# 제목처럼 보이는 줄\n●●● 겹친 기호\n" + LONG_KO
    return make_pdf(tmp_path / "guide.pdf", [(first, (595, 842)), ("그림", (300, 400)), (LONG_KO, (595, 842))])


def section(pdf, pages, heading="## [수학 1단원] 1차시 덧셈", **extra):
    return {"heading": heading, "pdf": str(pdf), "pages": pages, **extra}


def test_write_source_text_pages_become_md_without_images(tmp_path, guide_pdf):
    md, img = tmp_path / "out" / "s.md", tmp_path / "out" / "s_그림.pdf"
    info = nlm.write_source(md, img, ["# 제목", "원본 표시"], [section(guide_pdf, [(0, 1), (2, 3)])])
    body = md.read_text(encoding="utf-8")
    assert body.startswith("# 제목\n원본 표시\n\n## [수학 1단원] 1차시 덧셈\n\n〔p.1〕\n")
    assert "〔p.3〕" in body and "분수의 덧셈을 배우는 시간입니다." in body
    assert "\\# 제목처럼 보이는 줄" in body            # 원문 '#' 줄은 md 제목으로 읽히지 않게 막는다
    assert "●●●" not in body and "● 겹친 기호" in body  # 겹친 기호는 하나로
    assert body.endswith("\n") and not body.endswith("\n\n")
    assert (info["low_pages"], info["gray_pages"], info["missing"], info["too_big"]) == (0, 0, 0, False)
    assert info["words"] == len(body.split())
    assert not img.exists()


def test_write_source_low_text_page_becomes_gray_picture_pdf(tmp_path, guide_pdf):
    md, img = tmp_path / "s.md", tmp_path / "s_그림.pdf"
    info = nlm.write_source(md, img, [], [section(guide_pdf, [(0, 1), (1, 2), (2, 3)])])
    body = md.read_text(encoding="utf-8")
    assert "〔p.2〕 (글자가 거의 없는 쪽 — 그림은 s_그림.pdf 참고)" in body
    assert "〔p.1〕\n" in body and "〔p.3〕\n" in body   # 글 있는 쪽은 그대로
    assert (info["low_pages"], info["gray_pages"]) == (1, 1)
    with fitz.open(img) as gray:
        assert gray.page_count == 1
        assert (gray[0].rect.width, gray[0].rect.height) == (300, 400)   # 원래 종이 크기 그대로
        (xref, *_), = gray[0].get_images()
        assert gray.extract_image(xref)["colorspace"] == 1              # 흑백(1채널) 그림


def test_write_source_images_all_and_none(tmp_path, guide_pdf):
    pages = [(0, 1), (1, 2), (2, 3)]
    info = nlm.write_source(tmp_path / "a.md", tmp_path / "a.pdf", [], [section(guide_pdf, pages)], images="all")
    assert info["gray_pages"] == 3 and info["low_pages"] == 1
    info = nlm.write_source(tmp_path / "n.md", tmp_path / "n.pdf", [], [section(guide_pdf, pages)], images="none")
    assert info["gray_pages"] == 0 and info["low_pages"] == 1
    assert not (tmp_path / "n.pdf").exists()
    assert "그림은" not in (tmp_path / "n.md").read_text(encoding="utf-8")   # 그림 PDF 가 없으면 안내도 빼기


def test_write_source_removes_stale_image_pdf_when_no_gray_pages(tmp_path, guide_pdf):
    img = tmp_path / "old_그림.pdf"
    img.write_bytes(b"%PDF-old")
    nlm.write_source(tmp_path / "o.md", img, [], [section(guide_pdf, [(0, 1)])])
    assert not img.exists()


def test_write_source_note_section_needs_no_pdf_and_counts_missing(tmp_path, guide_pdf):
    sections = [{"heading": "## [수학 1단원] 2차시 뺄셈", "pdf": "", "pages": [], "note": "PDF가 없어 건너뜀"},
                section(guide_pdf, [(0, 1)])]
    info = nlm.write_source(tmp_path / "n.md", tmp_path / "n.pdf", [], sections)
    body = (tmp_path / "n.md").read_text(encoding="utf-8")
    assert "## [수학 1단원] 2차시 뺄셈\n\nPDF가 없어 건너뜀" in body
    assert info["missing"] == 1


def test_write_source_uses_display_page_labels_and_empty_page_text(tmp_path):
    pdf = make_pdf(tmp_path / "blank.pdf", [("", (200, 200))])
    nlm.write_source(tmp_path / "b.md", tmp_path / "b.pdf", [], [section(pdf, [(0, 57)])])
    body = (tmp_path / "b.md").read_text(encoding="utf-8")
    assert "〔p.57〕 (글자가 거의 없는 쪽" in body and "〔p.1〕" not in body


def test_write_source_flags_too_many_words(tmp_path, guide_pdf, monkeypatch):
    monkeypatch.setattr(nlm, "WORD_LIMIT", 10)
    info = nlm.write_source(tmp_path / "w.md", tmp_path / "w.pdf", [], [section(guide_pdf, [(0, 1)])])
    assert info["too_big"] is True


def test_whole_section_numbers_every_page(tmp_path, guide_pdf):
    assert nlm.whole_section("## 전체", str(guide_pdf))["pages"] == [(0, 1), (1, 2), (2, 3)]
    assert nlm.whole_section("## 전체", str(guide_pdf), start_label=20)["pages"] == [(0, 20), (1, 21), (2, 22)]


# ──────────────────────────── gemini_ask: 모델 차례 바꾸기 ────────────────────────────

class FakeRun:
    """subprocess.run 대역. outcomes 를 차례로 쓴다: CompletedProcess 또는 던질 예외."""

    def __init__(self, *outcomes):
        self.outcomes, self.calls = list(outcomes), []

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        out = self.outcomes.pop(0)
        if isinstance(out, BaseException):
            raise out
        return out

    @property
    def models(self):
        return [cmd[cmd.index("-m") + 1] for cmd, _ in self.calls]


def done(stdout="", stderr="", code=0):
    return subprocess.CompletedProcess(["gemini"], code, stdout, stderr)


def timeout():
    return subprocess.TimeoutExpired(["gemini"], 120)


@pytest.fixture
def ask(tmp_path, monkeypatch):
    """gemini_ask 를 가짜 CLI·키 없음으로 부르는 도우미. (함수, work 폴더) 를 돌려준다."""
    src = tmp_path / "자료 원본.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    work = tmp_path / "work"
    monkeypatch.setattr(nlm, "gemini_command", lambda: ["gemini"])
    monkeypatch.setattr(nlm, "env_values", lambda *a, **k: {})
    monkeypatch.setattr(nlm, "LAST_MODEL", "")

    def call(fake, prompt="질문 {file}", **kw):
        monkeypatch.setattr(nlm.subprocess, "run", fake)
        return nlm.gemini_ask(src, prompt, work=work, **kw)
    return call, work


def test_gemini_ask_first_model_answers(ask):
    call, work = ask
    fake = FakeRun(done("  답입니다 \n"))
    assert call(fake) == "답입니다"
    assert fake.models == [nlm.DEFAULT_MODEL] and nlm.LAST_MODEL == nlm.DEFAULT_MODEL
    cmd, kw = fake.calls[0]
    assert cmd[:5] == ["gemini", "-e", "none", "-m", nlm.DEFAULT_MODEL] and cmd[5] == "-p"
    assert cmd[6] == "질문 doc.pdf"                      # {file} 은 고정 이름으로
    assert (work / "doc.pdf").read_bytes() == b"%PDF-1.4 fake"
    assert kw["cwd"] == work and kw["stdin"] == subprocess.DEVNULL


def test_gemini_ask_503_moves_to_next_model(ask):
    call, _ = ask
    fake = FakeRun(done(stderr="Error: 503 The model is overloaded", code=1), done("두 번째 모델 답"))
    assert call(fake) == "두 번째 모델 답"
    assert fake.models == [nlm.DEFAULT_MODEL, nlm.FALLBACK_MODELS[0]]
    assert nlm.LAST_MODEL == nlm.FALLBACK_MODELS[0]


def test_gemini_ask_timeouts_then_next_models_in_order(ask):
    call, _ = ask
    fake = FakeRun(timeout(), timeout(), done("셋째 모델 답"))
    assert call(fake) == "셋째 모델 답"
    assert fake.models == [nlm.DEFAULT_MODEL, *nlm.FALLBACK_MODELS[:2]]
    assert nlm.LAST_MODEL == nlm.FALLBACK_MODELS[1]


def test_gemini_ask_503_then_timeout_then_success(ask):
    call, _ = ask
    fake = FakeRun(done(stderr="503", code=1), timeout(), done("답"))
    assert call(fake) == "답"
    assert fake.models == [nlm.DEFAULT_MODEL, *nlm.FALLBACK_MODELS[:2]]


def test_gemini_ask_empty_stdout_counts_as_failure(ask):
    call, _ = ask
    fake = FakeRun(done("  \n", code=0), done("진짜 답"))
    assert call(fake) == "진짜 답"
    assert fake.models == [nlm.DEFAULT_MODEL, nlm.FALLBACK_MODELS[0]]


def test_gemini_ask_all_models_fail_lists_each_reason(ask):
    call, _ = ask
    fake = FakeRun(done(stderr="Error: 503 busy", code=1), timeout(),
                   done(stderr="x\nRESOURCE quota exceeded\ny", code=1), done(code=0))
    with pytest.raises(RuntimeError) as err:
        call(fake)
    msg = str(err.value)
    assert msg.startswith("Gemini 실패 — ")
    for model in [nlm.DEFAULT_MODEL, *nlm.FALLBACK_MODELS]:
        assert model in msg
    assert "코드 1 Error: 503 busy" in msg and "초 넘음(붐빔)" in msg and "quota exceeded" in msg
    assert len(fake.calls) == 4 and not fake.outcomes


def test_gemini_ask_custom_model_goes_first_without_duplicates(ask):
    call, _ = ask
    fake = FakeRun(*[done(code=1)] * 3, done("답"))
    assert call(fake, model="my-model") == "답"
    assert fake.models == ["my-model", *nlm.FALLBACK_MODELS]
    fake = FakeRun(done(code=1), done("답"))
    call(fake, model=nlm.FALLBACK_MODELS[0])
    assert fake.models == [nlm.FALLBACK_MODELS[0], nlm.FALLBACK_MODELS[1]]   # 고른 모델은 한 번만


@pytest.mark.parametrize("asked, per_try", [(300, 120), (90, 90), (30, 60)])
def test_gemini_ask_per_model_timeout_is_clamped_to_60_120(ask, asked, per_try):
    call, _ = ask
    fake = FakeRun(done("답"))
    call(fake, timeout=asked)
    assert fake.calls[0][1]["timeout"] == per_try


def test_gemini_ask_uses_key_only_for_the_child_process(ask, monkeypatch):
    call, work = ask
    monkeypatch.setattr(nlm, "env_values", lambda *a, **k: {"GEMINI_API_KEY": "비밀-시험값"})
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    fake = FakeRun(done("답"))
    call(fake)
    assert fake.calls[0][1]["env"]["GEMINI_API_KEY"] == "비밀-시험값"
    assert "GEMINI_API_KEY" not in nlm.os.environ                      # 이 프로세스 환경은 그대로
    settings = json.loads((work / ".gemini" / "settings.json").read_text(encoding="utf-8"))
    assert settings == {"security": {"auth": {"selectedType": "gemini-api-key"}}}


def test_gemini_ask_without_key_removes_api_key_settings(ask):
    call, work = ask
    (work / ".gemini").mkdir(parents=True)
    (work / ".gemini" / "settings.json").write_text("{}", encoding="utf-8")
    call(FakeRun(done("답")))
    assert not (work / ".gemini" / "settings.json").exists()


def test_gemini_find_puts_query_in_the_find_prompt(ask, monkeypatch):
    call, work = ask
    fake = FakeRun(done("[p.3] 원문"))
    monkeypatch.setattr(nlm.subprocess, "run", fake)
    src = work.parent / "자료 원본.pdf"
    assert nlm.gemini_find(src, "분수의 덧셈") == "[p.3] 원문"   # work 를 안 주면 DATA/gemini_work 를 쓴다(임시 폴더)
    prompt = fake.calls[0][0][fake.calls[0][0].index("-p") + 1]
    assert "찾을 내용: 분수의 덧셈" in prompt and "@doc.pdf" in prompt and "{query}" not in prompt
