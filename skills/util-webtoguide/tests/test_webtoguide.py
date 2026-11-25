"""util-webtoguide webtoguide.py 시험 (T13)

- 네트워크 없이: urllib.request.urlopen / urlretrieve 는 가짜로 바꾼다.
- 파일은 모두 pytest 의 tmp_path 에 만든다(현재 폴더를 옮겨서 images/·guide_output.md 가 저장소에 생기지 않게 함).
- 소스는 고치지 않는다. 버그로 보이는 것은 xfail(strict) 로 남기고 ISSUES.md 에 적었다.

실행: python -m pytest skills/util-webtoguide/tests -q
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
FAKE_BLOG = "https://blog.naver.com/exampleid/123456"
FAKE_IMG = "https://example.invalid/img"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("webtoguide_under_test", SKILL_DIR / "webtoguide.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _no_real_network(mod, monkeypatch):
    """어떤 시험도 진짜 네트워크를 쓸 수 없게 막는다(필요한 시험이 따로 가짜로 바꿈)."""
    def blocked(*args, **kwargs):
        raise AssertionError("시험에서 실제 네트워크를 쓰면 안 됨")

    monkeypatch.setattr(mod.urllib.request, "urlopen", blocked)
    monkeypatch.setattr(mod.urllib.request, "urlretrieve", blocked)


def parse(mod, html: str):
    parser = mod.NaverParser()
    parser.feed(html)
    if parser.current_text.strip():  # main() 과 같은 마무리
        parser.record.append(("TEXT", parser.current_text.strip()))
    return parser


def post(body: str) -> str:
    return f'<html><body><div class="se-main-container">{body}</div></body></html>'


def img(src_attr: str, cls: str = "se-image-resource") -> str:
    return f'<img class="{cls}" {src_attr}>'


# ───────── NaverParser ─────────

def test_본문_밖의_글과_그림은_무시한다(mod):
    html = f'<html><p>머리말</p>{img(f"src={chr(34)}{FAKE_IMG}1.png{chr(34)}")}' + post("<p>본문</p>") + "<p>꼬리말</p></html>"
    parser = parse(mod, html)
    assert parser.record == [("TEXT", "본문")]
    assert parser.img_count == 0


def test_글_그림_글_순서를_지킨다(mod):
    html = post(f'<p>앞글</p>{img(f"src={chr(34)}{FAKE_IMG}1.png{chr(34)}")}<p>뒷글</p>')
    parser = parse(mod, html)
    assert parser.record == [
        ("TEXT", "앞글"),
        ("IMG", 1, f"{FAKE_IMG}1.png"),
        ("TEXT", "뒷글"),
    ]
    assert parser.img_urls == [f"{FAKE_IMG}1.png"]


def test_그림_번호는_1부터_이어진다(mod):
    body = "".join(img(f'src="{FAKE_IMG}{n}.png"') for n in range(1, 4))
    parser = parse(mod, post(body))
    assert [item[1] for item in parser.record if item[0] == "IMG"] == [1, 2, 3]
    assert parser.img_count == 3


def test_data_lazy_src_가_src_보다_먼저(mod):
    parser = parse(mod, post(img(f'src="{FAKE_IMG}-small.png" data-lazy-src="{FAKE_IMG}-big.png"')))
    assert parser.img_urls == [f"{FAKE_IMG}-big.png"]


def test_주소의_amp_는_앰퍼샌드로_바꾼다(mod):
    # HTMLParser 는 속성값의 &amp; 를 이미 풀어 주므로 결과는 &. 글자 그대로 "&amp;amp;" 로 오면 한 번만 풀린다.
    parser = parse(mod, post(img(f'src="{FAKE_IMG}?a=1&amp;b=2"')))
    assert parser.img_urls == [f"{FAKE_IMG}?a=1&b=2"]


def test_se_image_resource_클래스가_아니면_그림으로_치지_않는다(mod):
    parser = parse(mod, post(img(f'src="{FAKE_IMG}1.png"', cls="other")))
    assert parser.img_count == 0 and parser.record == []


def test_주소가_없는_그림은_건너뛰고_번호도_올리지_않는다(mod):
    parser = parse(mod, post(img("") + img(f'src="{FAKE_IMG}1.png"')))
    assert parser.img_count == 1
    assert parser.record == [("IMG", 1, f"{FAKE_IMG}1.png")]


def test_글_조각은_줄바꿈을_없애고_공백으로_이어_붙인다(mod):
    parser = parse(mod, post("<p>첫째\n줄</p><p>  둘째  </p><span>셋째</span>"))
    # 줄바꿈은 지우기만 하므로 '첫째줄', 조각 사이는 공백 하나
    assert parser.record == [("TEXT", "첫째줄 둘째 셋째")]


def test_빈_본문은_기록이_없다(mod):
    assert parse(mod, post("")).record == []
    assert parse(mod, post("<p>   \n </p>")).record == []


def test_그림_바로_앞의_글만_글_덩어리로_끊는다(mod):
    parser = parse(mod, post(f'<p>가</p><p>나</p>{img(f"src={chr(34)}{FAKE_IMG}1.png{chr(34)}")}'))
    assert parser.record[0] == ("TEXT", "가 나")


def test_본문_상자가_닫히면_그_뒤_글은_무시한다(mod):
    parser = parse(mod, post("<p>안</p>") + "<p>밖</p>")
    assert parser.record == [("TEXT", "안")]


def test_본문_상자_안의_안쪽_div_가_닫혀도_계속_읽는다(mod):
    parser = parse(mod, post("<div><p>안쪽</p></div><p>바깥쪽도 본문</p>"))
    assert parser.record == [("TEXT", "안쪽 바깥쪽도 본문")]


def page_with_comments(body: str) -> str:
    """본문 상자 뒤, </body> 앞에 댓글 영역이 있는 실제 모양에 가까운 쪽."""
    return (f'<html><body><div class="se-main-container">{body}</div>'
            '<div class="comments"><p>댓글 꼬리말</p></div></body></html>')


def test_빈_태그가_없으면_본문_밖_댓글은_섞이지_않는다(mod):
    parser = parse(mod, page_with_comments("<p>본문만</p>"))
    assert parser.record == [("TEXT", "본문만")]


@pytest.mark.xfail(strict=True, reason="ISSUE-001: img·br 같은 빈 태그는 닫는 태그가 없는데도 깊이를 올려, 본문 상자가 제때 닫히지 않고 본문 뒤 댓글·꼬리말 글까지 가이드에 섞임")
def test_빈_태그가_있어도_본문_밖_댓글이_섞이지_않아야_한다(mod):
    body = f'<p>앞</p>{img(f"src={chr(34)}{FAKE_IMG}1.png{chr(34)}")}<p>뒤</p>'
    parser = parse(mod, page_with_comments(body))
    texts = " ".join(item[1] for item in parser.record if item[0] == "TEXT")
    assert "댓글 꼬리말" not in texts


# ───────── main() — 주소 바꾸기 ─────────

class FakeResponse:
    def __init__(self, html: str):
        self._html = html

    def read(self):
        return self._html.encode("utf-8")


def out_dir(tmp_path: Path) -> Path:
    """시험에서 결과(가이드 .md·images/)가 생기는 곳 = data_dir("util-webtoguide", "output")."""
    return tmp_path / "data" / "util-webtoguide" / "output"


def run_main(mod, monkeypatch, tmp_path, url: str, html: str, *, download_fail=()):
    """main() 을 돌린다. 현재 폴더(작업 폴더)와 데이터 폴더는 모두 tmp_path 아래로 바꿔 둔다.
    요청 주소와 내려받은 그림(저장 경로는 out_dir 기준 상대 경로로 바꿔서)을 기록해 돌려준다."""
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    monkeypatch.chdir(work)
    monkeypatch.setenv("MY_SKILLS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(sys, "argv", ["webtoguide.py", url])
    requested = []
    downloaded = []

    def fake_urlopen(req):
        requested.append(req)
        return FakeResponse(html)

    def fake_urlretrieve(src, filename):
        if src in download_fail:
            raise OSError("가짜 다운로드 실패")
        downloaded.append((src, Path(filename).relative_to(out_dir(tmp_path)).as_posix()))
        Path(filename).write_bytes(b"fake")

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mod.urllib.request, "urlretrieve", fake_urlretrieve)
    mod.main()
    return requested, downloaded


def test_main_주소_없이_실행하면_사용법을_알리고_종료(mod, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["webtoguide.py"])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    assert "사용법" in capsys.readouterr().out


def test_main_블로그_글_주소는_PostView_주소로_바꿔_요청한다(mod, monkeypatch, tmp_path):
    requested, _ = run_main(mod, monkeypatch, tmp_path, FAKE_BLOG, post("<p>본문</p>"))
    assert requested[0].full_url == "https://blog.naver.com/PostView.naver?blogId=exampleid&logNo=123456"
    assert requested[0].get_header("User-agent") == "Mozilla/5.0"


def test_main_이미_PostView_주소면_그대로_요청한다(mod, monkeypatch, tmp_path):
    url = "https://blog.naver.com/PostView.naver?blogId=exampleid&logNo=123456"
    requested, _ = run_main(mod, monkeypatch, tmp_path, url, post("<p>본문</p>"))
    assert requested[0].full_url == url


def test_main_네이버_블로그가_아닌_주소는_그대로_요청한다(mod, monkeypatch, tmp_path):
    url = "https://example.invalid/post/1"
    requested, _ = run_main(mod, monkeypatch, tmp_path, url, post("<p>본문</p>"))
    assert requested[0].full_url == url


def test_main_짧은_블로그_주소는_바꾸지_않고_그대로_요청한다(mod, monkeypatch, tmp_path):
    url = "https://blog.naver.com/exampleid"  # 글 번호 없음 → split 결과가 4조각
    requested, _ = run_main(mod, monkeypatch, tmp_path, url, post("<p>본문</p>"))
    assert requested[0].full_url == url


def test_main_글_주소_끝의_슬래시는_글_번호에_섞이지_않는다(mod, monkeypatch, tmp_path):
    requested, _ = run_main(mod, monkeypatch, tmp_path, FAKE_BLOG + "/", post("<p>본문</p>"))
    assert requested[0].full_url.endswith("logNo=123456")


@pytest.mark.xfail(strict=True, reason="ISSUE-002: 주소 끝에 ?query 나 #조각이 붙으면 글 번호에 그대로 섞여 잘못된 PostView 주소가 됨")
@pytest.mark.parametrize("suffix", ["?fromRss=true", "#comment"])
def test_main_글_주소_끝에_붙은_것을_글_번호로_오해하지_않아야_한다(mod, monkeypatch, tmp_path, suffix):
    requested, _ = run_main(mod, monkeypatch, tmp_path, FAKE_BLOG + suffix, post("<p>본문</p>"))
    assert requested[0].full_url.endswith("logNo=123456")


def test_main_모바일_주소도_PC_PostView_주소로_바꿔_요청한다(mod, monkeypatch, tmp_path):
    """m.blog.naver.com 글 주소도 blog.naver.com 의 PostView 로 바뀐다(현재 동작)."""
    requested, _ = run_main(mod, monkeypatch, tmp_path, "https://m.blog.naver.com/exampleid/123456", post("<p>본문</p>"))
    assert requested[0].full_url == "https://blog.naver.com/PostView.naver?blogId=exampleid&logNo=123456"


# ───────── main() — 결과 파일 ─────────

def test_main_출처_링크가_맨_위에_들어간다(mod, monkeypatch, tmp_path):
    run_main(mod, monkeypatch, tmp_path, FAKE_BLOG, post("<p>본문</p>"))
    md = (out_dir(tmp_path) / "guide_output.md").read_text(encoding="utf-8")
    source = "https://blog.naver.com/PostView.naver?blogId=exampleid&logNo=123456"
    lines = md.splitlines()
    assert lines[0] == "# 블로그 가이드 변환 결과"
    assert lines[2] == f"> **원본 게시글 출처:** [{source}]({source})"


def test_main_글과_그림이_원래_순서로_마크다운에_들어간다(mod, monkeypatch, tmp_path):
    body = f'<p>1단계</p>{img(f"src={chr(34)}{FAKE_IMG}1.png{chr(34)}")}<p>2단계</p>{img(f"src={chr(34)}{FAKE_IMG}2.png{chr(34)}")}'
    _, downloaded = run_main(mod, monkeypatch, tmp_path, FAKE_BLOG, post(body))
    md = (out_dir(tmp_path) / "guide_output.md").read_text(encoding="utf-8")
    order = [md.index(t) for t in ("1단계", "![참고 이미지 1](images/img_1.png)", "2단계", "![참고 이미지 2](images/img_2.png)")]
    assert order == sorted(order)
    assert [name for _, name in downloaded] == ["images/img_1.png", "images/img_2.png"]
    assert (out_dir(tmp_path) / "images" / "img_1.png").exists()


@pytest.mark.parametrize("src, ext", [
    (f"{FAKE_IMG}/a.JPG?type=w800", "jpg"),
    (f"{FAKE_IMG}/a.jpeg", "jpeg"),
    (f"{FAKE_IMG}/a.png", "png"),
    (f"{FAKE_IMG}/a.gif", "png"),   # 모르는 확장자는 png 로 저장(현재 동작)
    (f"{FAKE_IMG}/noext", "png"),
])
def test_main_확장자는_주소에서_골라_저장한다(mod, monkeypatch, tmp_path, src, ext):
    _, downloaded = run_main(mod, monkeypatch, tmp_path, FAKE_BLOG, post(img(f'src="{src}"')))
    assert downloaded == [(src, f"images/img_1.{ext}")]


def test_main_그림_받기가_실패하면_그_그림만_빼고_계속한다(mod, monkeypatch, tmp_path, capsys):
    body = f'<p>앞</p>{img(f"src={chr(34)}{FAKE_IMG}/1.png{chr(34)}")}<p>뒤</p>{img(f"src={chr(34)}{FAKE_IMG}/2.png{chr(34)}")}'
    run_main(mod, monkeypatch, tmp_path, FAKE_BLOG, post(body), download_fail={f"{FAKE_IMG}/1.png"})
    md = (out_dir(tmp_path) / "guide_output.md").read_text(encoding="utf-8")
    assert "![참고 이미지 1]" not in md
    assert "![참고 이미지 2](images/img_2.png)" in md
    assert "앞" in md and "뒤" in md
    assert "이미지 1 다운로드 실패" in capsys.readouterr().out


def test_main_images_폴더가_이미_있어도_오류가_없다(mod, monkeypatch, tmp_path):
    (out_dir(tmp_path) / "images").mkdir(parents=True)
    run_main(mod, monkeypatch, tmp_path, FAKE_BLOG, post("<p>본문</p>"))
    assert (out_dir(tmp_path) / "guide_output.md").exists()


def test_main_웹페이지를_못_가져오면_파일을_만들지_않고_종료(mod, monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MY_SKILLS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(sys, "argv", ["webtoguide.py", FAKE_BLOG])

    def failing_urlopen(req):
        raise OSError("가짜 연결 실패")

    monkeypatch.setattr(mod.urllib.request, "urlopen", failing_urlopen)
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    assert "웹페이지를 가져오는 중 오류" in capsys.readouterr().out
    assert not (out_dir(tmp_path) / "guide_output.md").exists()
    assert not (out_dir(tmp_path) / "images").exists()


def test_main_본문을_못_찾아도_출처만_있는_빈_가이드를_만든다(mod, monkeypatch, tmp_path, capsys):
    """네이버 화면 구조가 바뀌면(se-main-container 없음) 조용히 빈 가이드가 된다 — 현재 동작."""
    run_main(mod, monkeypatch, tmp_path, FAKE_BLOG, "<html><body><p>다른 구조</p></body></html>")
    md = (out_dir(tmp_path) / "guide_output.md").read_text(encoding="utf-8")
    assert "다른 구조" not in md
    assert "원본 게시글 출처" in md
    assert "총 0개의 이미지를 찾았습니다" in capsys.readouterr().out


@pytest.mark.xfail(strict=True, reason="ISSUE-003: 본문을 하나도 못 찾아도 '완료되었습니다!' 라고만 알려 구조 변경(se-main-container 없음)을 눈치채기 어려움")
def test_main_본문을_못_찾으면_경고해야_한다(mod, monkeypatch, tmp_path, capsys):
    run_main(mod, monkeypatch, tmp_path, FAKE_BLOG, "<html><body><p>다른 구조</p></body></html>")
    out = capsys.readouterr().out.replace(str(out_dir(tmp_path)), "")  # 시험 폴더 이름이 섞이지 않게 경로는 뺀다
    assert "찾지 못" in out or "경고" in out


def test_main_결과는_작업_폴더가_아니라_데이터_폴더에만_저장한다(mod, monkeypatch, tmp_path, capsys):
    """저장소 폴더에서 돌려도 images/·guide_output.md 가 현재 폴더에 생기지 않아야 한다(T13 교사 결정)."""
    body = f'<p>글</p>{img(f"src={chr(34)}{FAKE_IMG}/1.png{chr(34)}")}'
    run_main(mod, monkeypatch, tmp_path, FAKE_BLOG, post(body))
    work = tmp_path / "work"
    assert list(work.iterdir()) == []
    assert (out_dir(tmp_path) / "guide_output.md").exists()
    assert (out_dir(tmp_path) / "images" / "img_1.png").exists()
    assert str(out_dir(tmp_path)) in capsys.readouterr().out
