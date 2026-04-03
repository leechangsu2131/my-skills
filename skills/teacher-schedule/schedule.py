"""
수업 진도 관리 앱
구글 시트에서 과목/진도 정보를 읽어 동적으로 운영
"""

import json
import os
import re
import sys
from datetime import date, datetime, timedelta

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False


load_dotenv()

SHEET_ID = os.getenv("SHEET_ID")
CREDS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
PDF_BASE_PATH = os.getenv("PDF_BASE_PATH", "./")
PREFERRED_PROGRESS_SHEET_NAME = os.getenv("SHEET_PROGRESS")
LEGACY_PROGRESS_SHEET_NAME = os.getenv("SHEET_NAME", "시트1")
SHEET_NAME = PREFERRED_PROGRESS_SHEET_NAME or LEGACY_PROGRESS_SHEET_NAME

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLUMN_SUBJECT = "과목"
COLUMN_LESSON_ID = "lesson_id"
COLUMN_DATE = "계획일"
COLUMN_DONE = "실행여부"
COLUMN_LESSON = "차시"
COLUMN_TITLE = "수업내용"
COLUMN_UNIT = "대단원"
COLUMN_PDF = "pdf파일"
COLUMN_START_PAGE = "시작페이지"
COLUMN_END_PAGE = "끝페이지"
COLUMN_NOTE = "비고"
COLUMN_EXTENSION_COUNT = "연장횟수"
DONE_COLUMN_FALLBACK_INDEX = 6

REQUIRED_COLUMNS = (
    COLUMN_SUBJECT,
    COLUMN_DATE,
)

DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d")
EXTENSION_NOTE_PREFIX = "[연장일정:"
EXTENSION_NOTE_PATTERN = re.compile(r"\[연장일정:([0-9,\-\s]+)\]")
LESSON_ID_PREFIX = "lesson-"
LESSON_ID_PATTERN = re.compile(rf"^{LESSON_ID_PREFIX}(\d+)$")
CORRUPTED_PROGRESS_HEADER_PREFIX = (
    "slot_date",
    "slot_period",
    "slot_order",
    COLUMN_SUBJECT,
    COLUMN_LESSON_ID,
    "status",
    "source",
    "memo",
)
CORRUPTED_PROGRESS_COLUMN_MAP = (
    (COLUMN_TITLE, 1),
    (COLUMN_SUBJECT, 2),
    (COLUMN_UNIT, 3),
    (COLUMN_LESSON, 4),
    (COLUMN_DATE, 5),
    (COLUMN_DONE, 6),
    (COLUMN_PDF, 7),
    (COLUMN_START_PAGE, 8),
    (COLUMN_END_PAGE, 9),
    (COLUMN_NOTE, 10),
    (COLUMN_LESSON_ID, 11),
)


class ScheduleError(Exception):
    """Base exception for schedule operations."""


class ConfigurationError(ScheduleError):
    """Raised when environment or dependency configuration is invalid."""


class SheetFormatError(ScheduleError):
    """Raised when the worksheet shape or headers are invalid."""


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_done_value(value):
    text = _clean_text(value)
    text = text.lstrip("'").strip()
    return text.upper()


def _sheet_name_candidates(*names):
    candidates = []
    seen = set()
    for name in names:
        normalized = _clean_text(name)
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)
    return candidates


def _lesson_id_of(record):
    return _clean_text(record.get(COLUMN_LESSON_ID))


def _record_identifier(record):
    lesson_id = _lesson_id_of(record)
    if lesson_id:
        return lesson_id
    row_number = record.get("_row")
    return str(row_number) if row_number else ""


def _format_date(value):
    return value.strftime("%Y-%m-%d")


def _row_label(row_number):
    return f"{row_number}행" if row_number else "알 수 없는 행"


def _parse_date(value, *, field_name=COLUMN_DATE, row_number=None, allow_blank=True):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = _clean_text(value)
    if not text:
        if allow_blank:
            return None
        raise ValueError(f"{field_name} 값이 비어 있습니다. ({_row_label(row_number)})")

    # '2026. 3. 2' → '2026-3-2' 정규화 (공백/점 혼합 형식 지원)
    normalized = re.sub(r'\s*\.\s*', '-', text).rstrip('-')
    for candidate in (normalized, text):
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue

    raise ValueError(
        f"{field_name} 날짜 형식이 올바르지 않습니다: {text} ({_row_label(row_number)})"
    )


def _coerce_date(value, *, field_name):
    return _parse_date(value, field_name=field_name, allow_blank=True)


def _coerce_days(days):
    try:
        return int(days)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"일수는 정수여야 합니다: {days}") from exc


def _safe_int(value, default=sys.maxsize):
    text = _clean_text(value)
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        match = re.match(r"^\d+", text)
        if match:
            return int(match.group(0))
        return default


def _looks_like_corrupted_progress_headers(headers, sample_row=None):
    normalized_headers = [_clean_text(header) for header in headers]
    if len(normalized_headers) < 11:
        return False
    if tuple(normalized_headers[:4]) != CORRUPTED_PROGRESS_HEADER_PREFIX[:4]:
        return False
    if tuple(normalized_headers[5:8]) != ("status", "source", "memo"):
        return False
    if _clean_text(normalized_headers[10]) != COLUMN_LESSON_ID:
        return False

    if sample_row is None:
        return True

    expanded = list(sample_row) + [""] * max(0, len(headers) - len(sample_row))
    if not any(_clean_text(value) for value in expanded):
        return True

    title = _clean_text(expanded[0]) if len(expanded) >= 1 else ""
    subject = _clean_text(expanded[1]) if len(expanded) >= 2 else ""
    lesson = _clean_text(expanded[3]) if len(expanded) >= 4 else ""
    planned_date = _clean_text(expanded[4]) if len(expanded) >= 5 else ""
    lesson_id = _clean_text(expanded[10]) if len(expanded) >= 11 else ""

    try:
        parsed_title = _parse_date(title, allow_blank=True)
    except ValueError:
        parsed_title = None
    try:
        parsed_planned_date = _parse_date(planned_date, allow_blank=True)
    except ValueError:
        parsed_planned_date = None

    return (
        bool(subject)
        and parsed_title is None
        and _safe_int(lesson, default=None) is not None
        and parsed_planned_date is not None
        and (not lesson_id or LESSON_ID_PATTERN.fullmatch(lesson_id) is not None)
    )


def _apply_progress_header_aliases(header_map, headers, sample_row=None):
    if not _looks_like_corrupted_progress_headers(headers, sample_row=sample_row):
        return header_map

    for column_name, column_index in CORRUPTED_PROGRESS_COLUMN_MAP:
        if column_index <= len(headers):
            header_map[column_name] = column_index
    return header_map


def _is_done(record):
    value = record.get(COLUMN_DONE, record.get("_done_value", ""))
    if isinstance(value, bool):
        return value

    normalized = _normalize_done_value(value)
    if normalized in {"TRUE", "1", "Y", "YES", "DONE"}:
        return True
    if normalized in {"FALSE", "0", "N", "NO", ""}:
        return False
    return False


def _planned_date(record):
    return _parse_date(
        record.get(COLUMN_DATE),
        field_name=COLUMN_DATE,
        row_number=record.get("_row"),
        allow_blank=True,
    )


def _subject_of(record):
    return _clean_text(record.get(COLUMN_SUBJECT))


def _record_sort_key(record):
    planned = _planned_date(record) or date.max
    lesson = _safe_int(record.get(COLUMN_LESSON))
    row_number = _safe_int(record.get("_row"))
    return (planned, lesson, row_number)


def _lesson_label(record):
    lesson = _clean_text(record.get(COLUMN_LESSON))
    return f"{lesson}차시" if lesson else "차시 미지정"


def _planned_date_label(record):
    planned = _planned_date(record)
    return _format_date(planned) if planned else "계획일 미정"


def _extension_count(record):
    value = record.get(COLUMN_EXTENSION_COUNT, 0)
    if value in ("", None):
        return 0
    try:
        return int(str(value).strip())
    except ValueError:
        return 0


def _strip_extension_note(note_text):
    return EXTENSION_NOTE_PATTERN.sub("", _clean_text(note_text)).strip(" |")


def _extension_dates(record):
    note_text = _clean_text(record.get(COLUMN_NOTE, ""))
    match = EXTENSION_NOTE_PATTERN.search(note_text)
    if not match:
        return []

    dates = []
    for raw_date in match.group(1).split(","):
        parsed = _parse_date(raw_date.strip(), field_name="연장일정", allow_blank=True)
        if parsed:
            dates.append(parsed)
    return sorted(dict.fromkeys(dates))


def _build_note_with_extension_dates(note_text, extension_dates):
    clean_note = _strip_extension_note(note_text)
    if not extension_dates:
        return clean_note

    unique_dates = sorted(dict.fromkeys(extension_dates))
    marker = f"{EXTENSION_NOTE_PREFIX}{','.join(_format_date(d) for d in unique_dates)}]"
    if clean_note:
        return f"{clean_note} | {marker}"
    return marker


def _scheduled_occurrence_dates(record):
    planned = _planned_date(record)
    if planned is None:
        return []
    return [planned] + _extension_dates(record)


def _column_letter(index):
    if index < 1:
        raise ValueError(f"유효하지 않은 컬럼 번호입니다: {index}")

    letters = []
    while index:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def validate_config():
    if not _clean_text(SHEET_ID):
        raise ConfigurationError("환경 변수 SHEET_ID가 설정되어 있지 않습니다.")

    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        return

    if not os.path.exists(CREDS_PATH):
        raise ConfigurationError(
            "GOOGLE_CREDENTIALS_JSON이 없고 자격증명 파일도 찾을 수 없습니다: "
            f"{CREDS_PATH}"
        )


def get_progress_sheet_candidates():
    return _sheet_name_candidates(PREFERRED_PROGRESS_SHEET_NAME, LEGACY_PROGRESS_SHEET_NAME) or ["시트1"]


def resolve_worksheet(spreadsheet, candidates, *, label):
    last_error = None
    for candidate in candidates:
        try:
            return spreadsheet.worksheet(candidate)
        except Exception as exc:
            if exc.__class__.__name__ != "WorksheetNotFound":
                raise
            last_error = exc

    raise SheetFormatError(
        f"{label} 시트를 찾을 수 없습니다. 확인한 이름: {', '.join(candidates)}"
    ) from last_error


def resolve_progress_worksheet(spreadsheet):
    candidates = get_progress_sheet_candidates()
    format_errors = []
    last_error = None

    for candidate in candidates:
        try:
            worksheet = spreadsheet.worksheet(candidate)
        except Exception as exc:
            if exc.__class__.__name__ != "WorksheetNotFound":
                raise
            last_error = exc
            continue

        try:
            _build_header_map(worksheet.row_values(1), sample_row=worksheet.row_values(2))
            return worksheet
        except SheetFormatError as exc:
            format_errors.append(f"{candidate}: {exc}")

    if format_errors:
        raise SheetFormatError(
            "진도표 후보 시트를 찾았지만 형식이 맞지 않습니다. "
            + " | ".join(format_errors)
        )

    raise SheetFormatError(
        f"진도표 시트를 찾을 수 없습니다. 확인한 이름: {', '.join(candidates)}"
    ) from last_error


