"""export.py 순수 함수 시험 (네트워크·비밀값·실제 학생 자료 없이, 가짜 이름만 사용).

- parse_names: 이름 칸 글(JSON 배열·쉼표·공백)을 이름 목록으로
- export_to_excel: 학생별로 나눠 시트를 만드는 부분 (저장 위치는 임시 폴더로 바꿔서 시험)
소스는 고치지 않는다. 현재 동작과 다르게 기대하는 것은 xfail 로 표시하고 이유를 적었다.
"""
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export  # noqa: E402

NAME_COL = "🧑‍🎓 이름"


# ── parse_names ────────────────────────────────────────────────

@pytest.mark.parametrize("raw", [None, "", "   "])
def test_parse_names_empty_inputs(raw):
    assert export.parse_names(raw) == []


def test_parse_names_json_array():
    assert export.parse_names('["학생A", "학생B", "학생C"]') == ["학생A", "학생B", "학생C"]


def test_parse_names_json_array_with_outer_spaces():
    assert export.parse_names('  ["학생A","학생B"]  ') == ["학생A", "학생B"]


def test_parse_names_json_array_strips_and_drops_blank_items():
    assert export.parse_names('[" 학생A ", "", "  ", "학생B"]') == ["학생A", "학생B"]


def test_parse_names_comma_separated():
    assert export.parse_names("학생A,학생B,학생C") == ["학생A", "학생B", "학생C"]


def test_parse_names_comma_and_space():
    assert export.parse_names("학생A, 학생B ,  학생C") == ["학생A", "학생B", "학생C"]


def test_parse_names_whitespace_separated():
    assert export.parse_names("학생A 학생B\t학생C\n학생D") == ["학생A", "학생B", "학생C", "학생D"]


def test_parse_names_single_name():
    assert export.parse_names("학생A") == ["학생A"]


def test_parse_names_leading_trailing_separators():
    assert export.parse_names(", 학생A, 학생B, ") == ["학생A", "학생B"]


def test_parse_names_empty_json_array():
    assert export.parse_names("[]") == []


def test_parse_names_broken_json_falls_back_to_split():
    # JSON 이 깨져도 멈추지 않고 쉼표·공백으로 나눈다(대괄호·따옴표는 남는 것이 현재 동작).
    result = export.parse_names('["학생A", "학생B"')
    assert len(result) == 2
    assert "학생A" in result[0] and "학생B" in result[1]


@pytest.mark.xfail(
    reason="대괄호는 있지만 JSON 이 아닌 글('[학생A 학생B]')은 대괄호가 이름에 붙는다 "
    "(현재 동작: ['[학생A', '학생B]']). 대괄호를 떼는 것이 바람직해 보임(추정).",
    strict=False,
)
def test_parse_names_brackets_without_json_are_removed():
    assert export.parse_names("[학생A 학생B]") == ["학생A", "학생B"]


@pytest.mark.xfail(
    reason="JSON 배열 안에 문자열이 아닌 값(숫자 등)이 있으면 p.strip() 에서 AttributeError 로 멈춘다.",
    strict=False,
)
def test_parse_names_json_array_with_non_string_items_does_not_crash():
    result = export.parse_names('["학생A", 3]')
    assert "학생A" in result


@pytest.mark.xfail(
    reason="공백으로도 나누므로 이름 안에 공백이 있는 값('학생 A')이 둘로 쪼개진다(JSON 배열이 아닐 때).",
    strict=False,
)
def test_parse_names_comma_list_keeps_names_with_inner_space():
    assert export.parse_names("학생 A, 학생 B") == ["학생 A", "학생 B"]


# ── export_to_excel ────────────────────────────────────────────

@pytest.fixture
def out_dir(tmp_path, monkeypatch):
    """data_dir() 결과를 임시 폴더로 바꿔 개인정보가 실제 폴더에 쓰이지 않게 한다."""
    monkeypatch.setattr(export, "data_dir", lambda: tmp_path)
    return tmp_path


