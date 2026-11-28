"""수업 녹음 받아쓰기 뼈대: 녹음(webm) → 글 → [mm:ss] 메모와 시간 맞추기 → 간단한 분석

    python transcribe.py --date 2026-11-26             # 그날 녹음 전부
    python transcribe.py --date 2026-11-26 --period 3  # 3교시 것만
    python transcribe.py --date 2026-11-26 --redo      # 이미 받아쓴 것도 다시
    python transcribe.py --date 2026-11-26 --no-transcribe  # 받아쓰기 없이, 이미 있는 글로 맞추기·분석만

- 데이터 폴더(내 문서\\my-skills-data\\teacherlesson-assistant\\sessions\\<날짜>)의 파일만 읽고 쓴다.
  받아쓴 글에는 학생 말·이름이 들어갈 수 있어 바깥으로 보내지 않고, 화면에는 개수만 낸다.
- 받아쓰기는 내 PC 에서 도는 faster-whisper 로 한다. 설치돼 있지 않으면 설치 방법만 안내하고 멈춘다
  (이미 받아쓴 글이 있으면 --no-transcribe 로 맞추기·분석은 할 수 있다).
  처음 한 번 모델 파일을 내려받는다(그 뒤로는 인터넷 없이 된다).
- 사전(선택): 데이터 폴더 stt_words.json — "자주 쓰는 말"(받아쓰기 힌트)·"고쳐 쓰기"(틀린 말→맞는 말). 모양은 stt_words.example.json.
- 결과(녹음 파일 옆): <녹음>.transcript.json(받아쓴 조각), <녹음>.transcript.md(메모를 끼워 넣은 글 + 분석)
- 메모 시각은 세션의 '수업 시작' 메모(`at`)를 0초로 잡는다. 메모의 `t` 는 녹음 중이 아니면 시계 시각(HH:MM)이라
  mm:ss 와 헷갈릴 수 있어 쓰지 않는다.
- 확인 필요: 교사 PC 에서 실제 50분 녹음으로 돌려 보기(속도·한국어 정확도). 이 파일의 시험은 가짜 받아쓰기 결과만 쓴다.
"""
import argparse
import json
import pathlib
import re
import sys
from datetime import date, datetime

