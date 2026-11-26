"""수업 비서(teacherlesson-assistant) 로컬 서버.

이 PC 안(127.0.0.1)에서만 열린다. 진도는 기본으로 Supabase 에서 읽고 바꾼다.

    python assistant_server.py          # 서버만 켜기
    python assistant_server.py --open   # 서버 + 왼쪽 수업 비서 창 열기

진도 저장소 고르기 (config.json 의 schedule_backend)
- supabase (기본): supabase_schedule.py 로 Supabase 진도표를 읽고 쓴다.
- 그 밖의 값: 옛 진도 서버(teacherlesson-schedule, config 의 schedule_api, 기본 http://127.0.0.1:5000)를 쓴다.

하는 일
- 진도 저장소(위)에서 그날 수업을 받아 교시별로 보여 준다.
- 수업 흐름(flows/*.json), 출판사별 주의점, 지난 메모를 왼쪽 창에 붙여 준다.
- 출판사 사이트를 오른쪽 창으로 연다. 아이디·비밀번호는 중앙 .env 에서 읽어 클립보드로만 넘긴다.
- 녹음 조각과 수업 기록(메모·알림장 초안)을 내 문서\\my-skills-data\\teacherlesson-assistant 에 저장한다.
- 완료·연장·미루기·따라잡기는 같은 진도 저장소(기본 Supabase 진도 슬롯)를 갱신한다.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SKILL_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(next(p / "_shared" for p in SKILL_DIR.parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import data_dir, env_values  # noqa: E402

SKILL = "teacherlesson-assistant"
DATA = data_dir(SKILL)
WEB = SKILL_DIR / "web"
CONFIG_PATH = DATA / "config.json"
FLOWS = DATA / "flows"
UNITS = DATA / "units"
SESSIONS = DATA / "sessions"
CAUTIONS_PATH = DATA / "publisher_notes.json"
NOTEBOOKLM = DATA / "notebooklm"
DEFAULT_AI_SITES = [
    {"name": "Claude", "url": "https://claude.ai/new"},
    {"name": "Gemini", "url": "https://gemini.google.com/app"},
    {"name": "ChatGPT", "url": "https://chatgpt.com/"},
    {"name": "Grok", "url": "https://grok.com/"},
    {"name": "NotebookLM", "url": "https://notebooklm.google.com/"},
]
PROGRESS_ACTIONS = {"done", "extend", "push", "catch-up", "replace-subject"}
_lock = threading.Lock()
# 녹음 조각 순번 기록: 파일 경로 → {"next": 다음에 받을 순번, "hashes": 조각마다 sha1(재전송 구분용)}. 서버를 끄면 사라진다.
_REC_STATE: dict[str, dict] = {}


# ──────────────────────────── 설정 ────────────────────────────

def load_config() -> dict:
    if not CONFIG_PATH.is_file():
        shutil.copyfile(SKILL_DIR / "config.example.json", CONFIG_PATH)
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))


def read_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def write_json(path: pathlib.Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def safe_name(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", str(text)).strip("_")[:80] or "x"


# NotebookLM 소스·노트에서 차시를 찾는 표시: "[수학 6단원] 4차시" (notebook_sources.py, split_notes.py 와 같이 씀)
def unit_label(unit: str) -> str:
    m = re.match(r"\s*(\d+(?:\.\d+)?)", str(unit))
    return f"{m.group(1)}단원" if m else (str(unit).split() or ["단원"])[0]


def lesson_tag(subject: str, unit: str) -> str:
    return f"[{subject} {unit_label(unit)}]"


def lesson_range(start: int, end: int | None = None) -> str:
    return f"{start}~{end}차시" if end and end != start else f"{start}차시"


def lesson_note_path(subject: str, unit: str, n: int) -> pathlib.Path:
    return NOTEBOOKLM / safe_name(subject) / "notes" / f"{safe_name(unit_label(unit))}_{n}차시.md"


# ──────────────────────────── 수업 목록 ────────────────────────────

def fetch_schedule(cfg: dict, day: date) -> tuple[list[dict], str]:
    """설정된 진도 저장소에서 그날 수업을 가져온다."""
    if cfg.get("schedule_backend", "supabase") == "supabase":
        try:
            import supabase_schedule
            return supabase_schedule.day_schedule(day), "Supabase 진도표"
        except Exception as exc:
            print(f"[schedule] Supabase 조회 실패: {type(exc).__name__}: {exc}", file=sys.stderr)
            return [], "Supabase 연결 오류"
    base = cfg.get("schedule_api", "http://127.0.0.1:5000").rstrip("/")
    url = f"{base}/api/dashboard?board_date={day.isoformat()}"
    try:
        with urllib.request.urlopen(url, timeout=25) as res:  # 진도 서버는 시트를 다시 읽을 때 10초 넘게 걸리기도 함
            payload = json.load(res)
        week = next((v for v in payload.get("views", []) if v.get("id") == "thisweek"), {})
        items = [i for i in week.get("data", []) if str(i.get("planned_date", ""))[:10] == day.isoformat()]
        lessons = [{
            "period": _period_no(i.get("planned_period")),
            "subject": i.get("subject", ""),
            "unit": i.get("unit", ""),
            "lesson": i.get("lesson", ""),
            "title": i.get("title", ""),
            "record_key": str(i.get("record_key") or ""),
            "row_number": i.get("row_number"),
            "bridge_row": i.get("bridge_row"),
            "status": i.get("status", ""),
            "has_pdf": bool(i.get("pdf_path")),
        } for i in items]
        # '여기부터 다시 잡기' 뒤에는 완료된 차시가 원래 날짜 칸에 남는다.
        # 오늘 이후 날짜에서는 완료된 칸을 숨기고, 같은 교시가 겹치면 예정된 수업을 보여 준다.
        if day > date.today():
            lessons = [l for l in lessons if l["status"] != "done"]
        by_period: dict = {}
        for l in lessons:
            key = l["period"] if l["period"] is not None else id(l)
            prev = by_period.get(key)
            if prev is None or (prev["status"] == "done" and l["status"] != "done"):
                by_period[key] = l
        lessons = list(by_period.values())
        return sorted(lessons, key=lambda x: x["period"] or 99), "진도표"
    except (urllib.error.URLError, OSError, ValueError):
        pass
    subjects = cfg.get("fallback_timetable", {}).get(str(day.isoweekday()), [])
    return ([{"period": n, "subject": s, "unit": "", "lesson": "", "title": "", "record_key": "",
              "status": "", "has_pdf": False} for n, s in enumerate(subjects, 1) if s],
            "기본 시간표(진도 서버 꺼짐)")


def _period_no(value) -> int | None:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def upcoming(subject: str) -> list[dict]:
    """'실제로 할 차시 고르기' 후보: 이 과목의 차시를 진도표 순서대로(완료 포함 → 되돌리기 가능).
    남은 첫 차시 앞의 완료 차시는 최근 12개만. 진도 서버가 옛 버전이면 남은 차시(agenda)만."""
    cfg = load_config()
    if cfg.get("schedule_backend", "supabase") == "supabase":
        import supabase_schedule
        items = supabase_schedule.upcoming(subject)
        first_open = next((n for n, item in enumerate(items) if not item.get("done")), len(items))
        return [{**item, "record_key": str(item.get("record_key") or "")}
                for item in items[max(0, first_open - 30):]]
    base = cfg.get("schedule_api", "http://127.0.0.1:5000").rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/api/lessons?subject={urllib.parse.quote(subject)}", timeout=25) as res:
            items = json.load(res).get("items", [])
        first_open = next((n for n, i in enumerate(items) if not i.get("done")), len(items))
        return [{**i, "record_key": str(i.get("record_key") or "")} for i in items[max(0, first_open - 30):first_open + 80]]
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise ValueError(f"진도 서버 오류({exc.code}) — 진도표 시트 형식을 확인해 주세요.") from exc
    with urllib.request.urlopen(f"{base}/api/dashboard", timeout=25) as res:
        payload = json.load(res)
    agenda = next((v for v in payload.get("views", []) if v.get("id") == "agenda"), {}).get("data", [])
    out = []
    for i in agenda:
        if i.get("subject") == subject and str(i.get("status", "")).lower() != "done":
            out.append({"record_key": str(i.get("record_key") or ""), "unit": i.get("unit", ""),
                        "lesson": i.get("lesson", ""), "title": i.get("title", ""),
                        "planned_date": str(i.get("planned_date", ""))[:10],
                        "planned_period": i.get("planned_period", "")})
    return out[:40]


def flow_candidates(lesson: dict) -> list[pathlib.Path]:
    """이 수업의 흐름 파일 후보(앞쪽이 우선): 차시 번호(record_key) → 과목__차시제목."""
    candidates = []
    if lesson.get("record_key"):
        candidates.append(FLOWS / f"{safe_name(lesson['record_key'])}.json")
    if lesson.get("title"):
        candidates.append(FLOWS / f"{safe_name(lesson['subject'])}__{safe_name(lesson['title'])}.json")
    return candidates


def find_flow(lesson: dict) -> dict | None:
    for path in flow_candidates(lesson):
        if path.is_file():
            return read_json(path, None)
    return None


_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")  # 줄바꿈(\n)·탭만 남기고 제어문자 제거


def _clean(value, limit: int = 600) -> str:
    return _CTRL.sub(" ", str(value if value is not None else "")).strip()[:limit]


def _clean_list(value, limit: int = 5, text_limit: int = 500) -> list[str]:
    if isinstance(value, str):
        value = value.splitlines()
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _clean(item, text_limit))][:limit]


def save_flow(body: dict) -> dict:
    """화면에서 고친 수업 흐름을 flows/ 에 저장한다. 값은 서버에서 다시 검사하고,
    직접 고친 흐름이 되도록 자동 준비 표시(auto)는 지운다(prepare_lessons 가 덮어쓰지 않음)."""
    lesson = {k: _clean(body.get(k), 200) for k in ("record_key", "subject", "title")}
    if not lesson["subject"] or not (lesson["record_key"] or lesson["title"]):
        raise ValueError("과목과 차시 정보가 없어 흐름을 저장할 수 없어요.")
    raw = body.get("flow")
    if not isinstance(raw, dict):
        raise ValueError("저장할 수업 흐름이 없어요.")
    steps_in = raw.get("steps")
    if not isinstance(steps_in, list) or not 1 <= len(steps_in) <= 12:
        raise ValueError("단계는 1~12개로 만들어 주세요.")
    steps = []
    for n, item in enumerate(steps_in, 1):
        if not isinstance(item, dict):
            raise ValueError(f"{n}번째 단계 형식이 올바르지 않아요.")
        name = _clean(item.get("name"), 60)
        if not name:
            raise ValueError(f"{n}번째 단계 이름이 비어 있어요.")
        try:
            minutes = int(item.get("minutes") or 0)
        except (TypeError, ValueError):
            raise ValueError(f"{n}번째 단계의 시간(분)이 숫자가 아니에요.") from None
        if not 0 <= minutes <= 120:
            raise ValueError(f"{n}번째 단계의 시간은 0~120분 사이로 적어 주세요.")
        step = {"name": name, "minutes": minutes,
                "purpose": _clean(item.get("purpose"), 300),
                **{k: _clean(item.get(k), 1000 if k in ("do", "say") else 600)
                   for k in ("do", "say", "tip")},
                "teacher_actions": _clean_list(item.get("teacher_actions")),
                "teacher_prompts": _clean_list(item.get("teacher_prompts")),
                "student_actions": _clean_list(item.get("student_actions")),
                "expected_responses": _clean_list(item.get("expected_responses")),
                "teacher_support": _clean(item.get("teacher_support"), 800),
                "check": _clean(item.get("check"), 500)}
        if item.get("flag") in ("keep", "cut"):  # 'keep'=꼭 해야 함, 'cut'=시간이 모자라면 줄여도 되는 단계 (없으면 키 자체를 안 둠 → 옛 흐름과 같은 모양)
            step["flag"] = item["flag"]
        steps.append(step)
    materials = raw.get("materials", [])
    if isinstance(materials, str):
        materials = re.split(r"[,\n]", materials)
    if not isinstance(materials, list):
        raise ValueError("준비물 형식이 올바르지 않아요.")
    materials = [m for m in (_clean(m, 60) for m in materials) if m][:20]

    candidates = flow_candidates(lesson)
    path = next((p for p in candidates if p.is_file()), candidates[0])
    if not path.resolve().is_relative_to(FLOWS.resolve()):
        raise ValueError("저장 위치가 올바르지 않아요.")
    base = read_json(path, {}) if path.is_file() else {}
    flow = {k: v for k, v in (base if isinstance(base, dict) else {}).items() if k != "auto"}
    flow.update(record_key=lesson["record_key"], subject=lesson["subject"], title=lesson["title"],
                lesson_type=_clean(raw.get("lesson_type", flow.get("lesson_type", "")), 80),
                goal=_clean(raw.get("goal"), 300), materials=materials, steps=steps,
                edited={"by": "teacher", "at": datetime.now().strftime("%Y-%m-%d %H:%M")})
    flow.setdefault("publisher", load_config().get("subjects", {}).get(lesson["subject"], {}).get("publisher", ""))
    with _lock:
        write_json(path, flow)
    return {"status": "success", "message": "수업 흐름을 저장했어요.", "flow": flow}


def find_unit(lesson: dict) -> dict | None:
    """단원 개관 요약: units/<과목>__<대단원>.json (Claude 가 지도서 단원 개관 쪽에서 만든다)."""
    if not lesson.get("unit"):
        return None
    path = UNITS / f"{safe_name(lesson['subject'])}__{safe_name(lesson['unit'])}.json"
    return read_json(path, None) if path.is_file() else None


def recent_memos(subject: str, limit: int = 6) -> list[dict]:
    """같은 과목의 지난 수업에서 남긴 '고칠점'·'좋았음' 메모 (최근 것부터)."""
    found = []
    for path in sorted(SESSIONS.glob(f"*/*_{safe_name(subject)}*.json"), reverse=True):
        rec = read_json(path, {})
        if rec.get("subject") != subject:
            continue
        for memo in rec.get("memos", []):
            if memo.get("kind") in ("fix", "good", "voice", "note"):
                found.append({"date": rec.get("date"), "title": rec.get("title", ""),
                              "kind": memo["kind"], "text": memo.get("text", "")})
        if len(found) >= limit:
            break
    return found[:limit]


def state(day: date) -> dict:
    cfg = load_config()
    lessons, source = fetch_schedule(cfg, day)
    cautions = read_json(CAUTIONS_PATH, {})
    subjects = cfg.get("subjects", {})
    for lesson in lessons:
        info = subjects.get(lesson["subject"], {})
        lesson["publisher"] = info.get("publisher", "")
        lesson["site"] = info.get("site", "")
        lesson["has_login"] = bool(info.get("secret_prefix"))
        lesson["has_helper"] = info.get("helper", "") in SITE_HELPERS
        lesson["flow"] = find_flow(lesson)
        lesson["unit_overview"] = find_unit(lesson)
        key = f"{lesson['publisher']}|{lesson['subject']}"
        lesson["cautions"] = cautions.get(key, []) + cautions.get(f"{lesson['publisher']}|*", [])
        lesson["recent_memos"] = recent_memos(lesson["subject"])
        old_session = read_json(session_path(day.isoformat(), lesson["period"], lesson["subject"]), None)
        if lesson.get("record_key"):
            lesson["saved"] = read_json(session_path(day.isoformat(), lesson["period"], lesson["subject"],
                                                        lesson["record_key"]), None)
            if lesson["saved"] is None and old_session:
                if not old_session.get("record_key") or old_session.get("record_key") == lesson["record_key"]:
                    lesson["saved"] = old_session
                else:
                    lesson["saved_mismatch"] = {
                        "record_key": old_session.get("record_key", ""),
                        "lesson": old_session.get("lesson", ""),
                        "title": old_session.get("title", ""),
                    }
        else:
            lesson["saved"] = old_session
    return {
        "date": day.isoformat(),
        "source": source,
        "periods": cfg.get("periods", []),
        "phones": cfg.get("phones", []),
        "links": cfg.get("links", []),
        "hiclass_url": cfg.get("hiclass_url", ""),
        "ai_sites": ai_sites(cfg),
        "schedule_api": cfg.get("schedule_api", ""),
        "lessons": lessons,
    }


def session_path(day: str, period, subject: str, record_key: str = "") -> pathlib.Path:
    try:
        period_no = int(period or 0)
    except (TypeError, ValueError):
        period_no = 0
    lesson_suffix = f"_{safe_name(record_key)}" if record_key else ""
    path = SESSIONS / day / f"{period_no}교시_{safe_name(subject)}{lesson_suffix}.json"
    if not path.resolve().is_relative_to(SESSIONS.resolve()):
        raise ValueError("저장 위치가 올바르지 않아요.")
    return path


# ──────────────────────────── 창 띄우기·클립보드 ────────────────────────────

def chrome_path() -> str | None:
    for base in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        p = pathlib.Path(os.environ.get(base, "")) / "Google/Chrome/Application/chrome.exe"
        if p.is_file():
            return str(p)
    return shutil.which("chrome")


def monitor_rects() -> list[tuple[int, int, int, int, bool]]:
    """Return monitor rectangles and primary flags in desktop coordinates."""
    try:
        import ctypes
        from ctypes import wintypes

        class RECT(ctypes.Structure):
            _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                        ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                        ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                           ctypes.POINTER(RECT), wintypes.LPARAM)
        found = []

        def visit(handle, _dc, _rect, _data):
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(info)
            if user32.GetMonitorInfoW(handle, ctypes.byref(info)):
                r = info.rcMonitor
                found.append((r.left, r.top, r.right, r.bottom, bool(info.dwFlags & 1)))
            return True

        callback = callback_type(visit)
        user32.EnumDisplayMonitors(0, None, callback, 0)
        if found:
            return found
    except Exception:
        pass
    return [(0, 0, 1920, 1080, True)]


def screen_size() -> tuple[int, int]:
    primary = next((r for r in monitor_rects() if r[4]), monitor_rects()[0])
    return primary[2] - primary[0], primary[3] - primary[1]


# ── 새로 연 Chrome 창을 앞으로 가져오기 ──
# 이미 떠 있는 Chrome 에 새 창을 만들게 하면, 백그라운드 프로그램(이 서버)이 시킨 창은 Windows 규칙상
# 다른 창 뒤에 깔릴 수 있다("눌렀는데 창이 안 보여요"). 새로 생긴 창을 찾아 앞으로 올린다.
# Windows 전용·실패해도 조용히 넘어간다(창 열기 자체에는 영향 없음).
CHROME_WINDOW_CLASS = "Chrome_WidgetWin_1"


def _is_windows() -> bool:
    return os.name == "nt"


def _win_api():
    """user32 (인자 형식을 맞춰 둠). 창 핸들 -1(HWND_TOPMOST)이 64비트에서도 안 깨지게 argtypes 를 지정한다."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    u.EnumWindows.argtypes = [enum_proc, wintypes.LPARAM]
    u.EnumWindows.restype = wintypes.BOOL
    u.IsWindowVisible.argtypes = u.IsIconic.argtypes = u.SetForegroundWindow.argtypes = u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    u.IsWindowVisible.restype = u.IsIconic.restype = u.SetForegroundWindow.restype = wintypes.BOOL
    u.GetWindowTextLengthW.restype = ctypes.c_int
    u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    u.GetClassNameW.restype = ctypes.c_int
    u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    u.ShowWindow.restype = wintypes.BOOL
    u.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    u.SetWindowPos.restype = wintypes.BOOL
    # HWND 는 64비트 포인터다. 창 위치 함수도 기본 c_int 변환을 쓰지 않도록
    # 인자와 BOOL 반환형을 명시한다. 두 번째 인자는 RECT 구조체 포인터다.
    u.GetWindowRect.argtypes = [wintypes.HWND, ctypes.c_void_p]
    u.GetWindowRect.restype = wintypes.BOOL
    u.IsZoomed.argtypes = [wintypes.HWND]
    u.IsZoomed.restype = wintypes.BOOL
    u.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
    u._enum_proc = enum_proc
    return u


