"""📅 오늘·이번 주 일정과 할 일 칸 (T107, ISSUE-052 ②).

school-todo-kakao 의 일정DB 시트(카톡 아침 알림과 같은 시트)를 읽어 수업 비서에 보여 준다.
어떤 행을 보여 줄지는 아침 메시지(schooltodo/message.py)와 같다: 상태 칸이 비어 있고, 대상이 '타학년·유치원'이 아닌 행.
  - 행사: 구분이 '개인'이 아닌 것(출장·학교·공지)
  - 할 일: 구분이 '개인'인 것(기한이 있는 해야 할 일)
쓰는 것은 '빠른 할 일' 한 가지뿐이다: 확인(confirm)을 거친 한 줄을 시트의 '빠른입력' 탭에 덧붙인다.
일정DB 로 옮기는 일은 school-todo-kakao 의 sync 가 한다(schooltodo/inbox.py).

schooltodo·gspread 는 쓸 때 불러온다 — 없어도 수업 비서의 다른 기능은 그대로 켜진다.
"""
from __future__ import annotations

import contextlib
import importlib
import os
import pathlib
import sys
import threading
import time
from collections import Counter
from datetime import date, timedelta

SKILL_DIR = pathlib.Path(__file__).resolve().parent
TODO_DIR = SKILL_DIR.parent / "school-todo-kakao"
TODO_SKILL = "school-todo-kakao"
# school-todo-kakao 설정 가운데 시트를 여는 데 필요한 것만 가져온다(다른 비밀값은 건드리지 않는다).
SHEET_KEYS = ("GOOGLE_SERVICE_ACCOUNT_JSON", "GOOGLE_SERVICE_ACCOUNT_FILE", "DB_SHEET_ID", "DB_TAB", "INBOX_TAB")
CACHE_SECONDS = 600
FAIL_SECONDS = 60  # 실패한 결과는 짧게만 기억한다(설정을 고치면 곧 다시 읽게)
WAIT_SECONDS = 15  # 화면 요청이 시트 응답을 기다리는 가장 긴 시간
GIVE_UP_SECONDS = 120  # 이만큼 응답 없는 읽기는 버리고 새로 읽는다
SLOW_REASON = "일정 시트가 아직 응답하지 않아요. 잠시 뒤 ↻ 새로 읽기를 눌러 주세요."
MAX_TEXT = 200


class PanelError(Exception):
    """화면에 그대로 보여 줘도 되는 쉬운 말 이유."""


def _todo(*names: str):
    """school-todo-kakao 의 schooltodo 모듈들. 읽기에는 필요 없는 것까지 부르지 않는다(inbox 는 requests 가 필요)."""
    if str(TODO_DIR) not in sys.path:
        sys.path.append(str(TODO_DIR))  # 뒤에 붙인다: 같은 이름의 수업 비서 파일을 가리지 않게
    try:
        return [importlib.import_module(f"schooltodo.{name}") for name in names]
    except ImportError as exc:
        raise PanelError(f"school-todo-kakao 스킬을 불러오지 못했어요(없는 것: {exc.name or '확인 필요'}). "
                         "파이썬 3.11 이상과 requests 설치를 확인해 주세요.") from exc


# ──────────────────────────── 정리(순수 함수) ────────────────────────────

def empty_agenda(today: date, reason: str = "") -> dict:
    return {"date": today.isoformat(), "today": [], "week": [], "week_label": "이번 주 남은 일정", "tasks": [],
            "due_today": 0, "summary": "", "reason": reason}


def build(rows: list[dict], today: date) -> dict:
    """일정DB 행 → 오늘 행사, 이번 주 남은 일정, 할 일(지난 것·오늘·30일 안)."""
    classify, dates, message = _todo("classify", "dates", "message")
    items = [i for i in message.parse_items(rows, today) if not i.status and i.target != classify.OTHER]
    order = message.CATEGORY_ORDER
    events = [i for i in items if i.category != message.TASK_CATEGORY]

    def entry(i) -> dict:
        return {"date": i.date.isoformat(), "when": dates.fmt_md_wd(i.date), "category": i.category, "text": i.text}

    todays = sorted((i for i in events if i.date == today), key=lambda i: order.get(i.category, 2))
    # 아침 메시지와 같은 끝 날짜: 다음 근무일이 속한 주의 일요일(금요일에는 주말과 다음 주).
    nxt = dates.next_workday(today)
    week_end = nxt - timedelta(days=nxt.weekday()) + timedelta(days=6)
    week = sorted((i for i in events if today < i.date <= week_end),
                  key=lambda i: (i.date, order.get(i.category, 2)))
    limit = today + timedelta(days=message.UPCOMING_DAYS)
    todo = sorted((i for i in items if i.category == message.TASK_CATEGORY and i.date <= limit),
                  key=lambda i: i.date)
    tasks = []
    for i in todo:
        left = (i.date - today).days
        tasks.append(dict(entry(i), left=left, dday=dday(left)))
    result = empty_agenda(today)
    result.update(
        today=[entry(i) for i in todays],
        week=[entry(i) for i in week],
        week_label="이번 주 남은 일정" if nxt.isocalendar()[:2] == today.isocalendar()[:2] else "주말·다음 주 일정",
        tasks=tasks,
        due_today=sum(1 for t in tasks if t["left"] <= 0),
    )
    result["summary"] = summary_line(result["today"], tasks, order)
    return result


