"""skills/teacherlesson-assistant/prepare_lessons.py 순수 함수 시험.

Gemini·진도 서버·슈파베이스는 부르지 않는다. 단원 md 는 임시 폴더에 가짜로 만든다.
xfail(strict) 시험은 skills/teacherlesson-assistant/ISSUES.md 에 적힌 버그의 재현이다 — 고치면 XPASS 로 실패해 알려 준다.
"""
import json
from datetime import date

import pytest

import prepare_lessons as pl

app = pl.app


# ──────────────────────────── parse_flow ────────────────────────────

def flow_data(**over):
    data = {
        "goal": "분수의 덧셈을 이해한다",
        "materials": ["분수 막대", "딱지"],
        "steps": [
            {"name": "도입", "minutes": 5, "do": "지난 시간 떠올리기", "say": "무엇을 배웠나요?", "tip": "앞 차시 확인", "flag": "keep"},
            {"name": "전개", "minutes": 30, "do": "분수 막대로 더하기", "say": "합이 얼마일까요?", "tip": "", "flag": ""},
            {"name": "정리", "minutes": 5, "do": "배운 것 말하기", "say": "오늘 알게 된 점은?", "tip": "", "flag": "cut"},
        ],
        "homework": "알림장에 준비물 쓰기",
        "pages": "p.2-4",
    }
    data.update(over)
    return data