def get_header_map(ws):
    headers = ws.row_values(1)
    return _build_header_map(headers, sample_row=ws.row_values(2))


def _build_header_map(headers, sample_row=None):
    header_map = {}
    for idx, header in enumerate(headers, start=1):
        normalized = _clean_text(header)
        if normalized and normalized not in header_map:
            header_map[normalized] = idx

    header_map = _apply_progress_header_aliases(header_map, headers, sample_row=sample_row)

    if COLUMN_DONE not in header_map:
        if len(headers) >= DONE_COLUMN_FALLBACK_INDEX:
            header_map[COLUMN_DONE] = DONE_COLUMN_FALLBACK_INDEX
        else:
            raise SheetFormatError(
                f"필수 컬럼이 없습니다: {COLUMN_DONE} (헤더가 없으면 F열이 필요합니다.)"
            )

    missing = [col for col in REQUIRED_COLUMNS if col not in header_map]
    if missing:
        raise SheetFormatError(f"필수 컬럼이 없습니다: {', '.join(missing)}")

    return header_map


def _validate_records(records):
    seen_lesson_ids = {}
    for record in records:
        _planned_date(record)
        _extension_dates(record)
        lesson_id = _lesson_id_of(record)
        if not lesson_id:
            continue
        if lesson_id in seen_lesson_ids:
            first_row = seen_lesson_ids[lesson_id]
            raise SheetFormatError(
                f"lesson_id가 중복되었습니다: {lesson_id} ({_row_label(first_row)}, {_row_label(record.get('_row'))})"
            )
        seen_lesson_ids[lesson_id] = record.get("_row")


def _batch_update_cells(ws, updates):
    _batch_update_cells_with_option(ws, updates, value_input_option="RAW")


def _batch_update_cells_with_option(ws, updates, *, value_input_option):
    if not updates:
        return

    ws.spreadsheet.values_batch_update(
        {
            "valueInputOption": value_input_option,
            "data": updates,
        }
    )


def _worksheet_title(ws):
    return getattr(ws, "title", SHEET_NAME)


def _make_cell_update(column_index, row_index, value, *, worksheet_name=None):
    cell = f"{_column_letter(column_index)}{row_index}"
    target_sheet_name = worksheet_name or SHEET_NAME
    return {"range": f"{target_sheet_name}!{cell}", "values": [[value]]}


def _append_header_column(ws, headers, header_name):
    if not hasattr(ws, "add_cols"):
        raise SheetFormatError(
            f"시트에 '{header_name}' 컬럼을 자동으로 추가할 수 없습니다. 시트에 직접 컬럼을 만든 뒤 다시 실행해 주세요."
        )

    ws.add_cols(1)
    column_index = len(headers) + 1
    _batch_update_cells_with_option(
        ws,
        [_make_cell_update(column_index, 1, header_name, worksheet_name=_worksheet_title(ws))],
        value_input_option="RAW",
    )
    return column_index


def _format_lesson_id(number):
    width = max(4, len(str(number)))
    return f"{LESSON_ID_PREFIX}{number:0{width}d}"


def _next_lesson_id_number(start_number, used_ids):
    candidate = start_number
    while True:
        candidate += 1
        if _format_lesson_id(candidate) not in used_ids:
            return candidate


def _pending_lessons(records, subject):
    pending = [
        record
        for record in records
        if _subject_of(record) == subject and not _is_done(record)
    ]
    return sorted(pending, key=_record_sort_key)


def _scheduled_lessons(records, subject, *, include_done=False):
    lessons = [record for record in records if _subject_of(record) == subject]
    if not include_done:
        lessons = [record for record in lessons if not _is_done(record)]
    lessons = [record for record in lessons if _planned_date(record) is not None]
    return sorted(lessons, key=_record_sort_key)


def _estimate_extension_gap(records, subject, target_record, occurrence_dates):
    for earlier, later in zip(reversed(occurrence_dates[:-1]), reversed(occurrence_dates[1:])):
        gap = later - earlier
        if gap > timedelta(0):
            return gap

    scheduled_all = _scheduled_lessons(records, subject, include_done=True)
    all_dates = []
    for record in scheduled_all:
        all_dates.extend(_scheduled_occurrence_dates(record))

    for earlier, later in zip(reversed(all_dates[:-1]), reversed(all_dates[1:])):
        gap = later - earlier
        if gap > timedelta(0):
            return gap

    return timedelta(days=7)


def _refresh_records(ws):
    records = load_all(ws)
    subjects = get_subjects(records)
    bridge_rows = load_bridge_rows_for_progress_ws(ws)
    return records, subjects, bridge_rows


def connect():
    validate_config()

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise ConfigurationError(
            "Google Sheets 연동 라이브러리가 없습니다. "
            "`pip install -r requirements.txt`를 먼저 실행하세요."
        ) from exc

    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_json = creds_json.replace("\\n", "\n")
        creds_dict = json.loads(creds_json, strict=False)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)

    gc = gspread.authorize(creds)
    return resolve_progress_worksheet(gc.open_by_key(SHEET_ID))


def load_all(ws):
    values = ws.get_all_values()
    headers = values[0] if values else []
    sample_row = values[1] if len(values) > 1 else None
    header_map = _build_header_map(headers, sample_row=sample_row)
    done_index = header_map[COLUMN_DONE]

    records = []
    for row_number, row_values in enumerate(values[1:], start=2):
        expanded = row_values + [""] * max(0, len(headers) - len(row_values))
        record = {}
        for col_index, header in enumerate(headers):
            normalized = _clean_text(header)
            if normalized:
                record[normalized] = expanded[col_index]

        for column_name, column_index in header_map.items():
            if column_index <= len(expanded):
                record[column_name] = expanded[column_index - 1]

        done_value = expanded[done_index - 1] if len(expanded) >= done_index else ""
        record[COLUMN_DONE] = done_value
        record["_done_value"] = done_value
        record[COLUMN_LESSON_ID] = _clean_text(record.get(COLUMN_LESSON_ID, ""))
        record["_row"] = row_number
        record["_record_key"] = _record_identifier(record)
        records.append(record)

    _validate_records(records)
    return records


def _bridge_row_sort_key(row):
    parsed_date = _parse_date(row.get("slot_date"), allow_blank=True) or date.max
    return (
        parsed_date,
        _safe_int(row.get("slot_period")),
        _safe_int(row.get("slot_order")),
        _clean_text(row.get(COLUMN_SUBJECT)),
        _clean_text(row.get(COLUMN_LESSON_ID)),
    )


def _bridge_status(row):
    return _clean_text(row.get("status")).casefold()


def _is_bridge_done(row):
    return _bridge_status(row) == "done"


def _is_bridge_planned(row):
    return _bridge_status(row) in {"", "planned"}


def _record_with_bridge_row(record, bridge_row):
    enriched = dict(record)
    enriched[COLUMN_DATE] = _clean_text(bridge_row.get("slot_date"))
    enriched["계획교시"] = _clean_text(bridge_row.get("slot_period"))
    enriched["slot_date"] = _clean_text(bridge_row.get("slot_date"))
    enriched["slot_period"] = _clean_text(bridge_row.get("slot_period"))
    enriched["slot_order"] = _clean_text(bridge_row.get("slot_order"))
    enriched["status"] = _clean_text(bridge_row.get("status"))
    enriched["source"] = _clean_text(bridge_row.get("source"))
    enriched["memo"] = _clean_text(bridge_row.get("memo"))
    enriched["_bridge_row"] = bridge_row.get("_row")
    return enriched


def _record_with_occurrence_date(record, occurrence_date):
    enriched = dict(record)
    formatted = _format_date(occurrence_date)
    enriched[COLUMN_DATE] = formatted
    enriched["slot_date"] = formatted
    if "slot_period" not in enriched:
        enriched["slot_period"] = ""
    return enriched


def _occurrence_sort_key(record):
    planned = _parse_date(record.get("slot_date") or record.get(COLUMN_DATE), allow_blank=True) or date.max
    return (
        planned,
        _safe_int(record.get("slot_period")),
        _safe_int(record.get(COLUMN_LESSON)),
        _safe_int(record.get("_row")),
    )


def _bridge_rows_for_records(records, bridge_rows, *, subject=None, include_done=False, start_date=None, end_date=None):
    records_by_lesson_id = {
        _lesson_id_of(record): record
        for record in records
        if _lesson_id_of(record)
    }
    matched = []
    for bridge_row in sorted(bridge_rows, key=_bridge_row_sort_key):
        if not include_done and not _is_bridge_planned(bridge_row):
            continue

        parsed_date = _parse_date(bridge_row.get("slot_date"), allow_blank=True)
        if parsed_date is None:
            continue
        if start_date and parsed_date < start_date:
            continue
        if end_date and parsed_date > end_date:
            continue

        bridge_subject = _clean_text(bridge_row.get(COLUMN_SUBJECT))
        if subject and bridge_subject != subject:
            continue

        lesson_id = _clean_text(bridge_row.get(COLUMN_LESSON_ID))
        record = records_by_lesson_id.get(lesson_id)
        if not record:
            continue
        matched.append(_record_with_bridge_row(record, bridge_row))
    return matched


def _load_bridge_support(progress_ws):
    if progress_ws is None:
        return None

    spreadsheet = getattr(progress_ws, "spreadsheet", None)
    if spreadsheet is None or not hasattr(spreadsheet, "worksheet"):
        return None

    try:
        import bridge_sheet
    except Exception:
        return None

    if _clean_text(getattr(progress_ws, "title", "")) == _clean_text(bridge_sheet.BRIDGE_SHEET_NAME):
        return None

    try:
        bridge_ws = spreadsheet.worksheet(bridge_sheet.BRIDGE_SHEET_NAME)
    except Exception as exc:
        if exc.__class__.__name__ == "WorksheetNotFound":
            return None
        raise

    return {
        "module": bridge_sheet,
        "worksheet": bridge_ws,
        "rows": bridge_sheet.load_bridge_rows(bridge_ws),
    }


def load_bridge_rows_for_progress_ws(progress_ws):
    support = _load_bridge_support(progress_ws)
    return list(support["rows"]) if support is not None else None


