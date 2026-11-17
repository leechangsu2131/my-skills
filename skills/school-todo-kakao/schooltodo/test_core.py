from datetime import date
from pathlib import Path

import pytest

from schooltodo.classify import OTHER, ClassifyConfig, classify
from schooltodo.dates import next_workday, parse_date, resolve_year
from schooltodo.db import CsvDb, MemoryDb
from schooltodo.message import build_message, build_weekly_trips, split_message
from schooltodo.sources import parse_today, parse_week, read_csv_file
from schooltodo.sync import make_key, plan_sync

FIX = Path(__file__).parent / "fixtures"
T = date(2026, 11, 18)  # 수요일
CFG = ClassifyConfig()


# ---------- 날짜 ----------
def test_parse_date_variants():
    want = date(2026, 11, 17)
    for s in ["2026-11-17", "2026. 11. 17", "2026.11.17.", "2026/11/17", "2026년 11월 17일", "11/17", "11월 17일"]:
        assert parse_date(s, T) == want, s
    assert parse_date(str((want - date(1899, 12, 30)).days), T) == want
    assert parse_date("", T) is None and parse_date("아무말", T) is None


def test_year_wraps_around_new_year():
    assert resolve_year(1, 3, date(2026, 12, 28)) == date(2027, 1, 3)
    assert resolve_year(12, 30, date(2027, 1, 2)) == date(2026, 12, 30)
    assert resolve_year(2, 30, T) is None


def test_next_workday_skips_weekend():
    assert next_workday(date(2026, 11, 20)) == date(2026, 11, 23)  # 금 -> 월
    assert next_workday(T) == date(2026, 11, 19)


# ---------- 분류 ----------
@pytest.mark.parametrize(
    "text,want",
    [
        ("3학년 현장학습", "3학년"),
        ("1~3학년 안전교육", "3학년"),
        ("(3-2 도시락 지참)", "3학년"),
        ("(유치원) 소풍", OTHER),
        ("6학년 졸업사진 촬영", OTHER),
        ("제2차 법무부 법교육(6-2)", OTHER),
        ("도서관 컨설팅(현곡초, 금장초 사서교사)", OTHER),
        ("4-5교시 보건교육", "전체"),
        ("체육 연합회의", "체육"),
        ("6학년 체력왕선발대회", "체육"),
        ("PAPS 측정", "체육"),
        ("교직원 협의회", "전체"),
    ],
)
def test_classify(text, want):
    assert classify(text, CFG) == want


# ---------- 원본 시트 파싱 ----------
def test_parse_week_fixture():
    got = {(c.date.isoformat(), c.text) for c in parse_week(read_csv_file(FIX / "week.csv"), T)}
    assert ("2026-11-17", "가상 안전교육") in got
    assert ("2026-11-17", "(유치원) 가상 체험") in got  # 줄바꿈 = 일정 하나
    assert ("2026-11-18", "4-5교시 보건교육") in got
    assert ("2026-11-19", "체육 연합회의") in got
    assert ("2026-11-25", "(3-2 도시락 지참)") in got
    assert not any(t.startswith("*세부") for _, t in got)


def test_parse_today_fixture():
    got = parse_today(read_csv_file(FIX / "today.csv"), T, my_name="테스트교사")
    assert (T, "학교", "15:30 교직원 협의회 (교직원)") in got
    assert (T, "학교", "10:00 6학년 졸업앨범 촬영 (6학년)") in got
    assert (T, "출장", "테스트교사(3-2) 체육 연수 14:00") in got  # 내 이름이 있는 줄만
    assert not any("가상선생" in c.text for c in got)  # 남의 출장은 제외
    assert (date(2026, 11, 25), "공지", "가상 개교기념식") in got
    assert not any("안내장 배부시" in c.text for c in got)  # 날짜 없는 상시 안내는 제외


def test_parse_today_without_my_name_has_no_trip():
    got = parse_today(read_csv_file(FIX / "today.csv"), T)
    assert not any(c.category == "출장" for c in got)


# ---------- 동기화 ----------
def test_sync_adds_only_new_future_rows_and_is_idempotent():
    cands = parse_week(read_csv_file(FIX / "week.csv"), T)
    db = MemoryDb()
    first = plan_sync(db.rows(), cands, T, CFG)
    assert first and all(r["날짜"] >= "2026-11-18" for r in first)  # 지난 날짜는 가져오지 않음
    assert all(r["출처"] == "자동" and r["상태"] == "" for r in first)
    db.append(first)
    assert plan_sync(db.rows(), cands, T, CFG) == []  # 두 번째는 추가할 것이 없음
    by_text = {r["내용"]: r["대상"] for r in first}
    assert "(유치원) 가상 체험" not in by_text  # 11/17은 오늘 이전이라 가져오지 않음
    assert by_text["체육 연합회의"] == "체육"
    assert by_text["6학년 졸업사진 촬영"] == OTHER
    assert by_text["(3-2 도시락 지참)"] == "3학년"


