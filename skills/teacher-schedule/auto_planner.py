import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta

import schedule

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False


load_dotenv()

SHEET_ID = os.getenv("SHEET_ID")
CREDS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
PREFERRED_PROGRESS_SHEET_NAME = os.getenv("SHEET_PROGRESS")
LEGACY_PROGRESS_SHEET_NAME = os.getenv("SHEET_NAME", "?쒗듃1")
PROGRESS_SHEET_NAME = PREFERRED_PROGRESS_SHEET_NAME or LEGACY_PROGRESS_SHEET_NAME
TIMETABLE_SHEET_NAME = os.getenv("SHEET_TIMETABLE") or os.getenv("TIMETABLE_SHEET", "기초시간표")
HOLIDAY_SHEET_NAME = os.getenv("SHEET_HOLIDAY") or os.getenv("HOLIDAY_SHEET", "휴업일")
SUBJECT_START_SHEET_NAME = os.getenv("SHEET_SUBJECT_START") or os.getenv("SUBJECT_START_SHEET", "수업시작일")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TRUE_VALUES = {"TRUE", "1", "Y", "YES", "DONE"}
DONE_COLUMN_FALLBACK_INDEX = 6
PLANNER_MODES = {
    "initial": "珥덇린 ?꾩껜 諛곗젙",
    "fill-blanks": "鍮덉뭏 蹂닿컯 諛곗젙",
}


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_done_value(value):
    return _clean_text(value).lstrip("'").strip().upper()


def _sheet_name_candidates(*names):
    candidates = []
    seen = set()
    for name in names:
        normalized = _clean_text(name)
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)
    return candidates


def _extract_number(value, default=0):
    text = _clean_text(value)
    match = re.search(r"\d+", text)
    if not match:
        return default
    return int(match.group())


def _is_done(value):
    return _normalize_done_value(value) in TRUE_VALUES


def _has_planned_date(record):
    return parse_date(record.get(schedule.COLUMN_DATE)) is not None


def _has_ordered_unit(record):
    return re.match(r"^\s*\d+", _clean_text(record.get(schedule.COLUMN_UNIT, ""))) is not None


def get_client():
    if not SHEET_ID:
        raise ValueError("?섍꼍 蹂??SHEET_ID媛 ?ㅼ젙?섏뼱 ?덉? ?딆뒿?덈떎. (.env ?뚯씪???뺤씤?섏꽭??")

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise ValueError(
            "Google Sheets ?곕룞 ?쇱씠釉뚮윭由ш? ?놁뒿?덈떎. `pip install -r requirements.txt`瑜?癒쇱? ?ㅽ뻾?섏꽭??"
        ) from exc

    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_json = creds_json.replace("\\n", "\n")
        creds_dict = json.loads(creds_json, strict=False)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)

    return gspread.authorize(creds)


def parse_date(date_str):
    if not date_str:
        return None

    if isinstance(date_str, datetime):
        return date_str.date()
    if isinstance(date_str, date):
        return date_str

    text = _clean_text(date_str)
    normalized = re.sub(r"\s*\.\s*", "-", text).rstrip("-")
    current_year = date.today().year

    month_day_match = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})", normalized)
    if month_day_match:
        month = int(month_day_match.group(1))
        day = int(month_day_match.group(2))
        try:
            return date(current_year, month, day)
        except ValueError:
            return None

    for candidate in (normalized, text):
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                pass
    return None


