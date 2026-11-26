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
WORKERS = 1  # Gemini CLI 요청을 동시에 여러 개 보내 API 종료 오류가 나지 않게 차례로 준비한다.
STALE_SECONDS = 30 * 60
PERSONAL_STORY = re.compile(r"(?:지난\s*(?:주|달|한 달|주말)|어제|이번\s*주말|가족|부모님|엄마|아빠|할머니|할아버지|친구와 함께|친구랑|저는|나는|우리 가족|다녀왔|놀러 갔|갔습니다|갔어요|탔습니다|탔어요)")

PLAN_PROMPT = """@{file} 이 자료는 초등학교 3학년 {subject} 교사용 지도서({publisher}) 가운데 「{unit}」 {lesson}차시 「{title}」 부분입니다.
지도서에서 이 한 차시의 학습 목표·준비물·수업 형태·실제 활동을 읽고, 40분 수업의 단계 뼈대만 JSON 하나로 답하세요. 설명 문장이나 ``` 표시는 쓰지 마세요.

{{"lesson_type":"예: 실험·탐구, 토의, 만들기, 연극·발표, 기능 연습, 읽기·감상",
 "goal":"학습 목표 한 문장", "materials":["지도서에 나온 준비물"],
 "steps":[{{"name":"단계 이름", "minutes":5, "purpose":"이 단계에서 하는 일", "flag":"keep 또는 cut 또는 빈 문자열"}}],
 "homework":"숙제·다음 시간 준비물(없으면 빈 문자열)",
 "pages":"근거 쪽수"}}

규칙
- 단계는 4~8개, 시간 합계는 40분. 도입·전개·정리만 기계적으로 나누지 말고 이 차시의 실제 활동이 드러나게 쪼갭니다.
- 서로 다른 일을 한 단계에 묶지 않습니다(예: "활동지 작성 및 발표"는 작성·발표 안내·발표·듣고 반응하기를 나눔). 발표가 지도서 활동에 있으면 최소한 "발표 방법과 듣는 약속 안내"와 "발표·듣는 학생의 반응"을 따로 둡니다. 모둠별 차례가 필요하면 발표 단계를 더 나누되 모둠 수·순서는 지어내지 않습니다.
- 탐구·실험은 질문·예상·준비·실행·관찰·설명 중 필요한 흐름을, 토의는 쟁점·생각·근거·공유·정리 중 필요한 흐름을, 만들기는 계획·제작·공유·돌아보기 중 필요한 흐름을 씁니다. 이는 참고이며 모든 형태에 억지로 맞추지 않습니다.
- 지도서에 없는 모둠 수·발표 순서·도구·평가 기준을 지어내지 않습니다. 정해져 있지 않으면 일반적인 운영 단계만 둡니다.
- flag: 핵심은 "keep", 시간이 모자라면 줄일 수 있는 보충은 "cut", 나머지는 "".
- 반드시 「{title}」 이번 차시만 씁니다. 묶음 차시면 한 시간 분량을 골라 구성합니다.
- 이 차시의 지도서 근거가 부족하면 없는 내용을 채우지 말고 목적에 "지도서에 안내 없음"을 적습니다.
{correction}{cautions}"""