SKILL_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(next(p / "_shared" for p in SKILL_DIR.parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir  # noqa: E402

SKILL = "teacherlesson-assistant"
AUDIO_EXTS = (".webm", ".mp4")
KIND = {"good": "👍", "fix": "🔧", "student": "🙋", "star": "★", "voice": "🎤", "step": "▶", "adj": "⏱", "note": "📝", "sys": "⏱"}
INSTALL_HELP = ("받아쓰기 도구(faster-whisper)가 없어요. 설치: pip install faster-whisper "
                "(처음 한 번 모델 파일을 내려받아요). 이미 받아쓴 글이 있으면 --no-transcribe 로 맞추기·분석만 할 수 있어요.")


WORDS_FILE = "stt_words.json"   # 데이터 폴더. 학생 이름이 들어갈 수 있어 저장소에는 stt_words.example.json 만 둔다
HINT_LIMIT = 200                # whisper initial_prompt 는 토큰 224개까지라 글자 수로 넉넉히 줄인다
PARTICLES = ("에서", "에게", "한테", "으로", "은", "는", "이", "가", "을", "를", "의", "에", "도", "와", "과", "로",
             "만", "까지", "부터", "에게서", "한테서", "하고", "처럼", "보다")
# 받침 있는 이름 뒤에만 붙는 꼴(지민이가·지민아)과 받침 없는 말 뒤에만 붙는 꼴(민수랑·민수야). 아무 데나 허용하면 다른 이름(민수아)을 바꾼다
AFTER_BATCHIM = ("이가", "이는", "이를", "이랑", "이도", "이만", "이의", "이한테", "이에게", "아")
AFTER_VOWEL = ("랑", "야")
# 뒤에 는·은·도·만 이 한 번 더 붙을 수 있는 조사(에게는·랑은)
CHAINABLE = ("에서", "에게", "한테", "으로", "로", "까지", "부터", "에게서", "한테서", "이한테", "이에게", "랑", "이랑", "하고", "처럼", "보다")


class Unavailable(RuntimeError):
    """받아쓰기 도구가 없을 때."""


def load_words(path=None, warn=print):
    """사전 파일 → (자주 쓰는 말 목록, {틀린 말: 맞는 말}). 파일이 없으면 빈 값.
    파일이 있는데 못 읽거나 모양이 틀리면 그 부분은 빼고 warn 으로 알린다(받아쓰기는 계속)."""
    path = pathlib.Path(path) if path else data_dir(SKILL) / WORDS_FILE
    if not path.is_file():
        return [], {}
    data = read_json(path)
    if not isinstance(data, dict):
        warn(f"⚠ 받아쓰기 사전({path.name})을 읽지 못해 쓰지 않았어요. 쉼표·따옴표·괄호가 맞는지, UTF-8 로 저장했는지 확인해 주세요.")
        return [], {}
    words, raw = data.get("자주 쓰는 말"), data.get("고쳐 쓰기")
    if words is not None and not isinstance(words, list):
        warn(f'⚠ 받아쓰기 사전의 "자주 쓰는 말"은 ["낱말", "낱말"] 모양이어야 해요. 이 부분은 쓰지 않았어요.')
        words = None
    if raw is not None and not isinstance(raw, dict):
        warn(f'⚠ 받아쓰기 사전의 "고쳐 쓰기"는 {{"틀린 말": "맞는 말"}} 모양이어야 해요. 이 부분은 쓰지 않았어요.')
        raw = None
    hints = [w.strip() for w in words or [] if isinstance(w, str) and w.strip()]
    fixes = {k.strip(): v.strip() for k, v in (raw or {}).items()
             if isinstance(k, str) and isinstance(v, str) and k.strip()}
    return hints, fixes


def build_hint(words, limit=HINT_LIMIT):
    """자주 쓰는 말 → whisper 힌트 글. 같은 말은 한 번만, 낱말 단위로 limit 글자 안에서 자른다."""
    out, seen = "", set()
    for w in words:
        if w in seen:
            continue
        seen.add(w)
        nxt = f"{out}, {w}" if out else w
        if len(nxt) > limit:
            break
        out = nxt
    return out


def _suffix_pattern(key: str) -> str:
    """key 뒤에 와도 되는 것(조사 또는 낱말 끝)을 보는 lookahead. 한글로 끝나면 받침에 맞는 조사만."""
    last = key[-1]
    batchim = (ord(last) - 0xAC00) % 28 != 0 if "가" <= last <= "힣" else None   # None: 영문·숫자 등은 둘 다 허용
    parts = list(PARTICLES)
    if batchim is not False:
        parts += AFTER_BATCHIM
    if batchim is not True:
        parts += AFTER_VOWEL
    chain = "|".join(map(re.escape, sorted((x for x in parts if x in CHAINABLE), key=len, reverse=True)))
    plain = "|".join(map(re.escape, sorted(parts, key=len, reverse=True)))
    return rf"(?=(?:(?:{chain})(?:는|은|도|만)|(?:{plain}))?(?!\w))"


def apply_fixes(text: str, fixes: dict) -> str:
    """틀린 말 → 맞는 말. 낱말 경계에서만(앞뒤가 글자·숫자로 이어지면 건드리지 않음, 뒤에 조사는 허용),
    긴 것부터, 한 번에 훑어 바꾼 결과가 다시 바뀌지 않는다. 조사는 그대로 두며 받침에 맞춰 바꾸지는 않는다."""
    keys = sorted((k for k in fixes if k), key=len, reverse=True)
    if not keys or not text:
        return text
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(k) + _suffix_pattern(k) for k in keys) + ")")
    return pattern.sub(lambda m: fixes[m.group(0)], text)


def fmt_time(sec) -> str:
    """초 → mm:ss (분은 60 을 넘어도 그대로)."""
    total = max(0, int(sec or 0))
    return f"{total // 60:02d}:{total % 60:02d}"