def ensure_lesson_ids(ws):
    values = ws.get_all_values()
    headers = values[0] if values else []
    header_map = _build_header_map(headers)

    created_column = False
    lesson_id_column = header_map.get(COLUMN_LESSON_ID)
    if lesson_id_column is None:
        lesson_id_column = _append_header_column(ws, headers, COLUMN_LESSON_ID)
        created_column = True

    records = load_all(ws)
    used_ids = {
        lesson_id
        for record in records
        if (lesson_id := _lesson_id_of(record))
    }
    used_numbers = [
        int(match.group(1))
        for lesson_id in used_ids
        if (match := LESSON_ID_PATTERN.fullmatch(lesson_id))
    ]
    next_number = max(used_numbers, default=0)

    updates = []
    assigned = []
    for record in records:
        if _lesson_id_of(record):
            continue

        next_number = _next_lesson_id_number(next_number, used_ids)
        lesson_id = _format_lesson_id(next_number)
        used_ids.add(lesson_id)
        updates.append(
            _make_cell_update(
                lesson_id_column,
                record["_row"],
                lesson_id,
                worksheet_name=_worksheet_title(ws),
            )
        )
        assigned.append(
            {
                "row": record["_row"],
                "lesson_id": lesson_id,
                "title": record.get(COLUMN_TITLE, ""),
            }
        )

    if updates:
        _batch_update_cells(ws, updates)

    if created_column and assigned:
        message = f"lesson_id 컬럼을 만들고 {len(assigned)}개 행에 ID를 채웠습니다."
    elif created_column:
        message = "lesson_id 컬럼을 만들었고, 기존 행에는 이미 모두 ID가 있었습니다."
    elif assigned:
        message = f"누락된 lesson_id {len(assigned)}개를 채웠습니다."
    else:
        message = "모든 행에 lesson_id가 이미 있어 변경할 내용이 없습니다."

    return {
        "created_column": created_column,
        "updated": len(assigned),
        "assigned": assigned,
        "message": message,
    }


def find_record_by_key(records, record_key):
    normalized_key = _clean_text(record_key)
    if not normalized_key:
        return None

    matched_by_id = next(
        (record for record in records if _lesson_id_of(record) == normalized_key),
        None,
    )
    if matched_by_id:
        return matched_by_id

    try:
        row_number = int(normalized_key)
    except ValueError:
        return None
    return next((record for record in records if record.get("_row") == row_number), None)


def get_subjects(records):
    seen = set()
    subjects = []
    for record in records:
        subject = _subject_of(record)
        if subject and subject not in seen:
            seen.add(subject)
            subjects.append(subject)
    return subjects


def get_schedule_by_date(records, target_date, bridge_rows=None):
    target_date = _coerce_date(target_date, field_name="조회 날짜")
    if target_date is None:
        return []
    if bridge_rows is not None:
        return _bridge_rows_for_records(
            records,
            bridge_rows,
            start_date=target_date,
            end_date=target_date,
        )

    lessons = [
        record
        for record in records
        if not _is_done(record)
        and target_date in _scheduled_occurrence_dates(record)
    ]
    return sorted(lessons, key=_record_sort_key)


def get_next_class(records, subject, bridge_rows=None):
    subject = _clean_text(subject)
    if bridge_rows is not None:
        matched = _bridge_rows_for_records(records, bridge_rows, subject=subject)
        return matched[0] if matched else None
    scheduled_pending = [
        record
        for record in _pending_lessons(records, subject)
        if _planned_date(record) is not None
    ]
    return scheduled_pending[0] if scheduled_pending else None


def get_progress(records, subject):
    all_lessons = [record for record in records if _subject_of(record) == subject]
    done = [record for record in all_lessons if _is_done(record)]
    total = len(all_lessons)
    completed = len(done)
    pct = (completed / total * 100) if total > 0 else 0
    return {
        "과목": subject,
        "완료": completed,
        "전체": total,
        "진도율": f"{pct:.1f}%",
    }


def get_remaining_week_lessons(records, start_date=None, bridge_rows=None):
    start_date = _coerce_date(start_date, field_name="조회 날짜") or date.today()
    if start_date.weekday() > 4:
        return []

    end_date = start_date + timedelta(days=4 - start_date.weekday())
    if bridge_rows is not None:
        return _bridge_rows_for_records(
            records,
            bridge_rows,
            start_date=start_date,
            end_date=end_date,
        )
    lessons = [
        record
        for record in records
        if not _is_done(record)
        and any(
            start_date <= scheduled_date <= end_date
            for scheduled_date in _scheduled_occurrence_dates(record)
        )
    ]
    return sorted(lessons, key=_record_sort_key)


def get_schedule_range(records, start_date=None, end_date=None, bridge_rows=None, include_done=False):
    start_date = _coerce_date(start_date, field_name="start date") if start_date is not None else None
    end_date = _coerce_date(end_date, field_name="end date") if end_date is not None else None
    if start_date and end_date and end_date < start_date:
        return []

    if bridge_rows is not None:
        return _bridge_rows_for_records(
            records,
            bridge_rows,
            include_done=include_done,
            start_date=start_date,
            end_date=end_date,
        )

    lessons = []
    for record in records:
        if not include_done and _is_done(record):
            continue

        for occurrence_date in _scheduled_occurrence_dates(record):
            if start_date and occurrence_date < start_date:
                continue
            if end_date and occurrence_date > end_date:
                continue
            lessons.append(_record_with_occurrence_date(record, occurrence_date))

    return sorted(lessons, key=_occurrence_sort_key)


def get_schedule_by_date(records, target_date, bridge_rows=None, include_done=False):
    target_date = _coerce_date(target_date, field_name="target date")
    if target_date is None:
        return []
    return get_schedule_range(
        records,
        start_date=target_date,
        end_date=target_date,
        bridge_rows=bridge_rows,
        include_done=include_done,
    )


def get_next_school_day(records, start_date=None, bridge_rows=None, include_done=False):
    start_date = _coerce_date(start_date, field_name="start date") or date.today()
    schedule_rows = get_schedule_range(
        records,
        start_date=start_date + timedelta(days=1),
        bridge_rows=bridge_rows,
        include_done=include_done,
    )
    for row in schedule_rows:
        parsed_date = _parse_date(row.get("slot_date") or row.get(COLUMN_DATE), allow_blank=True)
        if parsed_date is not None and parsed_date > start_date:
            return parsed_date
    return None


def get_remaining_week_lessons(records, start_date=None, bridge_rows=None, include_done=False):
    start_date = _coerce_date(start_date, field_name="target date") or date.today()
    if start_date.weekday() > 4:
        return []

    end_date = start_date + timedelta(days=4 - start_date.weekday())
    return get_schedule_range(
        records,
        start_date=start_date,
        end_date=end_date,
        bridge_rows=bridge_rows,
        include_done=include_done,
    )


def plan_lesson_extension(records, subject, row_number=None, extra_slots=1):
    subject = _clean_text(subject)
    extra_slots = _coerce_days(extra_slots)
    if extra_slots < 1:
        raise ValueError("연장할 차시 수는 1 이상이어야 합니다.")

    scheduled_pending = _scheduled_lessons(records, subject, include_done=False)

    if row_number is None:
        target_record = scheduled_pending[0] if scheduled_pending else None
    else:
        target_record = next(
            (
                record
                for record in scheduled_pending
                if record.get("_row") == row_number
            ),
            None,
        )

    if not target_record:
        return None

    target_index = next(
        index
        for index, record in enumerate(scheduled_pending)
        if record.get("_row") == target_record.get("_row")
    )
    tail_records = scheduled_pending[target_index:]

    flat_occurrences = []
    for record in tail_records:
        occurrence_dates = _scheduled_occurrence_dates(record)
        flat_occurrences.extend(
            (record, occurrence_index, occurrence_date)
            for occurrence_index, occurrence_date in enumerate(occurrence_dates)
        )

    target_occurrence_dates = _scheduled_occurrence_dates(target_record)
    insertion_index = len(target_occurrence_dates)
    flat_dates = [occurrence_date for _, _, occurrence_date in flat_occurrences]
    extension_gap = _estimate_extension_gap(records, subject, target_record, flat_dates)

    extended_dates = list(flat_dates)
    while len(extended_dates) < len(flat_dates) + extra_slots:
        base_date = extended_dates[-1] if extended_dates else _planned_date(target_record)
        extended_dates.append(base_date + extension_gap)

    added_extension_dates = extended_dates[insertion_index:insertion_index + extra_slots]

    updates_by_row = {}
    for flat_index, (record, occurrence_index, _old_date) in enumerate(
        flat_occurrences[insertion_index:],
        start=insertion_index,
    ):
        updates_by_row.setdefault(record["_row"], {})[occurrence_index] = extended_dates[flat_index + extra_slots]

    record_updates = []
    for record in tail_records:
        occurrence_updates = updates_by_row.get(record["_row"])
        if not occurrence_updates:
            continue

        original_dates = _scheduled_occurrence_dates(record)
        new_dates = [
            occurrence_updates.get(index, original_dates[index])
            for index in range(len(original_dates))
        ]
        record_updates.append(
            {
                "record": record,
                "new_planned_date": new_dates[0],
                "new_extension_dates": new_dates[1:],
            }
        )

    return {
        "subject": subject,
        "target_record": target_record,
        "extra_slots": extra_slots,
        "added_extension_dates": added_extension_dates,
        "record_updates": record_updates,
    }


def _legacy_mark_done_via_bridge(ws, records, subject, target_date=None, record_key=None, bridge_support=None):
    subject = _clean_text(subject)
    target_date = _coerce_date(target_date, field_name="?꾨즺 ?좎쭨")
    bridge_support = _load_bridge_support(ws)
    if bridge_support and bridge_support["rows"]:
        bridge_result = _mark_done_via_bridge(
            ws,
            records,
            subject,
            target_date=target_date,
            record_key=record_key,
            bridge_support=bridge_support,
        )
        if bridge_result is not None:
            return bridge_result
    bridge_support = _load_bridge_support(ws)
    if bridge_support and bridge_support["rows"]:
        bridge_result = _mark_done_via_bridge(
            ws,
            records,
            subject,
            target_date=target_date,
            record_key=record_key,
            bridge_support=bridge_support,
        )
        if bridge_result is not None:
            return bridge_result
    record_key = _clean_text(record_key)

    if record_key:
        target_record = find_record_by_key(records, record_key)
        candidates = [target_record] if target_record else []
    elif target_date:
        candidates = [
            record
            for record in get_schedule_by_date(records, target_date, bridge_rows=bridge_support["rows"])
            if _subject_of(record) == subject
        ]
    else:
        next_class = get_next_class(records, subject, bridge_rows=bridge_support["rows"])
        candidates = [next_class] if next_class else []

    lesson_ids = {
        _lesson_id_of(record)
        for record in candidates
        if record and _lesson_id_of(record)
    }
    if not lesson_ids:
        return None

    updated_bridge_rows = 0
    for bridge_row in bridge_support["rows"]:
        if _clean_text(bridge_row.get(COLUMN_LESSON_ID)) in lesson_ids and not _is_bridge_done(bridge_row):
            bridge_row["status"] = "done"
            updated_bridge_rows += 1

    if updated_bridge_rows == 0:
        return None

    done_column = get_header_map(ws)[COLUMN_DONE]
    worksheet_name = _worksheet_title(ws)
    progress_updates = [
        _make_cell_update(done_column, record["_row"], True, worksheet_name=worksheet_name)
        for record in records
        if _lesson_id_of(record) in lesson_ids and not _is_done(record)
    ]

    _rewrite_bridge_sheet(ws, records, bridge_support)
    _batch_update_cells_with_option(ws, progress_updates, value_input_option="USER_ENTERED")

    return {
        "updated": len(lesson_ids),
        "rows": [record["_row"] for record in records if _lesson_id_of(record) in lesson_ids],
        "message": f"{len(lesson_ids)}媛??섏뾽???꾨즺 泥섎━?덉뒿?덈떎.",
    }