def chrome_windows(user32) -> set[int]:
    """지금 보이는 Chrome 창(제목 있는 것)의 핸들 모음."""
    import ctypes
    found: set[int] = set()
    buf = ctypes.create_unicode_buffer(256)

    def visit(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            user32.GetClassNameW(hwnd, buf, 256)
            if buf.value == CHROME_WINDOW_CLASS and user32.GetWindowTextLengthW(hwnd) > 0:
                found.add(int(hwnd))
        return True

    user32.EnumWindows(user32._enum_proc(visit), 0)
    return found


def wait_for_new_window(list_windows, before: set[int], timeout: float = 6.0, interval: float = 0.2, sleep=None, clock=None):
    """before 에 없던 창이 나타날 때까지 기다려 그 핸들을 돌려준다(시간 안에 안 나타나면 None)."""
    import time as _time
    sleep, clock = sleep or _time.sleep, clock or _time.monotonic
    end = clock() + timeout
    while True:
        new = sorted(list_windows() - before)
        if new:
            return new[-1]
        if clock() >= end:
            return None
        sleep(interval)


def raise_window(user32, hwnd, rect: tuple[int, int, int, int] | None = None,
                 maximize: bool = False) -> None:
    """요청한 모니터로 옮겨 최대화하고 앞으로 가져온다."""
    SW_RESTORE, SW_MAXIMIZE, SWP = 9, 3, 0x0043  # SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
    HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
    if user32.IsIconic(hwnd) or rect:
        user32.ShowWindow(hwnd, SW_RESTORE)
    if rect:
        user32.SetWindowPos(hwnd, 0, *rect, 0x0040)  # SWP_SHOWWINDOW: 실제 위치·크기 적용
        if maximize:
            # Chrome 이 저장된 창 크기를 다시 적용할 수 있어, 목표 모니터로 옮긴 뒤
            # 그 모니터의 작업 영역 기준으로 최대화한다.
            user32.ShowWindow(hwnd, SW_MAXIMIZE)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP)
    user32.keybd_event(0x12, 0, 0, 0)                  # VK_MENU(Alt) 누름
    user32.keybd_event(0x12, 0, 0x0002, 0)             # 뗌(KEYEVENTF_KEYUP)
    user32.SetForegroundWindow(hwnd)


