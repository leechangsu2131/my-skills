"""수업 준비 미리 한 번에: 그날 수업 가운데 흐름(flows/*.json)이 없는 차시를 지도서로 자동 준비한다.

    python prepare_lessons.py                     # 다음 수업일(내일, 금요일이면 월요일)
    python prepare_lessons.py --date today        # 오늘 (today|tomorrow|오늘|내일|YYYY-MM-DD)
    python prepare_lessons.py --date 2026-11-24 --redo   # 자동으로 만든 흐름도 다시 만들기

차시마다: 진도 서버 /api/pdf/<record_key>(그 차시 지도서 쪽) → Gemini CLI(util-notebooklm, 무료 flash)로
목표·준비물·단계(활동·발문·시간·팁)·숙제 JSON → 형식 검사 → flows/<record_key>.json.
Claude 토큰은 쓰지 않는다. 사람이 고친 흐름(auto 표시 없음)은 --redo 로도 덮어쓰지 않는다.
학생 메모·녹음은 Gemini 에 보내지 않는다(출판사 주의점만 넣음).
진행 상황은 데이터 폴더 prepare_status.json — 수업 비서 화면의 '🌙 수업 준비' 단추가 읽는다.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import assistant_server as app

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "util-notebooklm"))
import nlm  # noqa: E402

STATUS = app.DATA / "prepare_status.json"
WORKERS = 2
STALE_SECONDS = 30 * 60

PROMPT = """@{file} 이 자료는 초등학교 3학년 {subject} 교사용 지도서({publisher}) 가운데 「{unit}」 {lesson}차시 「{title}」 부분입니다.
이 지도서를 바탕으로 40분 수업 흐름을 아래 형식의 JSON 하나로만 답하세요. 설명 문장이나 ``` 표시는 쓰지 마세요.

{{"goal": "학습 목표 한 문장",
 "materials": ["준비물"],
 "steps": [{{"name": "도입", "minutes": 5, "do": "교사·학생 활동 한두 문장", "say": "핵심 발문 한 문장", "tip": "주의하거나 보충할 점", "flag": "keep 또는 cut 또는 빈 문자열"}}],
 "homework": "알림장에 쓸 숙제·준비물 (없으면 빈 문자열)",
 "pages": "근거로 쓴 쪽 (예: p.2-4, 자료의 〔p.N〕 표시가 있으면 그 번호)"}}

규칙
- steps 는 3~6개(도입–전개–정리), minutes 합계는 40.
- flag: 이 차시의 핵심 활동은 "keep", 시간이 모자랄 때 줄이거나 건너뛰어도 되는 단계(복습·정리 보충 등)는 "cut", 모르겠으면 "".
- 지도서에 있는 활동과 발문을 우선 쓰고, 지도서에 없는 내용을 지어내지 않습니다. 근거가 없으면 tip 에 "지도서에 없음"이라고 씁니다.
- 자료에 여러 차시가 들어 있으면 반드시 「{title}」 차시 부분만 씁니다. 다른 차시 내용을 쓰지 않습니다.
- 묶음 차시(예: 3(3~4)차시)면 이번 한 시간 분량만 씁니다.
- 수업 중에 한눈에 보이도록 문장을 짧게 씁니다.{cautions}"""


def parse_day(text: str) -> date:
    text = (text or "tomorrow").strip().lower()
    today = date.today()
    if text in ("today", "오늘"):
        return today
    if text in ("tomorrow", "내일"):
        d = today + timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        return d
    return date.fromisoformat(text)


def pid_alive(pid) -> bool:
    try:
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return code.value == 259  # STILL_ACTIVE
    except Exception:
        return True


def is_running(status: dict) -> bool:
    """진행 중 표시가 있고, 그 프로세스가 아직 살아 있고, 너무 오래되지 않았을 때만 '준비 중'."""
    return bool(status.get("running")) and time.time() - status.get("started_ts", 0) < STALE_SECONDS \
        and pid_alive(status.get("pid", 0))


_status_lock = threading.Lock()


def write_status(status: dict) -> None:
    """동시에 쓰지 않게 잠그고, 화면이 읽는 순간과 겹쳐 윈도우가 막으면 잠깐 뒤 다시 쓴다."""
    with _status_lock:
        for attempt in range(10):
            try:
                app.write_json(STATUS, status)
                return
            except PermissionError:
                time.sleep(0.2 * (attempt + 1))


def lesson_pdf(cfg: dict, record_key: str, dest: pathlib.Path) -> bool:
    try:
        if cfg.get("schedule_backend", "supabase") == "supabase":
            import supabase_schedule
            data = supabase_schedule.pdf_for_lesson(record_key)
        else:
            base = cfg.get("schedule_api", "http://127.0.0.1:5000").rstrip("/")
            with urllib.request.urlopen(f"{base}/api/pdf/{urllib.parse.quote(record_key)}", timeout=90) as res:
                data = res.read()
    except (urllib.error.URLError, OSError, RuntimeError, ValueError):
        return False
    if data[:5] != b"%PDF-":
        return False
    dest.write_bytes(data)
    return True


SECTION_RANGE = re.compile(r"\]\s*(\d+)(?:\s*~\s*(\d+))?\s*차시")


def lesson_section(lesson: dict) -> str:
    """notebook_sources.py 가 만든 단원 md 에서 이 차시 구간 글만 꺼낸다(국어처럼 단원 한 권 PDF 일 때 정확).
    구간 제목 '## [국어 3.5단원] 3~4차시 …' 의 범위가 이 차시 번호를 품으면 그 구간."""
    nums = app.lesson_numbers(str(lesson.get("lesson", "")))
    unit = str(lesson.get("unit", ""))
    md = app.NOTEBOOKLM / app.safe_name(lesson["subject"]) / f"{app.safe_name(unit)}.md"
    if not unit or not md.is_file():
        return ""
    for m, head, body in nlm.split_text(md.read_text(encoding="utf-8"), r"^##\s*\[.*?\]\s*\d+(?:\s*~\s*\d+)?\s*차시"):
        r = SECTION_RANGE.search(head)
        if nums and r and int(r.group(1)) <= nums[0] <= int(r.group(2) or r.group(1)):
            return body if len(body) > 200 and "PDF가 없어" not in body[:300] else ""
        # Named stages such as '실천하기' have no printed lesson number in the
        # guide. Match their exact lesson title against the stage heading instead
        # of falling back to the entire unit PDF.
        title = re.sub(r"\s+", " ", str(lesson.get("title") or "")).strip()
        heading_title = re.sub(r"\s+", " ", head).strip()
        if not nums and title and title in heading_title:
            return body if len(body) > 200 and "PDF가 없어" not in body[:300] else ""
    return ""


def _find_flow_json(text: str):
    """답 글에서 흐름 JSON 객체를 찾는다. 앞뒤 설명에 `{ }` 가 있어도(ISSUE-031) 걸리지 않게
    각 `{` 위치에서 JSON 을 읽어 보고, `steps` 가 있는 첫 객체를 돌려준다.
    steps 가 있는 것이 없으면 처음 읽힌 객체(없으면 처음 `{` 의 오류)를 돌려줘 호출한 쪽이 알맞은 오류를 내게 한다."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("JSON 을 찾지 못함")
    decoder = json.JSONDecoder()
    first_obj, first_error = None, None
    pos = start
    while 0 <= pos <= end:
        try:
            obj, _ = decoder.raw_decode(text, pos)
        except json.JSONDecodeError as exc:
            first_error = first_error or exc
        else:
            if isinstance(obj, dict):
                if "steps" in obj:
                    return obj
                first_obj = first_obj if first_obj is not None else obj
        pos = text.find("{", pos + 1)
    if first_obj is not None:
        return first_obj
    raise first_error


def parse_flow(text: str) -> dict:
    """Gemini 답에서 JSON 을 꺼내 형식을 맞춘다. 잘못되면 ValueError."""
    data = _find_flow_json(text)
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("단계(steps)가 없음")
    clean_steps = []
    for s in steps[:8]:
        if not isinstance(s, dict) or not str(s.get("name", "")).strip():
            raise ValueError("단계 이름이 없음")
        try:
            minutes = int(re.search(r"\d+", str(s.get("minutes", "0"))).group())
        except (AttributeError, ValueError):
            minutes = 0
        step = {k: str(s.get(k, "") or "").strip() for k in ("name", "do", "say", "tip")} | {"minutes": minutes}
        if str(s.get("flag", "")).strip().lower() in ("keep", "cut"):
            step["flag"] = str(s["flag"]).strip().lower()
        clean_steps.append(step)
    materials = data.get("materials") or []
    if isinstance(materials, str):
        materials = [m.strip() for m in re.split(r"[,、·]", materials) if m.strip()]
    # JSON null 이 'None' 글자로 저장되지 않게(ISSUE-032)
    materials = [str(m).strip() for m in materials if m is not None and str(m).strip()]
    return {"goal": str(data.get("goal", "") or "").strip(), "materials": materials[:12],
            "steps": clean_steps, "homework": str(data.get("homework", "") or "").strip(),
            "pages": str(data.get("pages", "") or "").strip()}


def prepare_one(cfg: dict, lesson: dict, cautions: list[str], model: str) -> tuple[str, str]:
    """(상태, 메시지). 상태: ok | fail"""
    key = lesson["record_key"]
    with tempfile.TemporaryDirectory(prefix="prep_") as tmp:
        tmp = pathlib.Path(tmp)
        section = lesson_section(lesson)
        if section:  # 차시 구간 글(정확·가벼움)
            pdf = tmp / "lesson.md"
            pdf.write_text(section, encoding="utf-8")
        else:
            pdf = tmp / "lesson.pdf"
            if not lesson_pdf(cfg, key, pdf):
                return "fail", "지도서 PDF 없음(진도 서버·진도표 PDF 경로 확인)"
        caution_text = ("\n- 이 출판사 지도서를 쓰며 교사가 남긴 주의점도 반영합니다: " + " / ".join(cautions[:5])) if cautions else ""
        prompt = PROMPT.format(file="{file}", subject=lesson["subject"], publisher=lesson.get("publisher") or "출판사",
                               unit=lesson.get("unit", ""), lesson=lesson.get("lesson", ""),
                               title=lesson.get("title", ""), cautions=caution_text)
        last_error = ""
        for attempt in range(2):  # 형식이 틀리면 한 번 더
            try:
                # 차시 구간 글(md)은 작아 모델마다 45초면 됨. PDF 발췌는 예전처럼 모델마다 최대 120초
                answer, model = nlm.gemini_ask(pdf, prompt, model=model, timeout=120,
                                                model_timeout=45 if section else None, work=tmp / f"gemini{attempt}")
                flow = parse_flow(answer)
                break
            except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
                last_error = str(exc)[:200]
        else:
            return "fail", f"Gemini 결과를 쓰지 못함: {last_error}"
    total = sum(s["minutes"] for s in flow["steps"])
    pages = flow.pop("pages")
    flow.update({
        "record_key": key, "subject": lesson["subject"], "title": lesson.get("title", ""),
        "unit": lesson.get("unit", ""), "lesson": lesson.get("lesson", ""), "publisher": lesson.get("publisher", ""),
        "source": f"지도서 {pages} · Gemini 자동 {time.strftime('%m/%d')}".replace("지도서  ·", "지도서 ·"),
        "auto": {"by": model, "at": time.strftime("%Y-%m-%d %H:%M")},
    })
    app.write_json(app.FLOWS / f"{app.safe_name(key)}.json", flow)
    note = "" if 35 <= total <= 45 else f" (시간 합계 {total}분 — 확인 필요)"
    return "ok", f"{len(flow['steps'])}단계{note}"


def main() -> int:
    ap = argparse.ArgumentParser(description="그날 수업 흐름을 지도서로 자동 준비")
    ap.add_argument("--date", default="tomorrow")
    ap.add_argument("--redo", action="store_true", help="자동으로 만든 흐름도 다시 만들기(사람이 고친 것은 그대로)")
    ap.add_argument("--model", default=nlm.DEFAULT_MODEL)
    args = ap.parse_args()
    day = parse_day(args.date)
    old = app.read_json(STATUS, {})
    mine = bool(os.environ.get("PREPARE_TOKEN")) and old.get("token") == os.environ.get("PREPARE_TOKEN")
    if is_running(old) and not mine:
        print(f"이미 준비 중이에요 ({old.get('date')}).")
        return 1
    cfg = app.load_config()
    lessons, source = app.fetch_schedule(cfg, day)
    status = {"date": day.isoformat(), "running": True, "started_ts": time.time(), "pid": os.getpid(),
              "token": os.environ.get("PREPARE_TOKEN", ""),
              "started": time.strftime("%H:%M"), "items": []}
    notes = app.read_json(app.CAUTIONS_PATH, {})
    targets = []
    for lesson in lessons:
        info = cfg.get("subjects", {}).get(lesson["subject"], {})
        lesson["publisher"] = info.get("publisher", "")
        item = {"period": lesson.get("period"), "subject": lesson["subject"], "title": lesson.get("title", ""),
                "record_key": lesson.get("record_key", "")}
        flow = app.find_flow(lesson)
        if not lesson.get("record_key"):
            item.update(status="skip", msg="진도표 수업이 아님")
        elif flow and not (args.redo and flow.get("auto")):
            item.update(status="have", msg="이미 준비됨" + ("" if flow.get("auto") else "(직접 고친 흐름)"))
        else:
            item.update(status="wait", msg="")
            targets.append((lesson, item))
        status["items"].append(item)
    write_status(status)
    print(f"{day} ({source}) 수업 {len(lessons)}개 중 준비할 차시 {len(targets)}개")

    def run(pair):
        lesson, item = pair
        item.update(status="run", msg="지도서 읽는 중…")
        write_status(status)
        cautions = [c["text"] for c in notes.get(f"{lesson['publisher']}|{lesson['subject']}", []) + notes.get(f"{lesson['publisher']}|*", [])]
        t0 = time.time()
        try:
            state, msg = prepare_one(cfg, lesson, cautions, args.model)
        except Exception as exc:  # 한 차시가 실패해도 나머지는 계속
            state, msg = "fail", f"오류: {str(exc)[:200]}"
        item.update(status=state, msg=f"{msg} · {time.time() - t0:.0f}초")
        write_status(status)
        print(f"  {item['period']}교시 {item['subject']} {item['title']}: {state} {item['msg']}")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(run, targets))
    status.update(running=False, finished=time.strftime("%H:%M"))
    write_status(status)
    ok = sum(1 for i in status["items"] if i["status"] == "ok")
    fail = sum(1 for i in status["items"] if i["status"] == "fail")
    print(f"끝: 새로 준비 {ok}, 실패 {fail}")
    return 0 if not fail else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