def as_text(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def test_parse_flow_plain_json_is_normalized():
    flow = pl.parse_flow(as_text(flow_data()))
    assert set(flow) == {"goal", "materials", "steps", "homework", "pages"}
    assert flow["goal"] == "분수의 덧셈을 이해한다"
    assert flow["materials"] == ["분수 막대", "딱지"]
    assert flow["homework"] == "알림장에 준비물 쓰기" and flow["pages"] == "p.2-4"
    assert flow["steps"][0] == {"name": "도입", "do": "지난 시간 떠올리기", "say": "무엇을 배웠나요?",
                                "tip": "앞 차시 확인", "minutes": 5, "flag": "keep"}
    assert [s["minutes"] for s in flow["steps"]] == [5, 30, 5]


def test_parse_flow_flag_only_kept_for_keep_or_cut():
    flow = pl.parse_flow(as_text(flow_data()))
    assert [s.get("flag") for s in flow["steps"]] == ["keep", None, "cut"]   # 빈 flag 는 키 자체가 없다


@pytest.mark.parametrize("raw, expected", [
    ("KEEP", "keep"), (" Cut ", "cut"), ("", None), (None, None), ("skip", None), ("keep!", None)])
def test_parse_flow_flag_normalization(raw, expected):
    flow = pl.parse_flow(as_text({"steps": [{"name": "a", "flag": raw}]}))
    assert flow["steps"][0].get("flag") == expected


def test_parse_flow_answer_wrapped_in_code_block_with_chatter():
    text = ("네, 요청하신 수업 흐름입니다.\n\n```json\n" + json.dumps(flow_data(), ensure_ascii=False, indent=2)
            + "\n```\n\n더 필요하면 말씀해 주세요.")
    flow = pl.parse_flow(text)
    assert flow["goal"] == "분수의 덧셈을 이해한다" and len(flow["steps"]) == 3


def test_parse_flow_code_block_without_language_tag():
    assert pl.parse_flow("```\n" + as_text(flow_data()) + "\n```")["steps"][1]["name"] == "전개"


@pytest.mark.parametrize("raw, expected", [
    ("5분", 5), ("10분 내외", 10), ("약 15분", 15), (7, 7), ("20", 20), (3.0, 3), (None, 0), ("", 0), ("없음", 0)])
def test_parse_flow_minutes_notation(raw, expected):
    flow = pl.parse_flow(as_text({"steps": [{"name": "도입", "minutes": raw}]}))
    assert flow["steps"][0]["minutes"] == expected and isinstance(flow["steps"][0]["minutes"], int)


def test_parse_flow_minutes_missing_key_is_zero():
    assert pl.parse_flow(as_text({"steps": [{"name": "도입"}]}))["steps"][0]["minutes"] == 0


@pytest.mark.parametrize("data", [
    {"goal": "목표"},                       # steps 키 없음
    {"goal": "목표", "steps": []},          # 빈 목록
    {"goal": "목표", "steps": "도입"},      # 목록이 아님
    {"goal": "목표", "steps": None},
])
def test_parse_flow_without_steps_is_an_error(data):
    with pytest.raises(ValueError, match="단계\\(steps\\)가 없음"):
        pl.parse_flow(as_text(data))


@pytest.mark.parametrize("step", [{"name": ""}, {"name": "   "}, {"minutes": 5}, "도입", None, 3])
def test_parse_flow_step_without_name_is_an_error(step):
    with pytest.raises(ValueError, match="단계 이름이 없음"):
        pl.parse_flow(as_text({"steps": [{"name": "도입"}, step]}))


@pytest.mark.parametrize("text", ["죄송하지만 지도서 내용을 찾을 수 없습니다.", "", "}{"])
def test_parse_flow_no_json_is_an_error(text):
    with pytest.raises(ValueError, match="JSON 을 찾지 못함"):
        pl.parse_flow(text)


def test_parse_flow_broken_json_raises_value_error():
    # json.JSONDecodeError 는 ValueError 의 하위 클래스 — prepare_one 이 같이 잡아 한 번 더 묻는다
    with pytest.raises(ValueError):
        pl.parse_flow('{"goal": "끊긴 답", "steps": [')
    with pytest.raises(json.JSONDecodeError):
        pl.parse_flow('{"goal": 따옴표 없음}')


def test_parse_flow_top_level_list_has_no_steps():
    with pytest.raises(ValueError):
        pl.parse_flow(as_text([{"name": "도입"}]))


def test_parse_flow_limits_steps_and_materials():
    many = flow_data(steps=[{"name": f"단계{i}", "minutes": 1} for i in range(12)],
                     materials=[f"준비물{i}" for i in range(20)])
    flow = pl.parse_flow(as_text(many))
    assert [s["name"] for s in flow["steps"]] == [f"단계{i}" for i in range(8)]
    assert len(flow["materials"]) == 12


@pytest.mark.parametrize("raw, expected", [
    ("분수 막대, 딱지·가위、풀", ["분수 막대", "딱지", "가위", "풀"]),
    (" , ,", []),
    (None, []),
    ([], []),
])
def test_parse_flow_materials_forms(raw, expected):
    assert pl.parse_flow(as_text(flow_data(materials=raw)))["materials"] == expected


def test_parse_flow_strips_text_and_fills_missing_fields_with_empty_strings():
    flow = pl.parse_flow(as_text({"goal": "  목표  ", "steps": [{"name": " 도입 ", "do": None}], "pages": None}))
    assert flow["goal"] == "목표" and flow["steps"][0]["name"] == "도입"
    assert flow["steps"][0]["do"] == "" and flow["steps"][0]["say"] == "" and flow["steps"][0]["tip"] == ""
    assert flow["homework"] == "" and flow["pages"] == ""


def test_parse_flow_braces_inside_string_values_are_fine():
    flow = pl.parse_flow(as_text({"goal": "{x}", "steps": [{"name": "도입", "say": "}"}]}))
    assert flow["goal"] == "{x}" and flow["steps"][0]["say"] == "}"


@pytest.mark.parametrize("text", [
    "참고로 {지도서 p.3} 기준입니다.\n" + as_text(flow_data()),
    as_text(flow_data()) + "\n(활동 {모둠} 은 상황에 맞게 바꾸세요)",
], ids=["앞 설명에 중괄호", "뒤 설명에 중괄호"])
def test_parse_flow_explanation_containing_braces_around_json(text):
    assert pl.parse_flow(text)["goal"] == "분수의 덧셈을 이해한다"


@pytest.mark.parametrize("data, texts", [
    ({"goal": None, "steps": [{"name": "도입"}]}, lambda f: [f["goal"]]),
    ({"materials": ["분수 막대", None], "steps": [{"name": "도입"}]}, lambda f: f["materials"]),
], ids=["goal null", "materials 안의 null"])
def test_parse_flow_null_values_do_not_become_the_word_none(data, texts):
    assert "None" not in texts(pl.parse_flow(as_text(data)))


def test_parse_flow_null_material_is_dropped_and_goal_becomes_empty():
    # ISSUE-032 해결: null 은 빈 글·빠짐으로, 나머지 준비물은 그대로
    flow = pl.parse_flow(as_text({"goal": None, "materials": ["분수 막대", None, "  ", "딱지"],
                                  "steps": [{"name": "도입"}]}))
    assert flow["goal"] == ""
    assert flow["materials"] == ["분수 막대", "딱지"]


def test_parse_flow_braces_in_both_explanations_and_nested_json():
    # ISSUE-031 해결: 앞뒤 설명에 중괄호가 있고, JSON 안에도 중괄호 글자가 있어도 읽힌다
    data = flow_data(goal="모둠 {짝} 활동")
    text = "참고 {지도서 p.3}\n" + as_text(data) + "\n(끝 {모둠})"
    assert pl.parse_flow(text)["goal"] == "모둠 {짝} 활동"


def test_parse_flow_skips_empty_object_before_real_flow():
    text = "예시 {} 는 비웠습니다.\n" + as_text(flow_data())
    assert pl.parse_flow(text)["steps"][0]["name"] == "도입"


def test_parse_flow_braces_only_in_explanation_still_an_error():
    with pytest.raises(ValueError):
        pl.parse_flow("참고 {지도서 p.3} 만 있고 JSON 은 없습니다. {끝}")


# ──────────────────────────── parse_day ────────────────────────────

class FakeDate(date):
    """date.today() 만 고정한다. prepare_lessons 가 모듈 전역 date 를 쓰므로 그 이름을 바꿔 끼운다."""
    _today = date(2026, 11, 25)

    @classmethod
    def today(cls):
        return cls._today


@pytest.fixture
def today(monkeypatch):
    def set_today(iso: str):
        FakeDate._today = date.fromisoformat(iso)
    monkeypatch.setattr(pl, "date", FakeDate)
    return set_today


# 2026-11-25 는 수요일
@pytest.mark.parametrize("now, expected", [
    ("2026-11-25", "2026-11-26"),   # 수 → 목
    ("2026-11-26", "2026-11-27"),   # 목 → 금
    ("2026-11-27", "2026-11-30"),   # 금 → 월
    ("2026-11-28", "2026-11-30"),   # 토 → 월
    ("2026-11-29", "2026-11-30"),   # 일 → 월
    ("2026-11-30", "2026-12-01"),   # 월 → 화
    ("2026-12-31", "2027-01-01"),   # 해가 바뀜(금요일)
])
@pytest.mark.parametrize("word", ["tomorrow", "내일", " Tomorrow ", None, ""])
def test_parse_day_tomorrow_skips_weekend(today, now, expected, word):
    today(now)
    got = pl.parse_day(word)
    assert got == date.fromisoformat(expected) and got.weekday() < 5


def test_parse_day_friday_goes_to_monday(today):
    today("2026-11-27")
    assert pl.parse_day("tomorrow").strftime("%A") == "Monday"


@pytest.mark.parametrize("word", ["today", "오늘", "TODAY", "  오늘 "])
def test_parse_day_today_is_today_even_on_weekend(today, word):
    today("2026-11-28")   # 토요일
    assert pl.parse_day(word) == date(2026, 11, 28)


def test_parse_day_iso_date_is_taken_as_is(today):
    today("2026-11-25")
    assert pl.parse_day("2026-11-28") == date(2026, 11, 28)      # 주말이어도 직접 준 날짜는 그대로
    assert pl.parse_day(" 2026-11-24 ") == date(2026, 11, 24)


@pytest.mark.parametrize("bad", ["11/24", "어제", "2026-13-01", "2026-11-31"])
def test_parse_day_rejects_other_text(today, bad):
    today("2026-11-25")
    with pytest.raises(ValueError):
        pl.parse_day(bad)


# ──────────────────────────── lesson_section ────────────────────────────

def filler(tag: str) -> str:
    return (tag + " 지도서 본문 문장입니다. ") * 20     # 200자를 넘는 본문


UNIT_MD = "\n".join([
    "# [국어 3.5단원] 지도서 소스", "",
    "## [국어 3.5단원] 단원 개관 (지도서 p.1~2)", "〔p.1〕", filler("개관"), "",
    "## [국어 3.5단원] 1~2차시 다가가기 (지도서 p.3~6)", "〔p.3〕", filler("가"), "",
    "## [국어 3.5단원] 3~4차시 이해하기 (지도서 p.7~12)", "〔p.7〕", filler("나"), "",
    "## [국어 3.5단원] 5차시 실천하기 (지도서 p.13~16)", "〔p.13〕", filler("다"), "",
    "## [국어 3.5단원] 6차시 돌아보기 (지도서 p.17~18)", "〔p.17〕 짧다", "",
])
UNIT = "3.5. 매체"


@pytest.fixture
def notebooklm(tmp_path, monkeypatch):
    """app.NOTEBOOKLM 을 임시 폴더로 바꾸고, (과목, 단원) 이름으로 md 를 써 주는 함수를 돌려준다."""
    monkeypatch.setattr(app, "NOTEBOOKLM", tmp_path)

    def put(subject, unit, text):
        folder = tmp_path / app.safe_name(subject)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{app.safe_name(unit)}.md").write_text(text, encoding="utf-8")
    put("국어", UNIT, UNIT_MD)
    return put


def lesson(**over):
    base = {"subject": "국어", "unit": UNIT, "lesson": "", "title": ""}
    base.update(over)
    return base


def first_line(text: str) -> str:
    return text.splitlines()[0] if text else ""


@pytest.mark.parametrize("number, heading", [
    ("1", "1~2차시 다가가기"), ("2", "1~2차시 다가가기"),         # 묶음의 어느 쪽이든 그 구간
    ("3", "3~4차시 이해하기"), ("4", "3~4차시 이해하기"),
    ("5", "5차시 실천하기"),
    ("3(3~4)", "3~4차시 이해하기"),                              # 진도표 표기 '3(3~4)'
    ("4(3~4)", "3~4차시 이해하기"),
    ("1(1~2)", "1~2차시 다가가기"),
])
def test_lesson_section_picks_the_section_that_contains_the_lesson_number(notebooklm, number, heading):
    section = pl.lesson_section(lesson(lesson=number))
    assert heading in first_line(section) and first_line(section).startswith("## [국어 3.5단원]")


def test_lesson_section_body_stays_inside_its_own_section(notebooklm):
    section = pl.lesson_section(lesson(lesson="3"))
    assert "나 지도서 본문" in section and "〔p.7〕" in section
    assert "다 지도서 본문" not in section and "가 지도서 본문" not in section     # 앞뒤 구간 글은 없다
    assert "실천하기" not in section and "다가가기" not in section
    assert "개관 지도서 본문" not in section                                       # 단원 개관은 어느 차시에도 안 섞임


@pytest.mark.parametrize("number", ["6", "7", "0"])
def test_lesson_section_empty_when_no_range_or_body_too_short(notebooklm, number):
    # 6차시는 구간은 있으나 본문이 200자 이하, 7·0 은 어느 구간에도 속하지 않음
    assert pl.lesson_section(lesson(lesson=number)) == ""


@pytest.mark.parametrize("title, heading", [
    ("실천하기", "5차시 실천하기"),
    ("  실천하기 ", "5차시 실천하기"),        # 앞뒤·겹친 공백은 정리해 비교
    ("이해하기", "3~4차시 이해하기"),
    ("다가가기", "1~2차시 다가가기"),
])
def test_lesson_section_numberless_lesson_matches_stage_title(notebooklm, title, heading):
    section = pl.lesson_section(lesson(lesson="", title=title))
    assert heading in first_line(section)
    assert section.count("## [") == 1                    # 지도서 전체가 아니라 그 단계 구간만


@pytest.mark.parametrize("over", [
    {"lesson": "", "title": "없는 제목"},
    {"lesson": "", "title": ""},
    {"lesson": "실천하기", "title": ""},               # 숫자가 없으면 번호로는 못 찾음
])
def test_lesson_section_numberless_lesson_without_matching_title_gets_nothing(notebooklm, over):
    assert pl.lesson_section(lesson(**over)) == ""


def test_lesson_section_numbered_lesson_does_not_fall_back_to_title(notebooklm):
    # 번호가 있는데 구간이 없으면(7차시) 제목이 같은 구간이 있어도 그 구간을 주지 않는다
    assert pl.lesson_section(lesson(lesson="7", title="실천하기")) == ""


def test_lesson_section_missing_unit_or_file(notebooklm):
    assert pl.lesson_section(lesson(unit="", lesson="1")) == ""
    assert pl.lesson_section(lesson(unit="9. 없는 단원", lesson="1")) == ""
    assert pl.lesson_section(lesson(subject="수학", lesson="1")) == ""


def test_lesson_section_skips_notes_for_missing_pdf(notebooklm):
    notebooklm("국어", "노트 단원",
               "## [국어 노트 단원] 1차시 제목\n(이 PC에 지도서 PDF가 없어 글자를 넣지 못함: x.pdf)\n" + "가" * 300 + "\n")
    assert pl.lesson_section(lesson(unit="노트 단원", lesson="1")) == ""


def test_lesson_section_first_matching_section_wins(notebooklm):
    notebooklm("국어", "겹침", "## [국어 겹침] 1~3차시 가\n" + filler("첫째") + "\n## [국어 겹침] 3차시 나\n" + filler("둘째") + "\n")
    section = pl.lesson_section(lesson(unit="겹침", lesson="3"))
    assert "1~3차시 가" in first_line(section) and "둘째" not in section


def test_lesson_section_ignores_headings_without_a_lesson_range(notebooklm):
    notebooklm("국어", "표시없음", "## [국어 표시없음] 이름만 있는 제목\n" + filler("가") + "\n")
    assert pl.lesson_section(lesson(unit="표시없음", lesson="1")) == ""


def test_lesson_section_tilde_variants_in_heading(notebooklm):
    notebooklm("국어", "공백", "## [국어 공백] 3 ~ 4차시 공백 있는 표기\n" + filler("가") + "\n")
    assert "공백 있는 표기" in first_line(pl.lesson_section(lesson(unit="공백", lesson="4")))
