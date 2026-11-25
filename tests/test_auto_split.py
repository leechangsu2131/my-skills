"""skills/teacherlesson-guide/auto_split.py 시험 — Gemini 를 부르지 않는 검사·정규화 함수들.

main() 은 --inspect-only 와 --reuse-analysis(저장된 analysis.json 을 다시 검증) 경로만 돌리고,
혹시 Gemini 를 부르면 바로 실패하도록 nlm.gemini_ask 를 막아 둔다. PDF 는 PyMuPDF 로 그 자리에서 만든다.
xfail(strict) 시험은 skills/teacherlesson-guide/ISSUES.md 에 적힌 버그의 재현이다.
"""
import copy
import json
import pathlib
import sys

import fitz
import pytest

import auto_split as az
import prepare_lessons as pl

# 진도표 차시 목록(정답)과, 그에 맞게 만든 가짜 지도서 6쪽
MAP = [{"from": 1, "to": 1, "title": "곱셈의 뜻"},
       {"from": 2, "to": 3, "title": "곱셈구구 익히기"},
       {"from": 4, "to": 4, "title": "문제 풀이"}]
HEADS = ["단원 개관 곱셈 단원을 시작합니다", "1차시 곱셈의 뜻 알아보기", "활동 책 풀어 보기",
         "2~3차시 곱셈구구 익히기", "곱셈구구표 만들기", "4차시 문제 풀이"]
BODY = "지도서 본문 문장입니다. " * 16


def long_pages() -> list[str]:
    return [f"{head}\n{BODY}" for head in HEADS]


def detected(starts=(2, 4, 6), overview=(1, 1), titles=("곱셈의 뜻", "곱셈구구 익히기", "문제 풀이")) -> dict:
    data = {"overview": {"start_page": overview[0], "end_page": overview[1]} if overview else None,
            "lessons": [{"start_page": s, "source_title": t} for s, t in zip(starts, titles)]}
    return data


def merged(data=None, lesson_map=MAP) -> dict:
    data = data or detected()
    az.merge_lesson_map(data, copy.deepcopy(lesson_map))
    return data


def problems(data, pages=None, expected=3, offset=0, lesson_map=MAP):
    return az.validate(data, pages or long_pages(), expected, offset, lesson_map)


def has(issues, text) -> bool:
    return any(text in issue for issue in issues)


# ──────────────────────────── clean_page · extract_pages · source_page_text ────────────────────────────

def test_clean_page_removes_control_and_zero_width_chars_and_blank_lines():
    assert az.clean_page("가​나\x00 다\n\n  라   마 \n﻿") == "가 나 다\n라 마"


def test_clean_page_normalizes_decomposed_hangul_to_nfc():
    assert az.clean_page("각") == "각"          # 자모로 풀린 글자를 한 글자로


def test_clean_page_empty():
    assert az.clean_page("") == "" and az.clean_page(" \n\t\n") == ""


def make_pdf(path: pathlib.Path, texts: list[str]) -> pathlib.Path:
    doc = fitz.open()
    for text in texts:
        page = doc.new_page()
        if text:
            page.insert_textbox(fitz.Rect(40, 40, 555, 800), text, fontname="korea", fontsize=10)
    doc.save(path)
    doc.close()
    return path


def test_extract_pages_reads_each_page_and_keeps_blank_pages(tmp_path):
    pdf = make_pdf(tmp_path / "g.pdf", ["곱셈 단원\n도입", "", "셋째 쪽"])
    pages = az.extract_pages(pdf)
    assert len(pages) == 3
    assert pages[0].split() == ["곱셈", "단원", "도입"] and pages[1] == "" and pages[2] == "셋째 쪽"