def test_my_trip_is_never_filtered_even_if_text_mentions_other_grade():
    from schooltodo.sources import Cand

    added = plan_sync([], [Cand(date(2026, 11, 19), "출장", "테스트교사 6학년 인솔 출장")], T, CFG)
    assert added[0]["대상"] == "전체"


def test_sync_never_touches_existing_rows():
    cands = parse_week(read_csv_file(FIX / "week.csv"), T)
    key = make_key(date(2026, 11, 19), "체육 연합회의")
    db = MemoryDb([{"키": key, "날짜": "2026-11-19", "구분": "학교", "내용": "내가 고친 문구", "상태": "✔", "출처": "자동", "대상": "체육"}])
    added = plan_sync(db.rows(), cands, T, CFG)
    assert key not in {r["키"] for r in added}


# ---------- 메시지 ----------
def _rows():
    return CsvDb(str(FIX / "db.csv")).rows()


def test_message_sections():
    lines, count = build_message(_rows(), T)
    text = "\n".join(lines)
    assert "📅 11/18(수) 오늘" in text
    assert "[학교] 가상 안전교육(전교생)" in text and "[개인] (예시) 출전경비 보고서 작성" in text
    assert "졸업사진" not in text  # 타학년·유치원 제외
    assert "이미 끝낸 일" not in text  # 완료(✔) 제외
    assert "지나간 학교 행사" not in text  # 지난 자동 일정은 지연이 아님
    assert "⚠ 지연\n• 11/17 [개인] (예시) 안내장 회수" in text
    assert "👉 11/19(목) 미리보기" in text and "[출장] (예시) 연수 13:30" in text
    assert count == 6  # 오늘 3 + 지연 1 + 다음 근무일 2


def test_message_friday_previews_monday():
    rows = [{"키": "k", "날짜": "2026-11-23", "구분": "학교", "내용": "월요일 행사", "상태": "", "출처": "자동", "대상": "전체"}]
    lines, _ = build_message(rows, date(2026, 11, 20))
    assert "👉 11/23(월) 미리보기" in lines and "• [학교] 월요일 행사" in lines


def test_message_empty_day():
    lines, count = build_message([], T)
    assert "• 등록된 일정 없음" in lines and count == 0


def test_message_review_pending_status_is_not_sent():
    rows = [{"키": "k", "날짜": "2026-11-18", "구분": "개인", "내용": "쪽지에서 뽑은 후보", "상태": "검토대기", "출처": "쪽지", "대상": ""}]
    lines, count = build_message(rows, T)
    assert count == 0 and "쪽지에서 뽑은 후보" not in "\n".join(lines)


def test_split_keeps_every_chunk_under_limit_and_loses_nothing():
    rows = [
        {"키": str(i), "날짜": "2026-11-18", "구분": "학교", "내용": f"긴 일정 {i} " + "가" * 40, "상태": "", "출처": "자동", "대상": "전체"}
        for i in range(8)
    ]
    lines, _ = build_message(rows, T)
    chunks = split_message(lines)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    joined = "\n".join(chunks)
    for i in range(8):
        assert f"긴 일정 {i} " in joined
    assert chunks[0].startswith(f"(1/{len(chunks)}) ")
    assert "(계속)" in chunks[1]  # 소제목이 이어짐


def test_single_overlong_line_is_clipped():
    chunks = split_message(["📅 제목", "• " + "가" * 500])
    assert all(len(c) <= 200 for c in chunks)


def _task(key, d, text, status="", cat="개인"):
    return {"키": key, "날짜": d, "구분": cat, "내용": text, "상태": status, "출처": "수동", "대상": "3학년"}


def test_upcoming_tasks_are_shown_every_day_until_done():
    rows = [
        _task("a", "2026-11-25", "보고서 제출"),
        _task("b", "2026-11-27", "이미 한 일", status="✔"),
        _task("c", "2026-11-28", "행사 안내", cat="학교"),
        _task("d", "2027-03-01", "너무 먼 일"),
    ]
    lines, count = build_message(rows, T)
    text = "\n".join(lines)
    assert "📌 기한 있는 할 일\n• 11/25 D-7 보고서 제출" in text
    assert "이미 한 일" not in text and "행사 안내" not in text and "너무 먼 일" not in text
    assert count == 1
    # 다음 날에도 계속 보인다
    lines2, _ = build_message(rows, date(2026, 11, 19))
    assert "• 11/25 D-6 보고서 제출" in "\n".join(lines2)


def test_upcoming_task_is_not_repeated_in_today_or_preview():
    rows = [_task("t", "2026-11-18", "오늘 마감"), _task("n", "2026-11-19", "내일 마감")]
    lines, _ = build_message(rows, T)
    assert "📌 기한 있는 할 일" not in lines  # 이미 오늘·미리보기에 나온다
    assert lines.count("• [개인] 오늘 마감") == 1 and lines.count("• [개인] 내일 마감") == 1