def _open(out_dir):
    return load_workbook(out_dir / "student_records.xlsx")


def test_get_supabase_data_keeps_tls_verification_enabled(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_KEY", "fake-test-key")
    monkeypatch.setenv("SUPABASE_TABLE_NAME", "fake_table")
    monkeypatch.setattr(export, "load_env", lambda: None)
    captured = {}

    class FakeResponse:
        ok = True
        def json(self):
            return [{"id": 1}]

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(export.requests, "get", fake_get)
    assert export.get_supabase_data() == [{"id": 1}]
    assert captured["url"] == "https://example.invalid/rest/v1/fake_table?select=*"
    assert captured.get("verify", True) is not False


def test_export_splits_multi_student_record_into_each_sheet(out_dir):
    records = [
        {"id": 1, NAME_COL: '["학생A", "학생B"]', "내용": "모둠 발표"},
        {"id": 2, NAME_COL: "학생A", "내용": "독서 기록"},
    ]
    export.export_to_excel(records)
    wb = _open(out_dir)
    assert sorted(wb.sheetnames) == ["학생A", "학생B"]
    assert wb["학생A"].max_row == 3  # 머리글 + 기록 2개
    assert wb["학생B"].max_row == 2  # 머리글 + 기록 1개


def test_export_sheet_name_column_holds_only_sheet_owner(out_dir):
    records = [{"id": 1, NAME_COL: "학생A, 학생B", "내용": "함께 한 활동"}]
    export.export_to_excel(records)
    wb = _open(out_dir)
    for student in ("학생A", "학생B"):
        ws = wb[student]
        headers = [c.value for c in ws[1]]
        col = headers.index(NAME_COL) + 1
        assert ws.cell(row=2, column=col).value == student


def test_export_does_not_modify_original_records(out_dir):
    original = {"id": 1, NAME_COL: '["학생A", "학생B"]', "내용": "활동"}
    records = [original]
    export.export_to_excel(records)
    assert original[NAME_COL] == '["학생A", "학생B"]'


def test_export_sheets_sorted_by_student_name(out_dir):
    records = [
        {"id": 1, NAME_COL: "학생C", "내용": "x"},
        {"id": 2, NAME_COL: "학생A", "내용": "y"},
        {"id": 3, NAME_COL: "학생B", "내용": "z"},
    ]
    export.export_to_excel(records)
    assert _open(out_dir).sheetnames == ["학생A", "학생B", "학생C"]


def test_export_sheet_name_replaces_slash_and_backslash(out_dir):
    records = [{"id": 1, NAME_COL: '["학생/A", "학생\\\\B"]', "내용": "x"}]
    export.export_to_excel(records)
    names = _open(out_dir).sheetnames
    assert "학생_A" in names
    assert "학생_B" in names


def test_export_sheet_name_cut_to_31_chars(out_dir):
    long_name = "가" * 40
    export.export_to_excel([{"id": 1, NAME_COL: long_name, "내용": "x"}])
    assert _open(out_dir).sheetnames == ["가" * 31]


def test_export_record_without_name_column_is_skipped(out_dir):
    records = [
        {"id": 1, "내용": "이름 칸 없음"},
        {"id": 2, NAME_COL: "학생A", "내용": "정상"},
    ]
    export.export_to_excel(records)
    assert _open(out_dir).sheetnames == ["학생A"]


def test_export_writes_into_data_dir(out_dir):
    export.export_to_excel([{"id": 1, NAME_COL: "학생A", "내용": "x"}])
    assert (out_dir / "student_records.xlsx").is_file()


@pytest.mark.xfail(
    reason="모든 기록의 이름 칸이 비면 시트가 하나도 없어 openpyxl 이 IndexError 로 멈춘다. "
    "'기록 없음'으로 끝나는 것이 바람직해 보임(추정).",
    strict=False,
)
def test_export_all_records_without_names_does_not_crash(out_dir):
    export.export_to_excel([{"id": 1, "내용": "이름 없음"}])
