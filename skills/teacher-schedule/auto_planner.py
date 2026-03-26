import argparse
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
PROGRESS_SHEET_NAME = os.getenv("SHEET_NAME", "시트1")
TIMETABLE_SHEET_NAME = os.getenv("TIMETABLE_SHEET", "기초시간표")
HOLIDAY_SHEET_NAME = os.getenv("HOLIDAY_SHEET", "휴업일")
SUBJECT_START_SHEET_NAME = os.getenv("SUBJECT_START_SHEET", "수업시작일")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TRUE_VALUES = {"TRUE", "1", "Y", "YES", "DONE"}
DONE_COLUMN_FALLBACK_INDEX = 6
PLANNER_MODES = {
    "initial": "초기 전체 배정",
    "fill-blanks": "빈칸 보강 배정",
}


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_done_value(value):
    return _clean_text(value).lstrip("'").strip().upper()


def _extract_number(value, default=0):
    text = _clean_text(value)
    match = re.search(r"\d+", text)
    if not match:
        return default
    return int(match.group())


def _is_done(value):
    return _normalize_done_value(value) in TRUE_VALUES


def _has_planned_date(record):
    return parse_date(record.get("계획일")) is not None


def _has_ordered_unit(record):
    return re.match(r"^\s*\d+", _clean_text(record.get("대단원", ""))) is not None


def get_client():
    if not SHEET_ID:
        raise ValueError("환경 변수 SHEET_ID가 설정되어 있지 않습니다. (.env 파일을 확인하세요)")

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise ValueError(
            "Google Sheets 연동 라이브러리가 없습니다. `pip install -r requirements.txt`를 먼저 실행하세요."
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


def fetch_holidays(sh):
    try:
        ws = sh.worksheet(HOLIDAY_SHEET_NAME)
        records = ws.get_all_records(default_blank="")
    except Exception as exc:
        if exc.__class__.__name__ == "WorksheetNotFound":
            print(f"  [안내] '{HOLIDAY_SHEET_NAME}' 시트를 찾을 수 없어 평일(월~금)을 모두 수업일로 간주합니다.")
            return set()
        raise

    holidays = set()
    for record in records:
        values = list(record.values())
        date_value = record.get("날짜") if "날짜" in record else (values[0] if values else "")
        parsed = parse_date(date_value)
        if parsed:
            holidays.add(parsed)
    return holidays


def fetch_timetable(sh):
    ws = sh.worksheet(TIMETABLE_SHEET_NAME)
    rows = ws.get_all_values()
    if not rows or len(rows) < 2:
        raise ValueError("기초시간표 시트에 데이터가 존재하지 않습니다.")

    headers = [_clean_text(value).replace("요일", "") for value in rows[0]]
    valid_days = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4}
    day_indices = {}

    for col_idx, header in enumerate(headers):
        for day_name, weekday in valid_days.items():
            if day_name in header:
                day_indices[weekday] = col_idx
                break

    if not day_indices:
        raise ValueError(f"기초시간표 첫 번째 행({headers})에서 요일(월~금) 텍스트를 찾을 수 없습니다.")

    timetable = {day: [] for day in range(5)}
    for row in rows[1:]:
        for weekday, col_idx in day_indices.items():
            if col_idx < len(row):
                subject = _clean_text(row[col_idx])
                if subject:
                    timetable[weekday].append(subject)

    print("  [기초시간표 파싱 완료]")
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
        item.get("_unit_order", _extract_number(item.get("대단원"))),
        item.get("_lesson_order", _extract_number(item.get("차시"))),
        item["_row"],
    )


def should_include_record(record, planner_mode):
    if not _has_ordered_unit(record):
        return False
    if planner_mode == "initial":
        return True
    if planner_mode == "fill-blanks":
        return not _is_done(record.get("실행여부", "")) and not _has_planned_date(record)
    raise ValueError(f"지원하지 않는 배정 모드입니다: {planner_mode}")


def build_subject_queues(records, planner_mode="fill-blanks"):
    subject_queues = {}
    for row_number, record in enumerate(records, start=2):
        subject = _clean_text(record.get("과목"))
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
            unit_order = _extract_number(item.get("대단원"), default=None)
            if unit_order is None:
                unit_order = last_unit_order
            else:
                last_unit_order = unit_order

            item["_unit_order"] = unit_order
            item["_lesson_order"] = _extract_number(item.get("차시"), default=item["_row"])

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
    if any(_clean_text(header) == "실행여부" for header in headers):
        return records
    if len(headers) < DONE_COLUMN_FALLBACK_INDEX:
        return records

    for index, record in enumerate(records):
        row = rows[index + 1] if index + 1 < len(rows) else []
        record["실행여부"] = row[DONE_COLUMN_FALLBACK_INDEX - 1] if len(row) >= DONE_COLUMN_FALLBACK_INDEX else ""
    return records


