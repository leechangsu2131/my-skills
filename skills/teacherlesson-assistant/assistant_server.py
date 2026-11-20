"""수업 비서(teacherlesson-assistant) 로컬 서버.

파이썬 기본 기능만 쓴다(추가 설치 없음). 이 PC 안(127.0.0.1)에서만 열린다.

    python assistant_server.py          # 서버만 켜기
    python assistant_server.py --open   # 서버 + 왼쪽 수업 비서 창 열기

하는 일
- 진도 서버(teacherlesson-schedule, 기본 5000번)에서 그날 수업을 받아 교시별로 보여 준다.
- 수업 흐름(flows/*.json), 출판사별 주의점, 지난 메모를 왼쪽 창에 붙여 준다.
- 출판사 사이트를 오른쪽 창으로 연다. 아이디·비밀번호는 중앙 .env 에서 읽어 클립보드로만 넘긴다.
- 녹음 조각과 수업 기록(메모·알림장 초안)을 내 문서\\my-skills-data\\teacherlesson-assistant 에 저장한다.
- 진도 완료/늘리기/미루기는 진도 서버 API 로 그대로 넘긴다.
"""
from __future__ import annotations

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
DEFAULT_AI_SITES = [
    {"name": "Claude", "url": "https://claude.ai/new"},
    {"name": "Gemini", "url": "https://gemini.google.com/app"},
    {"name": "ChatGPT", "url": "https://chatgpt.com/"},
    {"name": "Grok", "url": "https://grok.com/"},
    {"name": "NotebookLM", "url": "https://notebooklm.google.com/"},
]
PROGRESS_ACTIONS = {"done", "extend", "push", "catch-up"}
_lock = threading.Lock()


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


# ──────────────────────────── 수업 목록 ────────────────────────────

def fetch_schedule(cfg: dict, day: date) -> tuple[list[dict], str]:
    """진도 서버에서 그날 수업을 가져온다. 실패하면 설정의 기본 시간표를 쓴다."""
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
    """오늘 이후 이 과목의 차시 목록(진도 서버 agenda). '여기부터 다시 잡기'에서 고를 후보."""
    cfg = load_config()
    base = cfg.get("schedule_api", "http://127.0.0.1:5000").rstrip("/")
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


def find_flow(lesson: dict) -> dict | None:
    candidates = []
    if lesson.get("record_key"):
        candidates.append(FLOWS / f"{safe_name(lesson['record_key'])}.json")
    if lesson.get("title"):
        candidates.append(FLOWS / f"{safe_name(lesson['subject'])}__{safe_name(lesson['title'])}.json")
    for path in candidates:
        if path.is_file():
            return read_json(path, None)
    return None


def find_unit(lesson: dict) -> dict | None:
    """단원 개관 요약: units/<과목>__<대단원>.json (Claude 가 지도서 단원 개관 쪽에서 만든다)."""
    if not lesson.get("unit"):
        return None
    path = UNITS / f"{safe_name(lesson['subject'])}__{safe_name(lesson['unit'])}.json"
    return read_json(path, None) if path.is_file() else None


def recent_memos(subject: str, limit: int = 6) -> list[dict]:
    """같은 과목의 지난 수업에서 남긴 '고칠점'·'좋았음' 메모 (최근 것부터)."""
    found = []
    for path in sorted(SESSIONS.glob(f"*/*_{safe_name(subject)}.json"), reverse=True):
        rec = read_json(path, {})
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
        lesson["flow"] = find_flow(lesson)
        lesson["unit_overview"] = find_unit(lesson)
        key = f"{lesson['publisher']}|{lesson['subject']}"
        lesson["cautions"] = cautions.get(key, []) + cautions.get(f"{lesson['publisher']}|*", [])
        lesson["recent_memos"] = recent_memos(lesson["subject"])
        lesson["saved"] = read_json(session_path(day.isoformat(), lesson["period"], lesson["subject"]), None)
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


def session_path(day: str, period, subject: str) -> pathlib.Path:
    try:
        period_no = int(period or 0)
    except (TypeError, ValueError):
        period_no = 0
    path = SESSIONS / day / f"{period_no}교시_{safe_name(subject)}.json"
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