def test_upcoming_tasks_are_capped_and_sorted_by_date():
    rows = [_task(str(i), f"2026-11-{20 + i}", f"할 일 {i}") for i in range(8)][::-1]
    lines, _ = build_message(rows, T)
    ups = lines[lines.index("📌 기한 있는 할 일") + 1 : lines.index("👉 11/19(목) 미리보기")]
    assert [x.split()[1] for x in ups[:5]] == ["11/20", "11/21", "11/22", "11/23", "11/24"]
    assert ups[-1] == "• … 외 3건"


def _ev(key, d, text, status=""):
    return _task(key, d, text, status, cat="학교")


def test_week_section_shows_rest_of_this_week_events_only():
    rows = [
        _task("t", "2026-11-21", "주말 할 일"),  # 개인(할 일)은 📌에 나오고 그 주 일정에는 안 나온다
        _ev("a", "2026-11-19", "내일 행사"),  # 다음 근무일 = 미리보기
        _ev("b", "2026-11-20", "금요일 행사"),
        _ev("c", "2026-11-21", "토요일 행사"),
        _ev("d", "2026-11-23", "다음 주 행사"),
        _ev("e", "2026-11-20", "끝낸 행사", status="✔"),
    ]
    lines, _ = build_message(rows, T)
    text = "\n".join(lines)
    assert "🗓 이번 주 남은 일정\n• 11/20(금) [학교] 금요일 행사\n• 11/21(토) [학교] 토요일 행사" in text
    assert "다음 주 행사" not in text and "끝낸 행사" not in text
    assert text.count("내일 행사") == 1 and "주말 할 일" in text and "🗓 이번 주 남은 일정\n• 11/21 D-3" not in text


def test_week_section_on_friday_shows_next_week():
    rows = [_ev("a", "2026-11-23", "월요일 행사"), _ev("b", "2026-11-25", "수요일 행사"), _ev("c", "2026-12-02", "그다음 주 행사")]
    lines, _ = build_message(rows, date(2026, 11, 20))
    text = "\n".join(lines)
    assert "🗓 다음 주 일정\n• 11/25(수) [학교] 수요일 행사" in text
    assert "그다음 주 행사" not in text and text.count("월요일 행사") == 1  # 월요일은 미리보기에만


def test_week_section_is_capped():
    rows = [_ev(str(i), f"2026-11-{20 + (i % 2)}", f"행사 {i}") for i in range(9)]
    lines, _ = build_message(rows, T)
    assert lines[-1] == "• … 외 3건"


def _trip(key, d, text, status="", target="3학년", src="수동"):
    return {"키": key, "날짜": d, "구분": "출장", "내용": text, "상태": status, "출처": src, "대상": target}


def test_weekly_trips_only_trip_rows_within_seven_days():
    rows = [
        _trip("a", "2026-11-23", "경주 연수 출장 (09:00~17:00)"),
        _trip("b", "2026-11-29", "일요일 출장"),
        _trip("c", "2026-11-30", "8일째라 제외"),
        _trip("d", "2026-11-24", "끝낸 출장", status="✔"),
        _trip("e", "2026-11-25", "타학년 출장", target="타학년·유치원", src="자동"),
        _task("t", "2026-11-24", "개인 할 일"),
        _ev("v", "2026-11-26", "학교 행사"),
        _trip("p", "2026-11-22", "지난 출장"),
    ]
    lines, count = build_weekly_trips(rows, date(2026, 11, 23))
    assert lines == ["🧳 11/23~11/29 출장 일정", "• 11/23(월) 경주 연수 출장 (09:00~17:00)", "• 11/29(일) 일요일 출장"]
    assert count == 2


def test_weekly_trips_empty_and_capped():
    lines, count = build_weekly_trips([_task("t", "2026-11-24", "개인 할 일")], date(2026, 11, 23))
    assert count == 0 and lines == ["🧳 11/23~11/29 출장 일정"]
    rows = [_trip(str(i), f"2026-11-{23 + i % 7}", f"출장 {i}") for i in range(10)]
    lines, count = build_weekly_trips(rows, date(2026, 11, 23))
    assert count == 10 and lines[-1] == "• … 외 2건"


def test_overdue_only_for_tasks_events_just_pass():
    rows = [
        _task("a", "2026-11-16", "밀린 할 일"),
        _task("b", "2026-11-16", "밀린 자동 할 일"),
        _trip("c", "2026-11-16", "지난 출장"),
        _ev("d", "2026-11-16", "지난 학교 행사"),
        _task("e", "2026-11-16", "지난 공지", cat="공지"),
        _task("f", "2026-11-16", "끝낸 할 일", status="✔"),
    ]
    lines, count = build_message(rows, T)
    text = "\n".join(lines)
    assert "⚠ 지연\n• 11/16 [개인] 밀린 할 일\n• 11/16 [개인] 밀린 자동 할 일" in text
    assert "지난 출장" not in text and "지난 학교 행사" not in text and "지난 공지" not in text and "끝낸 할 일" not in text
    assert count == 2
