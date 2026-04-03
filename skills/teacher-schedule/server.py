import json
import os
import re
from datetime import date, datetime, timedelta
from io import BytesIO

import fitz
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

import schedule


LOG_FILE = "activity_log.json"
SPLIT_PDF_FILENAME_PATTERN = re.compile(r"_p\d+(?:-\d+)?\.pdf$", re.IGNORECASE)


def log_action(action, subject, details=""):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "subject": subject,
        "details": details,
    }
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as handle:
                logs = json.load(handle)
        except Exception:
            logs = []
    logs.insert(0, log_entry)
    logs = logs[:50]
    with open(LOG_FILE, "w", encoding="utf-8") as handle:
        json.dump(logs, handle, ensure_ascii=False, indent=2)


def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return []


def _pdf_download_name(record):
    return (
        f"{record.get(schedule.COLUMN_SUBJECT, 'lesson')}_"
        f"{record.get(schedule.COLUMN_LESSON, 'fragment')}.pdf"
    )


def _is_pre_split_pdf(pdf_path):
    normalized = os.path.normpath(pdf_path)
    parts = [part.casefold() for part in normalized.split(os.sep) if part]
    if "pdf_splits" in parts:
        return True
    return SPLIT_PDF_FILENAME_PATTERN.search(os.path.basename(normalized)) is not None


def _month_bounds(target_date):
    month_start = target_date.replace(day=1)
    if target_date.month == 12:
        next_month = date(target_date.year + 1, 1, 1)
    else:
        next_month = date(target_date.year, target_date.month + 1, 1)
    return month_start, next_month - timedelta(days=1)


def _week_bounds(target_date):
    week_start = target_date - timedelta(days=target_date.weekday())
    return week_start, week_start + timedelta(days=4)


def _parse_item_date(item):
    return schedule._parse_date(
        item.get("planned_date") or item.get("slot_date") or item.get(schedule.COLUMN_DATE),
        allow_blank=True,
    )


def _item_status(item):
    status = schedule._clean_text(item.get("status")).casefold()
    if status:
        return status
    return "done" if schedule._is_done(item) else "planned"


def _sort_serialized_items(items):
    return sorted(
        items,
        key=lambda item: (
            _parse_item_date(item) or date.max,
            schedule._safe_int(item.get("planned_period")),
            schedule._safe_int(item.get("lesson")),
            schedule._safe_int(item.get("row_number")),
        ),
    )


def _serialize_lesson_item(item):
    subject = schedule._subject_of(item)
    lesson_id = schedule._clean_text(item.get(schedule.COLUMN_LESSON_ID))
    planned_date = schedule._clean_text(
        item.get("slot_date") or item.get(schedule.COLUMN_DATE)
    )
    planned_period = schedule._clean_text(
        item.get("slot_period") or item.get("planned_period") or item.get("怨꾪쉷援먯떆")
    )
    status = _item_status(item)
    row_number = item.get("_row")
    record_key = lesson_id or item.get("_record_key") or row_number

    payload = dict(item)
    payload.update(
        {
            "subject": subject,
            "lesson_id": lesson_id,
            "record_key": record_key,
            "row_number": row_number,
            "bridge_row": item.get("_bridge_row"),
            "title": schedule._clean_text(item.get(schedule.COLUMN_TITLE)),
            "lesson": schedule._clean_text(item.get(schedule.COLUMN_LESSON)),
            "unit": schedule._clean_text(item.get(schedule.COLUMN_UNIT)),
            "planned_date": planned_date,
            "planned_period": planned_period,
            "pdf_path": schedule._clean_text(item.get(schedule.COLUMN_PDF)),
            "status": status,
            "is_done": status == "done",
        }
    )
    return payload


def _serialize_lessons(items):
    return [_serialize_lesson_item(item) for item in items]


def _build_subject_timeline(records, subjects, bridge_rows, today):
    timeline_items = _sort_serialized_items(
        _serialize_lessons(
            schedule.get_schedule_range(records, bridge_rows=bridge_rows, include_done=True)
        )
    )

    grouped = {}
    for item in timeline_items:
        grouped.setdefault(item["subject"], []).append(item)

    timeline = {}
    for subject in subjects:
        items = _sort_serialized_items(grouped.get(subject, []))
        upcoming = [item for item in items if not item["is_done"]]
        recent_done = [item for item in items if item["is_done"]]
        recent_done = sorted(recent_done, key=lambda item: (_parse_item_date(item) or date.min, str(item.get("planned_period") or "")), reverse=True)

        next_item = None
        future_pending = [item for item in upcoming if (_parse_item_date(item) or today) >= today]
        if future_pending:
            next_item = future_pending[0]
        elif upcoming:
            next_item = upcoming[0]

        timeline[subject] = {
            "subject": subject,
            "next": next_item,
            "upcoming": upcoming[:8],
            "recent": recent_done[:4],
            "items": items,
            "completed_count": len(recent_done),
            "total_count": len(items),
        }

    return timeline


