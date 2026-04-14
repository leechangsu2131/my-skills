"""
migrate_from_sheets.py — v2
Google Sheets 진도표 → Supabase REST API 직접 호출 방식 (SSL 호환)
"""

import json
import os
import sys
import ssl
import urllib.request
import urllib.parse

# teacher-schedule 경로 추가
SCHEDULE_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "my-skills",
    "skills",
    "teacher-schedule",
)
sys.path.insert(0, os.path.abspath(SCHEDULE_DIR))

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **k): pass

# .env 로드
env_path = os.path.join(SCHEDULE_DIR, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

local_env = os.path.join(os.path.dirname(__file__), "..", ".env.local")
if os.path.exists(local_env):
    load_dotenv(local_env, override=True)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

# SSL 컨텍스트 (Windows 인증서 문제 우회)
SSL_CTX = ssl.create_default_context()
try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX.check_hostname = False
    SSL_CTX.verify_mode = ssl.CERT_NONE


def supabase_post(table, rows):
    """Supabase REST API에 행 삽입"""
    if not rows:
        return []
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(rows).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "return=representation",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
        return json.loads(resp.read())


def supabase_get(table, select="*"):
    """Supabase REST API에서 행 조회"""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
        return json.loads(resp.read())


# ---- Google Sheets 데이터 로드 ----
def load_from_sheets():
    import schedule
    schedule.validate_config()
    ws = schedule.connect()
    records = schedule.load_all(ws)
    bridge_rows = schedule.load_bridge_rows_for_progress_ws(ws)
    subjects = schedule.get_subjects(records)
    print(f"✅ 진도표 {len(records)}개 행 로드")
    print(f"   과목: {', '.join(subjects)}")
    if bridge_rows:
        print(f"   수업배치(bridge): {len(bridge_rows)}개 슬롯")
    else:
        print("   수업배치(bridge): 없음 (계획일로 슬롯 생성)")
    return records, bridge_rows, subjects


def _safe_int(val, default=None):
    if val in (None, ""): return default
    try: return int(str(val).strip())
    except: return default


def _is_done(val):
    return str(val).strip().upper() in ("TRUE", "1", "Y", "YES", "DONE")


SUBJECT_COLORS = {
    "국어": "#005bbf", "수학": "#e85d04", "사회": "#6a994e",
    "과학": "#9b5de5", "도덕": "#f4a261", "음악": "#e76f51",
    "미술": "#2a9d8f", "체육": "#264653", "영어": "#d62828", "실과": "#606c38",
}


def save_json(data, filename):
    out = os.path.join(os.path.dirname(__file__), "migrated_data")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"   💾 {path}")
    return path