def _legacy_push_schedule_via_bridge(ws, records, subject, days, from_date=None, bridge_support=None):
    subject = _clean_text(subject)
    days = _coerce_days(days)
    from_date = _coerce_date(from_date, field_name="湲곗? ?좎쭨")
    bridge_support = _load_bridge_support(ws)
    if bridge_support and bridge_support["rows"]:
        bridge_result = _push_schedule_via_bridge(
            ws,
            records,
            subject,
            days,
            from_date=from_date,
            bridge_support=bridge_support,
        )
        if bridge_result is not None:
            return bridge_result
    bridge_support = _load_bridge_support(ws)
    if bridge_support and bridge_support["rows"]:
        bridge_result = _push_schedule_via_bridge(
            ws,
            records,
            subject,
            days,
            from_date=from_date,
            bridge_support=bridge_support,
        )
        if bridge_result is not None:
            return bridge_result
    delta = timedelta(days=days)

    updated_rows = []
    for bridge_row in bridge_support["rows"]:
        if not _is_bridge_planned(bridge_row):
            continue
        if _clean_text(bridge_row.get(COLUMN_SUBJECT)) != subject:
            continue
        planned = _parse_date(bridge_row.get("slot_date"), allow_blank=True)
        if planned is None:
            continue
        if from_date and planned < from_date:
            continue
        bridge_row["slot_date"] = _format_date(planned + delta)
        updated_rows.append(bridge_row)

    if not updated_rows:
        return None

    _rewrite_bridge_sheet(ws, records, bridge_support)
    return {
        "updated": len(updated_rows),
        "rows": [row.get("_row") for row in updated_rows if row.get("_row")],
        "message": f"[{subject}] {len(updated_rows)}媛??섏뾽??{days}??諛?덉뒿?덈떎.",
    }


def _generate_future_bridge_slots(subject_rows, extra_slots):
    if extra_slots < 1:
        return []

    sorted_rows = sorted(subject_rows, key=_bridge_row_sort_key)
    parsed_dates = [
        _parse_date(row.get("slot_date"), allow_blank=True)
        for row in sorted_rows
    ]
    parsed_dates = [parsed for parsed in parsed_dates if parsed is not None]
    gap = timedelta(days=7)
    for earlier, later in zip(parsed_dates, parsed_dates[1:]):
        if later > earlier:
            gap = later - earlier

    last_row = sorted_rows[-1]
    last_date = _parse_date(last_row.get("slot_date"), allow_blank=True) or date.today()
    future_slots = []
    next_date = last_date
    for _ in range(extra_slots):
        next_date = next_date + gap
        future_slots.append(
            {
                "slot_date": _format_date(next_date),
                "slot_period": _clean_text(last_row.get("slot_period")),
                "slot_order": _clean_text(last_row.get("slot_order")),
            }
        )
    return future_slots


def _extend_lesson_via_bridge(ws, records, subject, row_number=None, extra_slots=1, bridge_support=None):
    subject = _clean_text(subject)
    extra_slots = _coerce_days(extra_slots)
    if extra_slots < 1:
        raise ValueError("?곗옣??李⑥떆 ?섎뒗 1 ?댁긽?댁뼱???⑸땲??")

    subject_rows = [
        row
        for row in bridge_support["rows"]
        if _is_bridge_planned(row)
        and _clean_text(row.get(COLUMN_SUBJECT)) == subject
        and _parse_date(row.get("slot_date"), allow_blank=True) is not None
    ]
    subject_rows = sorted(subject_rows, key=_bridge_row_sort_key)
    if not subject_rows:
        return None

    target_lesson_id = ""
    if row_number is not None:
        target_record = next((record for record in records if record.get("_row") == row_number), None)
        target_lesson_id = _lesson_id_of(target_record) if target_record else ""

    target_index = None
    if target_lesson_id:
        for index, row in enumerate(subject_rows):
            if _clean_text(row.get(COLUMN_LESSON_ID)) == target_lesson_id:
                target_index = index
                break
    if target_index is None:
        target_index = 0
        target_lesson_id = _clean_text(subject_rows[0].get(COLUMN_LESSON_ID))

    if not target_lesson_id:
        return None

    insertion_index = target_index + 1
    while (
        insertion_index < len(subject_rows)
        and _clean_text(subject_rows[insertion_index].get(COLUMN_LESSON_ID)) == target_lesson_id
    ):
        insertion_index += 1

    clones = [
        {
            COLUMN_SUBJECT: subject,
            COLUMN_LESSON_ID: target_lesson_id,
            "status": "planned",
            "source": "manual_extend",
            "memo": "",
        }
        for _ in range(extra_slots)
    ]
    rewritten_subject_rows = subject_rows[:insertion_index] + clones + subject_rows[insertion_index:]
    slot_templates = [
        {
            "slot_date": _clean_text(row.get("slot_date")),
            "slot_period": _clean_text(row.get("slot_period")),
            "slot_order": _clean_text(row.get("slot_order")),
        }
        for row in subject_rows
    ] + _generate_future_bridge_slots(subject_rows, extra_slots)

    for row, slot_template in zip(rewritten_subject_rows, slot_templates):
        row["slot_date"] = slot_template["slot_date"]
        row["slot_period"] = slot_template["slot_period"]
        row["slot_order"] = slot_template["slot_order"]

    subject_row_ids = {id(row) for row in subject_rows}
    remaining_rows = [row for row in bridge_support["rows"] if id(row) not in subject_row_ids]
    bridge_support["rows"] = remaining_rows + rewritten_subject_rows
    _rewrite_bridge_sheet(ws, records, bridge_support)

    return {
        "updated": len(rewritten_subject_rows),
        "rows": [row.get("_row") for row in rewritten_subject_rows if row.get("_row")],
        "message": (
            f"[{subject}] lesson {target_lesson_id}??{extra_slots}媛?slot???붽??섍퀬 "
            f"?ㅼ쓬 ?섏뾽???ㅻ줈 諛곗튂?덉뒿?덈떎."
        ),
        "shifted": max(0, len(rewritten_subject_rows) - insertion_index - extra_slots),
    }


def _legacy_mark_done(ws, records, subject, target_date=None, record_key=None):
    subject = _clean_text(subject)
    target_date = _coerce_date(target_date, field_name="완료 날짜")
    done_column = get_header_map(ws)[COLUMN_DONE]
    worksheet_name = _worksheet_title(ws)

    if target_date:
        candidates = [
            record
            for record in records
            if _subject_of(record) == subject
            and target_date in _scheduled_occurrence_dates(record)
            and not _is_done(record)
        ]
        candidates = sorted(candidates, key=_record_sort_key)
    else:
        next_class = get_next_class(records, subject)
        candidates = [next_class] if next_class else []

    if not candidates:
        message = f"완료할 수업을 찾지 못했습니다. (과목: {subject})"
        print(f"  [경고] {message}")
        return {"updated": 0, "rows": [], "message": message}

    updates = [
        _make_cell_update(done_column, record["_row"], True, worksheet_name=worksheet_name)
        for record in candidates
    ]
    _batch_update_cells_with_option(ws, updates, value_input_option="USER_ENTERED")

    for record in candidates:
        print(
            f"  [완료] [{record.get(COLUMN_SUBJECT, '')}] "
            f"{record.get(COLUMN_TITLE, '')} ({record.get(COLUMN_DATE, '')})"
        )

    return {
        "updated": len(candidates),
        "rows": [record["_row"] for record in candidates],
        "message": f"{len(candidates)}개 수업을 완료 처리했습니다.",
    }


def _legacy_push_schedule(ws, records, subject, days, from_date=None):
    subject = _clean_text(subject)
    days = _coerce_days(days)
    from_date = _coerce_date(from_date, field_name="기준 날짜")
    header_map = get_header_map(ws)
    date_column = header_map[COLUMN_DATE]
    note_column = header_map.get(COLUMN_NOTE)
    worksheet_name = _worksheet_title(ws)

    targets = []
    for record in _pending_lessons(records, subject):
        planned = _planned_date(record)
        if planned is None:
            continue
        if from_date and planned < from_date:
            continue
        targets.append(record)

    if not targets:
        message = f"밀 수 있는 수업이 없습니다. (과목: {subject})"
        print(f"  [경고] {message}")
        return {"updated": 0, "rows": [], "message": message}

    updates = []
    for record in targets:
        delta = timedelta(days=days)
        new_date = _planned_date(record) + delta
        updates.append(
            _make_cell_update(
                date_column,
                record["_row"],
                _format_date(new_date),
                worksheet_name=worksheet_name,
            )
        )
        extension_dates = _extension_dates(record)
        if note_column and extension_dates:
            shifted_extension_dates = [extension_date + delta for extension_date in extension_dates]
            updates.append(
                _make_cell_update(
                    note_column,
                    record["_row"],
                    _build_note_with_extension_dates(record.get(COLUMN_NOTE, ""), shifted_extension_dates),
                    worksheet_name=worksheet_name,
                )
            )

    _batch_update_cells(ws, updates)

    message = f"[{subject}] {len(targets)}개 수업을 {days}일 밀었습니다."
    print(f"  {message}")
    return {
        "updated": len(targets),
        "rows": [record["_row"] for record in targets],
        "message": message,
    }


def _legacy_extend_lesson(ws, records, subject, row_number=None, extra_slots=1):
    """선택한 차시를 연장하고 같은 과목의 뒤 차시 일정을 뒤로 민다."""
    subject = _clean_text(subject)
    bridge_support = _load_bridge_support(ws)
    if bridge_support and bridge_support["rows"]:
        bridge_result = _extend_lesson_via_bridge(
            ws,
            records,
            subject,
            row_number=row_number,
            extra_slots=extra_slots,
            bridge_support=bridge_support,
        )
        if bridge_result is not None:
            return bridge_result
    header_map = get_header_map(ws)
    note_column = header_map.get(COLUMN_NOTE)
    if not note_column:
        message = "차시 연장을 기록하려면 시트에 '비고' 컬럼이 필요합니다."
        print(f"  [경고] {message}")
        return {"updated": 0, "rows": [], "message": message}

    extension_count_column = header_map.get(COLUMN_EXTENSION_COUNT)
    date_column = header_map[COLUMN_DATE]
    worksheet_name = _worksheet_title(ws)

    plan = plan_lesson_extension(
        records,
        subject,
        row_number=row_number,
        extra_slots=extra_slots,
    )
    if not plan:
        message = f"연장할 미완료 수업을 찾지 못했습니다. ({subject})"
        print(f"  [경고] {message}")
        return {"updated": 0, "rows": [], "message": message}

    target_record = plan["target_record"]
    added_extension_dates = plan["added_extension_dates"]
    record_updates = plan["record_updates"]

    updates = [
        _make_cell_update(
            note_column,
            target_record["_row"],
            _build_note_with_extension_dates(
                target_record.get(COLUMN_NOTE, ""),
                _extension_dates(target_record) + added_extension_dates,
            ),
            worksheet_name=worksheet_name,
        )
    ]
    if extension_count_column:
        updates.append(
            _make_cell_update(
                extension_count_column,
                target_record["_row"],
                str(_extension_count(target_record) + len(added_extension_dates)),
                worksheet_name=worksheet_name,
            )
        )

    for record_update in record_updates:
        record = record_update["record"]
        updates.append(
            _make_cell_update(
                date_column,
                record["_row"],
                _format_date(record_update["new_planned_date"]),
                worksheet_name=worksheet_name,
            )
        )
        updates.append(
            _make_cell_update(
                note_column,
                record["_row"],
                _build_note_with_extension_dates(
                    record.get(COLUMN_NOTE, ""),
                    record_update["new_extension_dates"],
                ),
                worksheet_name=worksheet_name,
            )
        )

    _batch_update_cells(ws, updates)

    message = (
        f"[{subject}] '{target_record.get(COLUMN_TITLE, '')}' 차시를 연장했습니다. "
        f"연장 {len(added_extension_dates)}차시를 기록했고, "
        f"뒤 {len(record_updates)}개 차시 일정을 뒤로 밀었습니다."
    )
    print(f"  {message}")
    return {
        "updated": 1 + len(record_updates),
        "rows": [target_record["_row"]] + [item["record"]["_row"] for item in record_updates],
        "message": message,
        "shifted": len(record_updates),
    }


