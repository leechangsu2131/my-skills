"""일정DB 행 -> 아침 메시지. 카톡 텍스트 템플릿은 200자 제한이라 나눠 보낼 수 있게 만든다."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .classify import OTHER
from .dates import fmt_md, fmt_md_wd, next_workday, parse_date

MAX_CHARS = 190  # 카카오 제한 200자에서 여유를 둔다
CATEGORY_ORDER = {"출장": 0, "개인": 1, "학교": 2, "공지": 3}
LATE_CAP = 5


@dataclass(frozen=True)
class Item:
    date: date
    category: str
    text: str
    source: str
    target: str
    status: str


def parse_items(rows: list[dict], today: date) -> list[Item]:
    items = []
    for r in rows:
        d = parse_date(r.get("날짜", ""), today)
        text = " ".join((r.get("내용") or "").split())
        if d is None or not text:
            continue
        items.append(
            Item(
                d,
                (r.get("구분") or "").strip() or "학교",
                text,
                (r.get("출처") or "").strip(),
                (r.get("대상") or "").strip(),
                (r.get("상태") or "").strip(),
            )
        )
    return items


def _order(items: list[Item]) -> list[Item]:
    return sorted(items, key=lambda i: CATEGORY_ORDER.get(i.category, 2))  # 안정 정렬: 같은 구분은 시트 순서


def _bullet(i: Item, with_date: bool = False) -> str:
    prefix = f"{fmt_md(i.date)} " if with_date else ""
    return f"• {prefix}[{i.category}] {i.text}"


def build_message(rows: list[dict], today: date) -> tuple[list[str], int]:
    """(메시지 줄 목록, 보낼 일정 개수). 상태 칸이 비어 있는 행만 보낸다(✔·검토대기 등은 제외)."""
    items = [i for i in parse_items(rows, today) if not i.status and i.target != OTHER]
    todays = _order([i for i in items if i.date == today])
    nxt = next_workday(today)
    nexts = _order([i for i in items if i.date == nxt])
    # 지연은 내가 적은 할 일만. 학교 일정(자동)은 지나가면 그냥 끝난 일이다.
    late = sorted((i for i in items if i.date < today and i.source != "자동"), key=lambda i: i.date)

    lines = [f"📅 {fmt_md_wd(today)} 오늘"]
    lines += [_bullet(i) for i in todays] or ["• 등록된 일정 없음"]
    if late:
        lines.append("⚠ 지연")
        lines += [_bullet(i, with_date=True) for i in late[:LATE_CAP]]
        if len(late) > LATE_CAP:
            lines.append(f"• … 외 {len(late) - LATE_CAP}건")
    lines.append(f"👉 {fmt_md_wd(nxt)} 미리보기")
    lines += [_bullet(i) for i in nexts] or ["• 없음"]
    return lines, len(todays) + len(late) + len(nexts)


def _size(ls: list[str]) -> int:
    return sum(len(x) for x in ls) + max(len(ls) - 1, 0)


def _pack(lines: list[str], limit: int) -> list[list[str]]:
    line_max = limit - 25  # 소제목을 다음 묶음에 이어 붙일 여유
    chunks: list[list[str]] = []
    cur: list[str] = []
    header: str | None = None
    for raw in lines:
        line = raw if len(raw) <= line_max else raw[: line_max - 1] + "…"
        is_bullet = line.startswith("•")
        if not is_bullet:
            header = line
        if cur and _size(cur + [line]) > limit:
            orphan = cur.pop() if not cur[-1].startswith("•") else None  # 소제목만 남지 않게
            if cur:
                chunks.append(cur)
            if orphan is not None:
                cur = [orphan]
            elif is_bullet and header:
                cur = [header + " (계속)"]
            else:
                cur = []
        cur.append(line)
    if cur:
        chunks.append(cur)
    return chunks


def split_message(lines: list[str], limit: int = MAX_CHARS) -> list[str]:
    chunks = _pack(lines, limit)
    if len(chunks) == 1:
        return ["\n".join(chunks[0])]
    chunks = _pack(lines, limit - 8)  # '(1/3) ' 표시 자리
    n = len(chunks)
    return [f"({i}/{n}) " + "\n".join(c) for i, c in enumerate(chunks, 1)]
