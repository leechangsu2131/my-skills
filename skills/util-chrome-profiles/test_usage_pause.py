from datetime import datetime

import pytest

import usage_pause as up

NOW = datetime(2026, 11, 28, 9, 30)


@pytest.mark.parametrize("text, want", [
    ("일시 중지됨: 무료 사용량은 오후 12:10 이후 다시 제공됩니다. 그때 계속하세요.", datetime(2026, 11, 28, 12, 10)),
    ("무료 사용량은 오전 8:05 이후 다시 제공됩니다", datetime(2026, 11, 29, 8, 5)),  # 지난 시각 → 내일
    ("사용량 한도에 도달했습니다. 오후 3시 이후 다시 사용할 수 있어요", datetime(2026, 11, 28, 15, 0)),
    ("오후 12:30에 한도가 초기화됩니다", datetime(2026, 11, 28, 12, 30)),  # 오후 12시 = 낮 12시
    ("5-hour limit reached ∙ resets 3pm", datetime(2026, 11, 28, 15, 0)),
    ("You've hit the Free plan limit. Try again after 12:10 PM.", datetime(2026, 11, 28, 12, 10)),
    ("Usage limit reached. Your limit will reset at 1:05 AM", datetime(2026, 11, 29, 1, 5)),
    ("사용량 한도 — 2시간 30분 후 다시 시도하세요", datetime(2026, 11, 28, 12, 0)),
    ("usage limit, try again in 3 hours", datetime(2026, 11, 28, 12, 30)),
    ("한도에 도달했습니다. 14:20 이후 다시 사용", datetime(2026, 11, 28, 14, 20)),
])
def test_find_resume(text, want):
    assert up.find_resume(text, NOW) == want


@pytest.mark.parametrize("text", ["", "오늘 회의는 오후 3시", "12:10 에 점심", "사용량 한도에 도달했습니다"])
def test_no_resume(text):
    assert up.find_resume(text, NOW) is None


def test_record_list_and_due(tmp_path):
    path = tmp_path / "pauses.json"
    assert up.record(path, "claude-web-3", "무료 사용량은 오후 12:10 이후 다시 제공됩니다", NOW) == datetime(2026, 11, 28, 12, 10)
    assert up.record(path, "gpt-1", "Try again after 10:00 AM", NOW) == datetime(2026, 11, 28, 10, 0)
    assert up.record(path, "x", "아무 말", NOW) is None
    rows = up.due(up.load(path), datetime(2026, 11, 28, 11, 0))
    assert [(n, ok) for n, _, ok in rows] == [("gpt-1", True), ("claude-web-3", False)]
