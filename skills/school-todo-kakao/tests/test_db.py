import pytest

from schooltodo.db import SheetsDb


class FakeWorksheet:
    """gspread 워크시트 흉내: get_all_values / append_rows 만 구현."""

    def __init__(self, values):
        self.values = [list(r) for r in values]
        self.last_option = None

    def get_all_values(self):
        return [list(r) for r in self.values]

    def append_rows(self, rows, value_input_option=None):
        self.last_option = value_input_option
        self.values.extend(list(r) for r in rows)


def test_rows_use_header_names_not_positions_and_skip_blank_rows():
    ws = FakeWorksheet(
        [
            ["내용", "날짜", "키", "구분", "상태"],  # 열 순서가 달라도, 대상·출처 열이 없어도 읽힌다
            ["할 일 A", "2026-11-18", "k1", "개인", ""],
            ["", "", "", "", ""],
            ["할 일 B", "2026-11-19", "k2"],  # 뒤쪽 빈 칸이 잘려 온 행
        ]
    )
    rows = SheetsDb(ws).rows()
    assert [r["키"] for r in rows] == ["k1", "k2"]
    assert rows[1]["구분"] == "" and rows[1]["내용"] == "할 일 B"


def test_append_follows_sheet_column_order_and_writes_raw():
    ws = FakeWorksheet([["대상", "키", "날짜", "구분", "내용", "상태", "출처"]])
    SheetsDb(ws).append(
        [{"키": "k", "날짜": "2026-11-18", "구분": "학교", "내용": "x", "상태": "", "출처": "자동", "대상": "체육"}]
    )
    assert ws.values[1] == ["체육", "k", "2026-11-18", "학교", "x", "", "자동"]
    assert ws.last_option == "RAW"  # 날짜를 시트가 다른 형식으로 바꾸지 않게


def test_missing_required_header_is_reported():
    with pytest.raises(ValueError, match="열 이름"):
        SheetsDb(FakeWorksheet([["키", "날짜"]])).rows()