def resolve_progress_worksheet(sh):
    candidates = _sheet_name_candidates(PREFERRED_PROGRESS_SHEET_NAME, LEGACY_PROGRESS_SHEET_NAME) or ["?쒗듃1"]
    format_errors = []
    last_error = None
    for candidate in candidates:
        try:
            worksheet = sh.worksheet(candidate)
        except Exception as exc:
            if exc.__class__.__name__ != "WorksheetNotFound":
                raise
            last_error = exc
            continue

        headers = {_clean_text(header) for header in worksheet.row_values(1)}
        required = {schedule.COLUMN_SUBJECT, schedule.COLUMN_DATE}
        if required.issubset(headers):
            return worksheet
        format_errors.append(f"{candidate}: ?꾨씫 ?ㅻ뜑 {', '.join(sorted(required - headers))}")

    if format_errors:
        raise ValueError(
            "吏꾨룄???꾨낫 ?쒗듃瑜?李얠븯吏留??뺤떇??留욎? ?딆뒿?덈떎. "
            + " | ".join(format_errors)
        )

    attempted = ", ".join(candidates)
    raise ValueError(f"吏꾨룄???쒗듃瑜?李얠쓣 ???놁뒿?덈떎. ?뺤씤???대쫫: {attempted}") from last_error


def fetch_holidays(sh):
    try:
        ws = sh.worksheet(HOLIDAY_SHEET_NAME)
        records = ws.get_all_records(default_blank="")
    except Exception as exc:
        if exc.__class__.__name__ == "WorksheetNotFound":
            print(f"  [?덈궡] '{HOLIDAY_SHEET_NAME}' ?쒗듃瑜?李얠쓣 ???놁뼱 ?됱씪(??湲???紐⑤몢 ?섏뾽?쇰줈 媛꾩＜?⑸땲??")
            return set()
        raise

    holidays = set()
    for record in records:
        values = list(record.values())
        date_value = record.get("?좎쭨") if "?좎쭨" in record else (values[0] if values else "")
        parsed = parse_date(date_value)
        if parsed:
            holidays.add(parsed)
    return holidays


def fetch_timetable(sh):
    ws = sh.worksheet(TIMETABLE_SHEET_NAME)
    rows = ws.get_all_values()
    if not rows or len(rows) < 2:
        raise ValueError("湲곗큹?쒓컙???쒗듃???곗씠?곌? 議댁옱?섏? ?딆뒿?덈떎.")

    headers = [_clean_text(value).replace("?붿씪", "") for value in rows[0]]
    valid_days = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4}
    day_indices = {}

    for col_idx, header in enumerate(headers):
        for day_name, weekday in valid_days.items():
            if day_name in header:
                day_indices[weekday] = col_idx
                break

    if not day_indices:
        raise ValueError(f"湲곗큹?쒓컙??泥?踰덉㎏ ??{headers})?먯꽌 ?붿씪(??湲? ?띿뒪?몃? 李얠쓣 ???놁뒿?덈떎.")

    timetable = {day: [] for day in range(5)}
    for row in rows[1:]:
        for weekday, col_idx in day_indices.items():
            if col_idx < len(row):
                subject = _clean_text(row[col_idx])
                if subject:
                    timetable[weekday].append(subject)

    print("  [湲곗큹?쒓컙???뚯떛 ?꾨즺]")
    for weekday, subjects in sorted(timetable.items()):
        label = ["월", "화", "수", "목", "금"][weekday]
        print(f"    {label}: {', '.join(subjects)}")

    return timetable


def get_school_days(start_date, end_date, holidays):
    days = []
    current_day = start_date
    while current_day <= end_date:
        if current_day.weekday() < 5 and current_day not in holidays:
            days.append(current_day)
        current_day += timedelta(days=1)
    return days


def _lesson_sort_key(item):
    return (
        item.get("_unit_order", _extract_number(item.get(schedule.COLUMN_UNIT))),
        item.get("_lesson_order", _extract_number(item.get(schedule.COLUMN_LESSON))),
        item["_row"],
    )


def should_include_record(record, planner_mode):
    if not _has_ordered_unit(record):
        return False
    if planner_mode == "initial":
        return True
    if planner_mode == "fill-blanks":
        return not _is_done(record.get(schedule.COLUMN_DONE, "")) and not _has_planned_date(record)
    raise ValueError(f"吏?먰븯吏 ?딅뒗 諛곗젙 紐⑤뱶?낅땲?? {planner_mode}")