def test_source_page_text_marks_empty_and_short_pages():
    assert az.source_page_text("") == "[글자 없음: 그림/OCR 확인 필요]"
    assert az.source_page_text(" \n ") == "[글자 없음: 그림/OCR 확인 필요]"
    short = az.source_page_text("짧은 글")
    assert short.startswith("짧은 글\n") and "추출 글자가 적음" in short
    long = "가" * 40
    assert az.source_page_text(long) == long                         # 공백 뺀 40자부터는 그대로
    assert "추출 글자가 적음" in az.source_page_text("가" * 39)
    assert "추출 글자가 적음" in az.source_page_text("가 " * 39)      # 공백은 글자 수에 안 넣는다


# ──────────────────────────── page_index ────────────────────────────

def test_page_index_header_and_physical_page_numbers():
    pages = ["단원 도입 1차시", "분수의 덧셈 2차시", "곱셈 3차시"]
    rows = az.page_index(pages).splitlines()
    assert rows[:3] == ["# 지도서 페이지 색인", "총 3쪽", ""]
    assert [r for r in rows if r.startswith("[p.")] == ["[p.1] 단원 도입 1차시", "[p.2] 분수의 덧셈 2차시", "[p.3] 곱셈 3차시"]
    shifted = az.page_index(pages, page_offset=10)
    assert "[p.11] 단원 도입 1차시" in shifted and "[p.13] 곱셈 3차시" in shifted and "[p.1]" not in shifted


def test_page_index_cuts_the_head_at_limit_and_adds_lesson_marker_beyond_it():
    text = "가" * 200 + "\n2~3차시 곱셈구구 익히기"
    index = az.page_index([text], limit=50)
    assert "[p.1] " + "가" * 50 + "\n" in index and "가" * 51 not in index
    assert "  차시표시: 2~3차시 곱셈구구 익히기" in index


def test_page_index_skips_marker_already_in_head_and_ignored_phrases():
    text = "2차시 곱셈\n이 차시에서 배울 내용\n차시 정리 문제\n본문"
    index = az.page_index([text])
    assert "차시표시" not in index                                    # 앞부분에 이미 있고, 나머지 줄은 제외 문구


def test_page_index_dedups_and_caps_markers():
    lines = ["가" * 300] + ["3차시 반복"] * 3 + [f"{i}차시 " + "나" * 40 for i in range(10)]
    suffix = az.page_index(["\n".join(lines)], limit=10).split("차시표시: ")[1]
    assert suffix.startswith("3차시 반복 / 0차시") and suffix.count("3차시 반복") == 1
    assert len(suffix.rstrip("\n")) <= 260


def test_page_index_empty_page():
    assert az.page_index([""]) == "# 지도서 페이지 색인\n총 1쪽\n\n[p.1] \n"


# ──────────────────────────── json_object ────────────────────────────

def test_json_object_extracts_from_code_fence_and_chatter():
    text = '결과입니다.\n```json\n{"overview": null, "lessons": [{"start_page": 3}]}\n```\n끝.'
    assert az.json_object(text) == {"overview": None, "lessons": [{"start_page": 3}]}


def test_json_object_errors():
    with pytest.raises(ValueError, match="JSON을 찾지 못했습니다"):
        az.json_object("죄송합니다")
    with pytest.raises(ValueError, match="lessons 목록이 없습니다"):
        az.json_object('{"overview": null}')
    with pytest.raises(ValueError, match="lessons 목록이 없습니다"):
        az.json_object('{"lessons": "없음"}')
    with pytest.raises(ValueError):
        az.json_object('{"lessons": [')


@pytest.mark.xfail(strict=True, reason="teacherlesson-guide ISSUES.md: json_object 가 설명 글의 중괄호에 걸림")
@pytest.mark.parametrize("text", [
    '참고 {예시} 입니다.\n{"lessons": [{"start_page": 3}]}',
    '{"lessons": [{"start_page": 3}]}\n(설명 {끝})',
], ids=["앞 설명에 중괄호", "뒤 설명에 중괄호"])
def test_json_object_explanation_containing_braces_around_json(text):
    assert az.json_object(text)["lessons"][0]["start_page"] == 3


# ──────────────────────────── title_matches ────────────────────────────