def parse_iso(text):
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def seconds_between(start, end):
    """두 시각의 차이(초). 하나라도 없거나 시간대 표시(tz)가 서로 다르면 None."""
    if start is None or end is None or (start.tzinfo is None) != (end.tzinfo is None):
        return None
    return (end - start).total_seconds()


def read_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def find_recordings(day_dir: pathlib.Path, period=None):
    """그날 폴더의 녹음 파일(이름순). period 를 주면 '<N>교시_' 로 시작하는 것만."""
    if not day_dir.is_dir():
        return []
    prefix = f"{int(period)}교시_" if period not in (None, "") else ""
    return sorted(p for p in day_dir.iterdir() if p.suffix.lower() in AUDIO_EXTS and p.name.startswith(prefix))


def find_session(day_dir: pathlib.Path, recording_name: str):
    """세션 기록 중 rec_files 에 이 녹음 이름이 들어 있는 것. 없으면 None."""
    for path in sorted(day_dir.glob("*.json")):
        if path.name.endswith(".transcript.json"):
            continue
        rec = read_json(path)
        if isinstance(rec, dict) and recording_name in (rec.get("rec_files") or []):
            return rec
    return None


def recording_windows(session: dict):
    """'수업 시작' 메모마다 한 구간. 구간 끝은 뒤따르는 '수업 마침' 메모(없으면 None)."""
    windows = []
    for memo in session.get("memos") or []:
        if not isinstance(memo, dict) or memo.get("kind") != "sys":
            continue
        at = parse_iso(memo.get("at"))
        if at is None:
            continue
        if memo.get("text") == "수업 시작":
            windows.append({"start": at, "end": None})
        elif memo.get("text") == "수업 마침" and windows and windows[-1]["end"] is None:
            windows[-1]["end"] = at
    return windows


def pick_window(session: dict, recording_name: str):
    """(구간, 정확함 여부). 녹음 순서와 '수업 시작' 순서를 맞춘다.
    마이크 없이 시작한 수업은 녹음 파일이 없어 개수가 어긋날 수 있다 → 뒤에서부터 맞추고 '추정'."""
    files = session.get("rec_files") or []
    windows = recording_windows(session)
    if recording_name not in files or not windows or len(windows) < len(files):
        return None, False
    idx = files.index(recording_name)
    if len(windows) == len(files):
        return windows[idx], True
    return windows[len(windows) - len(files) + idx], False


def window_entries(session: dict, window: dict):
    """구간 안의 메모를 (초, 종류, 글) 로. 구간 시작이 0초."""
    entries = []
    for memo in session.get("memos") or []:
        if not isinstance(memo, dict):
            continue
        offset = seconds_between(window["start"], parse_iso(memo.get("at")))
        if offset is None or offset < 0:
            continue
        end_offset = seconds_between(window["start"], window["end"]) if window["end"] else None
        if end_offset is not None and offset > end_offset + 1:
            continue
        text = " ".join(str(memo.get("text") or "").split())
        if text:
            entries.append((offset, str(memo.get("kind") or ""), text))
    return sorted(entries, key=lambda e: e[0])


def count_questions(text: str) -> int:
    """물음표로 끝나는 문장 수. (받아쓰기가 물음표를 빼먹을 수 있어 실제보다 적을 수 있다 — 추정)"""
    return sum(1 for s in re.findall(r"[^.!?？。]*[?？]", str(text or "")) if re.sub(r"[?？\s]", "", s))