def _rewrite_bridge_sheet(progress_ws, records, bridge_support):
    bridge_support["rows"] = sorted(bridge_support["rows"], key=_bridge_row_sort_key)
    bridge_support["module"].write_bridge_sheet(bridge_support["worksheet"], bridge_support["rows"])
    bridge_support["rows"] = bridge_support["module"].load_bridge_rows(bridge_support["worksheet"])
    bridge_support["module"].sync_progress_sheet(progress_ws, records, bridge_support["rows"])


def _mark_done_via_bridge(
    ws,
    records,
    subject,
    target_date=None,
    record_key=None,
    bridge_row_number=None,
    bridge_support=None,
):
    subject = _clean_text(subject)
    target_date = _coerce_date(target_date, field_name="완료 날짜")
    if bridge_support is None:
        bridge_support = _load_bridge_support(ws)
    if bridge_support is None:
        return None

    record_key = _clean_text(record_key)
    bridge_row_number = _clean_text(bridge_row_number)
    if bridge_row_number:
        try:
            bridge_row_number = int(bridge_row_number)
        except ValueError as exc:
            raise ValueError(f"Invalid bridge row: {bridge_row_number}") from exc
    else:
        bridge_row_number = None

    sorted_bridge_rows = sorted(bridge_support["rows"], key=_bridge_row_sort_key)

    if bridge_row_number is not None:
        target_rows = [
            row
            for row in sorted_bridge_rows
            if row.get("_row") == bridge_row_number and _is_bridge_planned(row)
        ]
    elif record_key:
        target_record = find_record_by_key(records, record_key)
        lesson_id = _lesson_id_of(target_record) if target_record else ""
        target_rows = [
            row
            for row in sorted_bridge_rows
            if _is_bridge_planned(row)
            and _clean_text(row.get(COLUMN_LESSON_ID)) == lesson_id
            and (not target_date or _parse_date(row.get("slot_date"), allow_blank=True) == target_date)
        ]
        target_rows = target_rows[:1]
    elif target_date:
        target_rows = [
            row
            for row in sorted_bridge_rows
            if _is_bridge_planned(row)
            and _clean_text(row.get(COLUMN_SUBJECT)) == subject
            and _parse_date(row.get("slot_date"), allow_blank=True) == target_date
        ]
    else:
        next_class = get_next_class(records, subject, bridge_rows=bridge_support["rows"])
        bridge_row_id = next_class.get("_bridge_row") if next_class else None
        target_rows = [
            row
            for row in sorted_bridge_rows
            if row.get("_row") == bridge_row_id and _is_bridge_planned(row)
        ]
        target_rows = target_rows[:1]

    lesson_ids = {
        _clean_text(row.get(COLUMN_LESSON_ID))
        for row in target_rows
        if _clean_text(row.get(COLUMN_LESSON_ID))
    }
    if not lesson_ids:
        return None

    updated_target_rows = []
    for bridge_row in target_rows:
        if _is_bridge_done(bridge_row):
            continue
        bridge_row["status"] = "done"
        updated_target_rows.append(bridge_row)

    if not updated_target_rows:
        return None

    done_by_lesson_id = {}
    for lesson_id in lesson_ids:
        has_remaining_planned = any(
            _clean_text(row.get(COLUMN_LESSON_ID)) == lesson_id and _is_bridge_planned(row)
            for row in bridge_support["rows"]
        )
        done_by_lesson_id[lesson_id] = not has_remaining_planned

    done_column = get_header_map(ws)[COLUMN_DONE]
    worksheet_name = _worksheet_title(ws)
    progress_updates = [
        _make_cell_update(
            done_column,
            record["_row"],
            done_by_lesson_id[_lesson_id_of(record)],
            worksheet_name=worksheet_name,
        )
        for record in records
        if _lesson_id_of(record) in done_by_lesson_id
        and _is_done(record) != done_by_lesson_id[_lesson_id_of(record)]
    ]

    _rewrite_bridge_sheet(ws, records, bridge_support)
    _batch_update_cells_with_option(ws, progress_updates, value_input_option="USER_ENTERED")

    return {
        "updated": len(updated_target_rows),
        "rows": [record["_row"] for record in records if _lesson_id_of(record) in lesson_ids],
        "bridge_rows": [row.get("_row") for row in updated_target_rows if row.get("_row")],
        "message": f"Marked {len(updated_target_rows)} bridge slot(s) done.",
    }


def _push_schedule_via_bridge(ws, records, subject, days, from_date=None, bridge_support=None):
    subject = _clean_text(subject)
    days = _coerce_days(days)
    from_date = _coerce_date(from_date, field_name="기준 날짜")
    if bridge_support is None:
        bridge_support = _load_bridge_support(ws)
    if bridge_support is None:
        return None

    delta = timedelta(days=days)
    updated_rows = []
    for bridge_row in bridge_support["rows"]:
        if not _is_bridge_planned(bridge_row):
            continue
        if _clean_text(bridge_row.get(COLUMN_SUBJECT)) != subject:
            continue
        planned = _parse_date(bridge_row.get("slot_date"), allow_blank=True)
        if planned is None:
            continue
        if from_date and planned < from_date:
            continue
        bridge_row["slot_date"] = _format_date(planned + delta)
        updated_rows.append(bridge_row)

    if not updated_rows:
        return None

    _rewrite_bridge_sheet(ws, records, bridge_support)
    return {
        "updated": len(updated_rows),
        "rows": [row.get("_row") for row in updated_rows if row.get("_row")],
        "message": f"[{subject}] shifted {len(updated_rows)} bridge slot(s) by {days} day(s).",
    }


def _coerce_bridge_row_number(value, *, field_name="bridge row"):
    text = _clean_text(value)
    if not text:
        raise ValueError(f"{field_name} is required.")
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name}: {value}") from exc


def _bridge_slot_payload(row):
    return (
        _clean_text(row.get("slot_date")),
        _clean_text(row.get("slot_period")),
        _clean_text(row.get("slot_order")),
    )


def _apply_bridge_slot_payload(row, payload):
    row["slot_date"], row["slot_period"], row["slot_order"] = payload


def move_bridge_slot(ws, records, bridge_row_number, direction, bridge_support=None):
    if bridge_support is None:
        bridge_support = _load_bridge_support(ws)
    if bridge_support is None:
        message = "Bridge sheet is required for slot moves."
        return {"updated": 0, "rows": [], "message": message}

    bridge_row_number = _coerce_bridge_row_number(bridge_row_number)
    direction = _clean_text(direction).casefold()
    step = {
        "earlier": -1,
        "up": -1,
        "previous": -1,
        "later": 1,
        "down": 1,
        "next": 1,
    }.get(direction)
    if step is None:
        raise ValueError(f"Invalid move direction: {direction}")

    planned_rows = [row for row in sorted(bridge_support["rows"], key=_bridge_row_sort_key) if _is_bridge_planned(row)]
    current_index = next(
        (index for index, row in enumerate(planned_rows) if row.get("_row") == bridge_row_number),
        None,
    )
    if current_index is None:
        message = f"No planned bridge slot found for row {bridge_row_number}."
        return {"updated": 0, "rows": [], "message": message}

    target_index = current_index + step
    if target_index < 0 or target_index >= len(planned_rows):
        message = "The lesson is already at the edge of the schedule."
        return {"updated": 0, "rows": [bridge_row_number], "message": message}

    current_row = planned_rows[current_index]
    target_row = planned_rows[target_index]
    current_payload = _bridge_slot_payload(current_row)
    target_payload = _bridge_slot_payload(target_row)
    _apply_bridge_slot_payload(current_row, target_payload)
    _apply_bridge_slot_payload(target_row, current_payload)
    _rewrite_bridge_sheet(ws, records, bridge_support)

    return {
        "updated": 2,
        "rows": [bridge_row_number, target_row.get("_row")],
        "message": "Moved the lesson slot.",
    }


def pull_bridge_slot(ws, records, bridge_row_number, bridge_support=None):
    if bridge_support is None:
        bridge_support = _load_bridge_support(ws)
    if bridge_support is None:
        message = "Bridge sheet is required for subject flow adjustments."
        return {"updated": 0, "rows": [], "message": message}

    bridge_row_number = _coerce_bridge_row_number(bridge_row_number)
    sorted_rows = sorted(bridge_support["rows"], key=_bridge_row_sort_key)
    target_row = next(
        (row for row in sorted_rows if row.get("_row") == bridge_row_number and _is_bridge_planned(row)),
        None,
    )
    if target_row is None:
        message = f"No planned bridge slot found for row {bridge_row_number}."
        return {"updated": 0, "rows": [], "message": message}

    subject = _clean_text(target_row.get(COLUMN_SUBJECT))
    lesson_id = _clean_text(target_row.get(COLUMN_LESSON_ID))
    subject_rows = [
        row
        for row in sorted_rows
        if _is_bridge_planned(row) and _clean_text(row.get(COLUMN_SUBJECT)) == subject
    ]
    target_index = next(
        (index for index, row in enumerate(subject_rows) if row.get("_row") == bridge_row_number),
        None,
    )
    if target_index is None or target_index >= len(subject_rows) - 1:
        message = f"There is no later [{subject}] lesson to pull forward."
        return {"updated": 0, "rows": [bridge_row_number], "message": message}

    slot_templates = [_bridge_slot_payload(row) for row in subject_rows]
    rewritten_subject_rows = subject_rows[:target_index] + subject_rows[target_index + 1 :]
    for row, slot_template in zip(rewritten_subject_rows, slot_templates[: len(rewritten_subject_rows)]):
        _apply_bridge_slot_payload(row, slot_template)

    subject_row_ids = {id(row) for row in subject_rows}
    remaining_rows = [row for row in bridge_support["rows"] if id(row) not in subject_row_ids]
    bridge_support["rows"] = remaining_rows + rewritten_subject_rows
    _rewrite_bridge_sheet(ws, records, bridge_support)

    has_remaining_planned = any(
        _clean_text(row.get(COLUMN_LESSON_ID)) == lesson_id and _is_bridge_planned(row)
        for row in bridge_support["rows"]
    )
    done_value = not has_remaining_planned
    done_column = get_header_map(ws)[COLUMN_DONE]
    worksheet_name = _worksheet_title(ws)
    progress_updates = [
        _make_cell_update(
            done_column,
            record["_row"],
            done_value,
            worksheet_name=worksheet_name,
        )
        for record in records
        if _lesson_id_of(record) == lesson_id and _is_done(record) != done_value
    ]
    _batch_update_cells_with_option(ws, progress_updates, value_input_option="USER_ENTERED")

    return {
        "updated": 1,
        "rows": [bridge_row_number],
        "message": f"Pulled the next [{subject}] lesson forward.",
        "done_lesson": done_value,
    }


