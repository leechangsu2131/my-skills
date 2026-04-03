import json
import os
from datetime import date, datetime, timedelta
from io import BytesIO

import fitz
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

import schedule


LOG_FILE = "activity_log.json"


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


def build_unit_progress(records, subjects):
    unit_progress_data = {}
    for subject in subjects:
        subject_records = [record for record in records if schedule._subject_of(record) == subject]
        units = {}
        for record in subject_records:
            unit_name = schedule._clean_text(record.get(schedule.COLUMN_UNIT)) or "Other lessons"
            bucket = units.setdefault(unit_name, {"total": 0, "completed": 0, "lessons": []})
            is_done = schedule._is_done(record)
            bucket["total"] += 1
            if is_done:
                bucket["completed"] += 1
            bucket["lessons"].append(
                {
                    "lesson_id": record.get(schedule.COLUMN_LESSON_ID, ""),
                    schedule.COLUMN_LESSON: record.get(schedule.COLUMN_LESSON, ""),
                    schedule.COLUMN_TITLE: record.get(schedule.COLUMN_TITLE, ""),
                    schedule.COLUMN_DONE: is_done,
                    schedule.COLUMN_DATE: record.get(schedule.COLUMN_DATE, ""),
                    schedule.COLUMN_PDF: record.get(schedule.COLUMN_PDF, ""),
                    schedule.COLUMN_START_PAGE: record.get(schedule.COLUMN_START_PAGE, ""),
                    "_row": record.get("_row"),
                }
            )

        unit_progress_data[subject] = [
            {
                "name": unit_name,
                "total": payload["total"],
                "completed": payload["completed"],
                "percentage": round(payload["completed"] / payload["total"] * 100) if payload["total"] else 0,
                "lessons": payload["lessons"],
            }
            for unit_name, payload in units.items()
        ]
    return unit_progress_data


app = Flask(__name__)
CORS(app)


@app.route("/api/dashboard")
def dashboard():
    ws = schedule.connect()
    records = schedule.load_all(ws)
    bridge_rows = schedule.load_bridge_rows_for_progress_ws(ws)
    subjects = schedule.get_subjects(records)

    today = date.today()
    tomorrow = today + timedelta(days=1)

    views = []
    views.append(
        {
            "id": "history",
            "label": "History",
            "title": "Recent Activity",
            "type": "history_feed",
            "data": load_logs(),
        }
    )

    today_lessons = schedule.get_schedule_by_date(records, today, bridge_rows=bridge_rows)
    views.append(
        {
            "id": "today",
            "label": "Today",
            "title": f"Today ({today.strftime('%Y-%m-%d')})",
            "type": "lesson_list",
            "data": today_lessons,
        }
    )

    tomorrow_lessons = schedule.get_schedule_by_date(records, tomorrow, bridge_rows=bridge_rows)
    views.append(
        {
            "id": "tomorrow",
            "label": "Tomorrow",
            "title": f"Tomorrow ({tomorrow.strftime('%Y-%m-%d')})",
            "type": "lesson_list",
            "data": tomorrow_lessons,
        }
    )

    next_monday = today + timedelta(days=(7 - today.weekday()))
    nextweek_lessons = []
    for offset in range(5):
        target_date = next_monday + timedelta(days=offset)
        nextweek_lessons.extend(
            schedule.get_schedule_by_date(records, target_date, bridge_rows=bridge_rows)
        )
    views.append(
        {
            "id": "nextweek",
            "label": "Next Week",
            "title": "Next Week Lessons",
            "type": "lesson_list",
            "data": nextweek_lessons,
        }
    )

    next_classes = {}
    for subject in subjects:
        subject_records = [record for record in records if schedule._subject_of(record) == subject]
        done_records = [record for record in subject_records if schedule._is_done(record)]
        recent = done_records[-1] if done_records else None
        next_class = schedule.get_next_class(records, subject, bridge_rows=bridge_rows)
        if next_class or recent:
            next_classes[subject] = {"next": next_class, "recent": recent}
    views.append(
        {
            "id": "next",
            "label": "Next",
            "title": "Recent Completion And Next Lesson",
            "type": "next_class_grid",
            "data": next_classes,
        }
    )

    progress_data = {subject: schedule.get_progress(records, subject) for subject in subjects}
    views.append(
        {
            "id": "progress",
            "label": "Progress",
            "title": "Subject Progress",
            "type": "progress_list",
            "data": progress_data,
        }
    )

    views.append(
        {
            "id": "unit_progress",
            "label": "Units",
            "title": "Unit Progress",
            "type": "unit_progress",
            "data": build_unit_progress(records, subjects),
        }
    )

    views.append(
        {
            "id": "push",
            "label": "Push",
            "title": "Shift Subject Schedule",
            "type": "push_action",
            "data": None,
        }
    )
    views.append(
        {
            "id": "extend",
            "label": "Extend",
            "title": "Extend Current Lesson",
            "type": "extend_action",
            "data": None,
        }
    )

    return jsonify({"views": views, "subjects": subjects})


@app.route("/api/done", methods=["POST"])
def done():
    data = request.json or {}
    subject = data.get("subject")
    target = data.get("target_date")
    record_key = data.get("record_key")
    bridge_row = data.get("bridge_row")
    target_date = date.fromisoformat(target) if target else None

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
    log_action(
        "lesson_done",
        subject,
        f"target_date={target_date.strftime('%Y-%m-%d')}" if target_date else "next_slot",
    )
    return jsonify({"status": "success", "message": result.get("message", ""), "result": result})


@app.route("/api/push", methods=["POST"])
def push():
    data = request.json or {}
    subject = data.get("subject")
    days = data.get("days", 7)
    target = data.get("from_date")
    from_date = date.fromisoformat(target) if target else None

    ws = schedule.connect()
    records = schedule.load_all(ws)
    result = schedule.push_schedule(ws, records, subject, days, from_date)
    log_action(
        "push_schedule",
        subject,
        f"days={days}, from_date={from_date.strftime('%Y-%m-%d') if from_date else 'all'}",
    )
    return jsonify({"status": "success", "message": result.get("message", ""), "result": result})


@app.route("/api/extend", methods=["POST"])
def extend():
    data = request.json or {}
    subject = data.get("subject")

    ws = schedule.connect()
    records = schedule.load_all(ws)
    result = schedule.extend_lesson(ws, records, subject)
    log_action("extend_lesson", subject, "manual extend")
    return jsonify({"status": "success", "message": result.get("message", ""), "result": result})


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

    try:
        start_page = int(str(start_str).strip())
        end_page = int(str(end_str).strip()) if str(end_str).strip() else start_page
    except ValueError:
        return "Invalid PDF page range", 400

    doc = fitz.open(pdf_path)
    start_index = max(0, start_page - 1)
    end_index = min(len(doc) - 1, end_page - 1)
    if end_index < start_index:
        start_index, end_index = end_index, start_index

    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=start_index, to_page=end_index)
    pdf_bytes = new_doc.write()
    new_doc.close()
    doc.close()

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=(
            f"{record.get(schedule.COLUMN_SUBJECT, 'lesson')}_"
            f"{record.get(schedule.COLUMN_LESSON, 'fragment')}.pdf"
        ),
    )


if __name__ == "__main__":
    app.run(port=5000, debug=True)
