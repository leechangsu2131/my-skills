"""
Step 1: Google Sheets → JSON 파일 저장 (네트워크 불필요)
"""
import json, os, sys

SCHEDULE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "my-skills", "skills", "teacher-schedule"
)
sys.path.insert(0, os.path.abspath(SCHEDULE_DIR))

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **k): pass

load_dotenv(os.path.join(SCHEDULE_DIR, ".env"))

SUBJECT_COLORS = {
    "국어": "#005bbf", "수학": "#e85d04", "사회": "#6a994e",
    "과학": "#9b5de5", "도덕": "#f4a261", "음악": "#e76f51",
    "미술": "#2a9d8f", "체육": "#264653", "영어": "#d62828", "실과": "#606c38",
}

def _safe_int(val, default=None):
    if val in (None, ""): return default
    try: return int(str(val).strip())
    except: return default

def _is_done(val):
    return str(val).strip().upper() in ("TRUE", "1", "Y", "YES", "DONE")

def save_json(data, filename):
    out = os.path.join(os.path.dirname(__file__), "migrated_data")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"   💾 {filename} ({len(data)}개)")
    return path

if __name__ == "__main__":
    print("=" * 55)
    print("📥 Step 1: Google Sheets → JSON 파일 저장")
    print("=" * 55)

    import schedule
    schedule.validate_config()
    ws = schedule.connect()
    records = schedule.load_all(ws)
    bridge_rows = schedule.load_bridge_rows_for_progress_ws(ws)
    subjects = schedule.get_subjects(records)
    print(f"✅ 진도표 {len(records)}개 행, 과목: {', '.join(subjects)}")
    if bridge_rows:
        print(f"   수업배치(bridge): {len(bridge_rows)}개 슬롯")

    # subjects
    subject_rows = [
        {"name": name, "color": SUBJECT_COLORS.get(name, "#888"), "sort_order": i}
        for i, name in enumerate(subjects, 1)
    ]
    save_json(subject_rows, "subjects.json")

    # units
    unit_set = {}
    for rec in records:
        subj = (rec.get("과목") or "").strip()
        unit = (rec.get("대단원") or "").strip()
        if subj and unit:
            key = (subj, unit)
            if key not in unit_set:
                unit_set[key] = len(unit_set)
    unit_rows = [{"subject_name": s, "name": u, "sort_order": i} for (s, u), i in unit_set.items()]
    save_json(unit_rows, "units.json")

    # lessons
    lesson_rows = []
    for rec in records:
        subj = (rec.get("과목") or "").strip()
        if not subj: continue
        lesson_rows.append({
            "legacy_lesson_id": (rec.get("lesson_id") or "").strip() or None,
            "subject_name": subj,
            "unit_name": (rec.get("대단원") or "").strip() or None,
            "lesson_number": _safe_int(rec.get("차시")),
            "title": (rec.get("수업내용") or "").strip() or None,
            "pdf_path": (rec.get("pdf파일") or "").strip() or None,
            "start_page": _safe_int(rec.get("시작페이지")),
            "end_page": _safe_int(rec.get("끝페이지")),
            "note": (rec.get("비고") or "").strip() or None,
            "extension_count": _safe_int(rec.get("연장횟수"), 0),
            "sort_order": rec.get("_row", 0),
            "planned_date": (rec.get("계획일") or "").strip() or None,
            "planned_period": _safe_int(rec.get("계획교시")),
            "is_done": _is_done(rec.get("실행여부", "")),
        })
    save_json(lesson_rows, "lessons.json")

    # slots
    slot_rows = []
    if bridge_rows:
        for br in bridge_rows:
            slot_date = (br.get("slot_date") or "").strip() or None
            if not slot_date: continue
            slot_rows.append({
                "legacy_lesson_id": (br.get("lesson_id") or "").strip(),
                "slot_date": slot_date,
                "slot_period": _safe_int(br.get("slot_period")),
                "slot_order": _safe_int(br.get("slot_order"), 1),
                "status": (br.get("status") or "planned").lower(),
                "source": (br.get("source") or "migrated").strip(),
                "memo": (br.get("memo") or "").strip() or None,
            })
    else:
        for lesson in lesson_rows:
            if not lesson["planned_date"]: continue
            slot_rows.append({
                "legacy_lesson_id": lesson["legacy_lesson_id"],
                "slot_date": lesson["planned_date"],
                "slot_period": lesson["planned_period"],
                "slot_order": 1,
                "status": "done" if lesson["is_done"] else "planned",
                "source": "migrated",
                "memo": None,
            })
    save_json(slot_rows, "lesson_slots.json")

    print(f"\n✅ 완료! scripts/migrated_data/ 에 저장되었습니다.")
    print("   다음: node scripts/upload_to_supabase.mjs")