@pytest.mark.parametrize("title, page, expected", [
    ("분수의 덧셈", "분수 덧셈 공부", True),             # 두 낱말 중 하나 이상(절반 올림)
    ("곱셈 구구", "곱셈", True),
    ("1. 곱셈", "곱셈 활동", True),                     # 한 글자 숫자는 낱말로 안 침
    ("ABC test", "abc", True),                          # 영문은 대소문자 무시
    ("ＡＢ", "ab", True),                                # 전각 → 반각(NFKC)
    ("분수 막대 놀이", "분수 이야기", False),             # 3낱말 중 1개 < 2개
    ("분수 막대 놀이", "분수 막대 이야기", True),
    ("", "아무 글", False),
    ("가", "가", False),                                # 낱말(2자 이상)이 없으면 못 찾음
    ("곱셈의 뜻", "", False),
])
def test_title_matches(title, page, expected):
    assert az.title_matches(title, page) is expected


# ──────────────────────────── merge_lesson_map ────────────────────────────

def test_merge_lesson_map_takes_numbers_and_titles_from_the_schedule():
    data = detected()
    data["lessons"][0]["title"] = "Gemini 가 지은 제목"
    az.merge_lesson_map(data, [dict(r) for r in MAP])
    assert [(l["from"], l["to"], l["title"]) for l in data["lessons"]] == [(1, 1, "곱셈의 뜻"), (2, 3, "곱셈구구 익히기"), (4, 4, "문제 풀이")]
    assert data["lessons"][1]["start_page"] == 4 and data["lessons"][1]["source_title"] == "곱셈구구 익히기"


def test_merge_lesson_map_keeps_source_title_or_falls_back_to_gemini_title():
    data = {"lessons": [{"start_page": 1, "source_title": " 쪽에 적힌 제목 "}, {"start_page": 2, "title": "옛 제목"}, {"start_page": 3}]}
    az.merge_lesson_map(data, [{"from": 1, "title": "가"}, {"from": "2", "title": " 나 "}, {"from": 3, "to": "4"}])
    assert [l["source_title"] for l in data["lessons"]] == ["쪽에 적힌 제목", "옛 제목", ""]
    assert [(l["from"], l["to"], l["title"]) for l in data["lessons"]] == [(1, 1, "가"), (2, 2, "나"), (3, 4, "")]


def test_merge_lesson_map_leaves_data_alone_when_counts_differ_or_no_map():
    data = detected()
    before = copy.deepcopy(data)
    az.merge_lesson_map(data, MAP[:2])
    az.merge_lesson_map(data, None)
    assert data == before


# ──────────────────────────── unit_lesson_map ────────────────────────────

def write_json(path, obj, encoding="utf-8"):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding=encoding)
    return path


def test_unit_lesson_map_explicit_file_is_cleaned(tmp_path):
    f = write_json(tmp_path / "m.json", {"lessons": [{"from": "1", "to": 2, "title": " 곱셈 "}, {"from": 3}]})
    assert az.unit_lesson_map("수학", "1단원", f) == [{"from": 1, "to": 2, "title": "곱셈"}, {"from": 3, "to": 3, "title": ""}]


def test_unit_lesson_map_reads_utf8_bom(tmp_path):
    f = write_json(tmp_path / "m.json", {"lessons": [{"from": 1}]}, encoding="utf-8-sig")
    assert az.unit_lesson_map("수학", "1단원", f)[0]["from"] == 1


@pytest.mark.parametrize("obj", [{"lessons": []}, {"lessons": {}}, {}, {"lessons": None}])
def test_unit_lesson_map_empty_list_is_an_error(tmp_path, obj):
    with pytest.raises(ValueError, match="차시 목록이 비어 있습니다"):
        az.unit_lesson_map("수학", "1단원", write_json(tmp_path / "m.json", obj))


@pytest.mark.parametrize("row", [{"from": 0}, {"from": 3, "to": 2}, {"from": -1, "to": 1}])
def test_unit_lesson_map_bad_range(tmp_path, row):
    with pytest.raises(ValueError, match="차시 번호 범위가 올바르지 않습니다"):
        az.unit_lesson_map("수학", "1단원", write_json(tmp_path / "m.json", {"lessons": [row]}))


