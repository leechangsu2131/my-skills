import json
import os
from pathlib import Path

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials


SCHEDULE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(SCHEDULE_DIR / ".env")

SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME", "\uc2dc\ud2b81")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
DONE_COLUMN_NAME = "\uc2e4\ud589\uc5ec\ubd80"
DONE_COLUMN_FALLBACK_INDEX = 6
SUBJECT_KEY = "\uacfc\ubaa9"
LESSON_KEY = "\ucc28\uc2dc"
TITLE_KEY = "\uc218\uc5c5\ub0b4\uc6a9"
UNIT_KEY = "\ub300\ub2e8\uc6d0"
REPLACE_APPEND = "append"
REPLACE_SUBJECTS = "replace-subjects"
REPLACE_ALL = "replace-all"
VALID_REPLACE_MODES = {REPLACE_APPEND, REPLACE_SUBJECTS, REPLACE_ALL}


def get_sheet():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON").replace("\\n", "\n")
    creds = Credentials.from_service_account_info(
        json.loads(creds_json, strict=False),
        scopes=SCOPES,
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    return sh, sh.worksheet(SHEET_NAME)


def find_duplicate_rows(ws):
    records = ws.get_all_records(default_blank="")
    seen = {}
    duplicates = []

    for row_index, record in enumerate(records, start=2):
        key = (
            record.get(SUBJECT_KEY, ""),
            str(record.get(LESSON_KEY, "")),
            record.get(TITLE_KEY, ""),
            record.get(UNIT_KEY, ""),
        )
        if key[0]:
            if key in seen:
                duplicates.append(row_index)
            else:
                seen[key] = row_index

    return duplicates


def delete_duplicate_rows(ws):
    duplicates = find_duplicate_rows(ws)
    if not duplicates:
        print("  \uc911\ubcf5 \ud589\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.")
        return 0

    print(f"  \uc911\ubcf5 \ud589 {len(duplicates)}\uac1c \ubc1c\uacac: {duplicates}")
    for row_index in sorted(duplicates, reverse=True):
        ws.delete_rows(row_index)
        print(f"    - {row_index}\ud589 \uc0ad\uc81c")
    return len(duplicates)


def build_row_for_headers(headers, record):
    row = []
    for index, header in enumerate(headers, start=1):
        normalized_header = str(header).strip()
        if normalized_header:
            row.append(record.get(normalized_header, ""))
        elif index == DONE_COLUMN_FALLBACK_INDEX:
            row.append(record.get(DONE_COLUMN_NAME, False))
        else:
            row.append("")
    return row


def collect_subject_names(rows):
    subjects = []
    seen = set()
    for row in rows:
        subject = str(row.get(SUBJECT_KEY, "")).strip()
        if subject and subject not in seen:
            seen.add(subject)
            subjects.append(subject)
    return subjects


def find_rows_by_subjects(ws, subject_names):
    targets = {str(name).strip() for name in subject_names if str(name).strip()}
    if not targets:
        return []

    records = ws.get_all_records(default_blank="")
    return [
        row_index
        for row_index, record in enumerate(records, start=2)
        if str(record.get(SUBJECT_KEY, "")).strip() in targets
    ]


def _group_row_indices(row_indices):
    ordered = sorted(set(row_indices))
    if not ordered:
        return []

    ranges = []
    start = end = ordered[0]
    for row_index in ordered[1:]:
        if row_index == end + 1:
            end = row_index
            continue
        ranges.append((start, end))
        start = end = row_index
    ranges.append((start, end))
    return ranges


def delete_rows_by_indices(ws, row_indices, *, print_fn=print):
    ranges = _group_row_indices(row_indices)
    if not ranges:
        return 0

    total = 0
    for start, end in reversed(ranges):
        if start == end:
            ws.delete_rows(start)
            print_fn(f"    - {start}행 삭제")
            total += 1
        else:
            ws.delete_rows(start, end)
            print_fn(f"    - {start}~{end}행 삭제")
            total += end - start + 1
    return total


def delete_subject_rows(ws, subject_names, *, print_fn=print):
    row_indices = find_rows_by_subjects(ws, subject_names)
    if not row_indices:
        print_fn("  삭제할 기존 과목 행이 없습니다.")
        return 0

    print_fn(f"  기존 과목 행 {len(row_indices)}개 발견: {', '.join(collect_subject_names([{SUBJECT_KEY: name} for name in subject_names]))}")
    return delete_rows_by_indices(ws, row_indices, print_fn=print_fn)


def delete_all_data_rows(ws, *, print_fn=print):
    all_rows = ws.get_all_values()
    if len(all_rows) <= 1:
        print_fn("  삭제할 기존 데이터 행이 없습니다.")
        return 0

    start_row = 2
    end_row = len(all_rows)
    ws.delete_rows(start_row, end_row)
    print_fn(f"  기존 데이터 {end_row - start_row + 1}행 삭제")
    return end_row - start_row + 1


def upload_rows_to_sheet(rows, *, cleanup=False, replace_mode=REPLACE_APPEND, print_fn=print):
    if replace_mode not in VALID_REPLACE_MODES:
        raise ValueError(f"unsupported replace mode: {replace_mode}")

    _sh, ws = get_sheet()
    headers = ws.row_values(1)
    print_fn(f"\n[\uc5c5\ub85c\ub4dc] \ud5e4\ub354: {headers}")

    new_rows = [build_row_for_headers(headers, row) for row in rows]
    if not new_rows:
        print_fn("\n[\uc54c\ub9bc] \uc5c5\ub85c\ub4dc\ud560 \ud589\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.")
        return 0

    if replace_mode == REPLACE_SUBJECTS:
        subject_names = collect_subject_names(rows)
        print_fn(f"\n  [과목별 기존 행 삭제 중..] {', '.join(subject_names)}")
        deleted = delete_subject_rows(ws, subject_names, print_fn=print_fn)
        print_fn(f"  {deleted}개 기존 행 삭제 완료")
    elif replace_mode == REPLACE_ALL:
        print_fn("\n  [전체 기존 행 삭제 중..]")
        deleted = delete_all_data_rows(ws, print_fn=print_fn)
        print_fn(f"  {deleted}개 기존 행 삭제 완료")

    if cleanup:
        print_fn("\n  [\uc911\ubcf5 \ud589 \uc0ad\uc81c \uc911..]")
        deleted = delete_duplicate_rows(ws)
        print_fn(f"  {deleted}\uac1c \uc911\ubcf5 \ud589 \uc0ad\uc81c \uc644\ub8cc")

    ws.append_rows(new_rows, value_input_option="USER_ENTERED")
    print_fn(f"\n  -> {len(new_rows)}\ud589 \uc5c5\ub85c\ub4dc \uc644\ub8cc")
    return len(new_rows)
