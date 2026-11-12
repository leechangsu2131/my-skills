from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, request, send_from_directory


ROOT = Path(__file__).resolve().parent
MAX_RECORDS_PER_IMPORT = 1200
MAX_TEXT_LENGTH = 2000
LESSONS: dict[tuple[str, str, str], dict] = {}
STATE = {"last_imported_at": None, "range_start": None, "range_end": None, "source": None}
STORE_LOCK = Lock()

app = Flask(__name__, static_folder=str(ROOT / "web"), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024


def _is_loopback():
    return request.remote_addr in {"127.0.0.1", "::1"}


def _allowed_origin(origin: str | None) -> bool:
    if not origin:
        return True
    return origin in {"http://127.0.0.1:5101", "http://localhost:5101"} or origin.startswith(
        "chrome-extension://"
    )


@app.after_request
def add_local_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin and _allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Max-Age"] = "600"
    return response


def _text(value, limit=MAX_TEXT_LENGTH):
    if value is None:
        return ""
    return str(value).strip()[:limit]


def _iso_date(value):
    raw = _text(value, 32)
    if len(raw) != 10:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return None


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/status")
def status():
    with STORE_LOCK:
        return jsonify(
            {
                "count": len(LESSONS),
                "last_imported_at": STATE["last_imported_at"],
                "range_start": STATE["range_start"],
                "range_end": STATE["range_end"],
                "source": STATE["source"],
            }
        )


@app.get("/api/lessons")
def get_lessons():
    start = _iso_date(request.args.get("start_date"))
    end = _iso_date(request.args.get("end_date"))
    if not start or not end or start > end:
        return jsonify({"error": "날짜 범위를 확인해 주세요."}), 400

    with STORE_LOCK:
        records = [
            record
            for record in LESSONS.values()
            if start <= record["date"] <= end
        ]
    records.sort(key=lambda row: (row["date"], int(row["period"] or 0), row["subject"]))
    return jsonify({"records": records, "range_start": start, "range_end": end})


@app.route("/api/import", methods=["POST", "OPTIONS"])
def import_lessons():
    if request.method == "OPTIONS":
        return "", 204
    if not _is_loopback():
        return jsonify({"error": "로컬 컴퓨터에서만 가져올 수 있습니다."}), 403
    if not _allowed_origin(request.headers.get("Origin")):
        return jsonify({"error": "허용되지 않은 요청 출처입니다."}), 403

    payload = request.get_json(silent=True) or {}
    start = _iso_date(payload.get("range_start"))
    end = _iso_date(payload.get("range_end"))
    rows = payload.get("records")
    if not start or not end or start > end or not isinstance(rows, list):
        return jsonify({"error": "가져온 날짜 범위 또는 수업 목록이 올바르지 않습니다."}), 400
    if len(rows) > MAX_RECORDS_PER_IMPORT:
        return jsonify({"error": "가져온 수업이 너무 많습니다."}), 413

    normalized = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        lesson_date = _iso_date(row.get("date"))
        period = _text(row.get("period"), 3)
        subject = _text(row.get("subject"), 100)
        if not lesson_date or not start <= lesson_date <= end or not period.isdigit():
            continue
        if not subject:
            continue
        record = {
            "date": lesson_date,
            "period": str(int(period)),
            "subject": subject,
            "unit": _text(row.get("unit"), 300),
            "content": _text(row.get("content")),
            "lesson_number": _text(row.get("lessonNumber"), 20),
            "total_lessons": _text(row.get("totalLessons"), 20),
            "textbook_page": _text(row.get("textbookPage"), 100),
            "additional_page": _text(row.get("additionalPage"), 100),
        }
        key = (record["date"], record["period"], record["subject"])
        normalized[key] = record

    with STORE_LOCK:
        old_keys = [key for key, row in LESSONS.items() if start <= row["date"] <= end]
        for key in old_keys:
            LESSONS.pop(key, None)
        LESSONS.update(normalized)
        STATE.update(
            {
                "last_imported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "range_start": start,
                "range_end": end,
                "source": _text(payload.get("source"), 40) or "NEIS 주간학습안내",
            }
        )
    return jsonify({"ok": True, "imported": len(normalized), "range_start": start, "range_end": end})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5101, debug=False, use_reloader=False)
