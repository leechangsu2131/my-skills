import os
import re
import sys
from datetime import date, timedelta

import auto_planner
import schedule

BRIDGE_SHEET_NAME = os.getenv("BRIDGE_SHEET_NAME", "수업배치")
COLUMN_PLANNED_PERIOD = os.getenv("PLANNED_PERIOD_COLUMN", "계획교시")
STATUS_PLANNED = "planned"
STATUS_DONE = "done"
SOURCE_PROGRESS_SYNC = "progress_sync"
SOURCE_AUTO_PLAN = "auto_plan"
PERIOD_UNMATCHED_MEMO = "period-unmatched"
PERIOD_OUTSIDE_TIMETABLE_MEMO = "period-outside-timetable"

BRIDGE_HEADERS = (
    "slot_date",
    "slot_period",
    "slot_order",
    schedule.COLUMN_SUBJECT,
    schedule.COLUMN_LESSON_ID,
    "status",
    "source",
    "memo",
)
BRIDGE_HEADER_MAP = {header: index for index, header in enumerate(BRIDGE_HEADERS, start=1)}


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _extract_number(value):
    text = _clean_text(value)
    match = re.search(r"\d+", text)
    if not match:
        return None
    return int(match.group())


def _normalize_subject_key(value):
    return re.sub(r"\s+", "", _clean_text(value)).casefold()


def _period_sort_key(value):
    number = _extract_number(value)
    return number if number is not None else sys.maxsize


def _bridge_row_sort_key(row):
    parsed_date = schedule._parse_date(row.get("slot_date"), allow_blank=True) or schedule.date.max
    return (
        parsed_date,
        _period_sort_key(row.get("slot_period")),
        _extract_number(row.get("slot_order")) or sys.maxsize,
        _clean_text(row.get(schedule.COLUMN_SUBJECT)),
        _clean_text(row.get(schedule.COLUMN_LESSON_ID)),
    )


def _available_periods_for_subject(timetable, planned_date, subject):
    subject_key = _normalize_subject_key(subject)
    weekday_subjects = timetable.get(planned_date.weekday(), [])
    return [
        period
        for period, scheduled_subject in enumerate(weekday_subjects, start=1)
        if _normalize_subject_key(scheduled_subject) == subject_key
    ]


def build_bridge_rows_from_progress(records, timetable, *, planned_period_column=COLUMN_PLANNED_PERIOD):
    scheduled_records = [
        record
        for record in records
        if schedule._lesson_id_of(record) and schedule._planned_date(record) is not None
    ]
    scheduled_records = sorted(scheduled_records, key=schedule._record_sort_key)

    grouped_records = {}
    for record in scheduled_records:
        planned_date = schedule._planned_date(record)
        subject = schedule._subject_of(record)
        grouped_records.setdefault((planned_date, subject), []).append(record)

    bridge_rows = []
    for (planned_date, subject), group in sorted(grouped_records.items()):
        available_periods = _available_periods_for_subject(timetable, planned_date, subject)
        explicit_periods = {
            _extract_number(record.get(planned_period_column))
            for record in group
            if _extract_number(record.get(planned_period_column)) is not None
        }
        inferred_periods = [
            period
            for period in available_periods
            if period not in explicit_periods
        ]
        inferred_index = 0

        for slot_order, record in enumerate(group, start=1):
            explicit_period = _extract_number(record.get(planned_period_column))
            memo = ""
            if explicit_period is not None:
                slot_period = explicit_period
                if available_periods and explicit_period not in available_periods:
                    memo = PERIOD_OUTSIDE_TIMETABLE_MEMO
            elif inferred_index < len(inferred_periods):
                slot_period = inferred_periods[inferred_index]
                inferred_index += 1
            else:
                slot_period = ""
                memo = PERIOD_UNMATCHED_MEMO

            bridge_rows.append(
                {
                    "slot_date": schedule._format_date(planned_date),
                    "slot_period": slot_period,
                    "slot_order": slot_order,
                    schedule.COLUMN_SUBJECT: subject,
                    schedule.COLUMN_LESSON_ID: schedule._lesson_id_of(record),
                    "status": STATUS_DONE if schedule._is_done(record) else STATUS_PLANNED,
                    "source": SOURCE_PROGRESS_SYNC,
                    "memo": memo,
                }
            )

    return sorted(bridge_rows, key=_bridge_row_sort_key)


