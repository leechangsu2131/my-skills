import pathlib
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1] / "skills" / "admin-hitalk-sender"
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

import hitalk_sender  # noqa: E402


def test_parse_target_names_deduplicates_and_splits():
    assert hitalk_sender.parse_target_names(["학생A, 학생B", "학생A", "학생C"]) == [
        "학생A",
        "학생B",
        "학생C",
    ]
    assert hitalk_sender.parse_target_names(None) == []


def test_read_roster_file_csv_and_tsv(tmp_path):
    csv_file = tmp_path / "roster.csv"
    csv_file.write_text("번호,이름,성별\n1,학생A,남\n2,학생B,여\n", encoding="utf-8-sig")

    tsv_file = tmp_path / "roster.txt"
    tsv_file.write_text("번호\t이름\t성별\n1\t학생A\t남\n2\t학생B\t여\n", encoding="utf-8")

    expected = [["번호", "이름", "성별"], ["1", "학생A", "남"], ["2", "학생B", "여"]]
    assert hitalk_sender.read_roster_file(str(csv_file)) == expected
    assert hitalk_sender.read_roster_file(str(tsv_file)) == expected


def test_parse_students_with_target_names_and_missing_filter_column():
    raw_data = [
        ["번호", "이름", "성별"],
        ["1", "학생A", "남"],
        ["2", "학생B", "여"],
    ]
    config = {
        "name_column": 1,
        "score_column": 2,
        "recipient_filter_column": "보충지도",
        "recipient_filter_values": "y",
    }

    selected = hitalk_sender.parse_students(
        raw_data, config, target_names=["학생B"], allow_missing_filter_column=True
    )
    assert [s["name"] for s in selected] == ["학생B"]
    assert selected[0]["fields"]["성별"] == "여"

    all_students = hitalk_sender.parse_students(
        raw_data, config, target_names=None, allow_missing_filter_column=True
    )
    assert [s["name"] for s in all_students] == ["학생A", "학생B"]