def parse_subject_start_sheet(records):
    subject_key = _find_matching_key(records, ["과목", "subject"])
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
            f"  [{subject}] 수업시작일을 입력하세요 (Enter={semester_start_date}): "
        ).strip()
        parsed = parse_date(answer)
        if answer and not parsed:
            print(f"  [경고] '{subject}' 수업시작일 형식이 잘못되어 학기 시작일({semester_start_date})로 처리합니다.")
        resolved[subject] = parsed or semester_start_date

    return resolved


def fetch_subject_start_dates(sh, target_subjects, semester_start_date, input_fn=input):
    sheet_mapping = {}
    try:
        ws = sh.worksheet(SUBJECT_START_SHEET_NAME)
        records = ws.get_all_records(default_blank="")
        sheet_mapping = parse_subject_start_sheet(records)
        if sheet_mapping:
            print(f"  [수업시작일 시트 파싱 완료] {', '.join(sorted(sheet_mapping))}")
        else:
            print(f"  [안내] '{SUBJECT_START_SHEET_NAME}' 시트에서 과목/수업시작일 형식을 찾지 못했습니다.")
    except Exception as exc:
        if exc.__class__.__name__ == "WorksheetNotFound":
            print(f"  [안내] '{SUBJECT_START_SHEET_NAME}' 시트가 없어 과목별 시작일을 직접 확인합니다.")
        else:
            raise

    return resolve_subject_start_dates(
        target_subjects,
        sheet_mapping,
        semester_start_date,
        input_fn=input_fn,
    )


def select_target_subjects(subject_queues, input_fn=input):
    print(f"\n  [안내] 미수업 차시가 남아있는 과목: {', '.join(subject_queues.keys())}")
    print("  어느 과목에 이번 일정 배정을 적용하시겠습니까?")
    print("    1. 모든 과목 한 번에 배정 (그냥 엔터 입력)")
    print("    2. 특정 과목만 선택")

    choice = input_fn("  입력 (번호 또는 과목명 쉼표 구분): ").strip()
    target_subjects = list(subject_queues.keys())

    if choice and choice != "1":
        if choice == "2":
            choice = input_fn("  배정할 과목명을 입력하세요 (예: 국어, 도덕): ").strip()

        if choice:
            entered = [_clean_text(value) for value in choice.split(",") if _clean_text(value)]
            valid = [subject for subject in entered if subject in subject_queues]
            if not valid:
                print("  [경고] 입력하신 과목이 미수업 목록에 없거나 잘못 입력되었습니다. 작업을 취소합니다.")
                return []
            target_subjects = valid

    print(f"\n  [진행] 다음 과목에 대해서만 일정을 배정합니다: {', '.join(target_subjects)}")
    return target_subjects


