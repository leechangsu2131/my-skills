"""하루 녹음 나누기 표 (T116, ISSUE-055 ②): 녹음 파일은 만들거나 자르지 않고 '어디서 자를지' 표만 만든다.

    python day_split.py                          # 오늘
    python day_split.py --date 2026-11-30
    python day_split.py --date 2026-11-30 --last 4   # 그날 마지막 교시를 직접 알려 줄 때

- 읽는 것(데이터 폴더): 녹음 조각 day_audio/<날짜>/<시작 HHMMSS>.<확장자>, 세션의 '수업 시작'·'수업 마침' 메모,
  config.json 의 periods, 그날만 다른 시각 day_split/<날짜>.fix.json
- 쓰는 것(데이터 폴더): day_split/<날짜>.json, day_split/<날짜>.md. 소리·메모 글은 옮기지 않는다.
- 나누는 기준: 기록(교사가 누른 시각)이 먼저, 기록이 없는 쪽은 시간표 시각으로 '추정'. 종소리는 쓰지 않는다.
- 고침 파일 모양 (그날 있는 교시를 **모두** 적는다. lunch 는 없어도 됨):
  {"periods": [{"no": 1, "start": "09:00", "end": "09:35"}], "lunch": {"start": "12:00", "end": "13:00"}}
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from datetime import date, datetime, timedelta

SKILL_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(next(p / "_shared" for p in SKILL_DIR.parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # noqa: E402
sys.path.insert(0, str(SKILL_DIR))
import audio_export  # noqa: E402  (ffmpeg 찾기)
import transcribe  # noqa: E402  (메모 시각 읽기)

SKILL = "teacherlesson-assistant"
AUDIO_EXTS = (".webm", ".ogg", ".opus", ".m4a", ".mp4", ".mp3", ".aac", ".wav", ".flac", ".mka")
TOLERANCE = timedelta(minutes=60)  # 시간표와 이보다 크게 다른 기록은 잘못 누른 것으로 본다
MIN_RECORD = timedelta(seconds=60)  # 이보다 짧은 '시작~마침'은 누르기 실수
MIN_SEGMENT = timedelta(seconds=1)
DEFAULT_LENGTH = timedelta(minutes=40)
MAX_PIECE_SECONDS = 4 * 3600  # 파일이 바뀐 시각으로 길이를 짐작할 때의 한도
RECORDED, GUESSED = "기록", "추정"


class SplitError(Exception):
    """화면에 그대로 보여 줄 수 있는 실패 이유."""


# ──────────────────────────── 순수 함수 ────────────────────────────

def clock(day: date, text) -> datetime:
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(text))
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise SplitError(f"시각은 09:00 처럼 적어 주세요: {text!r}")
    return datetime(day.year, day.month, day.day, int(m.group(1)), int(m.group(2)))


def timetable(day: date, periods) -> dict[int, tuple[datetime, datetime]]:
    """[{"no", "start", "end"}] → {교시: (시작, 끝)}. 모양이 틀리면 SplitError."""
    if not isinstance(periods, list):
        raise SplitError("periods 는 목록이어야 해요.")
    table = {}
    for item in periods:
        try:
            no, start, end = int(item["no"]), clock(day, item["start"]), clock(day, item["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SplitError(f"교시는 no·start·end 를 모두 적어 주세요: {item!r}") from exc
        if no < 1 or end <= start or no in table:
            raise SplitError(f"교시 번호나 시각이 이상해요: {item!r}")
        table[no] = (start, end)
    return table


def lunch_from(table: dict) -> tuple[datetime, datetime] | None:
    """시간표에서 점심 찾기: 30분 이상 비고 가운데가 11~14시인 틈 가운데 가장 긴 것."""
    slots = sorted(table.values())
    gaps = [(a[1], b[0]) for a, b in zip(slots, slots[1:]) if b[0] - a[1] >= timedelta(minutes=30)]
    gaps = [g for g in gaps if 11 <= (g[0] + (g[1] - g[0]) / 2).hour < 14]
    return max(gaps, key=lambda g: g[1] - g[0], default=None)


def piece_start(day: date, name: str) -> datetime | None:
    """'<HHMMSS>.<확장자>' (뒤에 _2 같은 꼬리 가능) → 시작 시각. 녹음 파일이 아니면 None."""
    path = pathlib.Path(name)
    m = re.match(r"(\d{2})(\d{2})(\d{2})(?!\d)", path.stem)
    if path.suffix.lower() not in AUDIO_EXTS or not m:
        return None
    hour, minute, second = map(int, m.groups())
    if hour > 23 or minute > 59 or second > 59:
        return None
    return datetime(day.year, day.month, day.day, hour, minute, second)


def session_records(day: date, session: dict, default_period=None, tz=None) -> list[dict]:
    """세션 하나의 '수업 시작'~'수업 마침' → [{"period", "start", "end"|None}] (PC 시각, 그날 것만)."""
    records = []
    memos = session.get("memos") if isinstance(session, dict) else None
    for memo in memos if isinstance(memos, list) else []:
        if not isinstance(memo, dict) or memo.get("kind") != "sys" or memo.get("text") not in ("수업 시작", "수업 마침"):
            continue
        at = transcribe.parse_iso(memo.get("at"))
        if at is None:
            continue
        if at.tzinfo is not None:  # 화면은 UTC 로 저장한다
            at = at.astimezone(tz).replace(tzinfo=None)
        if at.date() != day:  # 지난 날짜 수업을 열고 누른 것은 그날 녹음이 아니다
            continue
        if memo["text"] == "수업 시작":
            period = memo.get("period") or session.get("period") or default_period
            try:
                period = int(period or 0)
            except (TypeError, ValueError):
                period = 0
            records.append({"period": period, "start": at, "end": None})
        elif records and records[-1]["end"] is None and at >= records[-1]["start"]:
            records[-1]["end"] = at
    return records


def _record_lesson(no: int, records: list[dict], slot, notes: list[str]) -> dict | None:
    """한 교시의 기록들 → 수업 구간 하나. 쓸 기록이 없으면 None."""
    usable = []
    for rec in sorted(records, key=lambda r: r["start"]):
        start, end = rec["start"], rec["end"]
        if end is not None and end - start < MIN_RECORD:
            notes.append(f"{no}교시 {start:%H:%M} 기록은 1분이 안 돼 누르기 실수로 보고 뺐어요.")
            continue
        if slot and not (slot[0] - TOLERANCE <= start <= slot[1] + TOLERANCE):
            notes.append(f"{no}교시 {start:%H:%M} 기록은 시간표와 1시간 넘게 달라 쓰지 않았어요. "
                         "시간이 바뀐 날이면 고침 파일에 그날 시각을 적어 주세요.")
            continue
        if slot and end is not None and end > slot[1] + TOLERANCE:
            notes.append(f"{no}교시 '수업 마침'({end:%H:%M})이 시간표보다 1시간 넘게 늦어 쓰지 않았어요.")
            end = None
        usable.append((start, end))
    if not usable:
        return None
    start = usable[0][0]
    ends = [e for _, e in usable if e is not None]
    if usable[-1][1] is not None:
        return {"period": no, "start": start, "end": max(ends), "from": RECORDED, "to": RECORDED}
    last_start = usable[-1][0]  # 마지막으로 시작한 것에 '마침'이 없다
    end = slot[1] if slot else last_start + DEFAULT_LENGTH
    if end <= last_start:
        end = last_start + (slot[1] - slot[0] if slot else DEFAULT_LENGTH)
    return {"period": no, "start": start, "end": max([end, *ends]), "from": RECORDED, "to": GUESSED}


def _free_parts(start: datetime, end: datetime, taken: list[dict]) -> list[tuple[datetime, datetime]]:
    parts, at = [], start
    for other in sorted(taken, key=lambda x: x["start"]):
        if other["end"] <= at or other["start"] >= end:
            continue
        if other["start"] > at:
            parts.append((at, other["start"]))
        at = max(at, other["end"])
    if at < end:
        parts.append((at, end))
    return parts


def lesson_segments(table: dict, records: list[dict], notes: list[str], usual: dict | None = None) -> list[dict]:
    """교시 구간(시작순). 기록이 있는 교시를 먼저 놓고, 시간표만 있는 교시는 남은 시간에 놓는다.

    table = 그날 있는 교시. usual = table 에 없는 교시의 기록이 그럴듯한지 볼 평소 시간표.
    """
    unknown = [r for r in records if r["period"] < 1]
    if unknown:
        notes.append(f"몇 교시인지 알 수 없는 기록 {len(unknown)}개는 쓰지 않았어요.")
    numbers = sorted(set(table) | {r["period"] for r in records if r["period"] >= 1})
    recorded, guessed = [], []
    for no in numbers:
        slot = table.get(no) or (usual or {}).get(no)
        lesson = _record_lesson(no, [r for r in records if r["period"] == no], slot, notes)
        if lesson:
            recorded.append(lesson)
        elif no in table:
            guessed.append({"period": no, "start": table[no][0], "end": table[no][1], "from": GUESSED, "to": GUESSED})
    recorded.sort(key=lambda x: (x["start"], x["period"]))
    for before, after in zip(recorded, recorded[1:]):
        if before["end"] > after["start"]:
            if before["to"] == RECORDED:
                notes.append(f"{before['period']}교시 끝과 {after['period']}교시 시작 기록이 겹쳐 "
                             f"{after['start']:%H:%M} 에서 나눴어요.")
            before["end"], before["to"] = after["start"], GUESSED
    placed = []
    for lesson in recorded:
        if lesson["end"] - lesson["start"] >= MIN_SEGMENT:
            placed.append(lesson)
        else:
            notes.append(f"{lesson['period']}교시는 다른 교시 기록과 시간이 겹쳐 표에서 뺐어요.")
    for lesson in guessed:
        parts = _free_parts(lesson["start"], lesson["end"], placed)
        best = max(parts, key=lambda p: p[1] - p[0], default=None)
        if not best or best[1] - best[0] < MIN_RECORD:
            notes.append(f"{lesson['period']}교시는 다른 교시 기록과 시간이 겹쳐 표에서 뺐어요.")
            continue
        lesson["start"], lesson["end"] = best
        placed.append(lesson)
    return sorted(placed, key=lambda x: (x["start"], x["period"]))


def _overlap(a_start, a_end, b_start, b_end) -> float:
    return max(0.0, (min(a_end, b_end) - max(a_start, b_start)).total_seconds())


def _with_pieces(kind: str, start: datetime, end: datetime, basis: str, pieces: list[dict]) -> dict:
    used, covered, reached = [], 0.0, start
    for piece in pieces:  # 시작순
        begin, finish = max(start, piece["start"]), min(end, piece["start"] + timedelta(seconds=piece["seconds"]))
        if (finish - begin).total_seconds() < 0.5:
            continue
        used.append({"파일": piece["file"], "시작초": round((begin - piece["start"]).total_seconds()),
                     "끝초": round((finish - piece["start"]).total_seconds())})
        covered += max(0.0, (finish - max(begin, reached)).total_seconds())
        reached = max(reached, finish)
    length = (end - start).total_seconds()
    return {"종류": kind, "시작": f"{start:%H:%M:%S}", "끝": "24:00:00" if end.date() > start.date() else f"{end:%H:%M:%S}",
            "근거": basis, "길이초": round(length), "빈초": round(length - covered), "조각": used}


def split_day(day: date, pieces: list[dict], periods, records: list[dict], fix: dict | None = None,
              last_period: int | None = None) -> dict:
    """pieces = [{"file", "start": datetime, "seconds"}], records = session_records() 를 모은 것.

    fix 에 periods 가 있으면 그날은 그 교시만 있다고 본다. 없으면 시간표에서 last_period 와
    기록이 있는 마지막 교시 가운데 큰 쪽까지만 쓴다(둘 다 모르면 시간표 전체).
    """
    notes: list[str] = []
    base = timetable(day, periods)
    lunch = lunch_from(base)
    if fix is not None and not isinstance(fix, dict):
        raise SplitError("고침 파일 모양이 달라요.")
    usual = None  # 고침 파일이 있는 날은 평소 시각과 견주지 않는다
    if fix and "periods" in fix:
        table = timetable(day, fix["periods"])
        lunch = lunch_from(table) or lunch
        source = "고침 파일"
    else:
        table, source, usual = base, "기본 시간표", base
        if last_period:
            held = [no for no in {r["period"] for r in records if r["period"] >= 1}  # 쓸 수 있는 기록이 있는 교시
                    if _record_lesson(no, [r for r in records if r["period"] == no], base.get(no), [])]
            last = max([last_period, *held])
            table = {no: slot for no, slot in base.items() if no <= last}
            notes.append(f"{last}교시까지 있는 날로 보고 나눴어요. 다르면 --last 나 고침 파일을 쓰세요.")
        else:
            notes.append("그날 몇 교시까지인지 몰라 시간표 전체로 나눴어요. 일찍 끝난 날이면 --last 나 고침 파일을 쓰세요.")
    if fix and fix.get("lunch"):
        try:
            lunch = (clock(day, fix["lunch"]["start"]), clock(day, fix["lunch"]["end"]))
        except (KeyError, TypeError) as exc:
            raise SplitError("lunch 는 start 와 end 를 적어 주세요.") from exc

    midnight = datetime(day.year, day.month, day.day) + timedelta(days=1)
    ordered = sorted((p for p in pieces if p["seconds"] > 0), key=lambda p: (p["start"], p["file"]))
    lessons = lesson_segments(table, records, notes, usual)
    segments = []
    if not lessons:
        notes.append("그날 교시가 없어 나누지 못했어요.")
    elif ordered:
        first = ordered[0]["start"]
        finish = min(midnight, max(p["start"] + timedelta(seconds=p["seconds"]) for p in ordered))
        if lessons[0]["start"] - first >= MIN_SEGMENT:
            segments.append(("수업 전", first, lessons[0]["start"], lessons[0]["from"]))
        gaps = [(a, b) for a, b in zip(lessons, lessons[1:]) if b["start"] - a["end"] >= MIN_SEGMENT]
        noon = None
        if lunch:
            noon = max(gaps, key=lambda g: _overlap(g[0]["end"], g[1]["start"], *lunch), default=None)
            if noon and _overlap(noon[0]["end"], noon[1]["start"], *lunch) <= 0:
                noon = None
        for i, lesson in enumerate(lessons):
            basis = RECORDED if lesson["from"] == lesson["to"] == RECORDED else GUESSED
            segments.append((f"교시{lesson['period']}", lesson["start"], lesson["end"], basis))
            for gap in gaps:
                if gap[0] is lesson:
                    kind = "점심" if gap is noon else "쉬는 시간"
                    edge = RECORDED if lesson["to"] == gap[1]["from"] == RECORDED else GUESSED
                    segments.append((kind, lesson["end"], gap[1]["start"], edge))
            if i == len(lessons) - 1 and finish - lesson["end"] >= MIN_SEGMENT:
                segments.append(("방과 후", lesson["end"], finish, lesson["to"]))
    else:  # 녹음이 없어도 교시 표는 보여 준다
        notes.append("그날 녹음 조각이 없어요.")
        segments = [(f"교시{x['period']}", x["start"], x["end"],
                     RECORDED if x["from"] == x["to"] == RECORDED else GUESSED) for x in lessons]
    return {"날짜": day.isoformat(), "시간표": source, "알림": notes,
            "구간": [_with_pieces(*segment, ordered) for segment in segments]}


def _mmss(seconds) -> str:
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


def to_markdown(result: dict) -> str:
    lines = [f"# 하루 녹음 나누기 표 {result['날짜']}", "", f"시간표: {result['시간표']} · 녹음 파일은 자르지 않았어요.", "",
             "| 구간 | 시작 | 끝 | 근거 | 녹음 조각 (조각 안 분:초) | 녹음이 빈 시간 |", "|---|---|---|---|---|---|"]
    for seg in result["구간"]:
        name = re.sub(r"^교시(\d+)$", r"\1교시", seg["종류"])
        used = "<br>".join(f"{p['파일']} {_mmss(p['시작초'])}~{_mmss(p['끝초'])}" for p in seg["조각"]) or "-"
        empty = _mmss(seg["빈초"]) if seg["빈초"] else "-"
        lines.append(f"| {name} | {seg['시작'][:5]} | {seg['끝'][:5]} | {seg['근거']} | {used} | {empty} |")
    if result["알림"]:
        lines += ["", "## 알림", *(f"- {note}" for note in result["알림"])]
    return "\n".join(lines) + "\n"


# ──────────────────────────── 파일 읽기·쓰기 ────────────────────────────

def _hms(match) -> float:
    return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))


def probe_seconds(ffmpeg: str, path: pathlib.Path, runner=subprocess.run) -> float | None:
    """ffmpeg 로 녹음 길이(초). 머리말에 길이가 없으면(끊긴 녹음) 끝까지 읽어 본다."""
    def run(*extra):
        result = runner([str(ffmpeg), "-hide_banner", "-nostdin", "-i", str(path), *extra],
                        capture_output=True, timeout=300, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return (result.stderr or b"").decode("utf-8", errors="replace")

    try:
        found = re.search(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)", run())
        if found:
            return _hms(found) or None
        times = list(re.finditer(r"time=\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)", run("-f", "null", "-")))
        return (_hms(times[-1]) or None) if times else None
    except (OSError, subprocess.SubprocessError):
        return None


def load_pieces(day: date, folder: pathlib.Path, length, notes: list[str]) -> list[dict]:
    """length(path) → 초 또는 None. None 이면 파일이 마지막으로 바뀐 시각으로 짐작한다."""
    pieces, guessed, skipped = [], 0, 0
    for path in sorted(folder.iterdir()) if folder.is_dir() else []:
        start = piece_start(day, path.name)
        if start is None or not path.is_file():
            continue
        seconds = length(path)
        if not seconds:
            seconds = path.stat().st_mtime - start.timestamp()
            if not 0 < seconds <= MAX_PIECE_SECONDS:
                skipped += 1
                continue
            guessed += 1
        pieces.append({"file": path.name, "start": start, "seconds": float(seconds)})
    if guessed:
        notes.append(f"녹음 조각 {guessed}개는 길이를 읽지 못해 파일이 바뀐 시각으로 짐작했어요.")
    if skipped:
        notes.append(f"녹음 조각 {skipped}개는 길이를 알 수 없어 뺐어요.")
    return pieces


def load_records(day: date, folder: pathlib.Path, tz=None) -> list[dict]:
    records = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        if path.name.endswith(".transcript.json"):
            continue
        prefix = re.match(r"(\d+)교시", path.name)
        records += session_records(day, transcribe.read_json(path), prefix and prefix.group(1), tz)
    return records


def load_json_strict(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise SplitError(f"{path.name} 을 읽지 못했어요(JSON 모양 확인): {exc}") from exc


def scheduled_last_period(day: date, cfg: dict) -> int | None:
    """수업 비서 진도표에서 그날 마지막 교시. 알 수 없으면 None."""
    try:
        import assistant_server

        lessons, _ = assistant_server.fetch_schedule(cfg, day)
        return max((int(x["period"]) for x in lessons if x.get("period")), default=None)
    except Exception as exc:  # 진도표를 못 읽어도 표는 만든다
        print(f"[day_split] 진도표를 읽지 못함: {type(exc).__name__}", file=sys.stderr)
        return None


def run(day: date, data: pathlib.Path, cfg: dict, last_period=None, length=None, tz=None) -> tuple[dict, pathlib.Path]:
    notes: list[str] = []
    if length is None:
        ffmpeg = audio_export.find_ffmpeg(cfg)
        length = (lambda path: probe_seconds(ffmpeg, path)) if ffmpeg else (lambda path: None)
    out = data / "day_split"
    fix_path = out / f"{day.isoformat()}.fix.json"
    fix = load_json_strict(fix_path) if fix_path.is_file() else None
    pieces = load_pieces(day, data / "day_audio" / day.isoformat(), length, notes)
    records = load_records(day, data / "sessions" / day.isoformat(), tz)
    result = split_day(day, pieces, cfg.get("periods", []), records, fix, last_period)
    result["알림"] = notes + result["알림"]
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{day.isoformat()}.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    target.with_suffix(".md").write_text(to_markdown(result), encoding="utf-8")
    return result, target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="하루 녹음 나누기 표 (녹음 파일은 건드리지 않음)")
    parser.add_argument("--date", type=date.fromisoformat, default=date.today(), help="YYYY-MM-DD (기본: 오늘)")
    parser.add_argument("--last", type=int, help="그날 마지막 교시 (기본: 진도표에서 확인)")
    args = parser.parse_args(argv)
    data = data_dir(SKILL)
    config = data / "config.json"
    try:
        cfg = load_json_strict(config if config.is_file() else SKILL_DIR / "config.example.json")
        last = args.last or scheduled_last_period(args.date, cfg)
        result, target = run(args.date, data, cfg, last)
    except SplitError as exc:
        print(f"⚠ {exc}", file=sys.stderr)
        return 1
    print(f"{result['날짜']}: 구간 {len(result['구간'])}개 · 알림 {len(result['알림'])}개\n{target.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