def build_subject_queues(records, planner_mode="fill-blanks"):
    subject_queues = {}
    for row_number, record in enumerate(records, start=2):
        subject = _clean_text(record.get(schedule.COLUMN_SUBJECT))
        if not subject:
            continue

        enriched = dict(record)
        enriched["_row"] = row_number
        subject_queues.setdefault(subject, [])
        if should_include_record(record, planner_mode):
            subject_queues[subject].append(enriched)

    for subject, queue in subject_queues.items():
        last_unit_order = 0
        for item in sorted(queue, key=lambda row: row["_row"]):
            unit_order = _extract_number(item.get(schedule.COLUMN_UNIT), default=None)
            if unit_order is None:
                unit_order = last_unit_order
            else:
                last_unit_order = unit_order

            item["_unit_order"] = unit_order
            item["_lesson_order"] = _extract_number(item.get(schedule.COLUMN_LESSON), default=item["_row"])

        subject_queues[subject] = sorted(queue, key=_lesson_sort_key)

    return {subject: queue for subject, queue in subject_queues.items() if queue}


def _find_matching_key(records, candidates):
    if not records:
        return None

    lowered = {key.lower(): key for key in records[0].keys()}
    for candidate in candidates:
        found = lowered.get(candidate.lower())
        if found:
            return found
    return None


def apply_done_column_fallback(headers, rows, records):
    if any(_clean_text(header) == schedule.COLUMN_DONE for header in headers):
        return records
    if len(headers) < DONE_COLUMN_FALLBACK_INDEX:
        return records

    for index, record in enumerate(records):
        row = rows[index + 1] if index + 1 < len(rows) else []
        record[schedule.COLUMN_DONE] = row[DONE_COLUMN_FALLBACK_INDEX - 1] if len(row) >= DONE_COLUMN_FALLBACK_INDEX else ""
    return records


def parse_subject_start_sheet(records):
    subject_key = _find_matching_key(records, [schedule.COLUMN_SUBJECT, "subject"])
    start_key = _find_matching_key(records, ["수업시작일", "시작일", "start_date"])
    if not subject_key or not start_key:
        return {}

    mapping = {}
    for record in records:
        subject = _clean_text(record.get(subject_key))
        start_date = parse_date(record.get(start_key))
        if subject and start_date:
            mapping[subject] = start_date
    return mapping


def resolve_subject_start_dates(target_subjects, sheet_mapping, semester_start_date, input_fn=input):
    resolved = {}
    for subject in target_subjects:
        if subject in sheet_mapping:
            resolved[subject] = sheet_mapping[subject]
            continue

        answer = input_fn(
            f"  [{subject}] ?섏뾽?쒖옉?쇱쓣 ?낅젰?섏꽭??(Enter={semester_start_date}): "
        ).strip()
        parsed = parse_date(answer)
        if answer and not parsed:
            print(f"  [寃쎄퀬] '{subject}' ?섏뾽?쒖옉???뺤떇???섎せ?섏뼱 ?숆린 ?쒖옉??{semester_start_date})濡?泥섎━?⑸땲??")
        resolved[subject] = parsed or semester_start_date

    return resolved


def fetch_subject_start_dates(sh, target_subjects, semester_start_date, input_fn=input):
    sheet_mapping = {}
    try:
        ws = sh.worksheet(SUBJECT_START_SHEET_NAME)
        records = ws.get_all_records(default_blank="")
        sheet_mapping = parse_subject_start_sheet(records)
        if sheet_mapping:
            print(f"  [?섏뾽?쒖옉???쒗듃 ?뚯떛 ?꾨즺] {', '.join(sorted(sheet_mapping))}")
        else:
            print(f"  [?덈궡] '{SUBJECT_START_SHEET_NAME}' ?쒗듃?먯꽌 怨쇰ぉ/?섏뾽?쒖옉???뺤떇??李얠? 紐삵뻽?듬땲??")
    except Exception as exc:
        if exc.__class__.__name__ == "WorksheetNotFound":
            print(f"  [?덈궡] '{SUBJECT_START_SHEET_NAME}' ?쒗듃媛 ?놁뼱 怨쇰ぉ蹂??쒖옉?쇱쓣 吏곸젒 ?뺤씤?⑸땲??")
        else:
            raise

    return resolve_subject_start_dates(
        target_subjects,
        sheet_mapping,
        semester_start_date,
        input_fn=input_fn,
    )