def _dashboard_payload(board_date=None):
    ws = schedule.connect()
    records = schedule.load_all(ws)
    bridge_rows = schedule.load_bridge_rows_for_progress_ws(ws)
    subjects = schedule.get_subjects(records)

    today = date.today()
    board_date = board_date or today
    week_start, week_end = _week_bounds(board_date)
    month_start, month_end = _month_bounds(board_date)
    next_school_day = schedule.get_next_school_day(
        records,
        start_date=today,
        bridge_rows=bridge_rows,
        include_done=True,
    )

    today_items = _serialize_lessons(
        schedule.get_schedule_by_date(records, today, bridge_rows=bridge_rows, include_done=True)
    )
    next_school_day_items = _serialize_lessons(
        schedule.get_schedule_by_date(
            records,
            next_school_day,
            bridge_rows=bridge_rows,
            include_done=True,
        )
    ) if next_school_day else []
    thisweek_items = _serialize_lessons(
        schedule.get_schedule_range(
            records,
            start_date=week_start,
            end_date=week_end,
            bridge_rows=bridge_rows,
            include_done=True,
        )
    )
    thismonth_items = _serialize_lessons(
        schedule.get_schedule_range(
            records,
            start_date=month_start,
            end_date=month_end,
            bridge_rows=bridge_rows,
            include_done=True,
        )
    )
    agenda_items = _serialize_lessons(
        schedule.get_schedule_range(records, bridge_rows=bridge_rows, include_done=False)
    )
    subject_timeline = _build_subject_timeline(records, subjects, bridge_rows, today)

    views = [
        {
            "id": "history",
            "label": "History",
            "title": "Recent Activity",
            "type": "history_feed",
            "data": load_logs(),
        },
        {
            "id": "today",
            "label": "Today",
            "title": f"Today ({today.isoformat()})",
            "type": "lesson_list",
            "date": today.isoformat(),
            "data": today_items,
        },
        {
            "id": "next_school_day",
            "label": "Next School Day",
            "title": (
                f"Next School Day ({next_school_day.isoformat()})"
                if next_school_day
                else "Next School Day"
            ),
            "type": "lesson_list",
            "date": next_school_day.isoformat() if next_school_day else "",
            "data": next_school_day_items,
        },
        {
            "id": "thisweek",
            "label": "This Week",
            "title": f"This Week ({week_start.isoformat()} - {week_end.isoformat()})",
            "type": "lesson_list",
            "board_date": board_date.isoformat(),
            "start_date": week_start.isoformat(),
            "end_date": week_end.isoformat(),
            "data": thisweek_items,
        },
        {
            "id": "thismonth",
            "label": "This Month",
            "title": f"This Month ({month_start.isoformat()} - {month_end.isoformat()})",
            "type": "lesson_list",
            "board_date": board_date.isoformat(),
            "start_date": month_start.isoformat(),
            "end_date": month_end.isoformat(),
            "data": thismonth_items,
        },
        {
            "id": "subject_timeline",
            "label": "Timeline",
            "title": "Subject Schedule Timeline",
            "type": "subject_timeline",
            "data": subject_timeline,
        },
        {
            "id": "agenda",
            "label": "Agenda",
            "title": "Upcoming Lesson Slots",
            "type": "lesson_list",
            "data": agenda_items,
        },
    ]

    return {"views": views, "subjects": subjects, "board_date": board_date.isoformat(), "today": today.isoformat()}


def _action_success(result, status_code=200):
    return jsonify(
        {
            "status": "success",
            "message": result.get("message", ""),
            "result": result,
        }
    ), status_code


def _action_error(message, status_code=400):
    return jsonify({"status": "error", "message": message}), status_code


app = Flask(__name__)
CORS(app)


@app.route("/api/dashboard")
def dashboard():
    board_date_text = request.args.get("board_date")
    board_date = date.fromisoformat(board_date_text) if board_date_text else None
    return jsonify(_dashboard_payload(board_date=board_date))


@app.route("/api/done", methods=["POST"])
def done():
    data = request.json or {}
    subject = data.get("subject")
    target = data.get("target_date")
    record_key = data.get("record_key")
    bridge_row = data.get("bridge_row")
    target_date = date.fromisoformat(target) if target else None

    try:
        ws = schedule.connect()
        records = schedule.load_all(ws)
        result = schedule.mark_done(
            ws,
            records,
            subject,
            target_date,
            record_key=record_key,
            bridge_row_number=bridge_row,
        )
    except ValueError as exc:
        return _action_error(str(exc))

    log_action(
        "lesson_done",
        subject,
        f"target_date={target_date.isoformat()}" if target_date else "next_slot",
    )
    return _action_success(result)