def test_unit_lesson_map_row_without_from_or_bad_file(tmp_path):
    with pytest.raises((TypeError, ValueError)):                      # main 이 둘 다 잡아 안내한다
        az.unit_lesson_map("수학", "1단원", write_json(tmp_path / "m.json", {"lessons": [{"title": "x"}]}))
    with pytest.raises(OSError):
        az.unit_lesson_map("수학", "1단원", tmp_path / "없음.json")
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        az.unit_lesson_map("수학", "1단원", tmp_path / "bad.json")


def test_unit_lesson_map_default_path_is_units_subject__unit(tmp_path, monkeypatch):
    monkeypatch.setattr(az.assistant, "UNITS", tmp_path)
    assert az.unit_lesson_map("수학", "1. 곱셈", None) is None         # 파일이 없으면 None
    write_json(tmp_path / "수학__1._곱셈.json", {"lessons": [{"from": 1, "title": "곱셈의 뜻"}]})
    assert az.unit_lesson_map("수학", "1. 곱셈", None) == [{"from": 1, "to": 1, "title": "곱셈의 뜻"}]


# ──────────────────────────── validate ────────────────────────────

def test_validate_accepts_matching_detection():
    assert problems(merged()) == []


def test_validate_page_offset_uses_physical_page_numbers():
    pages = long_pages()[1:]                                         # 물리 2~6쪽만 분석
    assert problems(merged(detected(overview=None)), pages, offset=1) == []
    assert has(problems(merged(detected(starts=(1, 4, 6), overview=None)), pages, offset=1), "선택한 PDF 범위를 벗어납니다")


def test_validate_without_lesson_map_flags_unverified_numbers():
    data = merged()                                                  # from/to 는 이미 들어 있음
    issues = problems(data, lesson_map=None)
    assert len(issues) == 1 and "미검증" in issues[0]
    bare = detected()                                                # from/to 가 없으면 줄마다 숫자가 아니라고 나온다
    issues = problems(bare, lesson_map=None)
    assert "미검증" in issues[0] and sum("숫자가 아닙니다" in i for i in issues) == 3


def test_validate_empty_lessons():
    assert problems({"overview": None, "lessons": []}, expected=None) == ["차시 시작 쪽을 찾지 못했습니다."]


def test_validate_lesson_count_differs_from_schedule_and_expectation():
    data = merged()
    data["lessons"].pop()
    issues = problems(data)
    assert has(issues, "진도표 차시 3개와 감지한 구간 2개가 다릅니다") and has(issues, "예상 차시 구간 3개와 감지한 2개가 다릅니다")
    assert has(problems(merged(), expected=4), "예상 차시 구간 4개와 감지한 3개가 다릅니다")
    assert problems(merged(), expected=None) == []


@pytest.mark.parametrize("starts, message", [
    ((4, 2, 6), "앞 차시보다 앞서거나 중복됩니다"),
    ((2, 2, 6), "앞 차시보다 앞서거나 중복됩니다"),
    ((2, 4, 99), "선택한 PDF 범위를 벗어납니다"),
    ((0, 4, 6), "선택한 PDF 범위를 벗어납니다"),
])
def test_validate_start_pages(starts, message):
    assert has(problems(merged(detected(starts=starts, overview=None))), message)


def test_validate_non_numeric_start_page():
    data = merged(detected(overview=None))
    data["lessons"][1]["start_page"] = "넷째 쪽"
    assert has(problems(data), "2번째 차시의 쪽 번호 또는 차시 번호가 숫자가 아닙니다")


def test_validate_lesson_numbers_must_match_schedule():
    data = merged(detected(overview=None))
    data["lessons"][1].update({"from": 2, "to": 2})
    assert has(problems(data), "2번째 차시 번호가 진도표와 다릅니다: 감지 2~2, 진도표 2~3")


