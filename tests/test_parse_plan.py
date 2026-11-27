"""skills/teacherlesson-assistant/prepare_lessons.py 의 parse_plan(수업 형태·단계 뼈대 검사) 시험 (S1).

Gemini·진도 서버·슈파베이스는 부르지 않는다(가짜 글만 넣는다). parse_flow 시험은 test_prepare_lessons.py 에 있다.
"""
import json

import pytest

import prepare_lessons as pl


def step(name, minutes, **extra):
    return {"name": name, "minutes": minutes, **extra}


def plan(steps, **over):
    base = {"lesson_type": "개념 익히기", "goal": "분수를 더한다", "materials": "분수 막대, 딱지",
            "steps": steps, "homework": "익힘책 3쪽", "pages": "교과서 10~12쪽"}
    base.update(over)
    return json.dumps(base, ensure_ascii=False)


FOUR = [step("도입", 5), step("활동 1", 15), step("활동 2", 15), step("정리", 5)]   # 합계 40


def test_valid_plan_is_normalized():
    r = pl.parse_plan(plan(FOUR))
    assert [s["name"] for s in r["steps"]] == ["도입", "활동 1", "활동 2", "정리"]
    assert [s["minutes"] for s in r["steps"]] == [5, 15, 15, 5]
    assert r["lesson_type"] == "개념 익히기" and r["goal"] == "분수를 더한다"
    assert r["materials"] == ["분수 막대", "딱지"]
    assert r["homework"] == "익힘책 3쪽" and r["pages"] == "교과서 10~12쪽"
    assert all(s["purpose"] == "" for s in r["steps"])


def test_answer_with_chatter_and_code_block_is_read():
    text = "뼈대는 아래와 같아요.\n```json\n" + plan(FOUR) + "\n```\n도움이 되길 바랍니다."
    assert len(pl.parse_plan(text)["steps"]) == 4