def _raise_new_window(before: set[int], rect: tuple[int, int, int, int] | None = None,
                      maximize: bool = False) -> None:
    try:
        api = _win_api()
        hwnd = wait_for_new_window(lambda: chrome_windows(api), before)
        if hwnd:
            import time as _time
            if rect:
                import ctypes
                class RECT(ctypes.Structure):
                    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

                # Chrome applies its remembered bounds after the new HWND appears.
                # 일정 시간 재배치해도 최종적으로 요청한 모니터에 최대화되어 있는지 확인한다.
                for _ in range(10):
                    _time.sleep(0.5)
                    raise_window(api, hwnd, rect, maximize)
                    bounds = RECT()
                    api.GetWindowRect(hwnd, ctypes.byref(bounds))
                    cx, cy = (bounds.left + bounds.right) // 2, (bounds.top + bounds.bottom) // 2
                    x, y, width, height = rect
                    placed = (api.IsZoomed(hwnd) and x <= cx < x + width and y <= cy < y + height) if maximize else (
                        bounds.left == x and bounds.top == y and bounds.right - bounds.left == width
                        and bounds.bottom - bounds.top == height)
                    if placed:
                        break
            else:
                _time.sleep(0.7)
                raise_window(api, hwnd, rect)
    except Exception as exc:
        print(f"[window] 새 Chrome 창 배치 실패: {type(exc).__name__}: {exc}", file=sys.stderr)