def dday(left: int) -> str:
    if left == 0:
        return "D-day"
    return f"D-{left}" if left > 0 else f"D+{-left}"


def summary_line(todays: list[dict], tasks: list[dict], order: dict) -> str:
    """위쪽 한 줄. 화면을 여럿이 볼 수 있어 내용은 넣지 않고 개수만 쓴다."""
    parts = []
    counts = Counter(e["category"] for e in todays)
    if counts:
        names = sorted(counts, key=lambda c: order.get(c, 2))
        parts.append("오늘 " + " · ".join(f"{c} {counts[c]}" for c in names))
    else:
        parts.append("오늘 행사 없음")
    late = sum(1 for t in tasks if t["left"] < 0)
    if late:
        parts.append(f"지난 할 일 {late}")
    coming = [t for t in tasks if t["left"] >= 0]
    if coming:
        first = coming[0]["left"]
        parts.append(f"할 일 {dday(first)} {sum(1 for t in coming if t['left'] == first)}건")
    return " · ".join(parts)


def quick_line(text, today: date) -> tuple[str, dict]:
    """빠른 할 일 한 줄 검사 → (시트에 넣을 글, 어떻게 읽히는지). 시트 규칙은 schooltodo/inbox.py."""
    dates, inbox = _todo("dates", "inbox")
    line = " ".join(str(text or "").split())
    if not line:
        raise PanelError("할 일을 적어 주세요.")
    if len(line) > MAX_TEXT:
        raise PanelError(f"한 줄은 {MAX_TEXT}자까지예요.")
    parsed = inbox.parse_line(line, today)
    if parsed is None:
        raise PanelError("날짜 뒤에 할 일 내용을 적어 주세요.")
    if parsed.date < today:
        raise PanelError(f"{dates.fmt_md_wd(parsed.date)}은 지난 날짜라 시트에서 반영되지 않아요. 날짜를 고쳐 주세요.")
    return line, {"date": parsed.date.isoformat(), "when": dates.fmt_md_wd(parsed.date),
                  "category": parsed.category, "text": parsed.text}


# ──────────────────────────── 시트 ────────────────────────────

_settings_lock = threading.Lock()  # 환경변수를 바꾸는 순간에만 잡는다(시트를 여는 동안은 잡지 않는다)
_settings_added = {}  # (id(environ), 키) → [쓰는 블록 수, 넣기 전 값]


@contextlib.contextmanager
def sheet_settings(values: dict, environ=os.environ, env_dir: pathlib.Path | None = None):
    """중앙 .env 의 시트 설정만, 이 블록 안에서만 환경변수에 둔다. 이미 있는 환경변수가 우선.

    schooltodo 는 설정을 환경변수에서 읽는다. 서비스 계정 키가 남으면 수업 비서가 나중에 띄우는 다른 프로그램이
    물려받으므로, 마지막 블록이 끝나면 여기서 넣은 것은 지운다. 여는 중에 시트가 응답하지 않아도
    다른 블록은 기다리지 않는다.
    """
    if env_dir is not None:  # 키 파일을 상대 경로로 적은 경우: 카톡 알림처럼 .env 폴더에서 찾는다
        (envload,) = _todo("envload")
        if env_dir not in envload.ENV_DIRS:
            envload.ENV_DIRS.append(env_dir)
    mine = []
    with _settings_lock:
        for key in SHEET_KEYS:
            value = (values.get(key) or "").strip()
            slot = (id(environ), key)
            if slot in _settings_added:
                _settings_added[slot][0] += 1
            elif value and not environ.get(key):
                _settings_added[slot] = [1, environ.get(key)]  # 없었으면 None, 빈 값이었으면 ""
            else:
                continue
            mine.append(slot)
            if value:
                environ[key] = value
    try:
        yield
    finally:
        with _settings_lock:
            for slot in mine:
                entry = _settings_added[slot]
                entry[0] -= 1
                if entry[0]:
                    continue
                del _settings_added[slot]
                if entry[1] is None:
                    environ.pop(slot[1], None)
                else:
                    environ[slot[1]] = entry[1]