def screen_size() -> tuple[int, int]:
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
        return ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1)
    except Exception:
        return 1920, 1080


def ai_sites(cfg: dict) -> list[dict]:
    return cfg.get("ai_sites") or DEFAULT_AI_SITES


def allowed_urls(cfg: dict) -> set[str]:
    urls = {s.get("site", "") for s in cfg.get("subjects", {}).values()}
    urls |= {l.get("url", "") for l in cfg.get("links", [])}
    urls.add(cfg.get("hiclass_url", ""))
    urls |= {s.get("url", "") for s in ai_sites(cfg)}
    return {u for u in urls if u}


def check_site_url(url: str, cfg: dict) -> str:
    """오른쪽 창으로 열 주소는 설정(과목 사이트·바로가기·하이클래스)에 있는 http(s) 주소만 허용."""
    parsed = urllib.parse.urlparse(str(url))
    if parsed.scheme not in ("http", "https") or url not in allowed_urls(cfg):
        raise ValueError("설정에 없는 주소는 열지 않아요.")
    return url


def open_window(url: str, side: str, cfg: dict) -> str:
    """수업 전용 Chrome 프로필로 창을 연다. side=left(수업 비서) / right(수업 사이트)."""
    exe = chrome_path()
    if not exe:
        import webbrowser
        webbrowser.open(url)
        return "Chrome 을 찾지 못해 기본 브라우저로 열었어요."
    w, h = screen_size()
    left_w = int(w * float(cfg.get("left_ratio", 0.32)))
    x, width = (0, left_w) if side == "left" else (left_w, w - left_w)
    # 음악·사회 도우미와 같은 프로필·포트를 써서 구글 로그인을 한 번만 하면 되게 한다.
    profile = cfg.get("chrome_profile") or str(
        pathlib.Path(os.environ.get("LOCALAPPDATA", str(pathlib.Path.home()))) / "MusicClassHelper" / "chrome_profile")
    args = [exe, f"--user-data-dir={os.path.expandvars(profile)}", f"--window-position={x},0", f"--window-size={width},{h - 40}"]
    if cfg.get("debug_port"):
        args.append(f"--remote-debugging-port={int(cfg['debug_port'])}")
    args += [f"--app={url}"] if side == "left" else ["--new-window", "--", url]
    subprocess.Popen(args, close_fds=True)
    return "창을 열었어요."


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
        if url.path in ("/", "/index.html"):
            return self._send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/state":
            try:
                day = date.fromisoformat(q.get("date", [date.today().isoformat()])[0])
            except ValueError:
                return self._json({"status": "error", "message": "날짜 형식이 잘못됐어요."}, 400)
            return self._json(state(day))
        if url.path == "/api/upcoming":
            try:
                return self._json({"status": "success", "items": upcoming(q.get("subject", [""])[0])})
            except (urllib.error.URLError, OSError, ValueError):
                return self._json({"status": "error", "message": "진도 서버(teacherlesson-schedule)가 꺼져 있어요."}, 502)
        if url.path.startswith("/api/unit-pdf/"):
            name = urllib.parse.unquote(url.path.rsplit("/", 1)[-1])
            path = UNITS / name
            if not name.endswith(".pdf") or "/" in name or "\\" in name or not path.is_file()                     or not path.resolve().is_relative_to(UNITS.resolve()):
                return self._json({"status": "error", "message": "단원 개관 PDF가 없어요."}, 404)
            return self._send(200, path.read_bytes(), "application/pdf")
        if url.path.startswith("/api/pdf/"):
            base = load_config().get("schedule_api", "http://127.0.0.1:5000").rstrip("/")
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
                return self._json(save_audio(q, raw))
            body = json.loads(raw.decode("utf-8") or "{}")
            if url.path == "/api/open-site":
                cfg = load_config()
                return self._json({"status": "success", "message": open_window(check_site_url(body.get("url", ""), cfg), "right", cfg)})
            if url.path == "/api/copy-secret":
                return self._json({"status": "success", "message": copy_secret(body.get("subject", ""), body.get("field", ""))})
            if url.path == "/api/ask-prepare":
                return self._json(ask_prepare(body))
            if url.path == "/api/session":
                return self._json(save_session(body))
            if url.path == "/api/caution":
                return self._json(add_caution(body))
            if url.path.startswith("/api/progress/"):
                return self._json(progress(url.path.rsplit("/", 1)[-1], body))
        except (ValueError, KeyError, subprocess.CalledProcessError) as exc:
            return self._json({"status": "error", "message": str(exc)}, 400)
        return self._json({"status": "error", "message": "없는 주소"}, 404)


