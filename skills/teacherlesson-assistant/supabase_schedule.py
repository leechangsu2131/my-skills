"""Supabase-backed schedule reads and progress mutations for the lesson assistant."""
from __future__ import annotations

import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
import truststore

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "skills" / "_shared"))
from skill_env import load_env  # noqa: E402

SUBJECTS = "lesson_subjects"
UNITS = "lesson_units"
LESSONS = "lesson_lessons"
SLOTS = "lesson_slots"
LESSON_REL = "id,lesson_id,slot_date,slot_period,slot_order,status,source,memo,lesson:lesson_lessons(id,legacy_lesson_id,subject_id,lesson_number,title,pdf_path,start_page,end_page,note,sort_order,subject:lesson_subjects(id,name,color),unit:lesson_units(name))"


_sessions: dict = {}          # (url, key) → Session. 요청마다 새 연결(TLS 악수)을 맺던 것을 재사용해 빠르게 한다
_sessions_lock = threading.Lock()
_PROGRESS_LOCK = threading.Lock()  # 진도 읽기·변경을 한 요청씩 처리
_truststore_done = False


def _client():
    global _truststore_done
    load_env()
    url = (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key:
        raise RuntimeError("중앙 .env에 SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY가 필요합니다.")
    with _sessions_lock:
        if not _truststore_done:
            truststore.inject_into_ssl()
            _truststore_done = True
        session = _sessions.get((url, key))
        if session is None:
            session = requests.Session()
            session.headers.update({"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            adapter = requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=8)  # 동시 갱신용 연결 8개까지
            session.mount("https://", adapter); session.mount("http://", adapter)
            _sessions[(url, key)] = session
    return url, session


def _parallel(fn, items, workers: int = 6):
    """items 마다 fn 을 동시에 실행한다(슬롯 여러 개를 하나씩 차례로 고치면 요청 수만큼 기다려야 해서).
    하나라도 실패하면 첫 오류를 그대로 올린다. 한 번에 한 행씩만 건드리는 갱신이라 서로 영향이 없다."""
    items = list(items)
    if len(items) <= 1:
        return [fn(i) for i in items]
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        return list(pool.map(fn, items))


def _get(table, **params):
    url, session = _client()
    out, offset = [], 0
    while True:
        query = {"select": "*", "limit": 1000, "offset": offset, **params}
        response = session.get(f"{url}/rest/v1/{table}", params=query, timeout=30)
        if not response.ok:
            raise RuntimeError(f"Supabase {table} 조회 실패 ({response.status_code})")
        rows = response.json()
        out.extend(rows)
        if len(rows) < 1000:
            return out
        offset += len(rows)


def _patch(table, row_id, values):
    url, session = _client()
    response = session.patch(
        f"{url}/rest/v1/{table}", params={"id": f"eq.{row_id}"},
        headers={"Prefer": "return=representation"}, json=values, timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Supabase {table} 갱신 실패 ({response.status_code})")
    return response.json()


def _post(table, values):
    url, session = _client()
    response = session.post(
        f"{url}/rest/v1/{table}", headers={"Prefer": "return=representation"},
        json=values, timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"Supabase {table} 추가 실패 ({response.status_code})")
    return response.json()


def _period(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def day_schedule(day: date) -> list[dict]:
    # PostgREST relation names match the workspace schema.
    slots = _get(SLOTS, slot_date=f"eq.{day.isoformat()}", order="slot_period,slot_order", select=LESSON_REL)
    rows = []
    for slot in slots:
        lesson = slot.get("lesson") or {}
        subject = lesson.get("subject") or {}
        unit = lesson.get("unit") or {}
        rows.append({
            "period": _period(slot.get("slot_period")), "subject": subject.get("name", ""),
            "unit": unit.get("name", ""), "lesson": str(lesson.get("lesson_number") or ""),
            "title": lesson.get("title") or "", "record_key": lesson.get("legacy_lesson_id") or "",
            "slot_id": slot.get("id"), "status": slot.get("status", "planned"),
            "has_pdf": bool(lesson.get("pdf_path")),
            "_lesson_sort": int(lesson.get("sort_order") or 0),
            "_slot_order": slot.get("slot_order") or 0,
            "_manual_catch_up": slot.get("source") == "manual_catch_up" and slot.get("status", "planned") == "planned",
        })
    # A completed previous lesson can share a period with the current planned
    # lesson. Prefer planned rows. If every row is complete, show the latest
    # lesson in curriculum order rather than whichever duplicate PostgREST
    # happened to return first (e.g. lesson 1 masking lesson 4 on the same day).
    # Among planned rows, a lesson the teacher just chose with "여기부터 다시 잡기"
    # (catch-up, still planned) comes first, newest choice first. Otherwise an
    # earlier lesson chosen for a period that already holds a later planned lesson
    # would never show (ISSUE-033). When it is done, the later lesson shows again.
    def rank(row):
        manual = row["_manual_catch_up"]
        return (
            row["status"] != "planned",
            not manual,
            -row["_slot_order"] if manual else 0,
            -row["_lesson_sort"],
            -row["_slot_order"],
        )

    by_period = {}
    for row in rows:
        key = row["period"] if row["period"] is not None else row["slot_id"]
        previous = by_period.get(key)
        if previous is None or rank(row) < rank(previous):
            by_period[key] = row
    selected = list(by_period.values())
    for row in selected:
        row.pop("_lesson_sort", None)
        row.pop("_slot_order", None)
        row.pop("_manual_catch_up", None)
    return sorted(selected, key=lambda x: x["period"] or 99)


def overdue_planned(day: date) -> list[dict]:
    """Return planned classes dated before day without changing the schedule."""
    slots = _get(SLOTS, slot_date=f"lt.{day.isoformat()}", status="eq.planned",
                 order="slot_date,slot_period,slot_order", select=LESSON_REL)
    rows = []
    for slot in slots:
        slot_date = str(slot.get("slot_date") or "")
        if slot.get("status") != "planned" or not slot_date or slot_date >= day.isoformat():
            continue
        lesson = slot.get("lesson") or {}
        rows.append({
            "subject": (lesson.get("subject") or {}).get("name", ""),
            "unit": (lesson.get("unit") or {}).get("name", ""),
            "lesson": str(lesson.get("lesson_number") or ""),
            "title": lesson.get("title") or "",
            "record_key": lesson.get("legacy_lesson_id") or "",
            "slot_id": slot.get("id"),
            "original_date": slot_date,
            "original_period": _period(slot.get("slot_period")),
        })
    return rows


def upcoming(subject: str) -> list[dict]:
    subjects = _get(SUBJECTS, name=f"eq.{subject}")
    if not subjects:
        return []
    lessons = _get(LESSONS, subject_id=f"eq.{subjects[0]['id']}", order="sort_order")
    slots = _get(SLOTS)
    by_lesson = {}
    for slot in slots:
        by_lesson.setdefault(slot.get("lesson_id"), []).append(slot)
    out = []
    for lesson in lessons:
        occurrences = by_lesson.get(lesson["id"], [])
        planned = [s for s in occurrences if s.get("status") == "planned"]
        out.append({
            "record_key": lesson.get("legacy_lesson_id") or "", "unit": "", # filled from unit relation below
            "lesson": str(lesson.get("lesson_number") or ""), "title": lesson.get("title") or "",
            "done": bool(occurrences) and not planned,
            "planned_date": min((s.get("slot_date", "") for s in planned), default=""),
            "planned_period": next((_period(s.get("slot_period")) for s in planned), None),
            "slot_id": next((s.get("id") for s in planned), None),
            "sort_order": lesson.get("sort_order", 0),
        })
    units = {u["id"]: u.get("name", "") for u in _get(UNITS)}
    lesson_unit = {l["id"]: units.get(l.get("unit_id"), "") for l in lessons}
    for row, lesson in zip(out, lessons):
        row["unit"] = lesson_unit.get(lesson["id"], "")
    return out


def subject_names() -> list[str]:
    """Subjects registered in Supabase, in the teacher's configured order."""
    return [row.get("name", "") for row in _get(SUBJECTS, order="sort_order", select="id,name,sort_order")
            if row.get("name")]


def records() -> list[dict]:
    """Return schedule rows in the legacy column shape for content builders."""
    lessons = _get(LESSONS, order="sort_order", select=(
        "id,legacy_lesson_id,lesson_number,title,pdf_path,start_page,end_page,note,extension_count,sort_order,"
        "subject:lesson_subjects(name),unit:lesson_units(name)"
    ))
    slots = _get(SLOTS, order="slot_date,slot_period,slot_order")
    by_lesson = {}
    for slot in slots:
        by_lesson.setdefault(slot.get("lesson_id"), []).append(slot)
    result = []
    for lesson in lessons:
        occurrences = by_lesson.get(lesson["id"], [])
        planned = sorted((s for s in occurrences if s.get("status") == "planned"), key=_slot_key)
        subject = lesson.get("subject") or {}
        unit = lesson.get("unit") or {}
        result.append({
            "lesson_id": lesson.get("legacy_lesson_id") or "",
            "과목": subject.get("name", ""), "대단원": unit.get("name", ""),
            "차시": str(lesson.get("lesson_number") or ""), "수업내용": lesson.get("title") or "",
            "pdf파일": lesson.get("pdf_path") or "", "시작페이지": lesson.get("start_page") or "",
            "끝페이지": lesson.get("end_page") or "", "비고": lesson.get("note") or "",
            "연장횟수": lesson.get("extension_count") or 0, "_row": lesson.get("sort_order") or 0,
            "계획일": planned[0].get("slot_date", "") if planned else "",
            "계획교시": planned[0].get("slot_period", "") if planned else "",
            "실행여부": bool(occurrences) and not planned,
        })
    return result


def _slots_joined():
    return _get(SLOTS, order="slot_date,slot_period,slot_order", select=LESSON_REL)


def _lesson_by_key(key: str):
    rows = _get(LESSONS, legacy_lesson_id=f"eq.{key}")
    return rows[0] if rows else None


def progress(action: str, body: dict) -> dict:
    """진도 변경 요청을 한 번에 하나씩 처리해 같은 옛 자료로 덮어쓰지 않게 한다."""
    with _PROGRESS_LOCK:
        return _progress_unlocked(action, body)


def _progress_unlocked(action: str, body: dict) -> dict:
    subject = str(body.get("subject") or "")
    key = str(body.get("record_key") or "")
    slot_id = str(body.get("slot_id") or "")
    day = str(body.get("target_date") or "")
    slots = _slots_joined()
    def lesson_of(slot):
        return slot.get("lesson") or {}
    def subject_of(slot):
        return (lesson_of(slot).get("subject") or {}).get("name", "")
    def target_matches(slot):
        lesson = lesson_of(slot)
        return (slot.get("id") == slot_id if slot_id else lesson.get("legacy_lesson_id") == key)

    if action == "replace-subject":
        return replace_subject_period(slots, body)

    if action == "done":
        candidates = [s for s in slots if target_matches(s) and s.get("status") == "planned"
                      and (not day or s.get("slot_date") == day)]
        if not candidates:
            return {"status": "error", "message": "완료할 예정 슬롯을 찾지 못했어요."}
        _patch(SLOTS, candidates[0]["id"], {"status": "done"})
        return {"status": "success", "updated": 1, "message": "Supabase에서 수업 완료를 기록했어요."}

    if action == "push":
        try:
            days = int(body.get("days", 7))
            from_date = date.fromisoformat(str(body.get("from_date") or day))
        except (TypeError, ValueError):
            return {"status": "error", "message": "미룰 날짜나 일수가 올바르지 않아요."}
        targets = [s for s in slots if subject_of(s) == subject and s.get("status") == "planned"
                   and s.get("slot_date", "") >= from_date.isoformat()]
        _parallel(lambda row: _patch(SLOTS, row["id"], {"slot_date": (date.fromisoformat(row["slot_date"]) + timedelta(days=days)).isoformat()}), targets)
        return {"status": "success", "updated": len(targets), "message": f"{len(targets)}개 슬롯을 {days}일 미뤘어요."}

    if action == "extend":
        target = next((s for s in slots if target_matches(s) and subject_of(s) == subject
                       and s.get("status") == "planned" and (not day or s.get("slot_date") == day)), None)
        if not target:
            return {"status": "error", "message": "연장할 예정 슬롯을 찾지 못했어요."}
        subject_slots = sorted([s for s in slots if subject_of(s) == subject and s.get("status") == "planned"], key=_slot_key)
        lesson_id = target.get("lesson_id")
        insertion = next((i for i, s in enumerate(subject_slots) if s["id"] == target["id"]), -1) + 1
        while insertion < len(subject_slots) and subject_slots[insertion].get("lesson_id") == lesson_id:
            insertion += 1
        last = subject_slots[-1]
        dates = [s.get("slot_date") for s in subject_slots if s.get("slot_date")]
        gap = 7
        for prev, current in zip(dates, dates[1:]):
            diff = (date.fromisoformat(current) - date.fromisoformat(prev)).days
            if diff > 0:
                gap = diff
        future = {
            "slot_date": (date.fromisoformat(last["slot_date"]) + timedelta(days=gap)).isoformat(),
            "slot_period": last.get("slot_period"), "slot_order": last.get("slot_order") or 1,
        }
        templates = [{"slot_date": s["slot_date"], "slot_period": s.get("slot_period"), "slot_order": s.get("slot_order") or 1} for s in subject_slots]
        templates.append(future)
        rewritten = subject_slots[:insertion] + [None] + subject_slots[insertion:]
        url, session = _client()
        jobs = []
        for index, row in enumerate(rewritten):
            template = templates[index]
            if row is None or any(row.get(k) != template[k] for k in ("slot_date", "slot_period", "slot_order")):
                jobs.append((row, template))
        def apply(job):
            row, template = job
            if row is None:
                result = session.post(f"{url}/rest/v1/{SLOTS}", headers={"Prefer": "return=representation"},
                    json={"lesson_id": lesson_id, **template, "status": "planned", "source": "manual_extend", "memo": ""}, timeout=30)
                if not result.ok: raise RuntimeError(f"Supabase 슬롯 추가 실패 ({result.status_code})")
            else:
                _patch(SLOTS, row["id"], template)
        _parallel(apply, jobs)
        changed = len(jobs)
        return {"status": "success", "updated": changed, "message": f"차시를 연장하고 {changed}개 시간표 슬롯을 조정했어요."}

    if action == "catch-up":
        lesson = _lesson_by_key(key)
        subject_rows = _get(SUBJECTS, name=f"eq.{subject}") if subject else []
        if not lesson or not subject_rows or lesson.get("subject_id") != subject_rows[0].get("id"):
            return {"status": "error", "message": "선택한 차시를 진도표에서 찾지 못했어요."}
        try:
            from_day = date.fromisoformat(day)
        except (TypeError, ValueError):
            return {"status": "error", "message": "오늘 날짜를 확인할 수 없어 차시를 옮기지 못했어요."}

        matches = [s for s in slots if target_matches(s) and subject_of(s) == subject]
        target = next((s for s in matches if s.get("status") == "planned"), None)
        if target is None and slot_id:
            target = next((s for s in matches if s.get("id") == slot_id), None)
        if target is None:
            target = next((s for s in matches if s.get("status") == "done"), None)

        # The UI promises to make the selected lesson today's lesson. Previously
        # this used the chronologically first slot in the whole semester, so an
        # out-of-date April slot kept today's lesson unchanged (and a repeat click
        # became a no-op). Prefer an existing slot for today; otherwise use the
        # first planned class on or after the requested date.
        wanted_period = _period(body.get("target_period"))
        today_slots = sorted(
            [s for s in slots if subject_of(s) == subject and s.get("slot_date") == from_day.isoformat()
             and (wanted_period is None or _period(s.get("slot_period")) == wanted_period)],
            key=_slot_key,
        )
        if not today_slots and wanted_period is not None:
            today_slots = sorted(
                [s for s in slots if subject_of(s) == subject and s.get("slot_date") == from_day.isoformat()],
                key=_slot_key,
            )
        if today_slots:
            destination = today_slots[0]
        else:
            future = sorted(
                [s for s in slots if subject_of(s) == subject and s.get("status") == "planned"
                 and s.get("slot_date", "") >= from_day.isoformat() and (not target or s.get("id") != target["id"])],
                key=_slot_key,
            )
            destination = future[0] if future else None
        if target is None and destination is None:
            return {"status": "error", "message": "오늘 이후 옮길 예정 시간표 칸을 찾지 못했어요."}

        # A catch-up means all earlier curriculum lessons are already covered,
        # not all rows whose calendar dates happen to precede an old target slot.
        earlier = [s for s in slots if subject_of(s) == subject and s.get("status") == "planned"
                   and int((s.get("lesson") or {}).get("sort_order") or 0) < int(lesson.get("sort_order") or 0)]
        if target:
            dest_date = from_day.isoformat() if today_slots else destination.get("slot_date")
            dest_period = (today_slots[0] if today_slots else destination).get("slot_period")
            same_period = [s for s in slots if s.get("slot_date") == dest_date and s.get("slot_period") == dest_period]
            dest_order = max((_period(s.get("slot_order")) or 0 for s in same_period if s.get("id") != target.get("id")), default=0) + 1
            _parallel(lambda row: _patch(SLOTS, row["id"], {"status": "done"}), earlier)
            _patch(SLOTS, target["id"], {
                "slot_date": dest_date, "slot_period": dest_period, "slot_order": dest_order,
                "status": "planned", "source": "manual_catch_up",
            })
        else:
            dest_date = from_day.isoformat() if today_slots else destination.get("slot_date")
            dest_period = (today_slots[0] if today_slots else destination).get("slot_period")
            same_period = [s for s in slots if s.get("slot_date") == dest_date and s.get("slot_period") == dest_period]
            dest_order = max((_period(s.get("slot_order")) or 0 for s in same_period), default=0) + 1
            _parallel(lambda row: _patch(SLOTS, row["id"], {"status": "done"}), earlier)
            _post(SLOTS, [{
                "lesson_id": lesson["id"], "slot_date": dest_date,
                "slot_period": dest_period, "slot_order": dest_order,
                "status": "planned", "source": "manual_catch_up", "memo": "",
            }])
        return {"status": "success", "updated": len(earlier), "completed": len(earlier),
                "message": f"선택한 차시를 {dest_date}에 배치하고 앞의 예정 차시 {len(earlier)}개를 완료 처리했어요."}
    return {"status": "error", "message": "지원하지 않는 진도 작업이에요."}


def replace_subject_period(slots: list[dict], body: dict) -> dict:
    """Replace today's planned class with another subject's selected lesson.

    The displaced class is moved into the next slots of its own subject. The
    selected subject's lesson sequence is advanced into its now-vacant slots.
    The final displaced lesson can remain without a dated slot at the end of
    the existing plan.
    """
    subject = str(body.get("subject") or "").strip()
    slot_id = str(body.get("slot_id") or "")
    target_key = str(body.get("target_record_key") or "")
    day = str(body.get("target_date") or "")
    period = _period(body.get("target_period"))
    if not subject or not slot_id or not target_key or not day or period is None:
        return {"status": "error", "message": "현재 교시와 바꿀 과목·차시 정보가 필요해요."}
    try:
        date.fromisoformat(day)
    except ValueError:
        return {"status": "error", "message": "수업 날짜를 확인해 주세요."}

    current = next((row for row in slots if row.get("id") == slot_id), None)
    if not current or current.get("status") != "planned":
        return {"status": "error", "message": "바꿀 현재 교시의 예정 슬롯을 찾지 못했어요."}
    if current.get("slot_date") != day or _period(current.get("slot_period")) != period:
        return {"status": "error", "message": "현재 화면의 날짜·교시와 진도표가 달라요. 화면을 새로고침해 주세요."}
    old_lesson = current.get("lesson") or {}
    old_subject = (old_lesson.get("subject") or {}).get("name", "")
    old_lesson_id = current.get("lesson_id")
    if not old_subject or not old_lesson_id:
        return {"status": "error", "message": "현재 교시의 과목 정보를 읽지 못했어요."}

    selected = _lesson_by_key(target_key)
    if not selected:
        return {"status": "error", "message": "선택한 차시를 진도표에서 찾지 못했어요."}
    subject_rows = _get(SUBJECTS, id=f"eq.{selected.get('subject_id')}")
    new_subject = subject_rows[0].get("name", "") if subject_rows else ""
    if not new_subject:
        return {"status": "error", "message": "선택한 차시의 과목을 찾지 못했어요."}
    if new_subject == old_subject:
        return {"status": "error", "message": "같은 과목 안의 차시는 ‘실제로 할 차시 고르기’를 사용해 주세요."}
    if selected.get("id") == old_lesson_id:
        return {"status": "error", "message": "현재 차시와 같은 차시는 선택할 수 없어요."}

    subject_lessons = _get(LESSONS, subject_id=f"eq.{selected['subject_id']}", order="sort_order",
                           select="id,legacy_lesson_id,lesson_number,title,sort_order")
    selected_sort = int(selected.get("sort_order") or 0)
    selected_planned = sorted(
        [row for row in slots if (row.get("lesson") or {}).get("id") == selected.get("id")
         and row.get("status") == "planned"],
        key=_slot_key,
    )
    cutoff = _slot_key(current)
    # The slot formerly assigned to the selected lesson, followed by all
    # upcoming slots of that subject, becomes the runway for later lessons.
    target_slots = sorted(
        [row for row in slots if row.get("status") == "planned"
         and ((row.get("lesson") or {}).get("subject") or {}).get("name") == new_subject
         and int((row.get("lesson") or {}).get("sort_order") or 0) >= selected_sort
         and _slot_key(row) > cutoff],
        key=_slot_key,
    )

    # Previously uncompleted lessons before the selected class are treated as
    # covered, matching the existing catch-up action.
    earlier = [row for row in slots if row.get("status") == "planned"
               and ((row.get("lesson") or {}).get("subject") or {}).get("name") == new_subject
               and int((row.get("lesson") or {}).get("sort_order") or 0) < selected_sort]

    by_lesson = {}
    for row in slots:
        by_lesson.setdefault((row.get("lesson") or {}).get("id"), []).append(row)
    later_lessons = []
    for lesson in subject_lessons:
        if int(lesson.get("sort_order") or 0) <= selected_sort:
            continue
        occurrences = by_lesson.get(lesson.get("id"), [])
        if occurrences and not any(row.get("status") == "planned" for row in occurrences):
            continue  # keep later lessons already recorded as completed
        later_lessons.append(lesson)

    # Move the displaced lesson and its following sequence one existing
    # subject slot later. The final lesson stays in the lesson table without a
    # date, so it is still available to schedule after the current plan ends.
    old_future = sorted(
        [row for row in slots if row.get("status") == "planned"
         and ((row.get("lesson") or {}).get("subject") or {}).get("name") == old_subject
         and _slot_key(row) > cutoff],
        key=_slot_key,
    )
    old_sequence = [old_lesson_id] + [(row.get("lesson") or {}).get("id") for row in old_future]
    displaced_tail = old_sequence[-1]

    jobs = []
    for row in earlier:
        jobs.append((row, {"status": "done"}))
    for index, row in enumerate(old_future):
        jobs.append((row, {"lesson_id": old_sequence[index], "source": "manual_subject_change"}))
    for index, row in enumerate(target_slots):
        if index < len(later_lessons):
            jobs.append((row, {"lesson_id": later_lessons[index]["id"], "status": "planned",
                               "source": "manual_subject_change"}))
        else:
            # A slot left at the end of the selected subject's plan has no
            # class assigned; clear its date so it does not appear as a blank
            # period in the schedule.
            jobs.append((row, {"lesson_id": None, "slot_date": None, "slot_period": None,
                               "status": "planned", "source": "manual_subject_change"}))

    _parallel(lambda job: _patch(SLOTS, job[0]["id"], job[1]), jobs)

    # If the selected lesson was already planned in an earlier calendar slot,
    # clear that old row so it does not remain as a duplicate planned class.
    target_future_ids = {row.get("id") for row in target_slots}
    for row in selected_planned:
        if row.get("id") not in target_future_ids and _slot_key(row) <= cutoff:
            _patch(SLOTS, row["id"], {"lesson_id": None, "slot_date": None, "slot_period": None,
                                       "status": "planned", "source": "manual_subject_change"})

    # If the tail lesson has no remaining planned slot, preserve it as a
    # date-less lesson instead of marking it complete or dropping it.
    tail_has_plan_elsewhere = any(
        row.get("status") == "planned" and (row.get("lesson") or {}).get("id") == displaced_tail
        and row.get("id") != current.get("id") and row.get("id") not in {x.get("id") for x in old_future}
        for row in slots
    )
    if displaced_tail and not tail_has_plan_elsewhere:
        _post(SLOTS, {"lesson_id": displaced_tail, "slot_date": None, "slot_period": None,
                      "slot_order": 1, "status": "planned", "source": "manual_subject_change",
                      "memo": "다음 같은 과목 수업으로 이월"})

    _patch(SLOTS, current["id"], {"lesson_id": selected["id"], "status": "planned",
                                   "source": "manual_subject_change", "memo": "교시 과목 변경"})
    updated = len(jobs) + 1
    return {"status": "success", "updated": updated,
            "message": f"{day} {period}교시를 {new_subject} 「{selected.get('title') or ''}」로 바꿨어요. "
                       f"기존 {old_subject} 차시는 다음 {old_subject} 시간으로 넘기고, 뒤 차시를 재배치했어요. "
                       "현재 계획 끝의 마지막 차시는 날짜 없이 남아 있어요."}


def _slot_key(slot):
    return (slot.get("slot_date") or "", _period(slot.get("slot_period")) or 0,
            _period(slot.get("slot_order")) or 0, str(slot.get("id") or ""))


def pdf_for_lesson(record_key: str) -> bytes:
    lesson = _lesson_by_key(record_key)
    if not lesson or not lesson.get("pdf_path"):
        raise FileNotFoundError("Supabase 차시 지도서 경로가 없어요.")
    raw = os.path.expandvars(os.path.expanduser(str(lesson["pdf_path"])))
    sys.path.insert(0, str(REPO / "skills" / "teacherlesson-schedule"))
    import schedule
    resolved = schedule.resolve_pdf_path(raw)
    if not os.path.isfile(resolved):
        raise FileNotFoundError("이 PC에서 지도서 PDF를 찾지 못했어요.")
    import fitz
    with fitz.open(resolved) as doc:
        is_split = "pdf_splits" in {p.casefold() for p in Path(raw).parts} and os.path.isfile(raw)
        start, end = lesson.get("start_page"), lesson.get("end_page")
        if not is_split and start and end and (resolved != raw or doc.page_count > int(end)):
            out = fitz.open()
            a, z = max(0, int(start) - 1), min(doc.page_count - 1, int(end) - 1)
            if z < a:
                raise FileNotFoundError("진도표의 PDF 쪽수가 파일 범위와 맞지 않아요.")
            out.insert_pdf(doc, from_page=a, to_page=z)
            data = out.tobytes(); out.close()
            return data
        return doc.tobytes()
