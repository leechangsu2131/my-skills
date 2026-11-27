"""supabase_schedule.replace_subject_period(오늘 교시 과목 바꾸기)와 progress("replace-subject") 시험 (S1).

    python -m pytest tests/test_replace_subject_period.py -v      (teacherlesson-assistant 폴더에서)

진짜 Supabase·네트워크·비밀값 없이 돈다. `_get`·`_patch`·`_post` 를 메모리 표로 바꿔서,
함수가 슬롯을 어떻게 고쳤는지 "최종 표"로 확인한다. 소스(supabase_schedule.py)는 고치지 않는다.

기본 장면(국어 K1~K4, 수학 M1~M4, 학생 정보 없음):
    11-30 1교시 국어 K2 (바꿀 현재 교시)   11-30 2교시 수학 M2
    12-01 1교시 국어 K3                    12-01 2교시 수학 M3 (고를 차시)
    12-02 1교시 국어 K4                    12-02 2교시 수학 M4
"""
import copy
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import supabase_schedule as sm  # noqa: E402

DAY, PERIOD = "2026-11-30", 1


def _lessons():
    out = []
    for sid, subject in (("sub-k", "국어"), ("sub-m", "수학")):
        prefix = "k" if subject == "국어" else "m"
        for n in range(1, 5):
            out.append({"id": f"{prefix}{n}", "legacy_lesson_id": f"key-{prefix}{n}", "subject_id": sid,
                        "lesson_number": n, "title": f"{subject} {n}차시", "sort_order": n, "pdf_path": ""})
    return out


SUBJECTS = [{"id": "sub-k", "name": "국어"}, {"id": "sub-m", "name": "수학"}]


def _slot(slot_id, day, period, lesson_id, status="planned", order=1):
    return {"id": slot_id, "lesson_id": lesson_id, "slot_date": day, "slot_period": period,
            "slot_order": order, "status": status, "source": "", "memo": ""}


def _base_slots():
    return [
        _slot("c", DAY, 1, "k2"), _slot("km", DAY, 2, "m2"),
        _slot("k3", "2026-12-01", 1, "k3"), _slot("m3", "2026-12-01", 2, "m3"),
        _slot("k4", "2026-12-02", 1, "k4"), _slot("m4", "2026-12-02", 2, "m4"),
    ]


class Store:
    """Supabase 대신 쓰는 메모리 표. 조회·고침·추가를 기록한다."""

    def __init__(self, slots=None):
        self.lessons = {row["id"]: row for row in _lessons()}
        self.slots = copy.deepcopy(slots if slots is not None else _base_slots())
        self.posts = []
        self.patches = []

    def joined(self):
        rows = []
        for slot in self.slots:
            row = dict(slot)
            lesson = self.lessons.get(slot["lesson_id"])
            if lesson:
                subject = next(s for s in SUBJECTS if s["id"] == lesson["subject_id"])
                row["lesson"] = {**lesson, "subject": {"id": subject["id"], "name": subject["name"]}}
            else:
                row["lesson"] = None
            rows.append(row)
        return sorted(rows, key=lambda r: (r["slot_date"] or "", r["slot_period"] or 0, r["slot_order"]))

    def get(self, table, **params):
        def eq(name):
            value = params.get(name)
            return None if value is None else value.removeprefix("eq.")
        if table == sm.LESSONS:
            rows = list(self.lessons.values())
            if eq("legacy_lesson_id") is not None:
                rows = [r for r in rows if r["legacy_lesson_id"] == eq("legacy_lesson_id")]
            if eq("subject_id") is not None:
                rows = [r for r in rows if r["subject_id"] == eq("subject_id")]
            return sorted(rows, key=lambda r: r["sort_order"])
        if table == sm.SUBJECTS:
            return [s for s in SUBJECTS if eq("id") in (None, s["id"])]
        raise AssertionError(f"예상 밖 조회: {table} {params}")

    def patch(self, table, row_id, values):
        assert table == sm.SLOTS
        slot = next(s for s in self.slots if s["id"] == row_id)
        slot.update(values)
        self.patches.append((row_id, dict(values)))
        return [slot]

    def post(self, table, values):
        assert table == sm.SLOTS
        row = dict(values)
        row.setdefault("id", f"new-{len(self.posts) + 1}")
        self.slots.append(row)
        self.posts.append(dict(values))
        return [row]

    def lesson_at(self, slot_id):
        return next(s for s in self.slots if s["id"] == slot_id)["lesson_id"]

    def slot(self, slot_id):
        return next(s for s in self.slots if s["id"] == slot_id)