def ai_sites(cfg: dict) -> list[dict]:
    return cfg.get("ai_sites") or DEFAULT_AI_SITES


def allowed_urls(cfg: dict) -> set[str]:
    urls = {s.get("site", "") for s in cfg.get("subjects", {}).values()}
    urls |= {l.get("url", "") for l in cfg.get("links", [])}
    urls.add(cfg.get("hiclass_url", ""))
    urls |= {s.get("url", "") for s in ai_sites(cfg)}
    urls |= {s.get("notebooklm", "") for s in cfg.get("subjects", {}).values()}
    reg = read_json(data_dir("util-notebooklm") / "notebooks.json", {})
    if isinstance(reg, dict):
        urls |= {registry_notebook(k) for k in reg if str(k).startswith("수업-")}
    return {u for u in urls if u}


def check_site_url(url: str, cfg: dict) -> str:
    """오른쪽 창으로 열 주소는 설정(과목 사이트·노트북·바로가기·하이클래스·AI)에 있는 http(s) 주소만 허용."""
    parsed = urllib.parse.urlparse(str(url))
    if parsed.scheme not in ("http", "https") or url not in allowed_urls(cfg):
        raise ValueError("설정에 없는 주소는 열지 않아요.")
    return url


def open_window(url: str, side: str, cfg: dict) -> str:
    """수업 비서는 왼쪽 화면 1/3, 수업 사이트는 오른쪽 화면 전체에 연다."""
    exe = chrome_path()
    if not exe:
        import webbrowser
        webbrowser.open(url)
        return "Chrome 을 찾지 못해 기본 브라우저로 열었어요."
    monitors = monitor_rects()
    primary = next((r for r in monitors if r[4]), monitors[0])
    px, py, pr, pb, _ = primary
    w, h = pr - px, pb - py
    left_w = max(280, min(w - 360, int(w * float(cfg.get("left_ratio", 0.32)))))
    if side == "left":
        rect = (px, py, left_w, h)
        app_args = [f"--app={url}"]
        maximize = False
    elif side == "right":
        right_monitor = min((r for r in monitors if r[0] >= pr),
                            key=lambda r: r[0], default=None)
        if right_monitor:
            rx, ry, rr, rb, _ = right_monitor
            rect = (rx, ry, rr - rx, rb - ry)
            maximize = True
        else:
            rect = (px + left_w, py, w - left_w, h)
            maximize = False
        app_args = ["--new-window", "--", url]
    else:
        raise ValueError("창 위치 설정이 올바르지 않아요.")
    x, y, width, height = rect
    # 음악·사회 도우미와 같은 프로필·포트를 써서 구글 로그인을 한 번만 하면 되게 한다.
    profile = cfg.get("chrome_profile") or str(
        pathlib.Path(os.environ.get("LOCALAPPDATA", str(pathlib.Path.home()))) / "MusicClassHelper" / "chrome_profile")
    args = [exe, f"--user-data-dir={os.path.expandvars(profile)}", f"--window-position={x},{y}",
            f"--window-size={width},{height}"]
    if cfg.get("debug_port"):
        args.append(f"--remote-debugging-port={int(cfg['debug_port'])}")
    args += app_args
    before = None
    if _is_windows():
        try:
            before = chrome_windows(_win_api())   # 새 창을 알아볼 수 있게 열기 전 Chrome 창 목록을 기억
        except Exception:
            before = None
    subprocess.Popen(args, close_fds=True)
    if before is not None:
        threading.Thread(target=_raise_new_window, args=(before, rect, maximize), daemon=True).start()
    return "창을 열었어요."


