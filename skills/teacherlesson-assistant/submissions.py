"""✅ 제출 확인표 (T108) — 동의서·신청서·과제를 누가 냈는지 번호 칸으로 체크한다.

저장: <데이터 폴더>/submissions/<제목>.json   {"title": 제목, "total": 반 인원, "marks": {"번호": "낸 날짜"}}
명단: <데이터 폴더>/roster.txt (선택)  한 줄에 한 명, 줄 순서 = 번호. "3 이름" 처럼 번호를 앞에 써도 된다.
  이름은 이 PC 의 화면에만 보이고, 로그·오류 글·저장소에는 쓰지 않는다. 명단이 없으면 번호만 쓴다.
네트워크·AI 호출 없음. 이 파일은 assistant_server 를 불러오지 않는다(시험에서 폴더만 바꿔 쓰기 쉽게).
"""
from __future__ import annotations

import json
import os
import pathlib
import re
from datetime import date

MAX_TOTAL = 60
DEFAULT_TOTAL = 25


def slug(title: str) -> str:
    """파일 이름으로 쓸 수 있게 다듬는다. 비면 ValueError."""
    text = re.sub(r'[\\/:*?"<>|\s]+', "_", str(title or "")).strip("._")[:60]
    if not text:
        raise ValueError("제목을 적어 주세요.")
    return text


def _path(base: pathlib.Path, title: str) -> pathlib.Path:
    return pathlib.Path(base) / f"{slug(title)}.json"


def _write(path: pathlib.Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _check_total(total) -> int:
    try:
        n = int(total)
    except (TypeError, ValueError):
        raise ValueError("반 인원은 숫자로 적어 주세요.") from None
    if not 1 <= n <= MAX_TOTAL:
        raise ValueError(f"반 인원은 1~{MAX_TOTAL} 사이로 적어 주세요.")
    return n


def load(base, title: str) -> dict | None:
    return _load_file(_path(base, title))


def create(base, title: str, total) -> dict:
    """새 확인표. 같은 제목이 이미 있으면 덮어쓰지 않고 ValueError."""
    n = _check_total(total)
    title = str(title or "").strip()
    path = _path(base, title)
    if path.exists():
        raise ValueError("같은 제목의 확인표가 이미 있어요.")
    rec = {"title": title, "total": n, "marks": {}}
    _write(path, rec)
    return rec


def mark(base, title: str, no, done: bool = True, today: date | None = None) -> dict:
    """번호 하나를 낸 것으로(done=True) 또는 안 낸 것으로 바꾼다."""
    rec = load(base, title)
    if rec is None:
        raise ValueError("그 확인표를 찾을 수 없어요.")
    try:
        n = int(no)
    except (TypeError, ValueError):
        raise ValueError("번호가 잘못됐어요.") from None
    if not 1 <= n <= int(rec["total"]):
        raise ValueError(f"번호는 1~{rec['total']} 사이여야 해요.")
    key = str(n)
    if done:
        rec["marks"].setdefault(key, (today or date.today()).isoformat())
    else:
        rec["marks"].pop(key, None)
    _write(_path(base, title), rec)
    return rec


def missing(rec: dict) -> list[int]:
    """아직 안 낸 번호(작은 순서)."""
    marks = rec.get("marks", {})
    return [n for n in range(1, int(rec["total"]) + 1) if str(n) not in marks]


def missing_text(rec: dict) -> str:
    """알림장에 붙여 넣을 글. 이름 없이 번호만."""
    left = missing(rec)
    if not left:
        return f"{rec['title']}: 모두 냈어요."
    return f"{rec['title']} 아직 안 낸 번호: " + ", ".join(str(n) for n in left) + "번"


def summarize(rec: dict) -> dict:
    left = missing(rec)
    return {"title": rec["title"], "total": rec["total"], "done": int(rec["total"]) - len(left), "missing": left}


def list_all(base) -> list[dict]:
    root = pathlib.Path(base)
    if not root.is_dir():
        return []
    items = []
    for path in sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        rec = _load_file(path)
        if rec:
            items.append(summarize(rec))
    return items


def _load_file(path: pathlib.Path) -> dict | None:
    try:
        rec = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if not isinstance(rec, dict) or not isinstance(rec.get("marks"), dict) or "total" not in rec or "title" not in rec:
        return None
    return rec


def load_roster(path) -> dict[int, str]:
    """명단 파일 → {번호: 이름}. 파일이 없으면 빈 사전."""
    try:
        lines = pathlib.Path(path).read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return {}
    roster: dict[int, str] = {}
    seq = 0
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        seq += 1
        m = re.match(r"^(\d{1,2})[.\s,:)]+(\S.*)$", text)
        if m:
            roster[int(m.group(1))] = m.group(2).strip()
        else:
            roster[seq] = text
    return roster