def select_target_subjects(subject_queues, input_fn=input):
    print(f"\n  [?덈궡] 誘몄닔??李⑥떆媛 ?⑥븘?덈뒗 怨쇰ぉ: {', '.join(subject_queues.keys())}")
    print("  ?대뒓 怨쇰ぉ???대쾲 ?쇱젙 諛곗젙???곸슜?섏떆寃좎뒿?덇퉴?")
    print("    1. 紐⑤뱺 怨쇰ぉ ??踰덉뿉 諛곗젙 (洹몃깷 ?뷀꽣 ?낅젰)")
    print("    2. ?뱀젙 怨쇰ぉ留??좏깮")

    choice = input_fn("  ?낅젰 (踰덊샇 ?먮뒗 怨쇰ぉ紐??쇳몴 援щ텇): ").strip()
    target_subjects = list(subject_queues.keys())

    if choice and choice != "1":
        if choice == "2":
            choice = input_fn("  諛곗젙??怨쇰ぉ紐낆쓣 ?낅젰?섏꽭??(?? 援?뼱, ?꾨뜒): ").strip()

        if choice:
            entered = [_clean_text(value) for value in choice.split(",") if _clean_text(value)]
            valid = [subject for subject in entered if subject in subject_queues]
            if not valid:
                print("  [寃쎄퀬] ?낅젰?섏떊 怨쇰ぉ??誘몄닔??紐⑸줉???녾굅???섎せ ?낅젰?섏뿀?듬땲?? ?묒뾽??痍⑥냼?⑸땲??")
                return []
            target_subjects = valid

    print(f"\n  [吏꾪뻾] ?ㅼ쓬 怨쇰ぉ????댁꽌留??쇱젙??諛곗젙?⑸땲?? {', '.join(target_subjects)}")
    return target_subjects


def choose_planner_mode(input_fn=input):
    print("\n  諛곗젙 紐⑤뱶瑜??좏깮?섏꽭??")
    print("    1. 珥덇린 ?꾩껜 諛곗젙: 怨꾪쉷?쇱쓣 泥섏쓬遺???ㅼ떆 ?ｌ뒿?덈떎. F???ㅽ뻾?щ?)怨?湲곗〈 怨꾪쉷?쇱쓣 臾댁떆?⑸땲??")
    print("    2. 鍮덉뭏 蹂닿컯 諛곗젙: F?댁씠 FALSE 怨꾩뿴?닿퀬 怨꾪쉷?쇱씠 鍮덉뭏???됰쭔 梨꾩썎?덈떎. (Enter=2)")

    choice = _clean_text(input_fn("  ?좏깮: "))
    if choice in {"", "2", "fill", "fill-blanks", "blank"}:
        return "fill-blanks"
    if choice in {"1", "initial", "all"}:
        return "initial"
    print("  [寃쎄퀬] ?????녿뒗 ?낅젰?대씪 ?덉쟾?섍쾶 '鍮덉뭏 蹂닿컯 諛곗젙'?쇰줈 吏꾪뻾?⑸땲??")
    return "fill-blanks"


def plan_lesson_assignments(subject_queues, school_days, timetable, target_subjects, subject_start_dates):
    remaining = {subject: list(queue) for subject, queue in subject_queues.items()}
    assignments = []

    for current_day in school_days:
        day_subjects = timetable.get(current_day.weekday(), [])
        for subject in day_subjects:
            if subject not in target_subjects:
                continue
            if current_day < subject_start_dates.get(subject, school_days[0] if school_days else current_day):
                continue

            queue = remaining.get(subject, [])
            if queue:
                lesson = queue.pop(0)
                assignments.append(
                    {
                        "subject": subject,
                        "date": current_day,
                        "record": lesson,
                    }
                )

    return assignments, remaining


def _get_column_letter(num):
    letter = ""
    while num > 0:
        num, remainder = divmod(num - 1, 26)
        letter = chr(65 + remainder) + letter
    return letter