class _Opened:
    """연 시트. '빠른입력' 탭 이름(INBOX_TAB)도 설정에서 읽으므로 inbox() 때 한 번 더 설정을 둔다."""

    def __init__(self, sheets, values: dict):
        self._sheets, self._values = sheets, values

    def rows(self) -> list[dict]:
        return self._sheets.rows()

    def inbox(self):
        with sheet_settings(self._values):
            return self._sheets.inbox()


def open_db():
    (db,) = _todo("db")
    from skill_env import central_env_path, env_values  # 수업 비서 서버가 _shared 를 이미 경로에 넣었다

    central = central_env_path()
    values = env_values(TODO_SKILL)
    with sheet_settings(values, env_dir=central.parent if central else None):
        sheets = db.SheetsDb.from_env()
    return _Opened(sheets, values)


def explain(exc: BaseException) -> str:
    """실패 이유를 한 줄로. 알 수 없는 오류는 시트 주소 같은 것이 섞일 수 있어 종류만 알린다."""
    if isinstance(exc, PanelError):
        return str(exc)
    if isinstance(exc, ImportError):
        return "일정 시트를 읽으려면 gspread 가 필요해요: python -m pip install gspread"
    if type(exc) in (SystemExit, ValueError):  # schooltodo 가 쉬운 말로 알려 주는 두 가지(하위 오류는 제외)
        first = (str(exc).strip().splitlines() or [""])[0]  # 둘째 줄부터는 계정 주소 등이 있어 뺀다
        if first:
            return first
    return f"일정 시트에 연결하지 못했어요({type(exc).__name__}). 인터넷과 school-todo-kakao 설정을 확인해 주세요."


class _Read:
    """시트 읽기 한 번. 응답이 없어도 화면 요청이 붙잡히지 않게 따로 도는 일로 둔다."""

    def __init__(self, started: float):
        self.started = started
        self.done = threading.Event()
        self.result = ([], SLOW_REASON)


class Panel:
    def __init__(self, opener=open_db, clock=time.monotonic, wait=WAIT_SECONDS):
        self._open = opener
        self._clock = clock
        self._wait = wait
        self._lock = threading.Lock()  # 아래 두 값을 바꿀 때만 잠깐 잡는다
        self._cache = None  # (읽은 시각, 행 목록, 이유)
        self._reading = None

    def _read(self, job: _Read) -> None:
        try:
            result = self._open().rows(), ""
        except (Exception, SystemExit) as exc:  # schooltodo 는 설정 오류를 SystemExit 로 알린다
            result = [], explain(exc)
            print(f"[agenda] 일정 시트 읽기 실패: {type(exc).__name__}", file=sys.stderr)
        with self._lock:
            job.result = result
            if self._reading is job:  # 버린 옛 읽기가 늦게 끝나도 새 결과를 덮지 않는다
                self._cache = (self._clock(), *result)
                self._reading = None
        job.done.set()

    def _rows(self, refresh: bool):
        with self._lock:
            now = self._clock()
            if self._cache and not refresh:
                read_at, rows, reason = self._cache
                if now - read_at < (FAIL_SECONDS if reason else CACHE_SECONDS):
                    return rows, reason
            job = self._reading
            if job is None or now - job.started >= GIVE_UP_SECONDS:
                job = self._reading = _Read(now)
                threading.Thread(target=self._read, args=(job,), daemon=True).start()
        job.done.wait(self._wait)
        return job.result

    def agenda(self, today: date, refresh: bool = False) -> dict:
        rows, reason = self._rows(refresh)
        if reason:
            return empty_agenda(today, reason)
        try:
            return build(rows, today)
        except PanelError as exc:
            return empty_agenda(today, str(exc))

    def quick(self, body: dict, today: date) -> dict:
        """confirm 이 true 가 아니면 읽히는 모양만 돌려주고 아무것도 쓰지 않는다."""
        try:
            line, parsed = quick_line(body.get("text"), today)
            if body.get("confirm") is not True:
                return {"status": "success", "written": False, "line": line, "parsed": parsed}
            inbox = self._open().inbox()
            if inbox is None:
                raise PanelError("일정 시트에 '빠른입력' 탭이 없어요. 시트에 그 이름의 탭을 만들어 주세요.")
            inbox.append(line)   # school-todo-kakao 의 공개 함수(글자 그대로 RAW 로 덧붙임, ISSUE-008)
        except (Exception, SystemExit) as exc:
            return {"status": "error", "written": False, "message": explain(exc)}
        return {"status": "success", "written": True, "line": line, "parsed": parsed,
                "message": "'빠른입력'에 적었어요. 다음 자동 정리(sync) 뒤에 일정에 나타나요."}


PANEL = Panel()