def prepare_status() -> dict:
    """수업 준비(prepare_lessons.py) 진행 상황. 프로세스가 죽었으면 진행 중이 아님."""
    import prepare_lessons  # 기본 파이썬만 씀
    status = read_json(prepare_lessons.STATUS, {})
    status["running"] = prepare_lessons.is_running(status)
    return status


def start_prepare(body: dict) -> dict:
    """그날 흐름이 없는 차시를 뒤에서 자동 준비(Gemini, 차시당 30초~2분). 화면은 /api/prepare-status 로 지켜본다."""
    day = str(body.get("date", ""))
    date.fromisoformat(day)
    if prepare_status().get("running"):
        return {"status": "error", "message": "이미 수업 준비가 돌고 있어요. 끝나면 알려 드릴게요."}
    args = [sys.executable, str(SKILL_DIR / "prepare_lessons.py"), "--date", day]
    if body.get("redo"):
        args.append("--redo")
    import time as _time
    import prepare_lessons
    with _lock:
        if prepare_status().get("running"):
            return {"status": "error", "message": "이미 수업 준비가 돌고 있어요."}
        token = os.urandom(6).hex()
        log = open(DATA / "prepare.log", "w", encoding="utf-8")
        proc = subprocess.Popen(args, cwd=SKILL_DIR, stdout=log, stderr=subprocess.STDOUT,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8", PREPARE_TOKEN=token),
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        # 두 번 눌러도 하나만 돌도록 바로 '준비 중' 표시. 스크립트는 같은 token 이면 자기 표시로 보고 계속한다
        # (가상환경 python 은 실행기라 pid 가 스크립트와 다를 수 있음)
        write_json(prepare_lessons.STATUS, {"date": day, "running": True, "started_ts": _time.time(),
                                            "pid": proc.pid, "token": token,
                                            "started": _time.strftime("%H:%M"), "items": []})
    return {"status": "success", "message": "수업 준비를 시작했어요. 차시당 30초~2분 걸려요(다른 일 하셔도 돼요)."}


SITE_HELPERS = {  # config subjects.<과목>.helper → sites/ 아래 차시 자료 자동 열기 도우미
    "music_douclass": ("music_douclass", "music_helper.py"),
    "social_class": ("social_class", "social_class_helper.py"),
}


def open_lesson(body: dict) -> str:
    """과목 도우미(selenium)를 새 창에서 실행해 출판사 사이트의 그 차시 자료를 연다: <도우미> run <단원> <차시>."""
    cfg = load_config()
    subject = str(body.get("subject", ""))
    helper = cfg.get("subjects", {}).get(subject, {}).get("helper", "")
    if helper not in SITE_HELPERS:
        raise ValueError("이 과목은 차시 자료 도우미가 설정되지 않았어요 (config subjects.<과목>.helper).")
    clean = lambda v: re.sub(r"[\x00-\x1f]", " ", str(v or "")).strip()[:100]
    unit, title = clean(body.get("unit")), clean(body.get("title"))
    if not unit or not title:
        raise ValueError("단원·차시 정보가 없어요.")
    folder, script = SITE_HELPERS[helper]
    cwd = SKILL_DIR / "sites" / folder
    py = cfg.get("helper_python") or r"C:\Python313\python.exe"
    if not pathlib.Path(py).is_file():
        py = sys.executable
    port = str(cfg.get("debug_port", 9233))
    profile = os.path.expandvars(cfg.get("chrome_profile", r"%LOCALAPPDATA%\MusicClassHelper\chrome_profile"))
    env = dict(os.environ, MUSIC_CLASS_REMOTE_PORT=port, SOCIAL_CLASS_REMOTE_PORT=port,
               SOCIAL_CLASS_CHROME_PROFILE_DIR=profile, PYTHONIOENCODING="utf-8")
    subprocess.Popen([py, script, "run", unit, title], cwd=cwd, env=env,
                     creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
    return f"{subject} 도우미가 「{title}」 자료를 여는 중이에요 (새 창)."


def copy_secret(subject: str, field: str) -> str:
    cfg = load_config()
    prefix = cfg.get("subjects", {}).get(subject, {}).get("secret_prefix")
    if not prefix or field not in ("id", "pw"):
        raise ValueError("이 과목에는 저장된 로그인 정보가 없어요.")
    key = f"{prefix}_{'ID' if field == 'id' else 'PW'}"
    value = os.environ.get(key) or env_values(SKILL).get(key)
    if not value:
        raise ValueError(f"중앙 .env 에 {key} 가 없어요.")
    # 화면·로그에 값을 남기지 않고 클립보드에만 넣는다.
    subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $input"],
                   input=value, text=True, encoding="utf-8", check=True,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    threading.Timer(30, _clear_clipboard).start()
    return f"{'아이디' if field == 'id' else '비밀번호'}를 복사했어요. 30초 안에 로그인 칸에 Ctrl+V 하세요."


def _clear_clipboard() -> None:
    subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ' '"],
                   check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


# ──────────────────────────── 진도 서버로 넘기기 ────────────────────────────

def progress(action: str, body: dict) -> dict:
    if action not in PROGRESS_ACTIONS:
        raise ValueError("지원하지 않는 진도 작업이에요.")
    cfg = load_config()
    if cfg.get("schedule_backend", "supabase") == "supabase":
        import supabase_schedule
        return supabase_schedule.progress(action, body)
    if action == "replace-subject":
        return {"status": "error", "message": "과목 바꾸기는 Supabase 진도표에서만 사용할 수 있어요."}
    base = cfg.get("schedule_api", "http://127.0.0.1:5000").rstrip("/")
    req = urllib.request.Request(f"{base}/api/{action}", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.load(res)
    except urllib.error.HTTPError as exc:
        try:
            return json.load(exc)
        except ValueError:
            return {"status": "error", "message": f"진도 서버 오류 {exc.code}"}
    except (urllib.error.URLError, OSError):
        return {"status": "error", "message": "진도 서버(teacherlesson-schedule)가 꺼져 있어요."}


# ──────────────────────────── HTTP ────────────────────────────

class Handler(BaseHTTPRequestHandler):
    server_version = "LessonAssistant/1"

    def log_message(self, fmt, *args):  # 녹음 조각 요청이 많아 조용히
        if "/api/rec" not in str(args[0] if args else ""):
            sys.stderr.write("[%s] %s\n" % (datetime.now().strftime("%H:%M:%S"), fmt % args))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, value, code: int = 200) -> None:
        self._send(code, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _send_audio(self, path: pathlib.Path) -> None:
        size = path.stat().st_size
        content_type = "audio/mp4" if path.suffix.lower() == ".mp4" else "audio/webm"
        start, end, status = 0, size - 1, 200
        range_header = self.headers.get("Range", "")
        if range_header.startswith("bytes="):
            try:
                first, last = range_header[6:].split("-", 1)
                start = int(first) if first else max(0, size - int(last))
                end = min(size - 1, int(last)) if first and last else size - 1
                if start > end or start >= size:
                    raise ValueError
                status = 206
            except (ValueError, TypeError):
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as audio:
            audio.seek(start)
            remaining = end - start + 1
            while remaining:
                chunk = audio.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _trusted(self) -> bool:
        """DNS 리바인딩·다른 사이트 요청 막기: Host 는 127.0.0.1/localhost 만, Origin 은 없거나 그 둘만."""
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host", "") not in hosts:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {f"http://{h}" for h in hosts}

    def do_GET(self):
        if not self._trusted():
            return self._json({"status": "error", "message": "이 PC의 수업 비서 화면에서만 열 수 있어요."}, 403)
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        if url.path == "/favicon.ico":
            return self._send(200, (WEB / "favicon.svg").read_bytes(), "image/svg+xml; charset=utf-8")
        if url.path in ("/", "/index.html"):
            return self._send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        if url.path == "/tools.js":
            return self._send(200, (WEB / "tools.js").read_bytes(), "application/javascript; charset=utf-8")
        if url.path == "/api/state":
            try:
                day = date.fromisoformat(q.get("date", [date.today().isoformat()])[0])
            except ValueError:
                return self._json({"status": "error", "message": "날짜 형식이 잘못됐어요."}, 400)
            return self._json(state(day))
        if url.path == "/api/upcoming":
            try:
                return self._json({"status": "success", "items": upcoming(q.get("subject", [""])[0])})
            except ValueError as exc:
                return self._json({"status": "error", "message": str(exc)}, 502)
            except (urllib.error.URLError, OSError):
                return self._json({"status": "error", "message": "진도 서버(teacherlesson-schedule)가 꺼져 있어요."}, 502)
            except RuntimeError as exc:
                return self._json({"status": "error", "message": str(exc)}, 502)
        if url.path == "/api/recordings":
            try:
                day = date.fromisoformat(q.get("date", [date.today().isoformat()])[0]).isoformat()
            except ValueError:
                return self._json({"status": "error", "message": "날짜 형식이 잘못됐어요."}, 400)
            return self._json({"status": "success", "items": recordings_for_day(day)})
        if url.path.startswith("/api/recording/"):
            parts = [urllib.parse.unquote(part) for part in url.path.split("/") if part]
            if len(parts) != 4 or parts[1] != "recording":
                return self._json({"status": "error", "message": "녹음 파일 주소가 올바르지 않아요."}, 404)
            try:
                day = date.fromisoformat(parts[2]).isoformat()
            except ValueError:
                return self._json({"status": "error", "message": "날짜 형식이 잘못됐어요."}, 400)
            name = parts[3]
            stem, suffix = os.path.splitext(name)
            if safe_name(stem) != stem or pathlib.Path(name).name != name or suffix.lower() not in {".webm", ".mp4"}:
                return self._json({"status": "error", "message": "녹음 파일 이름이 올바르지 않아요."}, 404)
            path = (SESSIONS / day / name).resolve()
            if not path.is_relative_to(SESSIONS.resolve()) or not path.is_file():
                return self._json({"status": "error", "message": "녹음 파일을 찾지 못했어요."}, 404)
            return self._send_audio(path)
        if url.path == "/api/subjects":
            try:
                import supabase_schedule
                if load_config().get("schedule_backend", "supabase") != "supabase":
                    return self._json({"status": "error", "message": "과목 바꾸기는 Supabase 진도표에서만 사용할 수 있어요."}, 400)
                return self._json({"status": "success", "items": supabase_schedule.subject_names()})
            except (ValueError, RuntimeError, urllib.error.URLError, OSError) as exc:
                return self._json({"status": "error", "message": str(exc) or "과목 목록을 불러오지 못했어요."}, 502)
        if url.path == "/api/prepare-status":
            return self._json(prepare_status())
        if url.path.startswith("/api/unit-pdf/"):
            name = urllib.parse.unquote(url.path.rsplit("/", 1)[-1])
            path = UNITS / name
            if not name.endswith(".pdf") or "/" in name or "\\" in name or not path.is_file()                     or not path.resolve().is_relative_to(UNITS.resolve()):
                return self._json({"status": "error", "message": "단원 개관 PDF가 없어요."}, 404)
            return self._send(200, path.read_bytes(), "application/pdf")
        if url.path.startswith("/api/pdf/"):
            cfg = load_config()
            if cfg.get("schedule_backend", "supabase") == "supabase":
                record_key = urllib.parse.unquote(url.path.rsplit("/", 1)[-1])
                try:
                    import supabase_schedule
                    return self._send(200, supabase_schedule.pdf_for_lesson(record_key), "application/pdf")
                except (OSError, ValueError, RuntimeError) as exc:
                    return self._json({"status": "error", "message": str(exc)}, 404)
            base = cfg.get("schedule_api", "http://127.0.0.1:5000").rstrip("/")
            self.send_response(302)
            self.send_header("Location", base + url.path)
            self.end_headers()
            return None
        return self._json({"status": "error", "message": "없는 주소"}, 404)

    def do_POST(self):
        if not self._trusted():
            return self._json({"status": "error", "message": "다른 사이트의 요청은 받지 않아요."}, 403)
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            if url.path == "/api/rec":
                result = save_audio(q, raw)
                return self._json(result, 409 if result.get("code") == "gap" else 200)
            body = json.loads(raw.decode("utf-8") or "{}")
            if url.path == "/api/open-site":
                cfg = load_config()
                return self._json({"status": "success", "message": open_window(check_site_url(body.get("url", ""), cfg), "right", cfg)})
            if url.path == "/api/prepare":
                return self._json(start_prepare(body))
            if url.path == "/api/open-lesson":
                return self._json({"status": "success", "message": open_lesson(body)})
            if url.path == "/api/copy-secret":
                return self._json({"status": "success", "message": copy_secret(body.get("subject", ""), body.get("field", ""))})
            if url.path == "/api/ask-prepare":
                return self._json(ask_prepare(body))
            if url.path == "/api/session":
                return self._json(save_session(body))
            if url.path == "/api/flow":
                return self._json(save_flow(body))
            if url.path == "/api/caution":
                return self._json(add_caution(body))
            if url.path.startswith("/api/progress/"):
                return self._json(progress(url.path.rsplit("/", 1)[-1], body))
        except (ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
            return self._json({"status": "error", "message": str(exc)}, 400)
        return self._json({"status": "error", "message": "없는 주소"}, 404)


ASK_ITEMS = ["1. 40분 수업 흐름(도입–전개–정리)과 시간 배분",
             "2. 핵심 발문 3~5개와 예상되는 학생 답",
             "3. 학생들이 어려워할 부분과 도와주는 방법",
             "4. 지도서 활동을 더 쉽게·재미있게 바꿀 아이디어 (준비물이 적은 것)",
             "5. 수업 끝에 이해를 확인할 질문 1~2개"]


def lesson_numbers(lesson: str) -> tuple[int, int] | None:
    """진도표 차시 '3(3~4)' → (3, 4), '5' → (5, 5)."""
    m = re.search(r"\((\d+)\s*[~∼]\s*(\d+)\)", lesson) or re.search(r"(\d+)(?:\s*[~∼]\s*(\d+))?", lesson)
    if not m:
        return None
    a = int(m.group(1))
    return a, int(m.group(2) or a)


def cautions_for(cfg: dict, subject: str) -> list[str]:
    publisher = cfg.get("subjects", {}).get(subject, {}).get("publisher", "")
    notes = read_json(CAUTIONS_PATH, {})
    return [c["text"] for c in notes.get(f"{publisher}|{subject}", []) + notes.get(f"{publisher}|*", [])]


def registry_notebook(topic: str) -> str:
    """util-notebooklm 의 노트북 목록(nlm.py nb add 수업-수학 <주소>)에서 주소 찾기. https://notebooklm.google.com/ 주소만."""
    reg = read_json(data_dir("util-notebooklm") / "notebooks.json", {})
    url = str(reg.get(topic, {}).get("url", "")) if isinstance(reg, dict) else ""
    return url if url.startswith("https://notebooklm.google.com/") else ""


def ask_notebooklm(cfg: dict, subject: str, unit: str, lesson: str, title: str) -> dict:
    """NotebookLM: 지도서는 이미 소스로 올라가 있으니 파일은 모으지 않고, '[과목 N단원] N차시' 를 짚는 질문만 만든다."""
    nums = lesson_numbers(lesson)
    mark = f"{lesson_tag(subject, unit)} {lesson_range(*nums)}" if nums and unit else ""
    url = cfg.get("subjects", {}).get(subject, {}).get("notebooklm", "") or registry_notebook(f"수업-{subject}")
    lines = [f"초등학교 3학년 {subject} 수업을 준비하고 있습니다."]
    if mark:
        lines += [f"소스 「{unit}」에서 \"{mark}\" 제목 아래 부분(이번 차시: 「{title}」)을 바탕으로 답해 주세요.",
                  f"답의 맨 위에는 다음 제목을 그대로 써 주세요: ## {mark} {title}"]
    else:
        lines.append(f"이번 차시: 「{title}」")
    lines += ["", "짧고 실용적으로 알려 주세요.", *ASK_ITEMS]
    cautions = cautions_for(cfg, subject)
    if cautions:
        lines += ["", "참고 – 이 출판사 지도서를 쓰며 느낀 점:"] + [f"- {c}" for c in cautions[:5]]
    msg = ("과목 노트북을 열고 질문을 복사했어요. 대화창에 Ctrl+V 하세요." if url else
           "이 과목 노트북 주소가 config 에 없어 NotebookLM 첫 화면을 열어요(subjects.<과목>.notebooklm).")
    return {"status": "success", "prompt": "\n".join(lines), "files": [], "missing": [],
            "url": url or None, "message": msg}


def ask_prepare(body: dict) -> dict:
    """웹 AI(Claude·Gemini·ChatGPT 등)에 물어볼 준비: 단원 개관 PDF + 차시 지도서 PDF 를 한 폴더에 모으고 질문 문장을 만든다.
    학생 메모·녹음은 넣지 않는다(개인정보). mode=notebooklm 이면 질문만 만든다."""
    cfg = load_config()
    day = body.get("date", "")
    date.fromisoformat(day)
    subject, unit = str(body.get("subject", "")), str(body.get("unit", ""))
    lesson, title = str(body.get("lesson", "")), str(body.get("title", ""))
    if body.get("mode") == "notebooklm":
        return ask_notebooklm(cfg, subject, unit, lesson, title)
    record_key = str(body.get("record_key", ""))
    if record_key and not re.fullmatch(r"[A-Za-z0-9_\-]{1,40}", record_key):
        raise ValueError("차시 번호 형식이 잘못됐어요.")
    folder = DATA / "ask" / day / safe_name(f"{body.get('period') or 0}교시_{subject}")
    if not folder.resolve().is_relative_to(DATA.resolve()):
        raise ValueError("저장 위치가 올바르지 않아요.")
    folder.mkdir(parents=True, exist_ok=True)
    files, missing = [], []
    unit_info = find_unit({"subject": subject, "unit": unit}) or {}
    overview = UNITS / str(unit_info.get("overview_pdf", ""))
    if unit_info.get("overview_pdf") and overview.is_file():
        dest = folder / f"1_단원개관_{safe_name(unit)}.pdf"
        shutil.copyfile(overview, dest)
        files.append(dest.name)
    else:
        missing.append("단원 개관 PDF")
    if record_key:
        try:
            if cfg.get("schedule_backend", "supabase") == "supabase":
                import supabase_schedule
                data = supabase_schedule.pdf_for_lesson(record_key)
            else:
                base = cfg.get("schedule_api", "http://127.0.0.1:5000").rstrip("/")
                with urllib.request.urlopen(f"{base}/api/pdf/{urllib.parse.quote(record_key)}", timeout=60) as res:
                    data = res.read()
            if data[:5] == b"%PDF-":
                dest = folder / f"2_차시지도서_{safe_name(lesson)}차시.pdf"
                dest.write_bytes(data)
                files.append(dest.name)
            else:
                missing.append("차시 지도서 PDF")
        except (urllib.error.URLError, OSError):
            missing.append("차시 지도서 PDF(진도 서버 확인)")
    else:
        missing.append("차시 지도서 PDF")
    nums = lesson_numbers(lesson)
    note = lesson_note_path(subject, unit, nums[0]) if nums and unit else None
    if note and note.is_file() and note.resolve().is_relative_to(NOTEBOOKLM.resolve()):
        dest = folder / f"3_NotebookLM노트_{nums[0]}차시.md"
        shutil.copyfile(note, dest)
        files.append(dest.name)
    publisher = cfg.get("subjects", {}).get(subject, {}).get("publisher", "")
    cautions = cautions_for(cfg, subject)
    lines = [f"초등학교 3학년 {subject} 수업을 준비하고 있습니다.",
             f"- 단원: {unit}", f"- 이번 차시: {lesson}차시 「{title}」"]
    if publisher:
        lines.append(f"- 교과서·지도서 출판사: {publisher}")
    if files:
        lines.append("첨부: " + ", ".join(files))
    lines += ["", "첨부한 지도서를 바탕으로 아래를 짧고 실용적으로 알려 주세요.", *ASK_ITEMS]
    if cautions:
        lines += ["", "참고 – 이 출판사 지도서를 쓰며 느낀 점:"] + [f"- {c}" for c in cautions[:5]]
    prompt = "\n".join(lines)
    (folder / "질문.txt").write_text(prompt, encoding="utf-8")
    subprocess.Popen(["explorer", str(folder)])
    return {"status": "success", "prompt": prompt, "files": files, "missing": missing,
            "message": "파일 폴더를 열고 질문을 복사했어요. 파일을 대화창에 끌어다 놓고 Ctrl+V 하세요."
                       + (f" (없음: {', '.join(missing)})" if missing else "")}


def _rec_gap(path: pathlib.Path, expected: int, got: int) -> dict:
    """순번이 건너뛰어 온 조각은 받지 않고, 먼저 보내야 할 순번을 알려 준다(클라이언트가 다시 보냄)."""
    return {"status": "error", "code": "gap", "expected": expected, "got": got, "file": path.name,
            "message": f"앞 조각이 빠졌어요. {expected}번 조각부터 다시 보내 주세요."}


def save_audio(q: dict, raw: bytes) -> dict:
    """녹음 조각(seq 0, 1, 2, …)을 순서대로 이어 붙인다(ISSUE-010).

    - 이미 받은 순번이 같은 내용으로 다시 오면(응답을 못 받고 재전송) 쓰지 않고 성공으로 답한다.
    - 순번이 건너뛰면 쓰지 않고 code='gap' 오류로 먼저 필요한 순번(expected)을 알려 준다.
    - 쓰다 실패하면 반쯤 쓴 조각이 남지 않게 되돌린다.
    """
    day = q.get("date", [""])[0]
    date.fromisoformat(day)  # 날짜 형식 검사
    name = safe_name(q.get("name", ["rec"])[0])
    seq = int(q.get("seq", ["0"])[0])
    if seq < 0:
        raise ValueError("조각 순번이 올바르지 않아요.")
    ext = "mp4" if q.get("ext", ["webm"])[0] == "mp4" else "webm"
    path = SESSIONS / day / f"{name}.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    key = str(path)
    digest = hashlib.sha1(raw).hexdigest()
    with _lock:
        state = _REC_STATE.get(key)

        def ok(**extra) -> dict:
            size = path.stat().st_size if path.exists() else 0
            return {"status": "success", "bytes": size, "file": path.name,
                    "next": _REC_STATE[key]["next"], **extra}

        if state is not None and seq < state["next"]:
            known = state["hashes"][seq]
            if known is None or known == digest:  # 응답을 못 받아 다시 보낸 같은 조각
                return ok(duplicate=True)
            if seq == 0:
                pass  # 같은 이름의 새 녹음 — 아래에서 이름 겹침 오류
            else:
                raise ValueError(f"{seq}번 조각이 이미 있는데 내용이 달라요. 새 녹음으로 시작해 주세요.")
        if seq == 0:
            if path.exists():  # 앞 녹음을 덮어쓰지 않는다
                n = 2
                while (SESSIONS / day / f"{name}_{n}.{ext}").exists():
                    n += 1
                raise ValueError(f"같은 이름 녹음이 있어요. 이름: {name}_{n}")
            before = 0
            new_state = {"next": 1, "hashes": [digest]}
        else:
            if state is None:
                if not path.exists():  # 첫 조각(머리 정보) 없이는 재생이 안 되므로 받지 않는다
                    return _rec_gap(path, 0, seq)
                # 서버를 다시 켠 뒤 이어서 오는 조각: 순번을 알 수 없으니 이 조각부터 이어 붙인다
                state = {"next": seq, "hashes": [None] * seq}
            if seq > state["next"]:
                return _rec_gap(path, state["next"], seq)
            before = path.stat().st_size
            new_state = {"next": seq + 1, "hashes": state["hashes"][:seq] + [digest]}
        try:
            with open(path, "wb" if seq == 0 else "ab") as fh:
                fh.write(raw)
        except OSError:
            try:  # 반쯤 쓴 조각이 남아 다음에 이어 붙을 때 깨지지 않게 되돌린다
                if seq == 0:
                    path.unlink(missing_ok=True)
                else:
                    with open(path, "r+b") as fh:
                        fh.truncate(before)
            except OSError:
                pass
            raise
        _REC_STATE[key] = new_state
        return ok()


def recordings_for_day(day: str) -> list[dict]:
    """수업 기록 JSON에 연결된 그날의 실제 음성 파일 목록."""
    date.fromisoformat(day)
    folder = SESSIONS / day
    if not folder.is_dir():
        return []
    sessions_by_file = {}
    for session_file in folder.glob("*.json"):
        record = read_json(session_file, {})
        for name in record.get("rec_files", []):
            sessions_by_file[pathlib.Path(str(name)).name] = record
    items = []
    for audio in folder.iterdir():
        if not audio.is_file() or audio.suffix.lower() not in {".webm", ".mp4"}:
            continue
        record = sessions_by_file.get(audio.name, {})
        period_match = re.match(r"(\d+)교시_", audio.name)
        items.append({
            "file": audio.name,
            "url": f"/api/recording/{day}/{urllib.parse.quote(audio.name)}",
            "period": record.get("period") or (int(period_match.group(1)) if period_match else None),
            "subject": record.get("subject", ""),
            "lesson": record.get("lesson", ""),
            "title": record.get("title", ""),
            "record_key": record.get("record_key", ""),
            "size": audio.stat().st_size,
        })
    return sorted(items, key=lambda item: (item.get("period") or 99, item["file"]))


def save_session(body: dict) -> dict:
    day = body.get("date", "")
    date.fromisoformat(day)
    path = session_path(day, body.get("period"), body.get("subject", ""), body.get("record_key", ""))
    body["saved_at"] = datetime.now().isoformat(timespec="seconds")
    with _lock:
        write_json(path, body)
    return {"status": "success", "message": f"저장했어요: {path.relative_to(DATA)}"}


def add_caution(body: dict) -> dict:
    text = str(body.get("text", "")).strip()
    if not text:
        raise ValueError("내용이 비어 있어요.")
    key = f"{body.get('publisher', '')}|{body.get('subject') or '*'}"
    with _lock:
        notes = read_json(CAUTIONS_PATH, {})
        notes.setdefault(key, []).append({"text": text, "date": date.today().isoformat()})
        write_json(CAUTIONS_PATH, notes)
    return {"status": "success", "message": "다음 수업 주의점에 추가했어요."}


def main() -> None:
    cfg = load_config()
    FLOWS.mkdir(parents=True, exist_ok=True)
    UNITS.mkdir(parents=True, exist_ok=True)
    SESSIONS.mkdir(parents=True, exist_ok=True)
    port = int(cfg.get("port", 5180))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"수업 비서: {url}\n데이터: {DATA}\n끄려면 이 창에서 Ctrl+C")
    if "--open" in sys.argv:
        day_arg = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--date=")), "")
        open_window(url + (f"?date={date.fromisoformat(day_arg).isoformat()}" if day_arg else ""), "left", cfg)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
