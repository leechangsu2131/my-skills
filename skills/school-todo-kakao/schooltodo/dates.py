from __future__ import annotations

import re
from datetime import date, timedelta

KO_WEEKDAY = "월화수목금토일"


def fmt_md(d: date) -> str:
    return f"{d.month}/{d.day}"


def fmt_md_wd(d: date) -> str:
    return f"{d.month}/{d.day}({KO_WEEKDAY[d.weekday()]})"


def next_workday(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def resolve_year(month: int, day: int, today: date) -> date | None:
    """연도가 없는 '월/일'을 오늘과 가장 가까운 연도로 해석한다 (연말·연초 걸침 대응). 없는 날짜면 None."""
    best: date | None = None
    for y in (today.year - 1, today.year, today.year + 1):
        try:
            d = date(y, month, day)
        except ValueError:
            continue
        if best is None or abs((d - today).days) < abs((best - today).days):
            best = d
    return best


_FULL = re.compile(r"^\s*(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})\s*일?\s*\.?\s*$")
_SHORT = re.compile(r"^\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})\s*일?\s*\.?\s*$")


def parse_date(value, today: date) -> date | None:
    """시트에서 읽은 날짜 문자열(2026-11-17, 2026. 11. 17, 11/17, 11월 17일, 시리얼 숫자)을 날짜로."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return date(1899, 12, 30) + timedelta(days=int(value))
    s = str(value).strip()
    if not s:
        return None
    if re.fullmatch(r"\d{5}(\.\d+)?", s):
        return date(1899, 12, 30) + timedelta(days=int(float(s)))
    m = _FULL.match(s)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    m = _SHORT.match(s)
    if m:
        return resolve_year(int(m[1]), int(m[2]), today)
    return None