def ask_prepare(body: dict) -> dict:
    """웹 AI(Claude·Gemini·ChatGPT 등)에 물어볼 준비: 단원 개관 PDF + 차시 지도서 PDF 를 한 폴더에 모으고 질문 문장을 만든다.
    학생 메모·녹음은 넣지 않는다(개인정보)."""
    cfg = load_config()
    day = body.get("date", "")
    date.fromisoformat(day)
    subject, unit = str(body.get("subject", "")), str(body.get("unit", ""))
    lesson, title = str(body.get("lesson", "")), str(body.get("title", ""))
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
        base = cfg.get("schedule_api", "http://127.0.0.1:5000").rstrip("/")
        try:
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
    publisher = cfg.get("subjects", {}).get(subject, {}).get("publisher", "")
    notes = read_json(CAUTIONS_PATH, {})
    cautions = [c["text"] for c in notes.get(f"{publisher}|{subject}", []) + notes.get(f"{publisher}|*", [])]
    lines = [f"초등학교 3학년 {subject} 수업을 준비하고 있습니다.",
             f"- 단원: {unit}", f"- 이번 차시: {lesson}차시 「{title}」"]
    if publisher:
        lines.append(f"- 교과서·지도서 출판사: {publisher}")
    if files:
        lines.append("첨부: " + ", ".join(files))
    lines += ["", "첨부한 지도서를 바탕으로 아래를 짧고 실용적으로 알려 주세요.",
              "1. 40분 수업 흐름(도입–전개–정리)과 시간 배분",
              "2. 핵심 발문 3~5개와 예상되는 학생 답",
              "3. 학생들이 어려워할 부분과 도와주는 방법",
              "4. 지도서 활동을 더 쉽게·재미있게 바꿀 아이디어 (준비물이 적은 것)",
              "5. 수업 끝에 이해를 확인할 질문 1~2개"]
    if cautions:
        lines += ["", "참고 – 이 출판사 지도서를 쓰며 느낀 점:"] + [f"- {c}" for c in cautions[:5]]
    prompt = "\n".join(lines)
    (folder / "질문.txt").write_text(prompt, encoding="utf-8")
    subprocess.Popen(["explorer", str(folder)])
    return {"status": "success", "prompt": prompt, "files": files, "missing": missing,
            "message": "파일 폴더를 열고 질문을 복사했어요. 파일을 대화창에 끌어다 놓고 Ctrl+V 하세요."
                       + (f" (없음: {', '.join(missing)})" if missing else "")}


def save_audio(q: dict, raw: bytes) -> dict:
    day = q.get("date", [""])[0]
    date.fromisoformat(day)  # 날짜 형식 검사
    name = safe_name(q.get("name", ["rec"])[0])
    seq = int(q.get("seq", ["0"])[0])
    ext = "mp4" if q.get("ext", ["webm"])[0] == "mp4" else "webm"
    path = SESSIONS / day / f"{name}.{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        if seq == 0 and path.exists():  # 앞 녹음을 덮어쓰지 않는다
            n = 2
            while (SESSIONS / day / f"{name}_{n}.{ext}").exists():
                n += 1
            raise ValueError(f"같은 이름 녹음이 있어요. 이름: {name}_{n}")
        with open(path, "wb" if seq == 0 else "ab") as fh:
            fh.write(raw)
    return {"status": "success", "bytes": path.stat().st_size, "file": path.name}


def save_session(body: dict) -> dict:
    day = body.get("date", "")
    date.fromisoformat(day)
    path = session_path(day, body.get("period"), body.get("subject", ""))
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
