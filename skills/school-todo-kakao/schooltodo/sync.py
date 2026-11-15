"""공용 시트에서 읽은 후보 중 일정DB에 없는 것만 새 행으로 만든다."""
from __future__ import annotations

import re
from datetime import date, timedelta

from .classify import ClassifyConfig, classify
from .dates import parse_date
from .sources import Cand


def make_key(d: date, text: str) -> str:
    compact = re.sub(r"\s+", "", text)
    return f"{d:%m%d}-{compact[:10]}"


def plan_sync(
    existing_rows: list[dict],
    cands: list[Cand],
    today: date,
    cfg: ClassifyConfig | None = None,
    horizon_days: int = 45,
) -> list[dict]:
    """오늘 이후 horizon_days 이내 후보 중, 같은 키가 DB에 없는 것만 돌려준다.
    상태·직접 고친 내용 같은 기존 행은 건드리지 않는다."""
    have = {(r.get("키") or "").strip() for r in existing_rows}
    last = today + timedelta(days=horizon_days)
    added: list[dict] = []
    for c in cands:
        if c.date < today or c.date > last:
            continue
        key = make_key(c.date, c.text)
        if key in have:
            continue
        have.add(key)
        added.append(
            {
                "키": key,
                "날짜": c.date.isoformat(),
                "구분": c.category,
                "내용": c.text,
                "상태": "",
                "출처": "자동",
                # 내 이름으로 찾은 출장은 어떤 경우에도 걸러지면 안 된다
                "대상": "전체" if c.category == "출장" else classify(c.text, cfg),
            }
        )
    return added