def swap_bridge_slots(ws, records, first_bridge_row, second_bridge_row, bridge_support=None):
    if bridge_support is None:
        bridge_support = _load_bridge_support(ws)
    if bridge_support is None:
        message = "Bridge sheet is required for slot swaps."
        return {"updated": 0, "rows": [], "message": message}

    first_bridge_row = _coerce_bridge_row_number(first_bridge_row, field_name="first bridge row")
    second_bridge_row = _coerce_bridge_row_number(second_bridge_row, field_name="second bridge row")
    if first_bridge_row == second_bridge_row:
        message = "Choose two different lesson slots to swap."
        return {"updated": 0, "rows": [first_bridge_row], "message": message}

    bridge_rows = {row.get("_row"): row for row in bridge_support["rows"]}
    first_row = bridge_rows.get(first_bridge_row)
    second_row = bridge_rows.get(second_bridge_row)
    if first_row is None or second_row is None or not _is_bridge_planned(first_row) or not _is_bridge_planned(second_row):
        message = "Only planned bridge slots can be swapped."
        return {"updated": 0, "rows": [], "message": message}

    first_payload = _bridge_slot_payload(first_row)
    second_payload = _bridge_slot_payload(second_row)
    _apply_bridge_slot_payload(first_row, second_payload)
    _apply_bridge_slot_payload(second_row, first_payload)
    _rewrite_bridge_sheet(ws, records, bridge_support)

    return {
        "updated": 2,
        "rows": [first_bridge_row, second_bridge_row],
        "message": "Swapped the two lesson slots.",
    }


def mark_done(ws, records, subject, target_date=None, record_key=None, bridge_row_number=None):
    subject = _clean_text(subject)
    target_date = _coerce_date(target_date, field_name="완료 날짜")
    bridge_support = _load_bridge_support(ws)
    if bridge_support is not None:
        bridge_result = _mark_done_via_bridge(
            ws,
            records,
            subject,
            target_date=target_date,
            record_key=record_key,
            bridge_row_number=bridge_row_number,
            bridge_support=bridge_support,
        )
        if bridge_result is not None:
            return bridge_result
        message = f"No planned bridge slot found for [{subject}]."
        print(f"  [warn] {message}")
        return {"updated": 0, "rows": [], "message": message}

    done_column = get_header_map(ws)[COLUMN_DONE]
    worksheet_name = _worksheet_title(ws)
    if target_date:
        candidates = [
            record
            for record in records
            if _subject_of(record) == subject
            and target_date in _scheduled_occurrence_dates(record)
            and not _is_done(record)
        ]
        candidates = sorted(candidates, key=_record_sort_key)
    else:
        next_class = get_next_class(records, subject)
        candidates = [next_class] if next_class else []

    if not candidates:
        message = f"No pending lesson found for [{subject}]."
        print(f"  [warn] {message}")
        return {"updated": 0, "rows": [], "message": message}

    updates = [
        _make_cell_update(done_column, record["_row"], True, worksheet_name=worksheet_name)
        for record in candidates
    ]
    _batch_update_cells_with_option(ws, updates, value_input_option="USER_ENTERED")

    return {
        "updated": len(candidates),
        "rows": [record["_row"] for record in candidates],
        "message": f"Marked {len(candidates)} lesson(s) done.",
    }


def push_schedule(ws, records, subject, days, from_date=None):
    subject = _clean_text(subject)
    days = _coerce_days(days)
    from_date = _coerce_date(from_date, field_name="기준 날짜")
    bridge_support = _load_bridge_support(ws)
    if bridge_support is not None:
        bridge_result = _push_schedule_via_bridge(
            ws,
            records,
            subject,
            days,
            from_date=from_date,
            bridge_support=bridge_support,
        )
        if bridge_result is not None:
            return bridge_result
        message = f"No planned bridge slot found for [{subject}]."
        print(f"  [warn] {message}")
        return {"updated": 0, "rows": [], "message": message}

    header_map = get_header_map(ws)
    date_column = header_map[COLUMN_DATE]
    note_column = header_map.get(COLUMN_NOTE)
    worksheet_name = _worksheet_title(ws)

    targets = []
    for record in _pending_lessons(records, subject):
        planned = _planned_date(record)
        if planned is None:
            continue
        if from_date and planned < from_date:
            continue
        targets.append(record)

    if not targets:
        message = f"No pending lesson found for [{subject}]."
        print(f"  [warn] {message}")
        return {"updated": 0, "rows": [], "message": message}

    updates = []
    for record in targets:
        delta = timedelta(days=days)
        new_date = _planned_date(record) + delta
        updates.append(
            _make_cell_update(
                date_column,
                record["_row"],
                _format_date(new_date),
                worksheet_name=worksheet_name,
            )
        )
        extension_dates = _extension_dates(record)
        if note_column and extension_dates:
            shifted_extension_dates = [extension_date + delta for extension_date in extension_dates]
            updates.append(
                _make_cell_update(
                    note_column,
                    record["_row"],
                    _build_note_with_extension_dates(record.get(COLUMN_NOTE, ""), shifted_extension_dates),
                    worksheet_name=worksheet_name,
                )
            )

    _batch_update_cells(ws, updates)
    return {
        "updated": len(targets),
        "rows": [record["_row"] for record in targets],
        "message": f"[{subject}] shifted {len(targets)} lesson(s) by {days} day(s).",
    }


def extend_lesson(ws, records, subject, row_number=None, extra_slots=1):
    subject = _clean_text(subject)
    bridge_support = _load_bridge_support(ws)
    if bridge_support is not None:
        bridge_result = _extend_lesson_via_bridge(
            ws,
            records,
            subject,
            row_number=row_number,
            extra_slots=extra_slots,
            bridge_support=bridge_support,
        )
        if bridge_result is not None:
            return bridge_result
        message = f"No planned bridge slot found to extend for [{subject}]."
        print(f"  [warn] {message}")
        return {"updated": 0, "rows": [], "message": message}

    header_map = get_header_map(ws)
    note_column = header_map.get(COLUMN_NOTE)
    if not note_column:
        message = "The note column is required to store extension dates."
        print(f"  [warn] {message}")
        return {"updated": 0, "rows": [], "message": message}

    extension_count_column = header_map.get(COLUMN_EXTENSION_COUNT)
    date_column = header_map[COLUMN_DATE]
    worksheet_name = _worksheet_title(ws)

    plan = plan_lesson_extension(
        records,
        subject,
        row_number=row_number,
        extra_slots=extra_slots,
    )
    if not plan:
        message = f"No pending lesson found to extend for [{subject}]."
        print(f"  [warn] {message}")
        return {"updated": 0, "rows": [], "message": message}

    target_record = plan["target_record"]
    added_extension_dates = plan["added_extension_dates"]
    record_updates = plan["record_updates"]

    updates = [
        _make_cell_update(
            note_column,
            target_record["_row"],
            _build_note_with_extension_dates(
                target_record.get(COLUMN_NOTE, ""),
                _extension_dates(target_record) + added_extension_dates,
            ),
            worksheet_name=worksheet_name,
        )
    ]
    if extension_count_column:
        updates.append(
            _make_cell_update(
                extension_count_column,
                target_record["_row"],
                str(_extension_count(target_record) + len(added_extension_dates)),
                worksheet_name=worksheet_name,
            )
        )

    for record_update in record_updates:
        record = record_update["record"]
        updates.append(
            _make_cell_update(
                date_column,
                record["_row"],
                _format_date(record_update["new_planned_date"]),
                worksheet_name=worksheet_name,
            )
        )
        updates.append(
            _make_cell_update(
                note_column,
                record["_row"],
                _build_note_with_extension_dates(
                    record.get(COLUMN_NOTE, ""),
                    record_update["new_extension_dates"],
                ),
                worksheet_name=worksheet_name,
            )
        )

    _batch_update_cells(ws, updates)
    return {
        "updated": 1 + len(record_updates),
        "rows": [target_record["_row"]] + [item["record"]["_row"] for item in record_updates],
        "message": f"[{subject}] extended one lesson and shifted {len(record_updates)} lesson(s).",
        "shifted": len(record_updates),
    }


def print_schedule(lessons, title):
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")
    if not lessons:
        print("  수업 없음 (또는 모두 완료)")
        return

    for record in lessons:
        print(f"  [{record.get(COLUMN_SUBJECT, '')}] {record.get(COLUMN_TITLE, '')}")
        print(
            f"    대단원: {record.get(COLUMN_UNIT, '')} | "
            f"차시: {record.get(COLUMN_LESSON, '')}"
        )
        extension_dates = _extension_dates(record)
        if extension_dates:
            print(
                "    연장일정: "
                + ", ".join(_format_date(extension_date) for extension_date in extension_dates)
            )
        if record.get(COLUMN_PDF):
            print(
                f"    PDF: {record.get(COLUMN_PDF)} "
                f"(p.{record.get(COLUMN_START_PAGE, '')}~{record.get(COLUMN_END_PAGE, '')})"
            )
        print()


def print_next_classes(records, subjects):
    print(f"\n{'=' * 50}")
    print("  과목별 다음 차시")
    print(f"{'=' * 50}")
    for subject in subjects:
        next_class = get_next_class(records, subject)
        if next_class:
            print(f"  [{subject}] {next_class.get(COLUMN_TITLE, '')}")
            print(
                f"    계획일: {next_class.get(COLUMN_DATE, '')} | "
                f"차시: {next_class.get(COLUMN_LESSON, '')}"
            )
        else:
            print(f"  [{subject}] 모든 진도 완료")
    print()


def print_progress(records, subjects):
    print(f"\n{'=' * 50}")
    print("  과목별 진도율")
    print(f"{'=' * 50}")
    for subject in subjects:
        progress = get_progress(records, subject)
        bar_len = 20
        filled = (
            int(bar_len * progress["완료"] / progress["전체"])
            if progress["전체"] > 0
            else 0
        )
        bar = "█" * filled + "░" * (bar_len - filled)
        print(
            f"  [{subject}] {bar} {progress['진도율']} "
            f"({progress['완료']}/{progress['전체']})"
        )
    print()


