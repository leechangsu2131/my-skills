"""공용 시트(주간 일정, 오늘 일정)를 읽어 (날짜, 구분, 내용) 후보로 바꾼다."""
from __future__ import annotations

import csv
import io
import re
from datetime import date
from typing import NamedTuple

import requests

from .dates import resolve_year


class SourceError(RuntimeError):
    pass


class Cand(NamedTuple):
    date: date
    category: str  # 학교 / 출장 / 공지
    text: str


# ---------- 읽기 ----------
def read_csv_file(path: str) -> list[list[str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def fetch_rows(sheet_id: str, gid: str = "0") -> list[list[str]]:
    """'링크가 있는 모든 사용자 보기'로 공유된 시트 탭을 로그인 없이 CSV로 읽는다.
    공개 로그에 시트 주소가 남지 않도록 오류 메시지에는 주소를 넣지 않는다."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        r = requests.get(url, timeout=30)
    except requests.RequestException:
        raise SourceError("공용 시트에 연결하지 못했습니다(네트워크 오류)") from None
    if r.status_code != 200 or "csv" not in r.headers.get("content-type", ""):
        raise SourceError(
            f"공용 시트를 읽지 못했습니다(HTTP {r.status_code}). "
            "'링크가 있는 모든 사용자 보기' 공유인지, gid가 맞는지 확인하세요."
        )
    r.encoding = "utf-8"
    return list(csv.reader(io.StringIO(r.text)))


# ---------- 공통 ----------
_JUNK = re.compile(r"^[\s\-–—_=\\|·•*]*$")


def split_lines(cell: str | None) -> list[str]:
    out: list[str] = []
    for line in (cell or "").replace("\r", "").split("\n"):
        line = line.strip()
        if line and not _JUNK.match(line):
            out.append(line)
    return out


def _cell(row: list[str], idx: int | None) -> str:
    if idx is None or idx >= len(row):
        return ""
    return row[idx] or ""


# ---------- 주간 일정 ----------
_DATE_CELL = re.compile(r"^\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*$")


def parse_week(rows: list[list[str]], today: date) -> list[Cand]:
    """'11월 17일' 같은 날짜 칸을 찾아, 바로 아래 칸의 줄(줄바꿈 = 일정 하나)을 그 날짜의 일정으로 읽는다."""
    out: list[Cand] = []
    for r, row in enumerate(rows):
        if r + 1 >= len(rows):
            break
        for c, cell in enumerate(row):
            m = _DATE_CELL.match(cell or "")
            if not m:
                continue
            d = resolve_year(int(m[1]), int(m[2]), today)
            if d is None:
                continue
            for line in split_lines(_cell(rows[r + 1], c)):
                if line.startswith("*세부"):
                    continue
                out.append(Cand(d, "학교", line))
    return out


# ---------- 오늘 일정 ----------
_NOTICE_DATE = re.compile(
    r"(?<!\d)(\d{1,2})\s*[./]\s*(\d{1,2})(?!\d|\s*(?:교시|시|명|차))|(\d{1,2})\s*월\s*(\d{1,2})\s*일"
)
_HEADERS = ("오늘의 일정", "시간", "대상", "출장정보", "공지사항")


def parse_today(rows: list[list[str]], today: date, my_name: str = "") -> list[Cand]:
    """'오늘의 일정/시간/대상/출장정보/공지사항' 표를 읽는다.
    - 오늘의 일정: 시간·대상을 붙여 '학교' 일정으로
    - 출장정보: MY_NAME이 들어 있는 줄만 '출장'으로 (남의 출장은 제외)
    - 공지사항: 날짜가 적힌 줄만 그 날짜의 '공지'로 (날짜 없는 상시 안내는 제외)"""
    hdr = next(
        (i for i, row in enumerate(rows) if any((c or "").strip() == "오늘의 일정" for c in row)),
        None,
    )
    if hdr is None:
        return []
    cols: dict[str, int] = {}
    for j, c in enumerate(rows[hdr]):
        name = (c or "").replace("✔", "").strip()
        if name in _HEADERS:
            cols[name] = j

    out: list[Cand] = []
    data = rows[hdr + 1 : hdr + 21]
    for k, row in enumerate(data):
        title = " ".join(split_lines(_cell(row, cols.get("오늘의 일정"))))
        if title and not title.startswith("오늘 일정 없음"):
            time = _cell(row, cols.get("시간")).strip()
            target = _cell(row, cols.get("대상")).strip()
            text = f"{time} {title}".strip()
            if target not in ("", "-", "전체"):
                text += f" ({target})"
            out.append(Cand(today, "학교", text))

        if my_name:
            for line in split_lines(_cell(row, cols.get("출장정보"))):
                if my_name in line:
                    out.append(Cand(today, "출장", line))

        if k == 0:  # 공지사항은 첫 줄 칸에 통째로 들어 있다
            for line in split_lines(_cell(row, cols.get("공지사항"))):
                m = _NOTICE_DATE.search(line)
                if not m:
                    continue
                mo, dy = (m[1], m[2]) if m[1] else (m[3], m[4])
                d = resolve_year(int(mo), int(dy), today)
                if d is None:
                    continue
                text = (line[: m.start()] + line[m.end() :]).strip(" ☆★※•·-:\t")
                if text:
                    out.append(Cand(d, "공지", text))
    return out