DETAIL_PROMPT = """@{file} 이 자료는 초등학교 3학년 {subject} 교사용 지도서({publisher}) 가운데 「{unit}」 {lesson}차시 「{title}」 부분입니다.
아래 수업 형태와 단계 뼈대를 유지하고, 각 단계를 교사가 바로 진행할 수 있도록 구체적인 안내로 채우세요. JSON 하나만 답하고 설명 문장이나 ``` 표시는 쓰지 마세요.

단계 뼈대:
{plan}

결과 형식:
{{"lesson_type":"핵심 수업 형태 한 가지", "goal":"학습 목표", "materials":["준비물"],
 "steps":[{{"name":"단계 이름", "minutes":5,
   "teacher_actions":["교사가 할 일을 순서대로"], "teacher_prompts":["교사가 실제로 할 발문"],
   "student_actions":["학생이 할 말이나 행동"], "expected_responses":["예상 학생 반응 예시"],
   "teacher_support":"반응이 없거나 어려워할 때 이어갈 안내", "check":"교사가 확인할 점",
   "tip":"안전·운영 주의점", "flag":"keep 또는 cut 또는 빈 문자열"}}],
 "homework":"숙제·다음 시간 준비물", "pages":"근거 쪽수"}}

규칙
- 단계 수·순서·이름·분은 뼈대와 정확히 같게 둡니다.
- 이름에 서로 다른 활동이 "및"으로 묶여 있더라도 안내·수행·공유처럼 교사 안내가 달라지는 일은 한 단계씩 나누어야 합니다. 발표는 발표자 안내·발표·듣는 학생의 반응이 각각 보이게 합니다.
- 교사 행동과 학생 행동은 짧은 순서 목록으로 씁니다. 막연한 "활동한다" 대신 무엇을 펼치고, 말하고, 만들고, 기록하고, 발표하는지 씁니다.
- 단계마다 실제로 쓸 수 있는 발문을 1~3개 넣고, 그 활동에서 나올 법한 학생 반응 예시를 1~2개 넣습니다. 예상 반응은 예시이며 모든 학생이 같은 답을 한다고 단정하지 않습니다. 학생의 이름·가족·구체적인 과거 일화·장소·날짜를 절대 지어내지 않습니다. 경험 질문은 "버스나 지하철을 타 본 적이 있어요."처럼 일반적인 반응 예시만 들거나 "학생마다 경험이 다를 수 있음"이라고 씁니다.
- 지도서의 내용·용어·발문을 우선 근거로 삼습니다. 지도서에 없는 진행 보조는 "운영 제안:"이라고 표시하고, 지도서에 없는 정답·평가 기준·준비물·학생 수를 지어내지 않습니다.
- 반응이 막힐 때의 지원은 정답을 바로 말하기보다 다시 관찰하거나 생각하게 하는 짧은 후속 질문으로 씁니다. 해당 없는 칸은 빈 문자열 또는 빈 목록으로 둡니다.
- 반드시 「{title}」 이번 차시만 쓰고 묶음 차시의 다른 차시 내용을 섞지 않습니다. 문장은 초등 수업 중 한눈에 읽히도록 쉽게 씁니다.
{correction}{cautions}"""


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


def pdf_text_source(pdf: pathlib.Path) -> str:
    """PDF 에서 글자를 뽑아 쪽 표시를 붙인다. 스캔 PDF 이거나 추출 실패면 빈 문자열."""
    try:
        import fitz
        doc = fitz.open(pdf)
    except (ImportError, OSError, RuntimeError):
        return ""
    try:
        pages = []
        for page_no, page in enumerate(doc, 1):
            text = page.get_text("text").strip()
            if text:
                pages.append(f"〔p.{page_no}〕\n{text}")
        return "\n\n".join(pages)
    except (OSError, RuntimeError):
        return ""
    finally:
        doc.close()


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


def _json_object(text: str) -> dict:
    """응답 설명문 앞뒤에서 JSON 객체를 찾아 흐름 단계가 있는 것을 고른다."""
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


def _text_list(value, limit: int = 5) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"\n+", value)
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:500] for item in value if item is not None and str(item).strip()][:limit]


def _material_list(value, limit: int) -> list[str]:
    if isinstance(value, str):
        value = re.split(r"[,、·\n]+", value)
    return _text_list(value, limit)