@pytest.mark.parametrize("n", [0, 1, 3, 9])
def test_step_count_must_be_4_to_8(n):
    # 3개(합 40)·9개(합 40) 등 합계는 맞지만 개수가 범위 밖
    steps = [step(f"단계{i}", 40 // n if n else 0) for i in range(n)]
    if n:
        steps[-1]["minutes"] += 40 - sum(s["minutes"] for s in steps)
    with pytest.raises(ValueError, match="4~8"):
        pl.parse_plan(plan(steps))


def test_steps_missing_or_not_a_list_is_an_error():
    for bad in ('{"lesson_type": "x"}', '{"steps": "도입 5분"}', '{"steps": {"name": "도입"}}'):
        with pytest.raises(ValueError):
            pl.parse_plan(bad)


@pytest.mark.parametrize("bad", [{"minutes": 5}, {"name": "  ", "minutes": 5}, "도입", None])
def test_step_without_name_is_an_error(bad):
    steps = [bad, step("활동 1", 15), step("활동 2", 15), step("정리", 5)]
    with pytest.raises(ValueError, match="이름"):
        pl.parse_plan(plan(steps))


@pytest.mark.parametrize("minutes", [0, 41, "없음", None, ""])
def test_step_minutes_out_of_range_is_an_error(minutes):
    steps = [step("도입", minutes), step("활동 1", 15), step("활동 2", 15), step("정리", 5)]
    with pytest.raises(ValueError, match="1~40"):
        pl.parse_plan(plan(steps))


def test_negative_minutes_is_an_error_not_read_as_positive():
    # 예전에는 -5 가 5 로 읽혀 합계 40 이 맞아 그대로 통과했다(ISSUE-새, 고침)
    steps = [step("도입", -5), step("활동 1", 15), step("활동 2", 15), step("정리", 5)]
    with pytest.raises(ValueError, match="1~40"):
        pl.parse_plan(plan(steps))


def test_minutes_may_be_written_as_text():
    steps = [step("도입", "5분"), step("활동 1", "15 분"), step("활동 2", 15.0), step("정리", "5")]
    assert [s["minutes"] for s in pl.parse_plan(plan(steps))["steps"]] == [5, 15, 15, 5]


@pytest.mark.parametrize("total", [39, 41])
def test_minutes_must_add_up_to_40(total):
    steps = [step("도입", 5), step("활동 1", 15), step("활동 2", 15), step("정리", total - 35)]
    with pytest.raises(ValueError, match="40분"):
        pl.parse_plan(plan(steps))


def test_flag_only_keep_or_cut_survives_case_insensitive():
    steps = [step("도입", 5, flag=" KEEP "), step("활동 1", 15, flag="cut"),
             step("활동 2", 15, flag="maybe"), step("정리", 5)]
    flags = [s.get("flag") for s in pl.parse_plan(plan(steps))["steps"]]
    assert flags == ["keep", "cut", None, None]


def test_text_fields_are_stripped_and_cut_to_their_limits():
    steps = [step("  " + "가" * 100 + "  ", 5, purpose="나" * 400), step("활동 1", 15),
             step("활동 2", 15), step("정리", 5)]
    r = pl.parse_plan(plan(steps, goal="다" * 400, homework="라" * 400, pages="마" * 200, lesson_type="바" * 100))
    assert r["steps"][0]["name"] == "가" * 80
    assert r["steps"][0]["purpose"] == "나" * 300
    assert (len(r["goal"]), len(r["homework"]), len(r["pages"]), len(r["lesson_type"])) == (300, 300, 100, 80)


def test_missing_or_null_top_level_fields_become_empty_not_none():
    r = pl.parse_plan(json.dumps({"steps": FOUR, "goal": None, "homework": None}))
    assert (r["lesson_type"], r["goal"], r["homework"], r["pages"], r["materials"]) == ("", "", "", "", [])


def test_step_with_and_in_name_is_split_in_two():
    steps = [step("도입", 5), step("관찰 및 비교", 15), step("활동 2", 15), step("정리", 5)]
    r = pl.parse_plan(plan(steps))
    got = [(s["name"], s["minutes"]) for s in r["steps"]]
    assert got == [("도입", 5), ("관찰", 7), ("비교", 8), ("활동 2", 15), ("정리", 5)]
    assert all(s["purpose"].startswith("운영 제안") for s in r["steps"][1:3])
    assert sum(s["minutes"] for s in r["steps"]) == 40


def test_and_split_is_skipped_for_one_minute_or_empty_side():
    steps = [step("도입 및 안내", 1), step("활동 1", 19), step("활동 2", 15), step("및 정리", 5)]
    r = pl.parse_plan(plan(steps))
    assert [s["name"] for s in r["steps"]] == ["도입 및 안내", "활동 1", "활동 2", "및 정리"]


def test_prepare_and_present_step_is_expanded_into_three():
    steps = [step("도입", 5), step("모둠 준비 및 발표", 18), step("활동 2", 12), step("정리", 5)]
    r = pl.parse_plan(plan(steps))
    names = [s["name"] for s in r["steps"]]
    assert names[1:4] == ["발표할 내용 준비", "발표 방법과 듣는 약속 안내", "발표하고 듣는 학생의 반응 나누기"]
    assert [s["minutes"] for s in r["steps"][1:4]] == [6, 1, 11]     # 18 = 18//3 + 1 + 나머지
    assert sum(s["minutes"] for s in r["steps"]) == 40
    assert "모둠 수" in r["steps"][2]["purpose"]                       # 모둠 수·순서를 정해 두지 않음


def test_two_minute_presentation_step_has_no_guide_step():
    steps = [step("도입", 5), step("발표 준비 및 발표", 2), step("활동 2", 28), step("정리", 5)]
    r = pl.parse_plan(plan(steps))
    assert [s["name"] for s in r["steps"][1:3]] == ["발표할 내용 준비", "발표하고 듣는 학생의 반응 나누기"]
    assert [s["minutes"] for s in r["steps"][1:3]] == [1, 1]


def test_too_many_detailed_steps_is_an_error():
    steps = [step(f"가 및 나{i}", 5) for i in range(8)]       # 8개 × 5분 = 40분, 각각 둘로 나뉘어 16개
    with pytest.raises(ValueError, match="12개"):
        pl.parse_plan(plan(steps))


def test_no_json_is_an_error():
    for text in ("없음", "", "중괄호 {만"):
        with pytest.raises(ValueError):
            pl.parse_plan(text)