@pytest.fixture
def store(monkeypatch):
    st = Store()
    monkeypatch.setattr(sm, "_get", st.get)
    monkeypatch.setattr(sm, "_patch", st.patch)
    monkeypatch.setattr(sm, "_post", st.post)
    monkeypatch.setattr(sm, "_slots_joined", st.joined)
    return st


def body(**over):
    base = {"subject": "수학", "slot_id": "c", "target_record_key": "key-m3",
            "target_date": DAY, "target_period": PERIOD}
    base.update(over)
    return base


def run(store, **over):
    return sm.replace_subject_period(store.joined(), body(**over))


def error_message(result):
    assert result["status"] == "error", result
    return result["message"]


# ── 잘 되는 경우 ──

def test_happy_path_final_table(store):
    result = run(store)
    assert result["status"] == "success"
    # 현재 교시는 고른 수학 3차시로 바뀐다
    assert store.slot("c")["lesson_id"] == "m3"
    assert (store.slot("c")["source"], store.slot("c")["memo"]) == ("manual_subject_change", "교시 과목 변경")
    # 밀려난 국어 K2 는 다음 국어 칸으로, K3 는 그다음 칸으로
    assert [store.lesson_at(s) for s in ("k3", "k4")] == ["k2", "k3"]
    # 고른 과목의 뒤 차시는 비워진 칸으로 당겨 오고, 남는 마지막 칸은 날짜를 비운다
    assert store.lesson_at("m3") == "m4"
    assert store.lesson_at("m4") is None
    assert (store.slot("m4")["slot_date"], store.slot("m4")["slot_period"]) == (None, None)
    # 고른 차시보다 앞의 안 한 수학(M2)은 이미 다룬 것으로 완료 처리
    assert store.slot("km")["status"] == "done"


def test_displaced_tail_lesson_is_kept_as_dateless_slot(store):
    run(store)
    assert len(store.posts) == 1
    post = store.posts[0]
    assert post["lesson_id"] == "k4"
    assert (post["slot_date"], post["slot_period"], post["status"]) == (None, None, "planned")
    assert post["source"] == "manual_subject_change"


def test_updated_count_and_message(store):
    result = run(store)
    # 완료 1 + 국어 밀기 2 + 수학 칸 2 + 현재 교시 1
    assert result["updated"] == 6
    assert "2026-11-30 1교시를 수학" in result["message"]
    assert "수학 3차시" in result["message"]
    assert "기존 국어 차시는 다음 국어 시간으로 넘기고" in result["message"]


def test_only_planned_future_slots_are_moved(store):
    store.slot("k3")["status"] = "done"  # 이미 한 국어 K3 는 건드리지 않는다
    run(store)
    assert store.lesson_at("k3") == "k3"
    assert store.slot("k3")["status"] == "done"
    assert store.lesson_at("k4") == "k2"


def test_completed_later_lessons_are_not_reassigned(store):
    store.slot("m4")["status"] = "done"  # 수학 M4 는 이미 함 → 당겨 올 뒤 차시가 없다
    run(store)
    assert store.slot("m4")["status"] == "done"
    assert store.lesson_at("m4") == "m4"
    assert store.lesson_at("m3") is None  # M3 칸은 채울 차시가 없어 비워짐
    assert store.slot("m3")["slot_date"] is None