def _find_header_index(headers, target_name):
    for index, header in enumerate(headers, start=1):
        if _clean_text(header) == target_name:
            return index
    return None


def fetch_progress_and_plan(sh, school_days, timetable, semester_start_date, planner_mode, input_fn=input):
    ws = resolve_progress_worksheet(sh)
    rows = ws.get_all_values()
    headers = rows[0] if rows else []
    date_col_idx = _find_header_index(headers, schedule.COLUMN_DATE)
    if not date_col_idx:
        raise ValueError("吏꾨룄???쒗듃?먯꽌 '怨꾪쉷?? 而щ읆 ?ㅻ뜑瑜?李얠쓣 ???놁뒿?덈떎.")

    records = ws.get_all_records(default_blank="")
    apply_done_column_fallback(headers, rows, records)
    excluded_unordered = [
        dict(record, _row=row_number)
        for row_number, record in enumerate(records, start=2)
        if _clean_text(record.get("怨쇰ぉ")) and not _has_ordered_unit(record)
    ]
    if excluded_unordered:
        print(f"  [?덈궡] ?レ옄濡??쒖옉?섏? ?딅뒗 ?⑥썝 {len(excluded_unordered)}媛쒕뒗 怨꾪쉷??諛곗젙?먯꽌 ?쒖쇅?⑸땲??")

    subject_queues = build_subject_queues(records, planner_mode=planner_mode)
    if not subject_queues:
        print(f"  [?뚮┝] '{PLANNER_MODES[planner_mode]}' ??곸쑝濡?諛곗젙??李⑥떆媛 ?놁뒿?덈떎.")
        return

    target_subjects = select_target_subjects(subject_queues, input_fn=input_fn)
    if not target_subjects:
        return

    subject_start_dates = fetch_subject_start_dates(
        sh,
        target_subjects,
        semester_start_date,
        input_fn=input_fn,
    )
    print("  [怨쇰ぉ蹂??섏뾽?쒖옉??")
    for subject in target_subjects:
        print(f"    {subject}: {subject_start_dates[subject]}")

    assignments, remaining = plan_lesson_assignments(
        subject_queues,
        school_days,
        timetable,
        target_subjects,
        subject_start_dates,
    )

    date_col_letter = _get_column_letter(date_col_idx)
    updates_by_row = {}
    if planner_mode == "initial":
        for row_number, record in enumerate(records, start=2):
            if _clean_text(record.get("怨쇰ぉ")) in target_subjects:
                updates_by_row[row_number] = ""

    for assignment in assignments:
        row_number = assignment["record"]["_row"]
        updates_by_row[row_number] = assignment["date"].strftime("%Y-%m-%d")

    updates = [
        {
            "range": f"{ws.title}!{date_col_letter}{row_number}",
            "values": [[value]],
        }
        for row_number, value in sorted(updates_by_row.items())
    ]

    if updates:
        print(f"  [?낅뜲?댄듃 以鍮? 珥?{len(updates)}媛쒖쓽 ?섏뾽 ?쇱젙??諛곗젙?섏뿀?듬땲??")
        preview = assignments[:10]
        for assignment in preview:
            record = assignment["record"]
            print(
                f"    - {assignment['subject']} | {record.get('??⑥썝', '')} | "
                f"{record.get('李⑥떆', '')}李⑥떆 | {assignment['date']}"
            )
        if len(assignments) > len(preview):
            print(f"    - and {len(assignments) - len(preview)} more")

        sh.values_batch_update({"valueInputOption": "USER_ENTERED", "data": updates})
        print("  [?깃났] 援ш? ?쒗듃 '怨꾪쉷?? ??ぉ??紐⑤뱺 ?좎쭨媛 怨꾩궛?섏뼱 ?낅젰?섏뿀?듬땲??")
    else:
        print("  [?뚮┝] 諛곗젙?????덈뒗 ?좎쭨(?쒓컙??湲곗?)媛 ?녾굅???대? 諛곗젙?섏뿀?듬땲??")

    unscheduled = {
        subject: len(queue)
        for subject, queue in remaining.items()
        if subject in target_subjects and queue
    }
    if unscheduled:
        print("  [?덈궡] ?먯깋 湲곌컙 ?덉뿉 諛곗젙?섏? 紐삵븳 李⑥떆媛 ?⑥븘 ?덉뒿?덈떎.")
        for subject, count in unscheduled.items():
            print(f"    {subject}: {count}媛??⑥쓬")