def build_progress_sync_rows(records, bridge_rows, *, lesson_ids=None):
    target_lesson_ids = {
        _clean_text(lesson_id)
        for lesson_id in (lesson_ids or [])
        if _clean_text(lesson_id)
    }
    earliest_slot_by_lesson_id = {}
    for row in bridge_rows:
        lesson_id = _clean_text(row.get(schedule.COLUMN_LESSON_ID))
        if not lesson_id:
            continue
        if target_lesson_ids and lesson_id not in target_lesson_ids:
            continue

        parsed_date = schedule._parse_date(row.get("slot_date"), allow_blank=True)
        if parsed_date is None:
            continue

        candidate = (
            parsed_date,
            _period_sort_key(row.get("slot_period")),
            _extract_number(row.get("slot_order")) or sys.maxsize,
        )
        existing = earliest_slot_by_lesson_id.get(lesson_id)
        if existing is None or candidate < existing["sort_key"]:
            earliest_slot_by_lesson_id[lesson_id] = {
                "sort_key": candidate,
                "slot_date": schedule._format_date(parsed_date),
                "slot_period": _extract_number(row.get("slot_period")) or "",
            }

    sync_rows = []
    for record in records:
        lesson_id = schedule._lesson_id_of(record)
        if target_lesson_ids and lesson_id not in target_lesson_ids:
            continue
        slot = earliest_slot_by_lesson_id.get(lesson_id)
        sync_rows.append(
            {
                "row": record.get("_row"),
                "lesson_id": lesson_id,
                "계획일": slot["slot_date"] if slot else "",
                COLUMN_PLANNED_PERIOD: slot["slot_period"] if slot else "",
            }
        )
    return sync_rows


def build_bridge_subject_queues(records, planner_mode="initial"):
    subject_queues = {}

    for record in records:
        subject = schedule._subject_of(record)
        lesson_id = schedule._lesson_id_of(record)
        if not subject or not lesson_id:
            continue

        if planner_mode == "fill-blanks":
            if schedule._is_done(record) or schedule._planned_date(record) is not None:
                continue

        enriched = dict(record)
        subject_queues.setdefault(subject, []).append(enriched)

    for subject, queue in subject_queues.items():
        last_unit_order = 0
        for item in sorted(queue, key=lambda row: row.get("_row", sys.maxsize)):
            unit_order = _extract_number(item.get(schedule.COLUMN_UNIT))
            if unit_order is None:
                unit_order = last_unit_order
            else:
                last_unit_order = unit_order

            lesson_order = _extract_number(item.get(schedule.COLUMN_LESSON))
            if lesson_order is None:
                lesson_order = item.get("_row", sys.maxsize)

            item["_unit_order"] = unit_order
            item["_lesson_order"] = lesson_order

        subject_queues[subject] = sorted(
            queue,
            key=lambda item: (
                item.get("_unit_order", 0),
                item.get("_lesson_order", sys.maxsize),
                item.get("_row", sys.maxsize),
            ),
        )

    return {subject: queue for subject, queue in subject_queues.items() if queue}


def plan_bridge_rows(subject_queues, school_days, timetable, subject_start_dates, *, source=SOURCE_AUTO_PLAN):
    remaining = {subject: list(queue) for subject, queue in subject_queues.items()}
    bridge_rows = []
    subject_lookup = {}
    for subject in subject_queues:
        subject_key = _normalize_subject_key(subject)
        if subject_key and subject_key not in subject_lookup:
            subject_lookup[subject_key] = subject

    for current_day in school_days:
        day_subjects = timetable.get(current_day.weekday(), [])
        slot_order_by_subject = {}

        for period_index, subject in enumerate(day_subjects, start=1):
            subject = _clean_text(subject)
            queue_subject = subject_lookup.get(_normalize_subject_key(subject))
            if not subject or not queue_subject:
                continue
            if current_day < subject_start_dates.get(
                queue_subject,
                school_days[0] if school_days else current_day,
            ):
                continue

            queue = remaining.get(queue_subject, [])
            if not queue:
                continue

            record = queue.pop(0)
            slot_order_by_subject[queue_subject] = slot_order_by_subject.get(queue_subject, 0) + 1
            bridge_rows.append(
                {
                    "slot_date": schedule._format_date(current_day),
                    "slot_period": period_index,
                    "slot_order": slot_order_by_subject[queue_subject],
                    schedule.COLUMN_SUBJECT: queue_subject,
                    schedule.COLUMN_LESSON_ID: schedule._lesson_id_of(record),
                    "status": STATUS_DONE if schedule._is_done(record) else STATUS_PLANNED,
                    "source": source,
                    "memo": "",
                }
            )

    return sorted(bridge_rows, key=_bridge_row_sort_key), remaining