def test_validate_lesson_numbers_overlapping_or_reversed():
    data = merged(detected(overview=None))
    data["lessons"][1].update({"from": 1, "to": 3})
    assert has(problems(data), "2번째 차시 번호 범위가 앞 차시와 겹치거나 역순입니다")
    data = merged(detected(overview=None))
    data["lessons"][2].update({"from": 5, "to": 4})
    assert has(problems(data), "3번째 차시 번호 범위가 앞 차시와 겹치거나 역순입니다")


def test_validate_schedule_title_must_appear_on_the_start_page():
    pages = long_pages()
    pages[3] = "엉뚱한 쪽\n" + BODY                                   # 2~3차시 시작 쪽(4쪽)에 제목 낱말이 없다
    assert has(problems(merged(detected(overview=None)), pages), "곱셈구구 익히기")
    assert not has(problems(merged(detected(overview=None)), long_pages()), "확인되지 않습니다")


def test_validate_without_schedule_uses_the_source_title():
    data = merged(detected(overview=None), lesson_map=MAP)
    issues = problems(data, lesson_map=None)
    assert not has(issues, "제목이 시작 쪽 글에서 확인되지 않습니다")
    data["lessons"][0]["source_title"] = "전혀 다른 제목"
    assert has(problems(data, lesson_map=None), "1번째 제목이 시작 쪽 글에서 확인되지 않습니다: 전혀 다른 제목")


@pytest.mark.parametrize("overview, message", [
    ({"start_page": 1, "end_page": None}, "시작·끝을 함께 지정해야 합니다"),
    ({"start_page": None, "end_page": 1}, "시작·끝을 함께 지정해야 합니다"),
    ({"start_page": 2, "end_page": 3}, "단원 개관 쪽 범위가 첫 차시 시작 쪽과 맞지 않습니다"),     # 1쪽에서 시작 안 함
    ({"start_page": 1, "end_page": 2}, "단원 개관 쪽 범위가 첫 차시 시작 쪽과 맞지 않습니다"),     # 첫 차시와 겹침
    ({"start_page": 1, "end_page": 0}, "단원 개관 쪽 범위가 첫 차시 시작 쪽과 맞지 않습니다"),
    ({"start_page": "처음", "end_page": "끝"}, "단원 개관 쪽 번호가 숫자가 아닙니다"),
])
def test_validate_overview_range(overview, message):
    data = merged()
    data["overview"] = overview
    assert has(problems(data), message)


def test_validate_overview_none_or_empty_is_fine():
    for overview in (None, {}, {"start_page": None, "end_page": None}):
        data = merged()
        data["overview"] = overview
        assert problems(data) == []


def test_validate_overview_conflicts_with_a_schedule_row_named_unit_intro():
    schedule = [{"from": 1, "to": 1, "title": "단원 도입 곱셈"}, {"from": 2, "to": 2, "title": "곱셈의 뜻"}]
    ok = merged(detected(starts=(1, 2), overview=None, titles=("단원 도입", "곱셈의 뜻")), lesson_map=schedule)
    assert problems(ok, expected=2, lesson_map=schedule) == []
    data = merged(detected(starts=(1, 2), overview=(1, 1), titles=("단원 도입", "곱셈의 뜻")), lesson_map=schedule)
    assert has(problems(data, expected=2, lesson_map=schedule), "'단원 도입' 차시가 있어 별도 단원 개관 구간과 겹칩니다")


# ──────────────────────────── make_markdown ────────────────────────────

def test_make_markdown_headings_ranges_and_page_labels():
    md = az.make_markdown("수학", "1. 곱셈", merged(), long_pages())
    heads = [l for l in md.splitlines() if l.startswith("#")]
    assert heads == ["# [수학 1. 곱셈] 지도서 소스",
                     "## [수학 1. 곱셈] 단원 개관 (지도서 p.1~1)",
                     "## [수학 1. 곱셈] 1차시 곱셈의 뜻 (지도서 p.2~3)",
                     "## [수학 1. 곱셈] 2~3차시 곱셈구구 익히기 (지도서 p.4~5)",
                     "## [수학 1. 곱셈] 4차시 문제 풀이 (지도서 p.6~6)"]
    assert [l for l in md.splitlines() if l.startswith("〔p.")] == [f"〔p.{n}〕" for n in range(1, 7)]
    assert md.endswith("\n") and not md.endswith("\n\n") and "추출 글자가 적음" not in md


