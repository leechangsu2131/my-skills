"""화면 설정(T110) 연결 점검 — 파일이 서버·index.html 에 이어져 있고, 어두운 화면 CSS 가 수업 진행(🎯) 화면을 덮지 않는지 본다.

    python -m pytest tests/test_layout_files.py -v      (teacherlesson-assistant 폴더에서)
"""
import pathlib
import re

SKILL = pathlib.Path(__file__).resolve().parent.parent
WEB = SKILL / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "theme.css").read_text(encoding="utf-8")
SERVER = (SKILL / "assistant_server.py").read_text(encoding="utf-8")


def test_html_loads_theme_and_layout():
    assert '<link rel="stylesheet" href="/theme.css">' in HTML
    assert '<script src="/layout.js"></script>' in HTML
    for el in ('id="layoutBtn"', 'id="layoutPanel"', 'id="themeBtn"', 'id="layoutList"', 'id="layoutReset"'):
        assert el in HTML


def test_theme_loads_after_mobile_css():
    assert HTML.index('href="/mobile.css"') < HTML.index('href="/theme.css"')


def test_server_serves_both_files():
    assert 'url.path == "/layout.js"' in SERVER and 'url.path == "/theme.css"' in SERVER
    assert (WEB / "layout.js").is_file() and (WEB / "theme.css").is_file()


def test_dark_rules_never_touch_focus_mode():
    # html[data-theme="dark"] 로 시작하는 규칙은 모두 body:not(.focus-mode) 를 거쳐야 한다(변수 정의 줄 포함)
    for rule in re.findall(r'html\[data-theme="dark"\][^{]*\{', CSS):
        if rule.strip() == 'html[data-theme="dark"]{':  # color-scheme 한 줄
            continue
        assert "body:not(.focus-mode)" in rule, rule


def test_hide_and_collapse_rules_are_skipped_in_focus_mode():
    for rule in re.findall(r"[^{}]*data-layout-(?:hidden|collapsed)[^{}]*\{", CSS):
        assert "body:not(.focus-mode)" in rule or "::after" in rule, rule


def test_theme_css_does_not_redefine_mobile_rules():
    mobile = (WEB / "mobile.css").read_text(encoding="utf-8")
    mobile_selectors = {s.strip() for s in re.findall(r"([^{}@]+)\{", mobile) if "#" in s or "." in s}
    for sel in re.findall(r"([^{}@/]+)\{", CSS):
        sel = sel.strip()
        assert not (sel in mobile_selectors and not sel.startswith("html[data-theme")), sel


def test_collapse_rule_beats_id_display_rules():
    # #recbar{display:flex} 같은 id 규칙보다 이겨야 접힌 칸에 제목만 남는다(브라우저 점검에서 찾은 문제)
    assert re.search(r"data-layout-collapsed\]>\*:not\(h2\)\{display:none!important\}", CSS)


def test_hidden_state_uses_attributes_not_classes():
    # index.html 이 hero.className 을 통째로 다시 써도 숨김이 풀리지 않게 속성으로 표시한다(PR #189 검토 🔴)
    js = (WEB / "layout.js").read_text(encoding="utf-8")
    assert "toggleAttribute('data-layout-hidden'" in js
    assert "classList.toggle('layout-hidden'" not in js
    assert "[data-layout-hidden]" in CSS


def test_dark_theme_covers_tabs():
    assert re.search(r'data-theme="dark"\] body:not\(\.focus-mode\) #tabs\{', CSS)
    assert re.search(r'#tabs button\.on\{', CSS)


def test_gear_button_gets_its_own_header_column_on_phones():
    assert "#layoutBtn{grid-column:4" in CSS