def _preview_items(items, *, limit=8):
    items = [item for item in items if _clean_text(item)]
    if not items:
        return "없음"
    preview = items[:limit]
    text = ", ".join(preview)
    remaining = len(items) - len(preview)
    if remaining > 0:
        text = f"{text} 외 {remaining}개"
    return text


def build_bridge_diagnostics(
    records,
    school_days,
    timetable,
    subject_queues,
    bridge_rows,
    subject_start_dates,
    *,
    end_date,
):
    populated_records = [
        record
        for record in records
        if schedule._subject_of(record) and schedule._lesson_id_of(record)
    ]
    queue_subjects = sorted(subject_queues)
    timetable_subjects = sorted(
        {
            _clean_text(subject)
            for subjects in timetable.values()
            for subject in subjects
            if _clean_text(subject)
        }
    )

    matched_subjects = sorted(
        {
            queue_subject
            for queue_subject in subject_queues
            if any(
                _normalize_subject_key(queue_subject) == _normalize_subject_key(timetable_subject)
                for timetable_subject in timetable_subjects
            )
        }
    )
    unmatched_queue_subjects = sorted(
        subject for subject in queue_subjects if subject not in matched_subjects
    )
    queue_sizes = {
        subject: len(queue)
        for subject, queue in sorted(subject_queues.items())
    }
    late_start_subjects = sorted(
        f"{subject}({schedule._format_date(start_date)})"
        for subject, start_date in subject_start_dates.items()
        if start_date and start_date > end_date
    )

    return {
        "record_count": len(records),
        "populated_record_count": len(populated_records),
        "queue_subjects": queue_subjects,
        "queue_sizes": queue_sizes,
        "timetable_subjects": timetable_subjects,
        "matched_subjects": matched_subjects,
        "unmatched_queue_subjects": unmatched_queue_subjects,
        "school_day_count": len(school_days),
        "school_day_first": schedule._format_date(school_days[0]) if school_days else "",
        "school_day_last": schedule._format_date(school_days[-1]) if school_days else "",
        "late_start_subjects": late_start_subjects,
        "generated_row_count": len(bridge_rows),
    }


def generate_bridge_rows_from_timetable(
    records,
    sh,
    timetable,
    *,
    semester_start_date,
    end_date,
    planner_mode="initial",
):
    holidays = auto_planner.fetch_holidays(sh)
    school_days = auto_planner.get_school_days(semester_start_date, end_date, holidays)
    subject_queues = build_bridge_subject_queues(records, planner_mode=planner_mode)
    target_subjects = list(subject_queues.keys())
    subject_start_dates = auto_planner.fetch_subject_start_dates(
        sh,
        target_subjects,
        semester_start_date,
        input_fn=lambda _prompt: "",
    )
    bridge_rows, remaining = plan_bridge_rows(
        subject_queues,
        school_days,
        timetable,
        subject_start_dates,
    )
    diagnostics = build_bridge_diagnostics(
        records,
        school_days,
        timetable,
        subject_queues,
        bridge_rows,
        subject_start_dates,
        end_date=end_date,
    )
    return bridge_rows, remaining, diagnostics


def _find_header_index(headers, target_name):
    for index, header in enumerate(headers, start=1):
        if _clean_text(header) == target_name:
            return index
    return None