@app.route("/api/push", methods=["POST"])
def push():
    data = request.json or {}
    subject = data.get("subject")
    days = data.get("days", 7)
    target = data.get("from_date")
    from_date = date.fromisoformat(target) if target else None

    try:
        ws = schedule.connect()
        records = schedule.load_all(ws)
        result = schedule.push_schedule(ws, records, subject, days, from_date)
    except ValueError as exc:
        return _action_error(str(exc))

    log_action(
        "push_schedule",
        subject,
        f"days={days}, from_date={from_date.isoformat() if from_date else 'all'}",
    )
    return _action_success(result)


@app.route("/api/extend", methods=["POST"])
def extend():
    data = request.json or {}
    subject = data.get("subject")
    row_number = data.get("row_number")

    try:
        if row_number not in (None, ""):
            row_number = int(row_number)
        else:
            row_number = None
        ws = schedule.connect()
        records = schedule.load_all(ws)
        result = schedule.extend_lesson(ws, records, subject, row_number=row_number)
    except ValueError as exc:
        return _action_error(str(exc))

    log_action("extend_lesson", subject, f"row_number={row_number or 'next'}")
    return _action_success(result)


@app.route("/api/pull", methods=["POST"])
def pull():
    data = request.json or {}
    bridge_row = data.get("bridge_row")
    subject = data.get("subject", "")

    try:
        ws = schedule.connect()
        records = schedule.load_all(ws)
        result = schedule.pull_bridge_slot(ws, records, bridge_row)
    except ValueError as exc:
        return _action_error(str(exc))

    log_action("pull_subject_flow", subject, f"bridge_row={bridge_row}")
    return _action_success(result)


@app.route("/api/move", methods=["POST"])
def move():
    data = request.json or {}
    bridge_row = data.get("bridge_row")
    direction = data.get("direction")
    subject = data.get("subject", "")

    try:
        ws = schedule.connect()
        records = schedule.load_all(ws)
        result = schedule.move_bridge_slot(ws, records, bridge_row, direction)
    except ValueError as exc:
        return _action_error(str(exc))

    log_action("move_slot", subject, f"bridge_row={bridge_row}, direction={direction}")
    return _action_success(result)


@app.route("/api/swap", methods=["POST"])
def swap():
    data = request.json or {}
    first_bridge_row = data.get("first_bridge_row")
    second_bridge_row = data.get("second_bridge_row")
    subject = data.get("subject", "")

    try:
        ws = schedule.connect()
        records = schedule.load_all(ws)
        result = schedule.swap_bridge_slots(ws, records, first_bridge_row, second_bridge_row)
    except ValueError as exc:
        return _action_error(str(exc))

    log_action(
        "swap_slots",
        subject,
        f"first_bridge_row={first_bridge_row}, second_bridge_row={second_bridge_row}",
    )
    return _action_success(result)


@app.route("/api/pdf/<record_key>")
def serve_pdf_fragment(record_key):
    ws = schedule.connect()
    records = schedule.load_all(ws)
    record = schedule.find_record_by_key(records, record_key)

    if not record:
        return "Record not found", 404

    raw_pdf_path = schedule._clean_text(record.get(schedule.COLUMN_PDF, ""))
    pdf_path = os.path.expandvars(os.path.expanduser(raw_pdf_path))
    start_str = record.get(schedule.COLUMN_START_PAGE, "")
    end_str = record.get(schedule.COLUMN_END_PAGE, "")

    if not pdf_path or not os.path.exists(pdf_path):
        return f"PDF not found: {pdf_path}", 404

    download_name = _pdf_download_name(record)

    if _is_pre_split_pdf(pdf_path):
        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=False,
            download_name=download_name,
        )

    try:
        start_page = int(str(start_str).strip())
        end_page = int(str(end_str).strip()) if str(end_str).strip() else start_page
    except ValueError:
        return "Invalid PDF page range", 400

    doc = fitz.open(pdf_path)
    start_index = max(0, start_page - 1)
    end_index = min(len(doc) - 1, end_page - 1)
    if end_index < start_index:
        doc.close()
        return "Invalid PDF page range", 400

    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=start_index, to_page=end_index)
    pdf_bytes = new_doc.write()
    new_doc.close()
    doc.close()

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=download_name,
    )


if __name__ == "__main__":
    app.run(port=5000, debug=True)