if __name__ == "__main__":
    print("=" * 55)
    print("📚 Teacher Workspace — Google Sheets → Supabase 이관")
    print("=" * 55)

    if "your-project" in SUPABASE_URL or not SUPABASE_URL:
        print("❌ SUPABASE_URL이 설정되지 않았습니다.")
        sys.exit(1)
    print(f"🔗 Supabase: {SUPABASE_URL}")

    # 1. Google Sheets 로드
    try:
        records, bridge_rows, subjects = load_from_sheets()
    except Exception as e:
        print(f"\n❌ Google Sheets 연결 실패: {e}")
        sys.exit(1)

    # 2. 과목 업로드
    print("\n📤 과목(subjects) 업로드 중...")
    subject_rows = [
        {"name": name, "color": SUBJECT_COLORS.get(name, "#888888"), "sort_order": i}
        for i, name in enumerate(subjects, 1)
    ]
    save_json(subject_rows, "subjects.json")
    try:
        result = supabase_post("subjects", subject_rows)
        subject_map = {r["name"]: r["id"] for r in result}
        print(f"   ✅ {len(result)}개 업로드 완료")
    except Exception as e:
        # 이미 있는 경우 GET으로 가져옴
        print(f"   ⚠️  INSERT 실패 ({e}) → 기존 데이터 조회")
        existing = supabase_get("subjects", "id,name")
        subject_map = {r["name"]: r["id"] for r in existing}
        print(f"   ℹ️  기존 {len(subject_map)}개 과목 사용")

    # 3. 단원(units) 수집
    unit_set = {}  # (subject_name, unit_name) → index
    for rec in records:
        subj = (rec.get("과목") or "").strip()
        unit = (rec.get("대단원") or "").strip()
        if subj and unit:
            key = (subj, unit)
            if key not in unit_set:
                unit_set[key] = len(unit_set)

    unit_rows = [
        {
            "subject_id": subject_map.get(subj),
            "name": unit,
            "sort_order": idx,
        }
        for (subj, unit), idx in unit_set.items()
        if subject_map.get(subj)
    ]
    save_json(unit_rows, "units.json")
    if unit_rows:
        print(f"\n📤 단원(units) {len(unit_rows)}개 업로드 중...")
        try:
            unit_result = supabase_post("units", unit_rows)
            # unit_map: (subject_id, unit_name) → unit_id
            unit_map = {(r["subject_id"], r["name"]): r["id"] for r in unit_result}
            print(f"   ✅ {len(unit_result)}개 완료")
        except Exception as e:
            print(f"   ⚠️  단원 업로드 실패: {e}")
            unit_map = {}
    else:
        unit_map = {}

    # 4. 수업/차시(lessons) 업로드
    print(f"\n📤 수업(lessons) {len(records)}개 업로드 중...")
    lesson_rows = []
    for rec in records:
        subj = (rec.get("과목") or "").strip()
        unit_name = (rec.get("대단원") or "").strip()
        subj_id = subject_map.get(subj)
        if not subj_id:
            continue
        unit_id = unit_map.get((subj_id, unit_name)) if unit_name else None
        lesson_rows.append({
            "legacy_lesson_id": (rec.get("lesson_id") or "").strip() or None,
            "subject_id": subj_id,
            "unit_id": unit_id,
            "lesson_number": _safe_int(rec.get("차시")),
            "title": (rec.get("수업내용") or "").strip() or None,
            "pdf_path": (rec.get("pdf파일") or "").strip() or None,
            "start_page": _safe_int(rec.get("시작페이지")),
            "end_page": _safe_int(rec.get("끝페이지")),
            "note": (rec.get("비고") or "").strip() or None,
            "extension_count": _safe_int(rec.get("연장횟수"), 0),
            "sort_order": rec.get("_row", 0),
        })

    save_json(lesson_rows, "lessons.json")
    try:
        lesson_result = supabase_post("lessons", lesson_rows)
        # legacy_lesson_id → supabase id 매핑
        lesson_id_map = {r["legacy_lesson_id"]: r["id"] for r in lesson_result if r.get("legacy_lesson_id")}
        print(f"   ✅ {len(lesson_result)}개 완료")
    except Exception as e:
        print(f"   ❌ 수업 업로드 실패: {e}")
        lesson_id_map = {}

    # 5. 슬롯(lesson_slots) 업로드
    slot_rows = []
    if bridge_rows:
        print(f"\n📤 수업 배치 슬롯(bridge) {len(bridge_rows)}개 업로드 중...")
        for br in bridge_rows:
            lid = (br.get("lesson_id") or "").strip()
            supabase_lid = lesson_id_map.get(lid)
            if not supabase_lid:
                continue
            slot_date = (br.get("slot_date") or "").strip() or None
            if not slot_date:
                continue
            slot_rows.append({
                "lesson_id": supabase_lid,
                "slot_date": slot_date,
                "slot_period": _safe_int(br.get("slot_period")),
                "slot_order": _safe_int(br.get("slot_order"), 1),
                "status": (br.get("status") or "planned").lower(),
                "source": (br.get("source") or "migrated").strip(),
                "memo": (br.get("memo") or "").strip() or None,
            })
    else:
        # bridge 없으면 진도표의 계획일로 슬롯 생성
        print(f"\n📤 계획일 기반 슬롯 생성 중...")
        for rec in records:
            lid = (rec.get("lesson_id") or "").strip()
            supabase_lid = lesson_id_map.get(lid)
            if not supabase_lid:
                continue
            slot_date = (rec.get("계획일") or "").strip() or None
            if not slot_date:
                continue
            slot_rows.append({
                "lesson_id": supabase_lid,
                "slot_date": slot_date,
                "slot_period": _safe_int(rec.get("계획교시")),
                "slot_order": 1,
                "status": "done" if _is_done(rec.get("실행여부", "")) else "planned",
                "source": "migrated",
                "memo": None,
            })

    save_json(slot_rows, "lesson_slots.json")
    if slot_rows:
        try:
            slot_result = supabase_post("lesson_slots", slot_rows)
            print(f"   ✅ {len(slot_result)}개 완료")
        except Exception as e:
            print(f"   ❌ 슬롯 업로드 실패: {e}")
    else:
        print("   ℹ️  슬롯 없음 (계획일이 비어 있음)")

    print("\n" + "=" * 55)
    print("✅ 마이그레이션 완료!")
    print(f"   JSON 백업: {os.path.join(os.path.dirname(__file__), 'migrated_data')}")
    print("=" * 55)