def analyze(segments, entries, total_sec=None, teacher_label=None):
    """받아쓴 조각과 메모로 분석. 화자 구분이 없으면 교사 말 비율은 None(확인 필요)."""
    clean = [s for s in segments if isinstance(s, dict) and str(s.get("text") or "").strip()]
    last_end = max((float(s.get("end") or 0) for s in clean), default=0.0)
    total = float(total_sec) if total_sec else last_end
    speech = sum(max(0.0, float(s.get("end") or 0) - float(s.get("start") or 0)) for s in clean)

    teacher_ratio = None
    labeled = [s for s in clean if s.get("speaker")]
    if teacher_label and labeled:
        durations = [(s["speaker"] == teacher_label, max(0.0, float(s["end"]) - float(s["start"]))) for s in labeled]
        denom = sum(d for _, d in durations)
        teacher_ratio = (sum(d for is_t, d in durations if is_t) / denom) if denom else None

    steps = []
    starts = [(off, text.split(":", 1)[-1].strip()) for off, kind, text in entries if kind == "step"]
    for i, (start, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else (total if total > start else start)
        lines = [s for s in clean if start <= float(s.get("start") or 0) < end]
        steps.append({"name": name, "start": start, "minutes": round((end - start) / 60, 1), "lines": len(lines),
                      "questions": sum(count_questions(s["text"]) for s in lines)})

    return {"total_sec": total, "speech_sec": speech, "speech_ratio": (speech / total) if total else None,
            "teacher_ratio": teacher_ratio, "questions": sum(count_questions(s["text"]) for s in clean),
            "lines": len(clean), "steps": steps}


def merged_lines(segments, entries):
    """받아쓴 조각과 메모를 시간 순으로 `[mm:ss] …` 줄로. 같은 초면 메모가 먼저."""
    rows = [(float(off), 0, f"{KIND.get(kind, '📝')} {text}") for off, kind, text in entries]
    rows += [(float(s.get("start") or 0), 1, str(s["text"]).strip()) for s in segments
             if isinstance(s, dict) and str(s.get("text") or "").strip()]
    return [f"[{fmt_time(t)}] {text}" for t, _, text in sorted(rows, key=lambda r: (r[0], r[1]))]


def build_markdown(recording_name, segments, entries, result, notes):
    out = [f"# 수업 녹음 받아쓰기 — {recording_name}", ""]
    if notes:
        out += ["## 확인 필요", *(f"- {n}" for n in notes), ""]
    out += ["## 분석", f"- 녹음 길이: {fmt_time(result['total_sec'])}"]
    if result["speech_ratio"] is not None:
        out.append(f"- 말소리가 있는 시간: {fmt_time(result['speech_sec'])} ({result['speech_ratio'] * 100:.0f}%) — 교사·학생 구분 없음")
    if result["teacher_ratio"] is None:
        out.append("- 교사 말 비율: 확인 필요 (받아쓰기 결과에 화자 구분이 없어요)")
    else:
        out.append(f"- 교사 말 비율: {result['teacher_ratio'] * 100:.0f}%")
    out.append(f"- 물음표 문장: {result['questions']}개 (추정 — 받아쓰기가 물음표를 빼먹을 수 있어요)")
    if result["steps"]:
        out += ["", "### 단계별 시간", "| 단계 | 시작 | 걸린 시간(분) | 말 줄 수 | 물음표 문장 |", "|---|---|---|---|---|"]
        out += [f"| {s['name']} | {fmt_time(s['start'])} | {s['minutes']} | {s['lines']} | {s['questions']} |" for s in result["steps"]]
    out += ["", "## 받아쓴 글 (메모 포함)", "", *merged_lines(segments, entries), ""]
    return "\n".join(out)


def load_transcriber(model_name="small", words=None):
    """faster-whisper 로 받아쓰는 함수(경로 → 조각 목록)를 돌려준다. 없으면 Unavailable.
    words = (자주 쓰는 말, 고쳐 쓰기) — 없으면 데이터 폴더의 stt_words.json 을 읽는다."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise Unavailable(INSTALL_HELP) from exc
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    hints, fixes = words if words is not None else load_words()
    hint = build_hint(hints)

    def run(path):
        kwargs = {"initial_prompt": hint} if hint else {}
        segments, _info = model.transcribe(str(path), language="ko", vad_filter=True, **kwargs)
        return [{"start": float(s.start), "end": float(s.end), "text": apply_fixes(s.text.strip(), fixes)} for s in segments]
    return run


def process_recording(recording: pathlib.Path, transcriber=None, redo=False, teacher_label=None):
    """녹음 하나 처리. transcriber 가 None 이면 이미 있는 .transcript.json 만 쓴다.
    돌려주는 값: {"status": "ok|skip|missing", "lines": 조각 수, "notes": [...]}"""
    json_path = recording.with_name(recording.stem + ".transcript.json")
    md_path = recording.with_name(recording.stem + ".transcript.md")
    segments = None
    if json_path.is_file() and not redo:
        data = read_json(json_path)
        if isinstance(data, dict) and isinstance(data.get("segments"), list):
            segments = data["segments"]
    if segments is None:
        if transcriber is None:
            return {"status": "missing", "lines": 0, "notes": ["받아쓴 글이 없어요(--no-transcribe)."]}
        segments = transcriber(recording)
        json_path.write_text(json.dumps({"recording": recording.name, "segments": segments}, ensure_ascii=False, indent=1), encoding="utf-8")

    notes, entries, total = [], [], None
    session = find_session(recording.parent, recording.name)
    if session is None:
        notes.append("이 녹음이 들어 있는 수업 기록(rec_files)을 못 찾아 메모를 맞추지 못했어요.")
    else:
        window, exact = pick_window(session, recording.name)
        if window is None:
            notes.append("'수업 시작' 메모가 없거나 녹음보다 적어 메모를 맞추지 못했어요.")
        else:
            entries = window_entries(session, window)
            total = seconds_between(window["start"], window["end"]) if window["end"] else None
            if not exact:
                notes.append("마이크 없이 시작한 수업이 섞여 녹음과 '수업 시작' 메모를 뒤에서부터 맞췄어요(추정).")
    if not any(k == "step" for _, k, _ in entries):
        notes.append("단계 이동 메모가 없어 단계별 시간을 못 냈어요.")
    result = analyze(segments, entries, total, teacher_label)
    md_path.write_text(build_markdown(recording.name, segments, entries, result, notes), encoding="utf-8")
    return {"status": "ok", "lines": result["lines"], "notes": notes}


def run(day: str, sessions_root: pathlib.Path, period=None, redo=False, no_transcribe=False,
        model="small", teacher_label=None, transcriber=None):
    """그날 녹음 전부 처리. 돌려주는 값: (처리 결과 목록, 받아쓰기 도구 없음 안내 또는 None)."""
    date.fromisoformat(day)
    recordings = find_recordings(sessions_root / day, period)
    results, unavailable = [], None
    for rec in recordings:
        tr = transcriber
        if tr is None and not no_transcribe and unavailable is None:
            has_text = rec.with_name(rec.stem + ".transcript.json").is_file() and not redo
            if not has_text:
                try:
                    tr = transcriber = load_transcriber(model)
                except Unavailable as exc:
                    unavailable = str(exc)
        if unavailable and not rec.with_name(rec.stem + ".transcript.json").is_file():
            results.append((rec.name, {"status": "missing", "lines": 0, "notes": [unavailable]}))
            continue
        results.append((rec.name, process_recording(rec, None if no_transcribe else tr, redo, teacher_label)))
    return results, unavailable


def main():
    ap = argparse.ArgumentParser(description="수업 녹음 받아쓰기 → 메모와 맞추기 → 분석")
    ap.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD (기본: 오늘)")
    ap.add_argument("--period", type=int, help="이 교시 녹음만")
    ap.add_argument("--model", default="small", help="faster-whisper 모델 크기(기본 small)")
    ap.add_argument("--redo", action="store_true", help="이미 받아쓴 것도 다시")
    ap.add_argument("--no-transcribe", action="store_true", help="받아쓰기 없이 있는 글로 맞추기·분석만")
    ap.add_argument("--teacher-label", help="받아쓰기 결과의 speaker 값 중 교사 표시(화자 구분이 있을 때만)")
    args = ap.parse_args()
    try:
        results, unavailable = run(args.date, data_dir(SKILL) / "sessions", args.period, args.redo,
                                   args.no_transcribe, args.model, args.teacher_label)
    except ValueError:
        print("날짜는 YYYY-MM-DD 모양으로 적어 주세요.")
        return 2
    if not results:
        print(f"{args.date} 녹음이 없어요.")
        return 0
    for name, res in results:
        print(f"{name}: {res['status']} · 조각 {res['lines']}개" + ("".join(f"\n  ⚠ {n}" for n in res["notes"])))
    return 1 if unavailable and all(r["status"] == "missing" for _, r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
