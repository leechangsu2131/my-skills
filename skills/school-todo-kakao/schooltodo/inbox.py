"""빠른입력: 급하게 생긴 일정을 시트 한 칸에 아무 말로 적어 두면 다음 sync에서 일정DB 행으로 옮긴다.

  입력 예)  내일 학부모 상담 전화 / 11/20 체육대회 물품 확인 / 다음주 화요일 출장 복명 / 금요일 공문 마감 / 장학지도 자료 준비
  날짜가 없으면 오늘(다음 아침 메시지)로 넣는다. '출장'이 들어 있으면 구분=출장, 아니면 개인.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from .dates import KO_WEEKDAY, resolve_year
from .sync import make_key

REL = {"오늘": 0, "내일": 1, "모레": 2, "글피": 3}
_SEP = r"[\s,:·-]*"
_RE_REL = re.compile(rf"^\s*(오늘|내일|모레|글피){_SEP}")
_RE_FULL = re.compile(rf"^\s*(\d{{4}})\s*[-./년]\s*(\d{{1,2}})\s*[-./월]\s*(\d{{1,2}})\s*일?{_SEP}")
_RE_MD = re.compile(rf"^\s*(\d{{1,2}})\s*(?:/|\.|월)\s*(\d{{1,2}})\s*일?{_SEP}")
_RE_WEEK = re.compile(rf"^\s*(?:(이번|다음|다다음)\s*주\s*([월화수목금토일])(?:요일)?|([월화수목금토일])요일){_SEP}")
_WEEK_OFFSET = {"이번": 0, "다음": 1, "다다음": 2}


@dataclass(frozen=True)
class Parsed:
    date: date
    category: str
    text: str


def parse_line(line: str, today: date) -> Parsed | None:
    """한 줄을 (날짜, 구분, 내용)으로. 내용이 비면 None. 날짜가 없으면 오늘."""
    s = line.strip()
    d: date | None = None
    m = _RE_REL.match(s)
    if m:
        d, s = today + timedelta(days=REL[m[1]]), s[m.end():]
    if d is None and (m := _RE_FULL.match(s)):
        try:
            d = date(int(m[1]), int(m[2]), int(m[3]))
            s = s[m.end():]
        except ValueError:
            d = None
    if d is None and (m := _RE_MD.match(s)):
        d = resolve_year(int(m[1]), int(m[2]), today)
        if d is not None:
            s = s[m.end():]
    if d is None and (m := _RE_WEEK.match(s)):
        wd = KO_WEEKDAY.index(m[2] or m[3])
        if m[1]:  # 이번/다음/다다음 주 + 요일
            monday = today - timedelta(days=today.weekday())
            d = monday + timedelta(days=7 * _WEEK_OFFSET[m[1]] + wd)
        else:  # 그냥 'OO요일' = 오늘 포함 가장 가까운 그 요일
            d = today + timedelta(days=(wd - today.weekday()) % 7)
        s = s[m.end():]
    text = s.strip()
    if not text:
        return None
    return Parsed(d or today, "출장" if "출장" in text else "개인", text)


def plan_inbox(items: list[tuple[int, str]], existing_keys: set[str], today: date) -> tuple[list[dict], dict[int, str]]:
    """items: [(시트 행번호, 입력 글)]. -> (새 일정DB 행들, {행번호: 처리 표시})."""
    rows: list[dict] = []
    marks: dict[int, str] = {}
    have = set(existing_keys)
    for rownum, line in items:
        p = parse_line(line, today)
        if p is None:
            marks[rownum] = "⚠ 내용 없음"
            continue
        if p.date < today:
            marks[rownum] = "⚠ 지난 날짜: 날짜를 고쳐 다시 적어 주세요"
            continue
        key = make_key(p.date, p.text)
        if key in have:
            marks[rownum] = "✔ 이미 있음"
            continue
        have.add(key)
        rows.append(
            {
                "키": key, "날짜": p.date.isoformat(), "구분": p.category, "내용": p.text,
                "상태": "", "출처": "수동", "대상": "전체",  # 내가 직접 적은 것은 걸러지면 안 된다
            }
        )
        marks[rownum] = "✔ 반영"
    return rows, marks


class InboxSheet:
    """'빠른입력' 탭: A열=내용(자유 입력), B열=처리(자동 표시). 첫 행이 '내용'이면 제목 행으로 본다."""

    def __init__(self, worksheet):
        self._ws = worksheet

    def pending(self) -> list[tuple[int, str]]:
        out = []
        for i, row in enumerate(self._ws.get_all_values(), start=1):
            text = (row[0] if row else "").strip()
            done = (row[1] if len(row) > 1 else "").strip()
            if i == 1 and text in ("내용", "빠른입력"):
                continue
            if text and not done:
                out.append((i, text))
        return out

    def append(self, line: str) -> None:
        """'빠른입력' 맨 아래에 한 줄 덧붙인다(A열). 수업 비서 칸 등 다른 곳에서 `_ws` 를 직접 건드리지 않게 둔 공개 함수.
        RAW: '=' 로 시작하는 글이 수식이 되거나 날짜가 시트 마음대로 바뀌지 않게 글자 그대로 넣는다."""
        self._ws.append_row([line], value_input_option="RAW", table_range="A1")

    def mark(self, marks: dict[int, str]) -> None:
        if marks:
            self._ws.batch_update([{"range": f"B{n}", "values": [[v]]} for n, v in sorted(marks.items())])