def test_make_markdown_without_overview_or_titles():
    data = {"overview": None, "lessons": [{"start_page": 1, "from": 1, "to": 1}, {"start_page": 2, "from": 2, "to": 4}]}
    md = az.make_markdown("국어", "1단원", data, long_pages()[:3])
    assert not [l for l in md.splitlines() if l.startswith("#") and "단원 개관" in l]
    assert "## [국어 1단원] 1차시 (지도서 p.1~1)" in md and "## [국어 1단원] 2~4차시 (지도서 p.2~3)" in md


def test_make_markdown_page_offset_labels_physical_pages():
    data = merged(detected(overview=None))
    md = az.make_markdown("수학", "1. 곱셈", data, long_pages()[1:], page_offset=1)
    assert [l for l in md.splitlines() if l.startswith("〔p.")][0] == "〔p.2〕"
    assert "## [수학 1. 곱셈] 4차시 문제 풀이 (지도서 p.6~6)" in md and "〔p.7〕" not in md
    assert "1차시 곱셈의 뜻 알아보기" in md.split("〔p.2〕")[1].split("〔p.3〕")[0]


def test_make_markdown_marks_blank_and_short_pages():
    pages = long_pages()
    pages[2], pages[4] = "", "짧음"
    md = az.make_markdown("수학", "1. 곱셈", merged(), pages)
    assert "〔p.3〕\n[글자 없음: 그림/OCR 확인 필요]" in md and "〔p.5〕\n짧음\n[추출 글자가 적음" in md


def test_make_markdown_output_is_found_by_prepare_lessons_lesson_section(tmp_path, monkeypatch):
    """auto_split 이 쓰는 제목 모양과 prepare_lessons.lesson_section 이 찾는 모양이 맞아야 한다."""
    monkeypatch.setattr(pl.app, "NOTEBOOKLM", tmp_path)
    (tmp_path / "수학").mkdir()
    (tmp_path / "수학" / f"{pl.app.safe_name('1. 곱셈')}.md").write_text(
        az.make_markdown("수학", "1. 곱셈", merged(), long_pages()), encoding="utf-8")

    def section(number):
        return pl.lesson_section({"subject": "수학", "unit": "1. 곱셈", "lesson": number, "title": ""})

    first = section("1")
    assert first.splitlines()[0].startswith("## [수학 1. 곱셈] 1차시 곱셈의 뜻") and "〔p.2〕" in first and "〔p.3〕" in first
    assert "〔p.4〕" not in first and "단원 개관" not in first
    for number in ("2", "3", "3(2~3)"):
        grouped = section(number)
        assert "2~3차시 곱셈구구 익히기" in grouped.splitlines()[0]
        assert "〔p.4〕" in grouped and "〔p.5〕" in grouped and "〔p.6〕" not in grouped
    assert "4차시 문제 풀이" in section("4").splitlines()[0]


# ──────────────────────────── main (Gemini 없이) ────────────────────────────

@pytest.fixture
def cli(tmp_path, monkeypatch):
    """main() 을 인자와 함께 돌리는 도우미. Gemini 를 부르면 실패, 수업 비서 폴더는 임시로."""
    def no_gemini(*a, **k):
        raise AssertionError("Gemini 를 부르면 안 된다")
    monkeypatch.setattr(az.nlm, "gemini_ask", no_gemini)
    monkeypatch.setattr(az.assistant, "UNITS", tmp_path / "units")
    monkeypatch.setattr(az.assistant, "NOTEBOOKLM", tmp_path / "notebooklm")
    pdf = make_pdf(tmp_path / "지도서.pdf", long_pages())
    out = tmp_path / "out"

    def run(*args, lesson_map=MAP):
        argv = ["auto_split.py", str(pdf), "--subject", "수학", "--unit", "1. 곱셈", "--out-dir", str(out), *args]
        if lesson_map is not None:
            argv += ["--lesson-list-json", str(write_json(tmp_path / "lessons.json", {"lessons": lesson_map}))]
        monkeypatch.setattr(sys, "argv", argv)
        return az.main()
    run.out, run.pdf, run.tmp = out, pdf, tmp_path
    return run