def print_remaining_week_schedule(records, start_date=None):
    start_date = _coerce_date(start_date, field_name="조회 날짜") or date.today()

    print(f"\n{'=' * 50}")
    print("  이번 주 남은 수업")
    print(f"{'=' * 50}")

    if start_date.weekday() > 4:
        print("  이번 주 수업은 모두 끝났습니다. (현재 주말)")
        return

    end_date = start_date + timedelta(days=4 - start_date.weekday())
    found_any = False
    for offset in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=offset)
        lessons = get_schedule_by_date(records, day)
        if lessons:
            print_schedule(lessons, f"이번 주 남은 수업 ({day.strftime('%Y-%m-%d, %a')})")
            found_any = True

    if not found_any:
        print("  이번 주에 남은 미완료 수업이 없습니다.")


def select_subject(subjects):
    print("\n  과목 선택:")
    for i, subject in enumerate(subjects, start=1):
        print(f"    {i}. {subject}")
    print("    0. 뒤로가기")

    while True:
        choice = input("  입력 (번호 또는 이름): ").strip()
        if choice in {"0", ""} or choice.lower() == "back":
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(subjects):
                return subjects[idx - 1]
        elif choice in subjects:
            return choice
        print("  [경고] 잘못된 입력입니다. 다시 선택해주세요.")


def select_lesson(records, subject, *, action_label):
    pending = _scheduled_lessons(records, subject, include_done=False)
    if not pending:
        print(f"  [경고] {subject} 과목에 계획일이 있는 미완료 수업이 없습니다.")
        return None

    print(f"\n  [{subject}] {action_label}할 차시 선택:")
    for i, record in enumerate(pending, start=1):
        print(
            f"    {i}. {_lesson_label(record)} | {_planned_date_label(record)} | "
            f"{record.get(COLUMN_TITLE, '')}"
        )
    print("    0. 뒤로가기")

    while True:
        choice = input("  선택: ").strip()
        if choice in {"0", ""} or choice.lower() == "back":
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(pending):
                return pending[idx - 1]
        print("  [경고] 잘못된 입력입니다. 다시 선택해주세요.")


def menu(ws, records, subjects):
    while True:
        today = date.today()
        tomorrow = today + timedelta(days=1)

        print(f"\n{'=' * 50}")
        print(f"  수업 진도 관리  |  {today.strftime('%Y-%m-%d (%a)')}")
        print(f"{'=' * 50}")
        print("  1. 오늘 수업 확인")
        print("  2. 내일 수업 확인")
        print("  3. 이번 주 남은 수업 확인")
        print("  4. 다음 주 수업 확인")
        print("  5. 과목별 다음 차시")
        print("  6. 과목별 진도율")
        print("  7. 수업 완료 처리")
        print("  8. 차시 연장")
        print("  9. 날짜 밀기")
        print(" 10. 데이터 새로고침")
        print("  0. 종료")
        print(f"{'=' * 50}")

        choice = input("  선택: ").strip()

        if choice == "1":
            lessons = get_schedule_by_date(records, today)
            print_schedule(lessons, f"오늘 수업 ({today})")

        elif choice == "2":
            lessons = get_schedule_by_date(records, tomorrow)
            print_schedule(lessons, f"내일 수업 ({tomorrow})")

        elif choice == "3":
            print_remaining_week_schedule(records, today)

        elif choice == "4":
            next_monday = today + timedelta(days=(7 - today.weekday()))
            found_any = False
            for offset in range(5):
                day = next_monday + timedelta(days=offset)
                lessons = get_schedule_by_date(records, day)
                if lessons:
                    print_schedule(lessons, f"다음 주 수업 ({day.strftime('%Y-%m-%d, %a')})")
                    found_any = True
            if not found_any:
                print("\n  [경고] 다음 주에 계획된 미완료 수업이 없습니다.")

        elif choice == "5":
            print_next_classes(records, subjects)

        elif choice == "6":
            print_progress(records, subjects)

        elif choice == "7":
            subject = select_subject(subjects)
            if not subject:
                continue

            done_list = [
                record
                for record in records
                if _subject_of(record) == subject and _is_done(record)
            ]
            pending_list = _pending_lessons(records, subject)

            print(f"\n  [{subject}] 시트 현황 요약")
            if done_list:
                last = sorted(done_list, key=_record_sort_key)[-1]
                print(
                    f"  직전 완료: {last.get(COLUMN_LESSON, '')}차시 - "
                    f"{last.get(COLUMN_TITLE, '')} ({last.get(COLUMN_DATE, '')})"
                )
            if pending_list:
                current = pending_list[0]
                print(
                    f"  현재 대상: {current.get(COLUMN_LESSON, '')}차시 - "
                    f"{current.get(COLUMN_TITLE, '')} ({current.get(COLUMN_DATE, '')})"
                )
                if len(pending_list) > 1:
                    next_item = pending_list[1]
                    print(
                        f"  다음 예정: {next_item.get(COLUMN_LESSON, '')}차시 - "
                        f"{next_item.get(COLUMN_TITLE, '')} ({next_item.get(COLUMN_DATE, '')})"
                    )

            date_input = input(
                "\n  완료할 날짜 (Enter=현재 대상 처리, YYYY-MM-DD=특정날짜): "
            ).strip()
            try:
                target = _coerce_date(date_input, field_name="완료 날짜") if date_input else None
            except ValueError as exc:
                print(f"  [경고] {exc}")
                continue

            mark_done(ws, records, subject, target)
            records, subjects = _refresh_records(ws)

        elif choice == "8":
            subject = select_subject(subjects)
            if not subject:
                continue

            target_record = select_lesson(records, subject, action_label="연장")
            if not target_record:
                continue

            extra_slots_input = input("  몇 차시 연장할까요? (Enter=1): ").strip()
            try:
                extra_slots = _coerce_days(extra_slots_input or "1")
                if extra_slots < 1:
                    raise ValueError("연장할 차시 수는 1 이상이어야 합니다.")
            except ValueError as exc:
                print(f"  [경고] {exc}")
                continue

            extension_plan = plan_lesson_extension(
                records,
                subject,
                row_number=target_record["_row"],
                extra_slots=extra_slots,
            )
            if not extension_plan:
                print("  [경고] 연장 계획을 만들지 못했습니다.")
                continue

            print(f"\n  선택한 차시: {_lesson_label(target_record)}")
            print(f"  계획일: {_planned_date_label(target_record)}")
            print(f"  수업내용: {target_record.get(COLUMN_TITLE, '')}")
            print(
                "  추가 연장일: "
                + ", ".join(_format_date(extension_date) for extension_date in extension_plan["added_extension_dates"])
            )
            if extension_plan["record_updates"]:
                print("  뒤로 밀리는 차시:")
                for item in extension_plan["record_updates"][:5]:
                    record = item["record"]
                    print(
                        f"    - {_lesson_label(record)} | "
                        f"{record.get(COLUMN_TITLE, '')} -> {_format_date(item['new_planned_date'])}"
                    )
                remaining = len(extension_plan["record_updates"]) - 5
                if remaining > 0:
                    print(f"    - 그 외 {remaining}개 차시")
            else:
                print("  뒤로 밀리는 차시는 없습니다.")

            confirm = input("  이 계획대로 차시를 연장할까요? (y/N): ").strip().lower()
            if confirm not in {"y", "yes"}:
                print("  연장을 취소했습니다.")
                continue

            extend_lesson(
                ws,
                records,
                subject,
                row_number=target_record["_row"],
                extra_slots=extra_slots,
            )
            records, subjects = _refresh_records(ws)

        elif choice == "9":
            subject = select_subject(subjects)
            if not subject:
                continue

            print("\n  1. 미완료 수업 전체 밀기")
            print("  2. 특정 날짜 이후 수업만 밀기")
            option = input("  선택 (번호, Enter=1): ").strip()

            days_input = input("  밀어낼 일수 (예: 1 또는 7): ").strip()
            try:
                days = _coerce_days(days_input)
            except ValueError as exc:
                print(f"  [경고] {exc}")
                continue

            from_date = None
            if option == "2":
                date_text = input("  기준 날짜 (YYYY-MM-DD): ").strip()
                try:
                    from_date = _coerce_date(date_text, field_name="기준 날짜") if date_text else None
                except ValueError as exc:
                    print(f"  [경고] {exc}")
                    continue

            push_schedule(ws, records, subject, days, from_date)
            records, subjects = _refresh_records(ws)

        elif choice == "10":
            print("  데이터 새로고침 중...")
            records, subjects = _refresh_records(ws)
            print(f"  완료. 과목: {', '.join(subjects)}")

        elif choice == "0":
            print("\n  종료합니다.\n")
            break

        else:
            print("  [경고] 잘못된 선택입니다.")


