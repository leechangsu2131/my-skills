"""prepare_lessons.parse_flow 의 '뼈대 없이 부르는 옛 경로' 에서 분(minutes)을 읽는 법 시험.

음수(-5)가 부호를 잃고 5분이 되던 것을 고친 뒤의 모습이다. 이 경로는 읽을 수 없는 분을 0 으로 두는 느슨한 경로라
음수도 오류가 아니라 0 이 된다(뼈대 검사 parse_plan 은 같은 값을 오류로 거부함 — test_parse_plan.py).
"""
import json

import pytest

import prepare_lessons as pl


def flow(minutes):
    return json.dumps({"steps": [{"name": "도입", "minutes": minutes}]}, ensure_ascii=False)


def first_minutes(minutes):
    return pl.parse_flow(flow(minutes))["steps"][0]["minutes"]


@pytest.mark.parametrize("raw", [-5, "-5", "-5분", "약 -3분", -0.5])
def test_negative_minutes_become_zero_not_positive(raw):
    assert first_minutes(raw) == 0


@pytest.mark.parametrize("raw, expected", [(5, 5), ("5", 5), ("5분", 5), ("15 분", 15), ("3-5분", 3), ("10~15분", 10),
                                           (0, 0), ("없음", 0), (None, 0), ("", 0)])
def test_usual_minutes_are_unchanged(raw, expected):
    assert first_minutes(raw) == expected