def choose_planner_mode(input_fn=input):
    print("\n  배정 모드를 선택하세요.")
    print("    1. 초기 전체 배정: 계획일을 처음부터 다시 넣습니다. F열(실행여부)과 기존 계획일을 무시합니다.")
    print("    2. 빈칸 보강 배정: F열이 FALSE 계열이고 계획일이 빈칸인 행만 채웁니다. (Enter=2)")

    choice = _clean_text(input_fn("  선택: "))
    if choice in {"", "2", "fill", "fill-blanks", "blank"}:
        return "fill-blanks"
    if choice in {"1", "initial", "all"}:
        return "initial"
    print("  [경고] 알 수 없는 입력이라 안전하게 '빈칸 보강 배정'으로 진행합니다.")
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
    ws = sh.worksheet(PROGRESS_SHEET_NAME)
    rows = ws.get_all_values()
    headers = rows[0] if rows else []
    date_col_idx = _find_header_index(headers, "계획일")
    if not date_col_idx:
        raise ValueError("진도표 시트에서 '계획일' 컬럼 헤더를 찾을 수 없습니다.")

    records = ws.get_all_records(default_blank="")
    apply_done_column_fallback(headers, rows, records)
    excluded_unordered = [
        dict(record, _row=row_number)
        for row_number, record in enumerate(records, start=2)
        if _clean_text(record.get("과목")) and not _has_ordered_unit(record)
    ]
    if excluded_unordered:
        print(f"  [안내] 숫자로 시작하지 않는 단원 {len(excluded_unordered)}개는 계획일 배정에서 제외합니다.")

    subject_queues = build_subject_queues(records, planner_mode=planner_mode)
    if not subject_queues:
        print(f"  [알림] '{PLANNER_MODES[planner_mode]}' 대상으로 배정할 차시가 없습니다.")
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
    print("  [과목별 수업시작일]")
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
            if _clean_text(record.get("과목")) in target_subjects:
                updates_by_row[row_number] = ""

    for assignment in assignments:
        row_number = assignment["record"]["_row"]
        updates_by_row[row_number] = assignment["date"].strftime("%Y-%m-%d")

    updates = [
        {
            "range": f"{PROGRESS_SHEET_NAME}!{date_col_letter}{row_number}",
            "values": [[value]],
        }
        for row_number, value in sorted(updates_by_row.items())
    ]

    if updates:
        print(f"  [업데이트 준비] 총 {len(updates)}개의 수업 일정이 배정되었습니다.")
        preview = assignments[:10]
        for assignment in preview:
            record = assignment["record"]
            print(
                f"    - {assignment['subject']} | {record.get('대단원', '')} | "
                f"{record.get('차시', '')}차시 | {assignment['date']}"
            )
        if len(assignments) > len(preview):
            print(f"    - 그 외 {len(assignments) - len(preview)}개")

        sh.values_batch_update({"valueInputOption": "USER_ENTERED", "data": updates})
        print("  [성공] 구글 시트 '계획일' 항목에 모든 날짜가 계산되어 입력되었습니다!")
    else:
        print("  [알림] 배정할 수 있는 날짜(시간표 기준)가 없거나 이미 배정되었습니다.")

    unscheduled = {
        subject: len(queue)
        for subject, queue in remaining.items()
        if subject in target_subjects and queue
    }
    if unscheduled:
        print("  [안내] 탐색 기간 안에 배정하지 못한 차시가 남아 있습니다.")
        for subject, count in unscheduled.items():
            print(f"    {subject}: {count}개 남음")


def main():
    parser = argparse.ArgumentParser(
        description="기초시간표, 진도표, 휴업일, 수업시작일을 조합해 수업 계획일을 자동 세팅합니다."
    )
    parser.add_argument(
        "--start-date",
        required=False,
        help="학기 시작일 또는 기본 수업 시작일 (예: 2026-03-02)",
    )
    parser.add_argument(
        "--end-date",
        required=False,
        help="학기 종료 일정 (생략 시 시작일로부터 150일간 탐색)",
    )
    parser.add_argument(
        "--mode",
        choices=sorted(PLANNER_MODES.keys()),
        required=False,
        help="initial=초기 전체 배정, fill-blanks=빈칸 보강 배정",
    )
    args = parser.parse_args()

    default_semester_start = date(date.today().year, 3, 2)
    raw_start_date = args.start_date
    if raw_start_date is None:
        print("=" * 60)
        print(" 📅 자동 진도표 배분 생성기 (Auto Schedule Planner)")
        print("=" * 60)
        raw_start_date = input("학기 시작일을 입력하세요 (Enter=3.2): ").strip()

    semester_start_date = parse_date(raw_start_date) if raw_start_date else default_semester_start
    if not semester_start_date:
        print("시작 날짜의 형식이 잘못 입력되었습니다.")
        input("\n엔터를 누르면 창이 닫힙니다...")
        sys.exit(1)

    end_date = parse_date(args.end_date) if args.end_date else semester_start_date + timedelta(days=150)
    if not end_date:
        print("종료 날짜의 형식이 잘못 입력되었습니다.")
        input("\n엔터를 누르면 창이 닫힙니다...")
        sys.exit(1)

    print(f"\n ▸ 배정 탐색 기간: {semester_start_date} ~ {end_date}")

    try:
        client = get_client()
        sh = client.open_by_key(SHEET_ID)

        holidays = fetch_holidays(sh)
        school_days = get_school_days(semester_start_date, end_date, holidays)
        print(f" ▸ 총 수업 일수 (주말/휴일 제외): {len(school_days)}일 확보됨")

        timetable = fetch_timetable(sh)
        planner_mode = args.mode or choose_planner_mode(input_fn=input)
        print(f" ▸ 배정 모드: {PLANNER_MODES[planner_mode]}")
        fetch_progress_and_plan(
            sh,
            school_days,
            timetable,
            semester_start_date,
            planner_mode,
            input_fn=input,
        )

        input("\n[작업 완료] 엔터를 누르면 창이 닫힙니다...")

    except Exception as exc:
        print(f"\n[오류 발생] 작업을 중단합니다: {exc}")
        input("\n[오류] 엔터를 누르면 창이 닫힙니다...")
        sys.exit(1)


if __name__ == "__main__":
    main()
