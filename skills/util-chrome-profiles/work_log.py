"""작업 시간 기록 남기기 (ISSUE-006).

앱의 '작업 시간 재기'를 멈출 때 한 줄씩 데이터 폴더 `work_log.csv` 에 남기고, 하루·주 합계를 본다.

    python work_log.py                 # 이번 주(월~오늘) 합계
    python work_log.py --days 1        # 오늘만
    python work_log.py --days 30       # 최근 30일

- 칸: 날짜, 시작, 끝, 분, 이름, 그룹   (이름은 프로필·그룹 이름. 창 글자·학생 정보는 남기지 않는다)
- 1분이 안 되는 것은 남기지 않는다(잘못 눌러 시작·멈춘 경우).
- 날짜는 시작한 날로 센다. 자정을 넘기면 시작한 날에 모두 센다.
- 기록은 '재기 시작~멈춤' 시계 시간이다. 창이 실제로 앞에 있던 시간(활성 시간)은 아직 아니다(ISSUE-006 남은 것).
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

FIELDS = ["날짜", "시작", "끝", "분", "이름", "그룹"]
MIN_MINUTES = 1


def store_path() -> Path:
    import pathlib
    here = pathlib.Path(__file__).resolve().parent
    sys.path.insert(0, str(next(p / "_shared" for p in here.parents if (p / "_shared" / "skill_env.py").is_file())))
    from skill_env import data_dir
    return data_dir("util-chrome-profiles") / "work_log.csv"


def append(path: Path, name: str, group: str, start: float, end: float) -> bool:
    """한 줄 남긴다. 1분 미만이거나 시각이 거꾸로면 남기지 않고 False."""
    minutes = int((end - start) // 60)
    if minutes < MIN_MINUTES:
        return False
    s, e = datetime.fromtimestamp(start), datetime.fromtimestamp(end)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.is_file() or path.stat().st_size == 0
    with open(path, "a", encoding="utf-8-sig", newline="") as f:   # 엑셀에서 바로 열리게 BOM
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        w.writerow([s.date().isoformat(), f"{s:%H:%M}", f"{e:%H:%M}", minutes, name, group or ""])
    return True


def read(path: Path) -> list[dict]:
    """기록 전부. 파일이 없거나 깨진 줄은 건너뛴다."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return []
    out = []
    for r in rows:
        try:
            out.append({"date": date.fromisoformat(r["날짜"]), "minutes": int(r["분"]),
                        "name": r.get("이름") or "", "group": r.get("그룹") or ""})
        except (KeyError, ValueError, TypeError):
            continue
    return out


def summarize(rows: list[dict], since: date, until: date) -> dict:
    """since~until(양끝 포함) 합계: {"total": 분, "by_day": {날짜: 분}, "by_name": {이름: 분}, "by_group": {그룹: 분}}"""
    total, by_day, by_name, by_group = 0, {}, {}, {}
    for r in rows:
        if not since <= r["date"] <= until:
            continue
        m = r["minutes"]
        total += m
        by_day[r["date"]] = by_day.get(r["date"], 0) + m
        by_name[r["name"]] = by_name.get(r["name"], 0) + m
        if r["group"]:
            by_group[r["group"]] = by_group.get(r["group"], 0) + m
    return {"total": total, "by_day": dict(sorted(by_day.items())),
            "by_name": dict(sorted(by_name.items(), key=lambda x: -x[1])),
            "by_group": dict(sorted(by_group.items(), key=lambda x: -x[1]))}


def hm(minutes: int) -> str:
    return f"{minutes // 60}시간 {minutes % 60:02d}분" if minutes >= 60 else f"{minutes}분"


def week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="작업 시간 기록 합계")
    ap.add_argument("--days", type=int, help="오늘 포함 최근 N일(기본: 이번 주 월요일부터)")
    a = ap.parse_args(argv)
    today = date.today()
    since = today - timedelta(days=a.days - 1) if a.days and a.days > 0 else week_start(today)
    res = summarize(read(store_path()), since, today)
    if not res["total"]:
        print(f"{since} ~ {today} 작업 시간 기록이 없어요.")
        return 0
    print(f"{since} ~ {today} 합계 {hm(res['total'])}")
    for d, m in res["by_day"].items():
        print(f"  {d}  {hm(m)}")
    for title, key in (("이름별", "by_name"), ("그룹별", "by_group")):
        if res[key]:
            print(title)
            for k, m in res[key].items():
                print(f"  {k}  {hm(m)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