def test_selected_lesson_planned_earlier_is_cleared_to_avoid_duplicate(store):
    # 수학 M3 가 현재 교시보다 앞(11-29)에도 예정으로 남아 있던 경우
    store.slots.append(_slot("old-m3", "2026-11-29", 3, "m3"))
    run(store)
    old = store.slot("old-m3")
    assert old["lesson_id"] is None
    assert (old["slot_date"], old["slot_period"]) == (None, None)
    assert store.lesson_at("c") == "m3"
    assert [s["lesson_id"] for s in store.slots].count("m3") == 1


def test_tail_with_planned_slot_elsewhere_is_not_posted_again(store):
    # 꼬리 차시 K4 가 이미 앞날(11-29)에 예정으로 남아 있으면 날짜 없는 칸을 또 만들지 않는다
    store.slots.append(_slot("k4-early", "2026-11-29", 3, "k4"))
    run(store)
    assert store.posts == []


def test_slot_order_is_used_for_same_period(store):
    store.slots.append(_slot("k3b", "2026-12-01", 1, "k4", order=2))
    run(store)
    # 같은 교시의 둘째 칸(slot_order 2)은 첫째 칸 다음 순서로 밀린다
    assert store.lesson_at("k3") == "k2"
    assert store.lesson_at("k3b") == "k3"


# ── 막는 경우(아무것도 고치지 않는다) ──

@pytest.mark.parametrize("over", [
    {"subject": ""}, {"subject": "  "}, {"slot_id": ""}, {"target_record_key": ""},
    {"target_date": ""}, {"target_period": None}, {"target_period": "가"},
])
def test_missing_fields_are_rejected(store, over):
    assert "필요해요" in error_message(run(store, **over))
    assert store.patches == [] and store.posts == []


def test_bad_date_is_rejected(store):
    assert "날짜를 확인" in error_message(run(store, target_date="11월 30일"))
    assert store.patches == []


def test_unknown_slot_is_rejected(store):
    assert "예정 슬롯을 찾지 못했어요" in error_message(run(store, slot_id="없는칸"))


def test_non_planned_current_slot_is_rejected(store):
    store.slot("c")["status"] = "done"
    assert "예정 슬롯을 찾지 못했어요" in error_message(run(store))
    assert store.patches == []


@pytest.mark.parametrize("over", [{"target_date": "2026-12-01"}, {"target_period": 2}])
def test_screen_and_table_mismatch_is_rejected(store, over):
    assert "새로고침" in error_message(run(store, **over))
    assert store.patches == []


def test_period_accepts_number_text(store):
    assert run(store, target_period="1")["status"] == "success"


def test_current_slot_without_lesson_is_rejected(store):
    store.slot("c")["lesson_id"] = None
    assert "과목 정보를 읽지 못했어요" in error_message(run(store))


def test_unknown_selected_lesson_is_rejected(store):
    assert "찾지 못했어요" in error_message(run(store, target_record_key="key-없음"))
    assert store.patches == []


def test_selected_lesson_subject_missing_is_rejected(store):
    slots = store.joined()  # 과목을 망가뜨리기 전에 표를 만든다
    store.lessons["m3"]["subject_id"] = "sub-없음"
    assert "과목을 찾지 못했어요" in error_message(sm.replace_subject_period(slots, body()))


def test_same_subject_is_rejected_with_pointer_to_other_feature(store):
    message = error_message(run(store, target_record_key="key-k3"))
    assert "같은 과목" in message and "실제로 할 차시 고르기" in message
    assert store.patches == []


# ── progress() 연결 ──

def test_progress_replace_subject_dispatches_and_changes_table(store):
    result = sm.progress("replace-subject", body())
    assert result["status"] == "success"
    assert store.lesson_at("c") == "m3"


def test_progress_unknown_action_is_error(store):
    assert sm.progress("없는작업", {})["status"] == "error"
    assert store.patches == []
