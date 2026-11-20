from schooltodo.message import MAX_CHARS, MORE_TAIL, friend_rows, one_message


def test_short_lines_fit_as_is():
    assert one_message(["a", "b"]) == "a\nb"


def test_long_message_is_cut_with_tail_and_within_limit():
    lines = ["📅 오늘"] + [f"• 행사 {i} " + "가" * 30 for i in range(10)]
    msg = one_message(lines)
    assert len(msg) <= MAX_CHARS
    assert msg.endswith(MORE_TAIL) and msg.startswith("📅 오늘")


def test_single_huge_line_is_truncated():
    msg = one_message(["가" * 500])
    assert len(msg) <= MAX_CHARS and msg.endswith(MORE_TAIL)


def test_friend_rows_drop_personal_tasks():
    rows = [{"구분": "개인", "내용": "내 할 일"}, {"구분": "출장", "내용": "연수"}, {"구분": "학교", "내용": "행사"}]
    assert [r["내용"] for r in friend_rows(rows)] == ["연수", "행사"]
