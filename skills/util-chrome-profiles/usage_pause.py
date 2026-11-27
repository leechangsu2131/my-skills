"""AI 웹 창의 '사용량 일시 중지' 문구에서 다시 쓸 수 있는 시각을 읽고 적어 둔다(ISSUE-005).

    python usage_pause.py --text "일시 중지됨: 무료 사용량은 오후 12:10 이후 다시 제공됩니다. 그때 계속하세요." --name claude-web-3
    python usage_pause.py --list          # 적어 둔 것: 이름 · 다시 쓸 시각 · 남은 시간 (지난 것은 '지금 가능')
    python usage_pause.py --clear claude-web-3

- 읽는 것: "오후 12:10 이후 다시 제공", "12:10 PM 이후", "resets at 3pm", "try again after 12:10 PM", "2시간 후", "in 3 hours" 같은 꼴.
  시각이 지금보다 앞이면 다음 날로 본다.
- 적는 곳: 데이터 폴더 `내 문서\\my-skills-data\\util-chrome-profiles\\pauses.json` — {이름: {"resume": ISO 시각, "seen": 본 시각, "text": 문구 앞 120자}}.
  앱(chrome_profiles.py)이 창 글자를 읽어(ISSUE-004 의 UI 자동화) 이 함수를 부르고, 미리보기에 '⏸ 12:10' 표시·그 시각에 알림을 주는 것은 ISSUE-005.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

PAUSE_WORDS = re.compile(r"일시\s*중지|사용량|한도|limit|usage|try again|다시 (제공|사용|시도)|resets?", re.I)

_KO = re.compile(r"(오전|오후)\s*(\d{1,2})(?:\s*[:시]\s*(\d{1,2}))?\s*분?")
_EN = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap])\.?\s*m\.?\b", re.I)
_24 = re.compile(r"(?<![\d:])(\d{1,2}):(\d{2})(?![\d:])")
_REL_KO = re.compile(r"(\d+)\s*시간(?:\s*(\d+)\s*분)?\s*(?:후|뒤)|(\d+)\s*분\s*(?:후|뒤)")
_REL_EN = re.compile(r"in\s+(\d+)\s*(hours?|hrs?|minutes?|mins?)", re.I)


def _at(now: datetime, hour: int, minute: int) -> datetime | None:
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    t = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return t if t > now else t + timedelta(days=1)  # 이미 지난 시각이면 내일


def find_resume(text: str, now: datetime | None = None) -> datetime | None:
    """문구에서 다시 쓸 수 있는 시각. 일시 중지·한도 문구가 아니거나 시각이 없으면 None."""
    now = now or datetime.now()
    if not text or not PAUSE_WORDS.search(text):
        return None
    m = _KO.search(text)
    if m:
        h, mi = int(m.group(2)) % 12, int(m.group(3) or 0)
        return _at(now, h + (12 if m.group(1) == "오후" else 0), mi)
    m = _EN.search(text)
    if m:
        h, mi = int(m.group(1)) % 12, int(m.group(2) or 0)
        return _at(now, h + (12 if m.group(3).lower() == "p" else 0), mi)
    m = _REL_KO.search(text)
    if m:
        mins = int(m.group(1) or 0) * 60 + int(m.group(2) or 0) if m.group(1) else int(m.group(3))
        return (now + timedelta(minutes=mins)).replace(second=0, microsecond=0)
    m = _REL_EN.search(text)
    if m:
        n = int(m.group(1))
        mins = n * 60 if m.group(2).lower().startswith("h") else n
        return (now + timedelta(minutes=mins)).replace(second=0, microsecond=0)
    m = _24.search(text)
    if m:
        return _at(now, int(m.group(1)), int(m.group(2)))
    return None


# ---------- 적어 두기 ----------

def store_path() -> Path:
    sys.path.insert(0, str(next(p / "_shared" for p in Path(__file__).resolve().parents
                                if (p / "_shared" / "skill_env.py").is_file())))
    from skill_env import data_dir
    return data_dir("util-chrome-profiles") / "pauses.json"


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def record(path: Path, name: str, text: str, now: datetime | None = None) -> datetime | None:
    """문구에서 시각을 찾으면 적고 그 시각을 돌려준다. 못 찾으면 아무것도 안 적음."""
    now = now or datetime.now()
    resume = find_resume(text, now)
    if resume is None:
        return None
    data = load(path)
    data[name] = {"resume": resume.isoformat(timespec="minutes"), "seen": now.isoformat(timespec="minutes"),
                  "text": " ".join(text.split())[:120]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return resume


def due(data: dict, now: datetime | None = None) -> list[tuple[str, datetime, bool]]:
    """(이름, 다시 쓸 시각, 지금 가능한지) — 빠른 시각부터."""
    now = now or datetime.now()
    out = []
    for name, v in data.items():
        try:
            t = datetime.fromisoformat(v["resume"])
        except (KeyError, ValueError):
            continue
        out.append((name, t, t <= now))
    return sorted(out, key=lambda x: x[1])


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="AI 웹 창 사용량 일시 중지 시각 적기")
    ap.add_argument("--text", help="창에 뜬 문구")
    ap.add_argument("--name", default="창", help="어느 창·작업자인지(예: claude-web-3)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--clear")
    a = ap.parse_args(argv)
    path = store_path()
    if a.text:
        t = record(path, a.name, a.text)
        if t is None:
            print("다시 쓸 시각을 못 찾았어요.")
            return 1
        print(f"⏸ {a.name}: {t:%m-%d %H:%M} 부터 다시 쓸 수 있어요 — 적어 둠")
    if a.clear:
        data = load(path)
        data.pop(a.clear, None)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.list or not (a.text or a.clear):
        now = datetime.now()
        rows = due(load(path), now)
        if not rows:
            print("적어 둔 일시 중지가 없어요.")
        for name, t, ok in rows:
            left = "지금 가능" if ok else f"{int((t - now).total_seconds() // 60)}분 남음"
            print(f"{'▶' if ok else '⏸'} {name}  {t:%m-%d %H:%M}  ({left})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
