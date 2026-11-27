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
MAX_TEXT = 200


class PanelError(Exception):
    """화면에 그대로 보여 줘도 되는 쉬운 말 이유."""


def _todo_modules():
    if str(TODO_DIR) not in sys.path:
        sys.path.append(str(TODO_DIR))  # 뒤에 붙인다: 같은 이름의 수업 비서 파일을 가리지 않게
    try:
        from schooltodo import classify, dates, db, inbox, message
    except ImportError as exc:
        raise PanelError("school-todo-kakao 스킬을 불러오지 못했어요(파이썬 3.11 이상이 필요해요).") from exc
    return classify, dates, db, inbox, message


# ──────────────────────────── 정리(순수 함수) ────────────────────────────

def empty_agenda(today: date, reason: str = "") -> dict:
    return {"date": today.isoformat(), "today": [], "week": [], "week_label": "이번 주 남은 일정", "tasks": [],
            "due_today": 0, "summary": "", "reason": reason}


def build(rows: list[dict], today: date) -> dict:
    """일정DB 행 → 오늘 행사, 이번 주 남은 일정, 할 일(지난 것·오늘·30일 안)."""
    classify, dates, _db, _inbox, message = _todo_modules()
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
    _classify, dates, _db, inbox, _message = _todo_modules()
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

def apply_settings(values: dict, environ=os.environ, env_dir: pathlib.Path | None = None) -> None:
    """중앙 .env 값에서 시트 설정만 환경변수로 옮긴다. 이미 있는 환경변수가 우선."""
    for key in SHEET_KEYS:
        value = (values.get(key) or "").strip()
        if value and not environ.get(key):
            environ[key] = value
    if env_dir is not None:  # 키 파일을 상대 경로로 적은 경우: 카톡 알림처럼 .env 폴더에서 찾는다
        from schooltodo import envload

        if env_dir not in envload.ENV_DIRS:
            envload.ENV_DIRS.append(env_dir)


def open_db():
    _classify, _dates, db, _inbox, _message = _todo_modules()
    from skill_env import central_env_path, env_values  # 수업 비서 서버가 _shared 를 이미 경로에 넣었다

    central = central_env_path()
    apply_settings(env_values(TODO_SKILL), env_dir=central.parent if central else None)
    return db.SheetsDb.from_env()


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


class Panel:
    def __init__(self, opener=open_db, clock=time.monotonic):
        self._open = opener
        self._clock = clock
        self._lock = threading.Lock()
        self._cache = None  # (읽은 시각, 행 목록 | None, 이유)

    def _rows(self, refresh: bool):
        with self._lock:
            now = self._clock()
            if self._cache and not refresh:
                read_at, rows, reason = self._cache
                if now - read_at < (FAIL_SECONDS if reason else CACHE_SECONDS):
                    return rows, reason
            try:
                rows, reason = self._open().rows(), ""
            except (Exception, SystemExit) as exc:  # schooltodo 는 설정 오류를 SystemExit 로 알린다
                rows, reason = [], explain(exc)
                print(f"[agenda] 일정 시트 읽기 실패: {type(exc).__name__}", file=sys.stderr)
            self._cache = (self._clock(), rows, reason)
            return rows, reason

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
            # RAW: '=' 로 시작하는 글이 수식이 되거나 날짜가 시트 마음대로 바뀌지 않게 글자 그대로 넣는다.
            inbox._ws.append_row([line], value_input_option="RAW", table_range="A1")
        except (Exception, SystemExit) as exc:
            return {"status": "error", "written": False, "message": explain(exc)}
        return {"status": "success", "written": True, "line": line, "parsed": parsed,
                "message": "'빠른입력'에 적었어요. 다음 자동 정리(sync) 뒤에 일정에 나타나요."}


PANEL = Panel()