def test_main_inspect_only_writes_page_index_and_nothing_else(cli, capsys):
    assert cli("--inspect-only", lesson_map=None) == 0
    index = (cli.out / "page_heads.md").read_text(encoding="utf-8")
    assert "총 6쪽" in index and "[p.4] 2~3차시 곱셈구구 익히기" in index
    assert "글자 있는 쪽 6/6" in capsys.readouterr().out
    assert [p.name for p in cli.out.iterdir()] == ["page_heads.md"]


def test_main_inspect_only_respects_page_range(cli):
    assert cli("--inspect-only", "--from-page", "2", "--to-page", "4", lesson_map=None) == 0
    index = (cli.out / "page_heads.md").read_text(encoding="utf-8")
    assert "총 3쪽" in index and "[p.2]" in index and "[p.4]" in index and "[p.1]" not in index and "[p.5]" not in index


@pytest.mark.parametrize("args", [("--from-page", "0"), ("--from-page", "5", "--to-page", "3"), ("--to-page", "99")])
def test_main_rejects_page_range_outside_pdf(cli, args):
    with pytest.raises(SystemExit) as exc:
        cli("--inspect-only", *args, lesson_map=None)
    assert exc.value.code == 2


def test_main_stops_before_gemini_without_a_schedule_list(cli):
    with pytest.raises(SystemExit) as exc:
        cli(lesson_map=None)                                         # units/ 도 --lesson-list-json 도 없음
    assert exc.value.code == 2


def test_main_expected_lessons_must_match_schedule(cli):
    with pytest.raises(SystemExit) as exc:
        cli("--expected-lessons", "5")
    assert exc.value.code == 2


def save_analysis(out, data):
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "analysis.json", {"analysis": data})


def test_main_reuse_analysis_writes_markdown_and_publishes(cli, capsys):
    save_analysis(cli.out, detected())
    assert cli("--reuse-analysis", "--publish-to-assistant") == 0
    md = (cli.out / "1._곱셈.md").read_text(encoding="utf-8")
    assert "## [수학 1. 곱셈] 2~3차시 곱셈구구 익히기 (지도서 p.4~5)" in md
    published = cli.tmp / "notebooklm" / "수학" / "1._곱셈.md"
    assert published.read_text(encoding="utf-8") == md
    report = json.loads((cli.out / "analysis.json").read_text(encoding="utf-8"))
    assert report["validation_issues"] == [] and report["page_count"] == 6 and report["analysis"]["lessons"][1]["from"] == 2
    assert "차시 소스 3개 생성" in capsys.readouterr().out


def test_main_reuse_analysis_failing_validation_returns_2_and_writes_no_source(cli, capsys):
    save_analysis(cli.out, detected(starts=(2, 3, 6)))               # 2~3차시가 3쪽에서 시작한다고 잘못 감지
    assert cli("--reuse-analysis", "--publish-to-assistant") == 2
    assert not (cli.out / "1._곱셈.md").exists() and not (cli.tmp / "notebooklm").exists()
    report = json.loads((cli.out / "analysis.json").read_text(encoding="utf-8"))
    assert any("곱셈구구 익히기" in i for i in report["validation_issues"])
    assert "검토 필요" in capsys.readouterr().out


def test_main_reuse_analysis_without_saved_file_is_a_usage_error(cli):
    with pytest.raises(SystemExit) as exc:
        cli("--reuse-analysis")
    assert exc.value.code == 2