def resolve_progress_worksheet(sh):
    candidates = _sheet_name_candidates(PREFERRED_PROGRESS_SHEET_NAME, LEGACY_PROGRESS_SHEET_NAME) or ["시트1"]
    format_errors = []
    last_error = None
    for candidate in candidates:
        try:
            worksheet = sh.worksheet(candidate)
        except Exception as exc:
            if exc.__class__.__name__ != "WorksheetNotFound":
                raise
            last_error = exc
            continue

        headers = {_clean_text(header) for header in worksheet.row_values(1)}
        required = {schedule.COLUMN_SUBJECT, schedule.COLUMN_DATE}
        if required.issubset(headers):
            return worksheet
        format_errors.append(f"{candidate}: missing headers {', '.join(sorted(required - headers))}")

    if format_errors:
        raise ValueError(
            "Could not find a valid progress sheet. " + " | ".join(format_errors)
        )

    attempted = ", ".join(candidates)
    raise ValueError(f"Could not find a progress sheet. Checked: {attempted}") from last_error


def fetch_progress_and_plan(sh, school_days, timetable, semester_start_date, planner_mode, input_fn=input):
    ws = resolve_progress_worksheet(sh)
    date_col_idx = schedule.get_header_map(ws).get(schedule.COLUMN_DATE)
    if not date_col_idx:
        raise ValueError("Progress sheet is missing the planned-date column.")

    records = schedule.load_all(ws)
    excluded_unordered = [
        record
        for record in records
        if _clean_text(record.get(schedule.COLUMN_SUBJECT)) and not _has_ordered_unit(record)
    ]
    if excluded_unordered:
        print(f"  [info] Skipping {len(excluded_unordered)} rows without an ordered unit.")

    subject_queues = build_subject_queues(records, planner_mode=planner_mode)
    if not subject_queues:
        print(f"  [skip] No lessons matched planner mode '{planner_mode}'.")
        return

    target_subjects = select_target_subjects(subject_queues, input_fn=input_fn)
    if not target_subjects:
        return

    subject_start_dates = fetch_subject_start_dates(
        sh,
        target_subjects,
        semester_start_date,
        input_fn=input_fn,
    )
    print("  [subject start dates]")
    for subject in target_subjects:
        print(f"    {subject}: {subject_start_dates[subject]}")

    assignments, remaining = plan_lesson_assignments(
        subject_queues,
        school_days,
        timetable,
        target_subjects,
        subject_start_dates,
    )

    date_col_letter = _get_column_letter(date_col_idx)
    updates_by_row = {}
    if planner_mode == "initial":
        for record in records:
            if _clean_text(record.get(schedule.COLUMN_SUBJECT)) in target_subjects:
                updates_by_row[record["_row"]] = ""

    for assignment in assignments:
        row_number = assignment["record"]["_row"]
        updates_by_row[row_number] = assignment["date"].strftime("%Y-%m-%d")

    updates = [
        {
            "range": f"{ws.title}!{date_col_letter}{row_number}",
            "values": [[value]],
        }
        for row_number, value in sorted(updates_by_row.items())
    ]

    if updates:
        print(f"  [preview] Prepared {len(updates)} date updates.")
        preview = assignments[:10]
        for assignment in preview:
            record = assignment["record"]
            print(
                f"    - {assignment['subject']} | {record.get(schedule.COLUMN_UNIT, '')} | "
                f"{record.get(schedule.COLUMN_LESSON, '')} | {assignment['date']}"
            )
        if len(assignments) > len(preview):
            print(f"    - and {len(assignments) - len(preview)} more")

        sh.values_batch_update({"valueInputOption": "USER_ENTERED", "data": updates})
        print("  [done] Updated planned dates in the progress sheet.")
    else:
        print("  [skip] No schedulable dates were available in the selected window.")

    unscheduled = {
        subject: len(queue)
        for subject, queue in remaining.items()
        if subject in target_subjects and queue
    }
    if unscheduled:
        print("  [info] Some lessons remain unscheduled within the search window.")
        for subject, count in unscheduled.items():
            print(f"    {subject}: {count} remaining")


