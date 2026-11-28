"""InboxSheet.append — '빠른입력' 맨 아래에 한 줄 덧붙이기 (ISSUE-008)."""
from schooltodo.inbox import InboxSheet


class FakeWs:
    def __init__(self, rows=()):
        self.rows, self.calls = [list(r) for r in rows], []

    def append_row(self, values, **options):
        self.calls.append((values, options))
        self.rows.append(list(values))

    def get_all_values(self):
        return self.rows


def test_append_writes_raw_one_cell_in_column_a():
    ws = FakeWs()
    InboxSheet(ws).append("다음주 화요일 공문 마감")
    assert ws.calls == [(["다음주 화요일 공문 마감"], {"value_input_option": "RAW", "table_range": "A1"})]


def test_formula_like_text_stays_text():
    ws = FakeWs()
    InboxSheet(ws).append("=HYPERLINK(\"x\")")
    assert ws.calls[0][1]["value_input_option"] == "RAW"      # USER_ENTERED 면 수식이 된다


def test_appended_line_is_pending_for_sync():
    ws = FakeWs([["내용", "처리"], ["이미 한 일", "완료"]])
    box = InboxSheet(ws)
    box.append("새 할 일")
    assert box.pending() == [(3, "새 할 일")]
