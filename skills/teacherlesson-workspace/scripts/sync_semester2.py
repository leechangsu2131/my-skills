"""Sync semester-two progress from the schedule sheet into Teacher Workspace Supabase.

The first-semester import populated lesson_lessons and lesson_slots. This script
adds missing lesson rows, refreshes lessons referenced by semester-two slots,
and adds or updates only slots on/after the semester start date. It is safe to
run again; existing rows are matched by legacy_lesson_id and slot identity.

    python sync_semester2.py --dry-run
    python sync_semester2.py --apply
    python sync_semester2.py --start-date 2026-08-01 --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

import requests
import truststore

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SHARED = REPO / "skills" / "_shared"
sys.path.insert(0, str(SHARED))
from skill_env import load_env  # noqa: E402

SCHEDULE_DIR = REPO / "skills" / "teacherlesson-schedule"
sys.path.insert(0, str(SCHEDULE_DIR))

SUBJECT_TABLE = "lesson_subjects"
UNIT_TABLE = "lesson_units"
LESSON_TABLE = "lesson_lessons"
SLOT_TABLE = "lesson_slots"

LESSON_FIELDS = (
    "legacy_lesson_id", "subject_id", "unit_id", "lesson_number", "title",
    "pdf_path", "start_page", "end_page", "note", "extension_count", "sort_order",
)


def safe_int(value, default=None):
    if value in (None, ""):
        return default
    text = str(value).strip()
    try:
        return int(text)
    except (TypeError, ValueError):
        pass
    try:
        # 시트·슈파베이스가 12.0 처럼 소수 꼴로 줄 때. 먼저 int 로 읽어 큰 정수는 그대로 둔다.
        return int(float(text))
    except (TypeError, ValueError, OverflowError):
        return default


def clean(value):
    return str(value or "").strip()


def make_client():
    load_env()
    url = (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key:
        missing = []
        if not url:
            missing.append("SUPABASE_URL 또는 NEXT_PUBLIC_SUPABASE_URL")
        if not key:
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        raise RuntimeError("중앙 .env에 설정이 필요합니다: " + ", ".join(missing))

    # Use Windows' trusted certificate store; do not disable TLS verification.
    truststore.inject_into_ssl()
    session = requests.Session()
    session.headers.update({
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    return url, session


class Supabase:
    def __init__(self, url, session):
        self.url = url
        self.session = session

    def get_all(self, table, select="*"):
        rows = []
        offset = 0
        while True:
            response = self.session.get(
                f"{self.url}/rest/v1/{table}",
                params={"select": select, "limit": 1000, "offset": offset},
                timeout=45,
            )
            self.check(response, table)
            batch = response.json()
            rows.extend(batch)
            if len(batch) < 1000:
                return rows
            offset += len(batch)

    @staticmethod
    def check(response, label):
        if not response.ok:
            raise RuntimeError(f"Supabase {label}: HTTP {response.status_code}: {response.text[:500]}")

    def post(self, table, rows):
        if not rows:
            return []
        result = []
        for offset in range(0, len(rows), 200):
            response = self.session.post(
                f"{self.url}/rest/v1/{table}",
                params={"select": "*"},
                headers={"Prefer": "return=representation"},
                json=rows[offset:offset + 200],
                timeout=60,
            )
            self.check(response, f"insert {table}")
            result.extend(response.json())
        return result

    def patch(self, table, row_id, values):
        response = self.session.patch(
            f"{self.url}/rest/v1/{table}",
            params={"id": f"eq.{row_id}", "select": "id"},
            headers={"Prefer": "return=representation"},
            json=values,
            timeout=45,
        )
        self.check(response, f"update {table}")
        return response.json()


def load_source(start_date: date):
    import schedule

    schedule.validate_config()
    ws = schedule.connect()
    records = schedule.load_all(ws)
    bridge_rows = schedule.load_bridge_rows_for_progress_ws(ws)
    by_legacy_id = {}
    for row in records:
        legacy_id = clean(row.get("lesson_id"))
        if not legacy_id:
            continue
        if legacy_id in by_legacy_id:
            raise ValueError(f"진도표 lesson_id 중복: {legacy_id}")
        by_legacy_id[legacy_id] = row

    semester_slots = []
    for slot in bridge_rows:
        slot_date = clean(slot.get("slot_date"))
        if not slot_date:
            continue
        try:
            parsed_date = date.fromisoformat(slot_date)
        except ValueError:
            continue
        if parsed_date >= start_date:
            semester_slots.append(slot)

    missing_lesson_refs = sorted({clean(s.get("lesson_id")) for s in semester_slots} - by_legacy_id.keys())
    if missing_lesson_refs:
        raise ValueError("2학기 슬롯에서 진도표 행을 찾을 수 없음: " + ", ".join(missing_lesson_refs))
    return by_legacy_id, semester_slots


def make_slot_key(legacy_id, slot):
    return (
        legacy_id,
        clean(slot.get("slot_date")),
        safe_int(slot.get("slot_period")),
        safe_int(slot.get("slot_order"), 1),
    )


def main():
    parser = argparse.ArgumentParser(description="진도표의 2학기 진도를 Supabase에 동기화")
    parser.add_argument("--start-date", default="2026-08-01", help="2학기 슬롯 시작일 (기본: 2026-08-01)")
    parser.add_argument("--apply", action="store_true", help="Supabase에 실제 반영 (기본은 읽기 전용 미리보기)")
    parser.add_argument("--dry-run", action="store_true", help="읽기 전용 미리보기")
    args = parser.parse_args()
    start_date = date.fromisoformat(args.start_date)

    by_legacy_id, semester_slots = load_source(start_date)
    url, session = make_client()
    sb = Supabase(url, session)

    subjects = sb.get_all(SUBJECT_TABLE, "id,name,color,sort_order")
    units = sb.get_all(UNIT_TABLE, "id,subject_id,name,sort_order")
    lessons = sb.get_all(LESSON_TABLE, "id,legacy_lesson_id," + ",".join(LESSON_FIELDS[1:]))
    slots = sb.get_all(SLOT_TABLE, "id,lesson_id,slot_date,slot_period,slot_order,status,source,memo")

    subject_map = {clean(s["name"]): s["id"] for s in subjects}
    for subject_name in sorted({clean(r.get("과목")) for r in by_legacy_id.values()} - subject_map.keys()):
        raise ValueError(f"Supabase 과목 테이블에 과목이 없습니다: {subject_name}")

    lesson_by_legacy = {clean(l.get("legacy_lesson_id")): l for l in lessons if clean(l.get("legacy_lesson_id"))}
    existing_unit_keys = {(u.get("subject_id"), clean(u.get("name"))) for u in units}
    selected_ids = set()
    # Include all new lesson rows since the first-semester import and every
    # existing lesson that has a second-semester slot (reused lessons included).
    selected_ids.update(set(by_legacy_id) - set(lesson_by_legacy))
    selected_ids.update(clean(s.get("lesson_id")) for s in semester_slots)
    selected_rows = [by_legacy_id[lid] for lid in sorted(selected_ids)]

    needed_units = {}
    for row in selected_rows:
        subject_name = clean(row.get("과목"))
        unit_name = clean(row.get("대단원"))
        if unit_name:
            key = (subject_map[subject_name], unit_name)
            if key not in existing_unit_keys:
                needed_units.setdefault(key, len(needed_units))

    slot_by_lesson_id = {l["id"]: clean(l.get("legacy_lesson_id")) for l in lessons}
    existing_slot_keys = {
        (
            slot_by_lesson_id.get(s.get("lesson_id"), ""),
            clean(s.get("slot_date")),
            safe_int(s.get("slot_period")),
            safe_int(s.get("slot_order"), 1),
        ): s
        for s in slots
    }
    slot_keys_seen = set()
    slot_inserts = []
    slot_updates = []
    for slot in semester_slots:
        legacy_id = clean(slot.get("lesson_id"))
        key = make_slot_key(legacy_id, slot)
        if key in slot_keys_seen:
            raise ValueError(f"2학기 슬롯 키 중복: {key}")
        slot_keys_seen.add(key)
        status = clean(slot.get("status")).lower()
        if status not in {"done", "planned"}:
            status = "planned"
        values = {
            "slot_date": key[1],
            "slot_period": key[2],
            "slot_order": key[3],
            "status": status,
            "source": clean(slot.get("source")) or "migrated",
            "memo": clean(slot.get("memo")) or None,
        }
        current = existing_slot_keys.get(key)
        if current is None:
            slot_inserts.append((legacy_id, values))
        elif any(current.get(k) != v for k, v in values.items()):
            slot_updates.append((current["id"], values))

    missing_lessons = [lid for lid in selected_ids if lid not in lesson_by_legacy]
    changed_lessons = []
    for row in selected_rows:
        legacy_id = clean(row.get("lesson_id"))
        current = lesson_by_legacy.get(legacy_id)
        if current is None:
            continue
        subject_id = subject_map[clean(row.get("과목"))]
        unit_name = clean(row.get("대단원"))
        unit = next((u for u in units if u.get("subject_id") == subject_id and clean(u.get("name")) == unit_name), None)
        values = lesson_payload(row, subject_id, unit.get("id") if unit else None)
        if any(current.get(k) != v for k, v in values.items()):
            changed_lessons.append((current["id"], values))

    print(f"2학기 시작일: {start_date.isoformat()}")
    print(f"진도표 행 전체: {len(by_legacy_id)}")
    print(f"Supabase 미등록 차시: {len(missing_lessons)}")
    print(f"2학기 슬롯: {len(semester_slots)} (신규 {len(slot_inserts)}, 갱신 {len(slot_updates)})")
    print(f"필요한 단원 추가: {len(needed_units)}")
    print(f"기존 차시 정보 갱신: {len(changed_lessons)}")
    if not args.apply or args.dry_run:
        print("미리보기만 실행했습니다. 실제 반영은 --apply 옵션이 필요합니다.")
        return

    # Add missing units, then refresh the unit map from returned rows.
    new_unit_rows = [
        {"subject_id": subject_id, "name": name, "sort_order": sort_order}
        for (subject_id, name), sort_order in needed_units.items()
    ]
    new_units = sb.post(UNIT_TABLE, new_unit_rows)
    units.extend(new_units)
    unit_map = {(u.get("subject_id"), clean(u.get("name"))): u["id"] for u in units}

    lesson_payloads = []
    for row in selected_rows:
        legacy_id = clean(row.get("lesson_id"))
        subject_id = subject_map[clean(row.get("과목"))]
        unit_name = clean(row.get("대단원"))
        unit_id = unit_map.get((subject_id, unit_name)) if unit_name else None
        values = lesson_payload(row, subject_id, unit_id)
        current = lesson_by_legacy.get(legacy_id)
        if current is None:
            lesson_payloads.append(values)
        elif any(current.get(k) != v for k, v in values.items()):
            sb.patch(LESSON_TABLE, current["id"], values)

    inserted_lessons = sb.post(LESSON_TABLE, lesson_payloads)
    lessons.extend(inserted_lessons)
    lesson_id_map = {clean(l.get("legacy_lesson_id")): l["id"] for l in lessons if clean(l.get("legacy_lesson_id"))}

    for row_id, values in slot_updates:
        sb.patch(SLOT_TABLE, row_id, values)
    new_slot_rows = []
    for legacy_id, values in slot_inserts:
        lesson_id = lesson_id_map.get(legacy_id)
        if not lesson_id:
            raise RuntimeError(f"Supabase 차시 ID를 찾을 수 없습니다: {legacy_id}")
        new_slot_rows.append({"lesson_id": lesson_id, **values})
    inserted_slots = sb.post(SLOT_TABLE, new_slot_rows)

    # Verify every 2nd-semester slot and every selected lesson now exists.
    verified_lessons = {clean(l.get("legacy_lesson_id")) for l in sb.get_all(LESSON_TABLE, "legacy_lesson_id")}
    if not selected_ids.issubset(verified_lessons):
        raise RuntimeError("반영 후 Supabase에서 일부 차시를 찾을 수 없습니다.")
    verified_lesson_rows = sb.get_all(LESSON_TABLE, "id,legacy_lesson_id")
    verified_legacy_by_id = {l["id"]: clean(l.get("legacy_lesson_id")) for l in verified_lesson_rows}
    verified_slot_rows = sb.get_all(SLOT_TABLE, "lesson_id,slot_date,slot_period,slot_order")
    verified_slot_keys = {
        (
            verified_legacy_by_id.get(s.get("lesson_id"), ""),
            clean(s.get("slot_date")),
            safe_int(s.get("slot_period")),
            safe_int(s.get("slot_order"), 1),
        )
        for s in verified_slot_rows
    }
    expected_slot_keys = {make_slot_key(clean(s.get("lesson_id")), s) for s in semester_slots}
    if not expected_slot_keys.issubset(verified_slot_keys):
        raise RuntimeError("반영 후 Supabase에서 일부 2학기 슬롯을 찾을 수 없습니다.")
    print(f"반영 완료: 신규 차시 {len(inserted_lessons)}, 신규 단원 {len(new_units)}, 신규 슬롯 {len(inserted_slots)}")
    print(f"Supabase 재조회로 차시 {len(selected_ids)}개와 2학기 슬롯 {len(expected_slot_keys)}개 연결을 확인했습니다.")


def lesson_payload(row, subject_id, unit_id):
    return {
        "legacy_lesson_id": clean(row.get("lesson_id")) or None,
        "subject_id": subject_id,
        "unit_id": unit_id,
        "lesson_number": safe_int(row.get("차시")),
        "title": clean(row.get("수업내용")) or None,
        "pdf_path": clean(row.get("pdf파일")) or None,
        "start_page": safe_int(row.get("시작페이지")),
        "end_page": safe_int(row.get("끝페이지")),
        "note": clean(row.get("비고")) or None,
        "extension_count": safe_int(row.get("연장횟수"), 0),
        "sort_order": safe_int(row.get("_row"), 0),
    }


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        sys.exit(1)