def cli_mode():
    """터미널에서 직접 명령어로 실행하는 모드"""
    ws = connect()
    records = load_all(ws)
    subjects = get_subjects(records)
    today = date.today()
    tomorrow = today + timedelta(days=1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else None

    if cmd in {"lesson-ids", "ensure-lesson-ids"}:
        result = ensure_lesson_ids(ws)
        print(f"  {result['message']}")
        for item in result["assigned"][:10]:
            print(
                f"    - {_row_label(item['row'])}: {item['lesson_id']} | "
                f"{item['title']}"
            )
        remaining = len(result["assigned"]) - 10
        if remaining > 0:
            print(f"    - 그 외 {remaining}개 행")
    elif cmd == "today":
        lessons = get_schedule_by_date(records, today)
        print_schedule(lessons, f"오늘 수업 ({today})")
    elif cmd == "tomorrow":
        lessons = get_schedule_by_date(records, tomorrow)
        print_schedule(lessons, f"내일 수업 ({tomorrow})")
    elif cmd == "thisweek":
        print_remaining_week_schedule(records, today)
    elif cmd == "nextweek":
        next_monday = today + timedelta(days=(7 - today.weekday()))
        for offset in range(5):
            day = next_monday + timedelta(days=offset)
            lessons = get_schedule_by_date(records, day)
            if lessons:
                print_schedule(lessons, f"다음 주 수업 ({day.strftime('%Y-%m-%d, %a')})")
    elif cmd == "next":
        print_next_classes(records, subjects)
    elif cmd == "progress":
        print_progress(records, subjects)
    elif cmd == "done" and len(sys.argv) > 2:
        subject = sys.argv[2]
        date_arg = sys.argv[3] if len(sys.argv) > 3 else None
        mark_done(ws, records, subject, date_arg)
    elif cmd == "push" and len(sys.argv) > 3:
        subject = sys.argv[2]
        days = sys.argv[3]
        from_arg = sys.argv[4] if len(sys.argv) > 4 else None
        push_schedule(ws, records, subject, days, from_arg)
    else:
        menu(ws, records, subjects)


def print_schedule(lessons, title):
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")
    if not lessons:
        print("  수업 없음 (또는 모두 완료)")
        return

    for record in lessons:
        subject = _clean_text(record.get(COLUMN_SUBJECT))
        title_text = _clean_text(record.get(COLUMN_TITLE))
        unit = _clean_text(record.get(COLUMN_UNIT))
        lesson = _clean_text(record.get(COLUMN_LESSON))
        planned_date = _clean_text(record.get(COLUMN_DATE) or record.get("slot_date"))
        planned_period = _clean_text(record.get("slot_period"))

        print(f"  [{subject}] {title_text}")
        print(f"    대단원: {unit} | 차시: {lesson}")
        if planned_date or planned_period:
            if planned_period:
                print(f"    배치: {planned_date} | {planned_period}교시")
            else:
                print(f"    배치: {planned_date}")

        extension_dates = _extension_dates(record)
        if extension_dates:
            print("    연장일정: " + ", ".join(_format_date(d) for d in extension_dates))
        if record.get(COLUMN_PDF):
            print(
                f"    PDF: {record.get(COLUMN_PDF)} "
                f"(p.{record.get(COLUMN_START_PAGE, '')}~{record.get(COLUMN_END_PAGE, '')})"
            )
        print()


def print_next_classes(records, subjects, bridge_rows=None):
    print(f"\n{'=' * 50}")
    print("  과목별 다음 차시")
    print(f"{'=' * 50}")
    for subject in subjects:
        next_class = get_next_class(records, subject, bridge_rows=bridge_rows)
        if next_class:
            print(f"  [{subject}] {next_class.get(COLUMN_TITLE, '')}")
            print(
                f"    계획일: {next_class.get(COLUMN_DATE, '')} | "
                f"차시: {next_class.get(COLUMN_LESSON, '')}"
            )
            planned_period = _clean_text(next_class.get("slot_period"))
            if planned_period:
                print(f"    계획교시: {planned_period}")
        else:
            print(f"  [{subject}] 모든 진도 완료")
    print()


def print_progress(records, subjects):
    print(f"\n{'=' * 50}")
    print("  과목별 진도율")
    print(f"{'=' * 50}")
    for subject in subjects:
        progress = get_progress(records, subject)
        total = int(progress.get("?꾩껜", 0))
        done = int(progress.get("?꾨즺", 0))
        percentage_text = progress.get("吏꾨룄??", "0.0%")
        filled = int(20 * done / total) if total > 0 else 0
        bar = "#" * filled + "." * (20 - filled)
        print(f"  [{subject}] {bar} {percentage_text} ({done}/{total})")
    print()


def print_remaining_week_schedule(records, start_date=None, bridge_rows=None):
    start_date = _coerce_date(start_date, field_name="조회 날짜") or date.today()

    print(f"\n{'=' * 50}")
    print("  이번 주 남은 수업")
    print(f"{'=' * 50}")

    if start_date.weekday() > 4:
        print("  이번 주 수업은 모두 지난 상태입니다. (현재 주말)")
        return

    end_date = start_date + timedelta(days=4 - start_date.weekday())
    found_any = False
    for offset in range((end_date - start_date).days + 1):
        day = start_date + timedelta(days=offset)
        lessons = get_schedule_by_date(records, day, bridge_rows=bridge_rows)
        if lessons:
            print_schedule(lessons, f"이번 주 남은 수업 ({day.strftime('%Y-%m-%d, %a')})")
            found_any = True

    if not found_any:
        print("  이번 주에 남은 미완료 수업이 없습니다.")


def menu(ws, records, subjects, bridge_rows=None):
    while True:
        today = date.today()
        tomorrow = today + timedelta(days=1)

        print(f"\n{'=' * 50}")
        print(f"  수업 진도 관리  |  {today.strftime('%Y-%m-%d (%a)')}")
        print(f"{'=' * 50}")
        print("  1. 오늘 수업 확인")
        print("  2. 내일 수업 확인")
        print("  3. 이번 주 남은 수업 확인")
        print("  4. 다음 주 수업 확인")
        print("  5. 과목별 다음 차시")
        print("  6. 과목별 진도율")
        print("  7. 수업 완료 처리")
        print("  8. 차시 연장")
        print("  9. 날짜 밀기")
        print(" 10. 데이터 새로고침")
        print("  0. 종료")
        print(f"{'=' * 50}")

        choice = input("  선택: ").strip()

        if choice == "1":
            lessons = get_schedule_by_date(records, today, bridge_rows=bridge_rows)
            print_schedule(lessons, f"오늘 수업 ({today})")

        elif choice == "2":
            lessons = get_schedule_by_date(records, tomorrow, bridge_rows=bridge_rows)
            print_schedule(lessons, f"내일 수업 ({tomorrow})")

        elif choice == "3":
            print_remaining_week_schedule(records, today, bridge_rows=bridge_rows)

        elif choice == "4":
            next_monday = today + timedelta(days=(7 - today.weekday()))
            found_any = False
            for offset in range(5):
                day = next_monday + timedelta(days=offset)
                lessons = get_schedule_by_date(records, day, bridge_rows=bridge_rows)
                if lessons:
                    print_schedule(lessons, f"다음 주 수업 ({day.strftime('%Y-%m-%d, %a')})")
                    found_any = True
            if not found_any:
                print("\n  [경고] 다음 주에 계획된 미완료 수업이 없습니다.")

        elif choice == "5":
            print_next_classes(records, subjects, bridge_rows=bridge_rows)

        elif choice == "6":
            print_progress(records, subjects)

        elif choice == "7":
            subject = select_subject(subjects)
            if not subject:
                continue

            done_list = [record for record in records if _subject_of(record) == subject and _is_done(record)]
            next_item = get_next_class(records, subject, bridge_rows=bridge_rows)

            print(f"\n  [{subject}] 현재 상태 요약")
            if done_list:
                last = sorted(done_list, key=_record_sort_key)[-1]
                print(
                    f"  직전 완료: {last.get(COLUMN_LESSON, '')}차시 - "
                    f"{last.get(COLUMN_TITLE, '')} ({last.get(COLUMN_DATE, '')})"
                )
            if next_item:
                print(
                    f"  현재 대상: {next_item.get(COLUMN_LESSON, '')}차시 - "
                    f"{next_item.get(COLUMN_TITLE, '')} ({next_item.get(COLUMN_DATE, '')})"
                )
                planned_period = _clean_text(next_item.get('slot_period'))
                if planned_period:
                    print(f"  계획교시: {planned_period}")

            date_input = input(
                "\n  완료할 날짜 (Enter=현재 대상 처리, YYYY-MM-DD=특정 날짜): "
            ).strip()
            try:
                target = _coerce_date(date_input, field_name="완료 날짜") if date_input else None
            except ValueError as exc:
                print(f"  [경고] {exc}")
                continue

            mark_done(ws, records, subject, target)
            records, subjects, bridge_rows = _refresh_records(ws)

        elif choice == "8":
            subject = select_subject(subjects)
            if not subject:
                continue

            target_record = select_lesson(records, subject, action_label="연장")
            if not target_record:
                continue

            extra_slots_input = input("  몇 차시 연장할까요? (Enter=1): ").strip()
            try:
                extra_slots = _coerce_days(extra_slots_input or "1")
                if extra_slots < 1:
                    raise ValueError("연장할 차시는 1 이상이어야 합니다.")
            except ValueError as exc:
                print(f"  [경고] {exc}")
                continue

            extension_plan = plan_lesson_extension(
                records,
                subject,
                row_number=target_record["_row"],
                extra_slots=extra_slots,
            )
            if not extension_plan:
                print("  [경고] 연장 계획을 만들지 못했습니다.")
                continue

            print(f"\n  선택한 차시: {_lesson_label(target_record)}")
            print(f"  계획일: {_planned_date_label(target_record)}")
            print(f"  수업내용: {target_record.get(COLUMN_TITLE, '')}")
            print(
                "  추가 연장일: "
                + ", ".join(_format_date(extension_date) for extension_date in extension_plan["added_extension_dates"])
            )

            confirm = input("  이 계획대로 차시를 연장할까요? (y/N): ").strip().lower()
            if confirm not in {"y", "yes"}:
                print("  연장을 취소했습니다.")
                continue

            extend_lesson(
                ws,
                records,
                subject,
                row_number=target_record["_row"],
                extra_slots=extra_slots,
            )
            records, subjects, bridge_rows = _refresh_records(ws)

        elif choice == "9":
            subject = select_subject(subjects)
            if not subject:
                continue

            print("\n  1. 미완료 수업 전체 밀기")
            print("  2. 특정 날짜 이후 수업만 밀기")
            option = input("  선택 (번호, Enter=1): ").strip()

            days_input = input("  밀어낼 일수 (예: 1 또는 7): ").strip()
            try:
                days = _coerce_days(days_input)
            except ValueError as exc:
                print(f"  [경고] {exc}")
                continue

            from_date = None
            if option == "2":
                date_text = input("  기준 날짜 (YYYY-MM-DD): ").strip()
                try:
                    from_date = _coerce_date(date_text, field_name="기준 날짜") if date_text else None
                except ValueError as exc:
                    print(f"  [경고] {exc}")
                    continue

            push_schedule(ws, records, subject, days, from_date)
            records, subjects, bridge_rows = _refresh_records(ws)

        elif choice == "10":
            print("  데이터를 새로고침하는 중입니다...")
            records, subjects, bridge_rows = _refresh_records(ws)
            print(f"  완료. 과목: {', '.join(subjects)}")

        elif choice == "0":
            print("\n  종료합니다.\n")
            break

        else:
            print("  [경고] 잘못된 선택입니다.")


def cli_mode():
    ws = connect()
    records, subjects, bridge_rows = _refresh_records(ws)
    today = date.today()
    tomorrow = today + timedelta(days=1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else None

    if cmd in {"lesson-ids", "ensure-lesson-ids"}:
        result = ensure_lesson_ids(ws)
        print(f"  {result['message']}")
        for item in result["assigned"][:10]:
            print(f"    - {_row_label(item['row'])}: {item['lesson_id']} | {item['title']}")
    elif cmd == "today":
        lessons = get_schedule_by_date(records, today, bridge_rows=bridge_rows)
        print_schedule(lessons, f"오늘 수업 ({today})")
    elif cmd == "tomorrow":
        lessons = get_schedule_by_date(records, tomorrow, bridge_rows=bridge_rows)
        print_schedule(lessons, f"내일 수업 ({tomorrow})")
    elif cmd == "thisweek":
        print_remaining_week_schedule(records, today, bridge_rows=bridge_rows)
    elif cmd == "nextweek":
        next_monday = today + timedelta(days=(7 - today.weekday()))
        for offset in range(5):
            day = next_monday + timedelta(days=offset)
            lessons = get_schedule_by_date(records, day, bridge_rows=bridge_rows)
            if lessons:
                print_schedule(lessons, f"다음 주 수업 ({day.strftime('%Y-%m-%d, %a')})")
    elif cmd == "next":
        print_next_classes(records, subjects, bridge_rows=bridge_rows)
    elif cmd == "progress":
        print_progress(records, subjects)
    elif cmd == "done" and len(sys.argv) > 2:
        subject = sys.argv[2]
        date_arg = sys.argv[3] if len(sys.argv) > 3 else None
        mark_done(ws, records, subject, date_arg)
    elif cmd == "push" and len(sys.argv) > 3:
        subject = sys.argv[2]
        days = sys.argv[3]
        from_arg = sys.argv[4] if len(sys.argv) > 4 else None
        push_schedule(ws, records, subject, days, from_arg)
    else:
        menu(ws, records, subjects, bridge_rows)


def main():
    try:
        cli_mode()
    except (ScheduleError, ValueError, json.JSONDecodeError) as exc:
        print(f"\n[오류] {exc}\n")
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        print("\n\n종료합니다.\n")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