def parse_plan(text: str) -> dict:
    """Gemini 의 수업 형태·단계 뼈대를 검사한다."""
    data = _json_object(text)
    steps = data.get("steps")
    if not isinstance(steps, list) or not 4 <= len(steps) <= 8:
        raise ValueError("단계 뼈대는 4~8개여야 함")
    clean_steps = []
    for s in steps:
        if not isinstance(s, dict) or not str(s.get("name", "")).strip():
            raise ValueError("단계 이름이 없음")
        try:
            minutes = int(re.search(r"\d+", str(s.get("minutes", "0"))).group())
        except (AttributeError, ValueError):
            minutes = 0
        if not 1 <= minutes <= 40:
            raise ValueError("단계 시간이 1~40분 범위가 아님")
        name = str(s["name"]).strip()[:80]
        step = {"name": name, "minutes": minutes,
                "purpose": str(s.get("purpose") or "").strip()[:300]}
        if str(s.get("flag", "")).strip().lower() in ("keep", "cut"):
            step["flag"] = str(s["flag"]).strip().lower()
        clean_steps.append(step)
    if sum(s["minutes"] for s in clean_steps) != 40:
        raise ValueError("단계 시간 합계가 40분이 아님")
    expanded = []
    combined_presentation = re.compile(r"(?:작성|준비|연습|제작|계획)\s*(?:및|하고|한 뒤)\s*발표")
    for step in clean_steps:
        if combined_presentation.search(step["name"]) and step["minutes"] >= 2:
            minutes = step["minutes"]
            prep_minutes = max(1, minutes // 3)
            guide_minutes = 1 if minutes >= 3 else 0
            share_minutes = minutes - prep_minutes - guide_minutes
            prefix = "운영 제안: "
            expanded.append({"name": "발표할 내용 준비", "minutes": prep_minutes,
                             "purpose": prefix + (step["purpose"] or "발표할 내용을 정리합니다.")})
            if guide_minutes:
                expanded.append({"name": "발표 방법과 듣는 약속 안내", "minutes": guide_minutes,
                                 "purpose": prefix + "발표할 내용과 듣는 방법을 안내합니다. 모둠 수와 순서는 정하지 않습니다."})
            expanded.append({"name": "발표하고 듣는 학생의 반응 나누기", "minutes": share_minutes,
                             "purpose": prefix + "정해진 모둠 수나 발표 순서를 가정하지 않고 발표와 듣기를 진행합니다."})
        elif "및" in step["name"] and step["minutes"] >= 2:
            left, right = (part.strip() for part in step["name"].split("및", 1))
            if left and right:
                left_minutes = max(1, step["minutes"] // 2)
                right_minutes = step["minutes"] - left_minutes
                expanded.extend([
                    {"name": left, "minutes": left_minutes,
                     "purpose": f"운영 제안: 「{left}」에 집중합니다."},
                    {"name": right, "minutes": right_minutes,
                     "purpose": f"운영 제안: 이어서 「{right}」를 진행합니다."},
                ])
            else:
                expanded.append(step)
        else:
            expanded.append(step)
    clean_steps = expanded
    if len(clean_steps) > 12:
        raise ValueError("세부 단계가 12개를 넘음; 합칠 단계와 분 배분을 다시 정해야 함")
    return {"lesson_type": str(data.get("lesson_type") or "").strip()[:80],
            "goal": str(data.get("goal") or "").strip()[:300],
            "materials": _material_list(data.get("materials"), 20), "steps": clean_steps,
            "homework": str(data.get("homework") or "").strip()[:300],
            "pages": str(data.get("pages") or "").strip()[:100]}


def parse_flow(text: str, plan: dict | None = None) -> dict:
    """Gemini 의 단계별 안내를 뼈대에 맞춰 정리한다. 잘못되면 ValueError."""
    data = _json_object(text)
    steps = data.get("steps")
    if plan is None:  # 기존 자동 시험·옛 한 번 생성 형식과의 호환
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
            step = {k: str(s.get(k) or "").strip() for k in ("name", "do", "say", "tip")} | {"minutes": minutes}
            if str(s.get("flag", "")).strip().lower() in ("keep", "cut"):
                step["flag"] = str(s["flag"]).strip().lower()
            clean_steps.append(step)
        return {"goal": str(data.get("goal") or "").strip(), "materials": _material_list(data.get("materials"), 12),
                "steps": clean_steps, "homework": str(data.get("homework") or "").strip(),
                "pages": str(data.get("pages") or "").strip()}
    if not isinstance(steps, list) or len(steps) != len(plan["steps"]):
        raise ValueError("상세 단계 수가 뼈대와 다름")
    clean_steps = []
    for s, outline in zip(steps, plan["steps"]):
        if not isinstance(s, dict) or not str(s.get("name", "")).strip():
            raise ValueError("단계 이름이 없음")
        teacher = _text_list(s.get("teacher_actions"), 5)
        students = _text_list(s.get("student_actions"), 5)
        prompts = _text_list(s.get("teacher_prompts"), 5)
        expected = _text_list(s.get("expected_responses"), 5)
        if any(PERSONAL_STORY.search(item) for item in expected):
            expected = ["학생마다 경험과 생각이 다를 수 있어요. 각자 생각을 정리하고 원하는 학생이 나눌 수 있습니다."]
        if not teacher or not students:
            raise ValueError(f"{outline['name']} 단계의 교사·학생 행동이 비어 있음")
        step = {"name": outline["name"], "minutes": outline["minutes"],
                "purpose": outline.get("purpose", ""),
                "teacher_actions": teacher, "teacher_prompts": prompts,
                "student_actions": students, "expected_responses": expected,
                "teacher_support": str(s.get("teacher_support") or "").strip()[:600],
                "check": str(s.get("check") or "").strip()[:400],
                "tip": str(s.get("tip") or "").strip()[:400]}
        # 옛 화면·자료와의 호환: 자세한 안내를 기존 활동·발문 칸에도 간단히 요약한다.
        step["do"] = "교사: " + " / ".join(teacher[:2]) + " · 학생: " + " / ".join(students[:2])
        step["say"] = prompts[0] if prompts else ""
        if outline.get("flag") in ("keep", "cut"):
            step["flag"] = outline["flag"]
        clean_steps.append(step)
    return {"lesson_type": plan["lesson_type"], "goal": plan["goal"], "materials": plan["materials"],
            "steps": clean_steps, "homework": plan["homework"], "pages": plan["pages"]}


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
            extracted = pdf_text_source(pdf)
            if len(extracted) >= 300:
                text_source = tmp / "lesson.md"
                text_source.write_text(extracted, encoding="utf-8")
                pdf = text_source  # 큰 PDF 대신 쪽 표시가 붙은 작은 텍스트를 Gemini 에 보낸다
        caution_text = ("\n- 이 출판사 지도서를 쓰며 교사가 남긴 주의점도 반영합니다: " + " / ".join(cautions[:5])) if cautions else ""
        prompt_values = {"file": "{file}", "subject": lesson["subject"],
                         "publisher": lesson.get("publisher") or "출판사", "unit": lesson.get("unit", ""),
                         "lesson": lesson.get("lesson", ""), "title": lesson.get("title", ""),
                         "cautions": caution_text, "correction": ""}
        last_error = ""
        plan = None
        failed_stage = "plan"
        for attempt in range(2):  # 형식이 틀리면 한 번 더
            try:
                if plan is None:
                    failed_stage = "plan"
                    plan_prompt = PLAN_PROMPT.format(**prompt_values)
                    plan_answer, model = nlm.gemini_ask(
                        pdf, plan_prompt, model=model, timeout=120,
                        model_timeout=45 if section else None,
                        work=tmp / f"gemini_plan{attempt}")
                    plan = parse_plan(plan_answer)
                failed_stage = "detail"
                detail_values = dict(prompt_values, plan=json.dumps(plan, ensure_ascii=False, indent=2))
                detail_prompt = DETAIL_PROMPT.format(**detail_values)
                answer, model = nlm.gemini_ask(
                    pdf, detail_prompt, model=model, timeout=120,
                    model_timeout=45 if section else None,
                    work=tmp / f"gemini_steps{attempt}")
                flow = parse_flow(answer, plan)
                break
            except RuntimeError as exc:
                # gemini_ask 가 이미 사용 가능한 모델을 모두 시도했으므로 같은 요청을 즉시 반복하지 않는다.
                return "fail", f"Gemini 연결 실패: {str(exc)[:200]}"
            except (ValueError, json.JSONDecodeError) as exc:
                last_error = str(exc)[:200]
                prompt_values["correction"] = f"\n이전 응답 수정 요청: {last_error}. 이 규칙을 반영해 다시 답하세요.\n"
                if failed_stage == "plan":
                    plan = None
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