def _ensure_column(ws, header_name):
    headers = ws.row_values(1)
    header_index = _find_header_index(headers, header_name)
    if header_index:
        return header_index

    if not hasattr(ws, "add_cols"):
        raise schedule.SheetFormatError(
            f"시트에 '{header_name}' 컬럼을 자동으로 추가할 수 없습니다. 시트에 직접 컬럼을 만든 뒤 다시 실행해 주세요."
        )

    ws.add_cols(1)
    column_index = len(headers) + 1
    schedule._batch_update_cells_with_option(
        ws,
        [
            schedule._make_cell_update(
                column_index,
                1,
                header_name,
                worksheet_name=ws.title,
            )
        ],
        value_input_option="RAW",
    )
    return column_index


def _ensure_bridge_sheet(sh):
    created = False
    try:
        ws = sh.worksheet(BRIDGE_SHEET_NAME)
    except Exception as exc:
        if exc.__class__.__name__ != "WorksheetNotFound":
            raise
        ws = sh.add_worksheet(title=BRIDGE_SHEET_NAME, rows=1000, cols=len(BRIDGE_HEADERS))
        created = True

    existing_headers = ws.row_values(1)
    if not created and len(existing_headers) < len(BRIDGE_HEADERS):
        ws.add_cols(len(BRIDGE_HEADERS) - len(existing_headers))

    schedule._batch_update_cells_with_option(
        ws,
        [
            schedule._make_cell_update(
                index,
                1,
                header,
                worksheet_name=ws.title,
            )
            for index, header in enumerate(BRIDGE_HEADERS, start=1)
        ],
        value_input_option="RAW",
    )
    return ws


def _bridge_rows_to_values(bridge_rows):
    values = [list(BRIDGE_HEADERS)]
    for row in bridge_rows:
        values.append([row.get(header, "") for header in BRIDGE_HEADERS])
    return values


def get_bridge_header_map(_ws=None):
    return dict(BRIDGE_HEADER_MAP)


def load_bridge_rows(ws):
    values = ws.get_all_values()
    headers = values[0] if values else []
    header_map = {_clean_text(header): index for index, header in enumerate(headers, start=1)}
    missing = [header for header in BRIDGE_HEADERS if header not in header_map]
    if missing:
        raise schedule.SheetFormatError(
            f"브릿지 시트 필수 컬럼이 없습니다: {', '.join(missing)}"
        )

    bridge_rows = []
    for row_number, row_values in enumerate(values[1:], start=2):
        expanded = row_values + [""] * max(0, len(headers) - len(row_values))
        row = {
            header: expanded[header_map[header] - 1] if header_map[header] <= len(expanded) else ""
            for header in BRIDGE_HEADERS
        }
        row["_row"] = row_number
        bridge_rows.append(row)

    return sorted(bridge_rows, key=_bridge_row_sort_key)


def write_bridge_sheet(ws, bridge_rows):
    values = _bridge_rows_to_values(bridge_rows)
    ws.clear()
    end_column = schedule._column_letter(len(BRIDGE_HEADERS))
    end_row = len(values)
    ws.spreadsheet.values_batch_update(
        {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {
                    "range": f"{ws.title}!A1:{end_column}{end_row}",
                    "values": values,
                }
            ],
        }
    )


def sync_progress_sheet(progress_ws, records, bridge_rows, *, lesson_ids=None):
    header_map = schedule.get_header_map(progress_ws)
    date_column = header_map[schedule.COLUMN_DATE]
    period_column = header_map.get(COLUMN_PLANNED_PERIOD)
    if period_column is None:
        period_column = _ensure_column(progress_ws, COLUMN_PLANNED_PERIOD)

    sync_rows = build_progress_sync_rows(records, bridge_rows, lesson_ids=lesson_ids)
    worksheet_name = getattr(progress_ws, "title", auto_planner.PROGRESS_SHEET_NAME)
    updates = []
    for item in sync_rows:
        updates.append(
            schedule._make_cell_update(
                date_column,
                item["row"],
                item[schedule.COLUMN_DATE],
                worksheet_name=worksheet_name,
            )
        )
        updates.append(
            schedule._make_cell_update(
                period_column,
                item["row"],
                item[COLUMN_PLANNED_PERIOD],
                worksheet_name=worksheet_name,
            )
        )

    schedule._batch_update_cells_with_option(
        progress_ws,
        updates,
        value_input_option="USER_ENTERED",
    )
    return {
        "updated_rows": len(sync_rows),
        "period_column_added": schedule.get_header_map(progress_ws).get(COLUMN_PLANNED_PERIOD) == period_column,
    }


