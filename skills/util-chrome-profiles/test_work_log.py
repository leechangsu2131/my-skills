import csv
import time
from datetime import date, datetime

import work_log as wl


def ts(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi).timestamp()


def test_append_and_read(tmp_path):
    p = tmp_path / "work_log.csv"
    assert wl.append(p, "학교 계정", "수업", ts(2026, 11, 28, 9, 0), ts(2026, 11, 28, 10, 30))
    assert wl.append(p, "투자", "", ts(2026, 11, 28, 13, 0), ts(2026, 11, 28, 13, 45))
    rows = wl.read(p)
    assert rows == [{"date": date(2026, 11, 28), "minutes": 90, "name": "학교 계정", "group": "수업"},
                    {"date": date(2026, 11, 28), "minutes": 45, "name": "투자", "group": ""}]
    with open(p, encoding="utf-8-sig", newline="") as f:
        assert next(csv.reader(f)) == wl.FIELDS      # 머리줄은 한 번만
        assert len(list(csv.reader(f))) == 2


def test_under_one_minute_or_backwards_is_skipped(tmp_path):
    p = tmp_path / "w.csv"
    t = ts(2026, 11, 28, 9, 0)
    assert not wl.append(p, "a", "", t, t + 59)
    assert not wl.append(p, "a", "", t, t - 600)
    assert not p.exists()
    assert wl.append(p, "a", "", t, t + 60)


def test_midnight_counts_on_start_day(tmp_path):
    p = tmp_path / "w.csv"
    wl.append(p, "a", "", ts(2026, 11, 28, 23, 30), ts(2026, 11, 29, 0, 30))
    assert wl.read(p)[0]["date"] == date(2026, 11, 28) and wl.read(p)[0]["minutes"] == 60


def test_missing_or_broken_file(tmp_path):
    assert wl.read(tmp_path / "none.csv") == []
    p = tmp_path / "w.csv"
    p.write_text("날짜,시작,끝,분,이름,그룹\n2026-11-28,09:00,10:00,60,a,\n깨짐,x,x,x,x,x\n2026-11-28,09:00,10:00,,b,\n",
                 encoding="utf-8")
    assert [r["name"] for r in wl.read(p)] == ["a"]


def test_summarize_range_and_groups():
    rows = [
        {"date": date(2026, 11, 23), "minutes": 60, "name": "a", "group": "수업"},
        {"date": date(2026, 11, 24), "minutes": 30, "name": "b", "group": "수업"},
        {"date": date(2026, 11, 24), "minutes": 15, "name": "a", "group": ""},
        {"date": date(2026, 11, 22), "minutes": 999, "name": "old", "group": "x"},   # 범위 밖
    ]
    r = wl.summarize(rows, date(2026, 11, 23), date(2026, 11, 28))
    assert r["total"] == 105
    assert r["by_day"] == {date(2026, 11, 23): 60, date(2026, 11, 24): 45}
    assert r["by_name"] == {"a": 75, "b": 30}
    assert r["by_group"] == {"수업": 90}
    assert wl.summarize(rows, date(2026, 12, 1), date(2026, 12, 2))["total"] == 0


def test_range_edges_inclusive():
    rows = [{"date": date(2026, 11, 23), "minutes": 5, "name": "a", "group": ""},
            {"date": date(2026, 11, 28), "minutes": 7, "name": "a", "group": ""}]
    assert wl.summarize(rows, date(2026, 11, 23), date(2026, 11, 28))["total"] == 12


def test_hm_and_week_start():
    assert wl.hm(45) == "45분" and wl.hm(60) == "1시간 00분" and wl.hm(125) == "2시간 05분"
    assert wl.week_start(date(2026, 11, 28)) == date(2026, 11, 23)   # 토 → 월
    assert wl.week_start(date(2026, 11, 23)) == date(2026, 11, 23)