def main():
    parser = argparse.ArgumentParser(
        description="湲곗큹?쒓컙?? 吏꾨룄?? ?댁뾽?? ?섏뾽?쒖옉?쇱쓣 議고빀???섏뾽 怨꾪쉷?쇱쓣 ?먮룞 ?명똿?⑸땲??"
    )
    parser.add_argument(
        "--start-date",
        required=False,
        help="?숆린 ?쒖옉???먮뒗 湲곕낯 ?섏뾽 ?쒖옉??(?? 2026-03-02)",
    )
    parser.add_argument(
        "--end-date",
        required=False,
        help="?숆린 醫낅즺 ?쇱젙 (?앸왂 ???쒖옉?쇰줈遺??150?쇨컙 ?먯깋)",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(PLANNER_MODES.keys()),
        required=False,
        help="initial=珥덇린 ?꾩껜 諛곗젙, fill-blanks=鍮덉뭏 蹂닿컯 諛곗젙",
    )
    args = parser.parse_args()

    default_semester_start = date(date.today().year, 3, 2)
    raw_start_date = args.start_date
    if raw_start_date is None:
        print("=" * 60)
        print(" ?뱟 ?먮룞 吏꾨룄??諛곕텇 ?앹꽦湲?(Auto Schedule Planner)")
        print("=" * 60)
        raw_start_date = input("?숆린 ?쒖옉?쇱쓣 ?낅젰?섏꽭??(Enter=3.2): ").strip()

    semester_start_date = parse_date(raw_start_date) if raw_start_date else default_semester_start
    if not semester_start_date:
        print("?쒖옉 ?좎쭨???뺤떇???섎せ ?낅젰?섏뿀?듬땲??")
        input("\n?뷀꽣瑜??꾨Ⅴ硫?李쎌씠 ?ロ옓?덈떎...")
        sys.exit(1)

    end_date = parse_date(args.end_date) if args.end_date else semester_start_date + timedelta(days=150)
    if not end_date:
        print("醫낅즺 ?좎쭨???뺤떇???섎せ ?낅젰?섏뿀?듬땲??")
        input("\n?뷀꽣瑜??꾨Ⅴ硫?李쎌씠 ?ロ옓?덈떎...")
        sys.exit(1)

    print(f"\n ??諛곗젙 ?먯깋 湲곌컙: {semester_start_date} ~ {end_date}")

    try:
        client = get_client()
        sh = client.open_by_key(SHEET_ID)

        holidays = fetch_holidays(sh)
        school_days = get_school_days(semester_start_date, end_date, holidays)
        print(f" Total school days (weekdays minus holidays): {len(school_days)}")

        timetable = fetch_timetable(sh)
        planner_mode = args.mode or choose_planner_mode(input_fn=input)
        print(f" ??諛곗젙 紐⑤뱶: {PLANNER_MODES[planner_mode]}")
        fetch_progress_and_plan(
            sh,
            school_days,
            timetable,
            semester_start_date,
            planner_mode,
            input_fn=input,
        )

        input("\n[?묒뾽 ?꾨즺] ?뷀꽣瑜??꾨Ⅴ硫?李쎌씠 ?ロ옓?덈떎...")

    except Exception as exc:
        print(f"\n[?ㅻ쪟 諛쒖깮] ?묒뾽??以묐떒?⑸땲?? {exc}")
        input("\n[?ㅻ쪟] ?뷀꽣瑜??꾨Ⅴ硫?李쎌씠 ?ロ옓?덈떎...")
        sys.exit(1)


if __name__ == "__main__":
    main()