def main():
    try:
        client = auto_planner.get_client()
        sh = client.open_by_key(auto_planner.SHEET_ID)
        progress_ws = auto_planner.resolve_progress_worksheet(sh)
        if _clean_text(progress_ws.title) == _clean_text(BRIDGE_SHEET_NAME):
            raise ValueError(
                "진도표 시트와 브릿지 시트 이름이 같습니다. "
                "BRIDGE_SHEET_NAME을 다른 시트 이름으로 설정해 주세요."
            )

        lesson_id_result = schedule.ensure_lesson_ids(progress_ws)
        records = schedule.load_all(progress_ws)
        timetable = auto_planner.fetch_timetable(sh)
        bridge_rows = build_bridge_rows_from_progress(records, timetable)
        generated_from_planner = False

        if not bridge_rows:
            semester_start_date = date(date.today().year, 3, 2)
            end_date = semester_start_date + timedelta(days=150)
            bridge_rows, remaining, diagnostics = generate_bridge_rows_from_timetable(
                records,
                sh,
                timetable,
                semester_start_date=semester_start_date,
                end_date=end_date,
                planner_mode="initial",
            )
            generated_from_planner = True

        if not bridge_rows:
            detail_parts = [
                f"진도표 수업 행 {diagnostics['populated_record_count']}개",
                f"대상 과목 { _preview_items(diagnostics['queue_subjects']) }",
                f"시간표 과목 { _preview_items(diagnostics['timetable_subjects']) }",
                f"일치 과목 { _preview_items(diagnostics['matched_subjects']) }",
                f"수업일 {diagnostics['school_day_count']}일",
            ]
            if diagnostics["unmatched_queue_subjects"]:
                detail_parts.append(
                    f"시간표와 안 맞는 과목 { _preview_items(diagnostics['unmatched_queue_subjects']) }"
                )
            if diagnostics["late_start_subjects"]:
                detail_parts.append(
                    f"범위 밖 시작일 { _preview_items(diagnostics['late_start_subjects']) }"
                )
            raise ValueError(
                "수업배치로 만들 수 있는 수업이 없습니다. "
                + " / ".join(detail_parts)
            )

        bridge_ws = _ensure_bridge_sheet(sh)
        write_bridge_sheet(bridge_ws, bridge_rows)
        sync_result = sync_progress_sheet(progress_ws, records, bridge_rows)

        print("=" * 60)
        print(" 브릿지 시트 동기화 완료")
        print("=" * 60)
        print(f" - lesson_id 처리: {lesson_id_result['message']}")
        print(f" - 브릿지 시트: {BRIDGE_SHEET_NAME}")
        print(f" - 생성된 수업배치 행 수: {len(bridge_rows)}")
        print(f" - 진도표 동기화 행 수: {sync_result['updated_rows']}")
        if generated_from_planner:
            print(" - 생성 방식: 시간표와 진도 순서를 기준으로 새로 자동 배치했습니다.")
        else:
            print(" - 생성 방식: 기존 진도표의 계획일을 브릿지 시트로 옮겼습니다.")

        unmatched = [row for row in bridge_rows if row.get("memo") == PERIOD_UNMATCHED_MEMO]
        if unmatched:
            print(" - 안내: 시간표와 맞지 않아 교시를 추정하지 못한 항목이 있습니다.")
            for row in unmatched[:10]:
                print(
                    f"    - {row['slot_date']} | {row.get(schedule.COLUMN_SUBJECT, '')} | "
                    f"{row.get(schedule.COLUMN_LESSON_ID, '')}"
                )
            remaining = len(unmatched) - 10
            if remaining > 0:
                print(f"    - 그 외 {remaining}개")

    except Exception as exc:
        print(f"\n[오류] 브릿지 시트 동기화에 실패했습니다: {exc}\n")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
