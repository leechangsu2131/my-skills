"""학교 PC 점검 — 수업 비서를 쓰기 전에 이 PC 에 빠진 것이 없는지 한 번에 확인한다.

    python check_setup.py          (또는 점검_PC.bat 더블클릭)

항목마다 ✅(괜찮음) / ⚠(일부 기능만 안 됨·확인 필요) / ❌(꼭 고쳐야 함) 와 고치는 방법 한 줄을 보여 준다.
- 아무것도 설치·생성·수정하지 않는다(읽기만 한다). 서버·크롬도 켜지 않는다.
- 중앙 .env 의 값은 절대 출력하지 않는다. 키 "이름"이 있는지만 본다.
- 하나라도 ❌ 이면 종료 코드 1, 아니면 0.
"""
from __future__ import annotations

import http.client
import importlib.util
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

SKILL_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(next(p / "_shared" for p in SKILL_DIR.parents if (p / "_shared" / "skill_env.py").is_file())))
import skill_env  # noqa: E402  (불러오기만으로는 폴더를 만들지 않는다)

SKILL = "teacherlesson-assistant"
OK, WARN, FAIL = "ok", "warn", "fail"
MARK = {OK: "✅", WARN: "⚠", FAIL: "❌"}

MIN_PYTHON = (3, 10)
RECOMMENDED_PYTHON = (3, 13)          # 실행_수업비서.bat: py -3.13 이 되면 그것, 아니면 python 하나로 전부 실행
DEFAULT_PORT = 5180
DEFAULT_DEBUG_PORT = 9233
ASSISTANT_SERVER_PREFIX = "LessonAssistant"   # assistant_server.py 의 Handler.server_version 과 같게 둔다
PY_LAUNCHER = ["py", "-3.13"]                 # 실행_수업비서.bat 이 build_units.py 를 돌리는 명령
PY_PLAIN = ["python"]                         # 실행_수업비서.bat 이 서버·prepare_lessons.py 를 돌리는 명령
# pip 이름(소문자) → import 이름. requirements.txt 에 없는 이름은 import 이름을 그대로 쓴다.
IMPORT_NAMES = {"pymupdf": "fitz", "selenium": "selenium"}
EXTRA_PACKAGES = ("selenium", "PyMuPDF")       # requirements.txt 밖에서 더 필요한 것
SUPABASE_URL_KEYS = ("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_SECRET_KEY = "SUPABASE_SERVICE_ROLE_KEY"
GEMINI_KEYS = ("UTIL_NOTEBOOKLM__GEMINI_API_KEY", "GEMINI_API_KEY", "GEMINI_API_KEY_FROM_VAULT_NOTE")
DATA_SUBFOLDERS = ("flows", "units", "notebooklm")
_PERCENT_VAR = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")


@dataclass
class Result:
    status: str
    title: str
    detail: str = ""
    fix: str = ""


# ──────────────────────────── 작은 도우미 ────────────────────────────

def expand_percent(value: str, env: dict) -> str:
    """%VAR% 를 env 값으로 펼친다(없는 변수는 그대로 둔다)."""
    return _PERCENT_VAR.sub(lambda m: env.get(m.group(1), m.group(0)), value)


def port_is_open(port: int, host: str = "127.0.0.1", timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def identify_assistant(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> str | None:
    """포트에 실제로 HTTP 로 물어 서버가 밝힌 이름(Server 머리글)을 돌려준다.

    HTTP 로 답하지 않거나 연결이 안 되면 None. 본문은 읽지 않고, 컴퓨터에 설정된 프록시는 쓰지 않는다.
    """
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://{host}:{port}/", timeout=timeout) as resp:
            return resp.headers.get("Server", "") or ""
    except urllib.error.HTTPError as exc:          # 403·404 도 '답은 한' 것 — 머리글은 읽을 수 있다
        try:
            return exc.headers.get("Server", "") or ""
        finally:
            exc.close()
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
        return None


def read_python_version(cmd: list[str]) -> tuple[int, int, int] | None:
    """cmd(예: ["py", "-3.13"], ["python"]) 로 Python 을 돌려 버전을 읽는다. 못 돌리면 None."""
    try:
        out = subprocess.run([*cmd, "-c", "import sys;print('.'.join(map(str,sys.version_info[:3])))"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", (out.stdout or "").strip())     # 윈도우 스토어 안내 같은 엉뚱한 출력은 버린다
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def parse_port(cfg: dict, key: str, default: int, falsy_is_default: bool = False) -> tuple[int | None, Result | None]:
    """config 의 포트 값을 서버와 같은 방식(int())으로 읽는다. (쓸 포트, 문제 결과)를 돌려준다.

    키가 없으면 기본값. 값이 숫자로 읽히지 않거나 1~65535 밖이면 (None, ❌ 결과) — 서버가 그 값으로는 못 켜지기 때문.
    falsy_is_default=True 면 null·0·"" 도 기본값으로 본다(서버가 그런 값을 건너뛰는 debug_port 용).
    """
    if key not in cfg or (falsy_is_default and not cfg[key]):
        return default, None
    raw = cfg[key]
    try:
        if isinstance(raw, bool):
            raise ValueError("bool")
        port = int(raw)
    except (TypeError, ValueError, OverflowError):
        port = None
    if port is None or not 1 <= port <= 65535:
        shown = repr(raw)[:30]
        return None, Result(FAIL, f"설정 {key}", f"쓸 수 없는 값이에요: {shown}",
                            f'config.json 의 "{key}" 를 {default} 처럼 1~65535 사이 숫자로 고치세요 (그 전에는 수업 비서가 켜지지 않아요)')
    return port, None


def read_node_version(node_path: str) -> str:
    try:
        out = subprocess.run([node_path, "--version"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_requirement_names(text: str) -> list[str]:
    names: list[str] = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", line)
        if m:
            names.append(m.group(0))
    return names


def import_name_for(pip_name: str) -> str:
    key = pip_name.lower().replace("_", "-")
    return IMPORT_NAMES.get(key, key.replace("-", "_"))


def load_config(data_path: pathlib.Path, example_path: pathlib.Path) -> tuple[dict, Result]:
    """데이터 폴더의 config.json (없으면 config.example.json 기본값)을 읽는다. 쓰지는 않는다."""
    real = data_path / "config.json"
    not_object = Result(FAIL, "설정 파일 config.json", "{ } 모양이 아니에요",
                        "config.json 은 { 로 시작해 } 로 끝나야 해요 — 고치거나 지우고 서버를 한 번 켜면 예시로 다시 만들어져요")
    try:
        if real.is_file():
            cfg = json.loads(real.read_text(encoding="utf-8-sig"))
            if not isinstance(cfg, dict):          # [] · 5 · "글" 처럼 JSON 이긴 한데 객체가 아닐 때
                return {}, not_object
            return cfg, Result(OK, "설정 파일 config.json", "읽음")
        cfg = json.loads(example_path.read_text(encoding="utf-8-sig")) if example_path.is_file() else {}
        if not isinstance(cfg, dict):
            return {}, not_object
    except (OSError, ValueError) as exc:
        return {}, Result(FAIL, "설정 파일 config.json", f"읽지 못했어요 ({type(exc).__name__})",
                          "config.json 의 쉼표·따옴표를 확인하거나 지우고 서버를 한 번 켜면 예시로 다시 만들어져요")
    return cfg, Result(WARN, "설정 파일 config.json", "아직 없음 — 예시 설정으로 점검했어요",
                       "실행_수업비서.bat 을 처음 켜면 config.example.json 이 복사돼 만들어져요")


# ──────────────────────────── 점검 항목 ────────────────────────────

def check_python(version=None, executable: str | None = None) -> Result:
    v = tuple(version or sys.version_info[:3])
    text = ".".join(str(n) for n in v[:3])
    if v[:2] < MIN_PYTHON:
        return Result(FAIL, "Python 버전", f"{text} — 너무 낮아요",
                      "https://www.python.org/downloads/ 에서 Python 3.13 을 설치하세요 (Add to PATH 체크)")
    if v[:2] < RECOMMENDED_PYTHON:
        return Result(WARN, "Python 버전", f"{text} (권장 3.13)",
                      "실행_수업비서.bat 은 py -3.13 이 되면 그것으로, 아니면 python 으로 서버·단원 개관·수업 준비를 모두 켜요. "
                      "3.13 을 설치하면 py -3.13 이 먼저 쓰여요. 어느 쪽이 쓰이는지는 바로 아래 'Python 실행기' 항목에서 봐요")
    return Result(OK, "Python 버전", text)


def check_python_launchers(read_version=read_python_version) -> Result:
    """실행_수업비서.bat 이 고르는 Python 하나를 알려 준다(py -3.13 이 되면 그것, 아니면 python).

    bat 는 단원 개관·수업 준비·서버를 모두 같은 실행기로 켜므로 두 명령이 달라도 문제가 아니다.
    고른 쪽이 권장(3.13)보다 낮거나 둘 다 없을 때만 ⚠.
    """
    via_py, via_plain = read_version(PY_LAUNCHER), read_version(PY_PLAIN)
    show = lambda v: ".".join(str(n) for n in v)  # noqa: E731
    title = "Python 실행기 (py -3.13 / python)"
    if via_py is None and via_plain is None:
        return Result(WARN, title, "py -3.13 도 python 도 못 돌렸어요 — 실행_수업비서.bat 이 안 켜져요",
                      "https://www.python.org/downloads/ 에서 Python 3.13 을 설치하세요 (Add to PATH 체크)")
    if via_py is not None:
        return Result(OK, title, f"py -3.13 ({show(via_py)}) 으로 전부 실행돼요")
    if via_plain[:2] < RECOMMENDED_PYTHON:
        return Result(WARN, title, f"py -3.13 은 못 찾았고 python {show(via_plain)} 으로 전부 실행돼요 (권장 3.13)",
                      "https://www.python.org/downloads/ 에서 Python 3.13 을 설치하세요 (py 실행기 포함)")
    return Result(OK, title, f"python ({show(via_plain)}) 으로 전부 실행돼요")


def check_packages(requirements_text: str, find_spec=importlib.util.find_spec,
                   executable: str | None = None) -> list[Result]:
    pip_names = parse_requirement_names(requirements_text)
    for extra in EXTRA_PACKAGES:
        if extra.lower() not in {n.lower() for n in pip_names}:
            pip_names.append(extra)
    py = executable or sys.executable or "python"
    results: list[Result] = []
    for name in pip_names:
        try:
            found = find_spec(import_name_for(name)) is not None
        except (ImportError, ValueError):
            found = False
        title = f"패키지 {name}"
        if found:
            results.append(Result(OK, title, "설치됨"))
            continue
        extra_only = name.lower() == "selenium"          # 차시 자료 바로 열기·지도서 받기에만 필요
        results.append(Result(WARN if extra_only else FAIL, title, "설치 안 됨" + (" (일부 기능만 안 돼요)" if extra_only else ""),
                              f'"{py}" -m pip install {name}'))
    return results


def check_node(which=shutil.which, version_of=read_node_version) -> Result:
    path = which("node")
    if not path:
        return Result(WARN, "Node.js", "없음 — Gemini 자동 수업 준비(🌙)가 안 돼요",
                      "https://nodejs.org 에서 LTS 설치 후 이 창을 닫고 다시 여세요")
    return Result(OK, "Node.js", version_of(path) or "있음")


def check_gemini_cli(which=shutil.which, is_file=lambda p: pathlib.Path(p).is_file()) -> Result:
    shim = which("gemini.cmd") or which("gemini")
    if not shim:
        return Result(WARN, "Gemini CLI", "없음 — 🌙 수업 준비·지도서 찾기가 안 돼요",
                      "npm i -g @google/gemini-cli  (Node.js 가 먼저 있어야 해요)")
    js = pathlib.Path(shim).parent / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"
    if is_file(js):
        return Result(OK, "Gemini CLI", "npm 전역 설치 확인")
    if not str(shim).lower().endswith((".cmd", ".bat")):
        return Result(OK, "Gemini CLI", "gemini 실행 파일 확인")
    return Result(WARN, "Gemini CLI", "gemini.cmd 는 있는데 본체(gemini.js)를 못 찾았어요",
                  "npm i -g @google/gemini-cli  로 다시 설치하세요")


def find_chrome(env: dict, is_file=lambda p: pathlib.Path(p).is_file(), which=shutil.which) -> str | None:
    for base in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        p = pathlib.Path(env.get(base, "")) / "Google/Chrome/Application/chrome.exe"
        if is_file(p):
            return str(p)
    return which("chrome")


def check_chrome_exe(env: dict | None = None, is_file=lambda p: pathlib.Path(p).is_file(), which=shutil.which) -> Result:
    found = find_chrome(os.environ if env is None else env, is_file, which)
    if found:
        return Result(OK, "크롬 실행 파일", "찾음")
    return Result(FAIL, "크롬 실행 파일", "Google Chrome 을 못 찾았어요 — 수업 사이트 창을 못 열어요",
                  "https://www.google.com/chrome 에서 Chrome 을 설치하세요")


def check_chrome_profile(cfg: dict, env: dict | None = None, is_dir=lambda p: pathlib.Path(p).is_dir()) -> Result:
    env = dict(os.environ) if env is None else env
    raw = cfg.get("chrome_profile") or r"%LOCALAPPDATA%\MusicClassHelper\chrome_profile"
    path = expand_percent(str(raw), env)
    if _PERCENT_VAR.search(path):
        return Result(WARN, "크롬 프로필 폴더(chrome_profile)", "config 의 경로에 이 PC 에 없는 %변수%가 있어요",
                      "config.json 의 chrome_profile 을 %LOCALAPPDATA% 로 시작하는 경로로 고치세요")
    if is_dir(path):
        return Result(OK, "크롬 프로필 폴더(chrome_profile)", path)
    return Result(WARN, "크롬 프로필 폴더(chrome_profile)", f"아직 없음: {path}",
                  "수업 사이트 열기를 처음 누르면 만들어져요. 그 창에서 출판사·구글에 한 번 로그인하세요")


def check_central_env(env_path: pathlib.Path | None) -> Result:
    if env_path is None:
        rel = "\\".join((skill_env.ONEDRIVE_FOLDER_NAME, *skill_env.CENTRAL_ENV_RELATIVE.parts))
        return Result(FAIL, "중앙 .env 위치", "못 찾았어요",
                      f"OneDrive 가 로그인·동기화됐는지 확인하세요. 파일 위치는 사용자 폴더의 {rel}")
    return Result(OK, "중앙 .env 위치", str(env_path))


def check_env_keys(names: set[str], gemini_names: set[str], supabase_required: bool = True) -> list[Result]:
    """키 이름이 있는지만 본다. names 는 이미 '값이 비어 있지 않은 이름'만 담은 집합.

    supabase_required=False(진도 저장소 schedule_backend 가 supabase 가 아님)면 슈파베이스 키가 없어도 ❌ 대신 ⚠.
    """
    results: list[Result] = []
    missing_status = FAIL if supabase_required else WARN
    not_needed = "" if supabase_required else " (진도 저장소가 supabase 가 아니라 지금은 꼭 필요하진 않아요)"
    if names & set(SUPABASE_URL_KEYS):
        results.append(Result(OK, "키 이름 SUPABASE_URL", "있음 (" + ", ".join(k for k in SUPABASE_URL_KEYS if k in names) + ")"))
    else:
        results.append(Result(missing_status, "키 이름 SUPABASE_URL", "SUPABASE_URL 도 NEXT_PUBLIC_SUPABASE_URL 도 없어요" + not_needed,
                              "중앙 .env 에 SUPABASE_URL=… 한 줄을 추가하세요(값은 슈파베이스 프로젝트 설정에서)"))
    if SUPABASE_SECRET_KEY in names:
        results.append(Result(OK, f"키 이름 {SUPABASE_SECRET_KEY}", "있음"))
    else:
        results.append(Result(missing_status, f"키 이름 {SUPABASE_SECRET_KEY}", "없어요" + not_needed,
                              f"중앙 .env 에 {SUPABASE_SECRET_KEY}=… 한 줄을 추가하세요(코드·메신저에 붙여넣지 마세요)"))
    have = [k for k in GEMINI_KEYS if k in names or k in gemini_names]
    if have:
        results.append(Result(OK, "키 이름 Gemini 키", "있음 (" + have[0] + ")"))
    else:
        results.append(Result(WARN, "키 이름 Gemini 키", "없음 — 이 PC 의 구글 로그인으로 대신해요",
                              "키를 쓰려면 중앙 .env 에 GEMINI_API_KEY=… 를 추가하세요(로그인으로 되면 없어도 돼요)"))
    return results


def _count_files(path: pathlib.Path) -> int:
    try:
        return sum(1 for p in path.iterdir() if p.is_file())
    except OSError:
        return 0


def check_data_dir(data_path: pathlib.Path) -> list[Result]:
    results: list[Result] = []
    if data_path.is_dir():
        results.append(Result(OK, "데이터 폴더(data_dir)", str(data_path)))
    else:
        results.append(Result(WARN, "데이터 폴더(data_dir)", f"아직 없음: {data_path}",
                              "서버를 처음 켜면 만들어져요. 집 PC 의 같은 폴더를 OneDrive 로 옮겨 오면 흐름·단원 개관도 그대로 써요"))
    for sub in DATA_SUBFOLDERS:
        folder = data_path / sub
        title = f"데이터 하위 폴더 {sub}"
        if folder.is_dir():
            results.append(Result(OK, title, f"파일 {_count_files(folder)}개"))
        else:
            hint = {"flows": "🌙 수업 준비를 누르면 생겨요(또는 집 PC 의 flows 폴더 복사)",
                    "units": "py -3.13 build_units.py 로 생겨요(또는 집 PC 의 units 폴더 복사)",
                    "notebooklm": "py -3.13 notebook_sources.py 로 생겨요(또는 집 PC 의 notebooklm 폴더 복사)"}[sub]
            results.append(Result(WARN, title, "없음", hint))
    return results


def find_onedrive(env: dict, home: pathlib.Path, is_dir=lambda p: pathlib.Path(p).is_dir()) -> pathlib.Path | None:
    candidates = [pathlib.Path(env[v]) for v in ("OneDriveCommercial", "OneDrive") if env.get(v)]
    candidates.append(home / skill_env.ONEDRIVE_FOLDER_NAME)
    return next((c for c in candidates if is_dir(c)), None)


def check_onedrive(env: dict | None = None, home: pathlib.Path | None = None, is_dir=lambda p: pathlib.Path(p).is_dir()) -> Result:
    found = find_onedrive(os.environ if env is None else env, home or pathlib.Path.home(), is_dir)
    if found:
        return Result(OK, "OneDrive 폴더", str(found))
    return Result(WARN, "OneDrive 폴더", "찾지 못했어요 — 중앙 .env 와 공유 데이터를 못 읽을 수 있어요",
                  "작업표시줄 OneDrive 아이콘에서 학교 계정(gyo6.net)으로 로그인하고 동기화를 켜세요")


def check_port(port: int, label: str, closed_note: str, probe=port_is_open) -> Result:
    title = f"{port}번 포트 ({label})"
    if probe(port):
        return Result(OK, title, "열려 있어요(켜져 있음)")
    return Result(WARN, title, "닫혀 있어요", closed_note)


def check_assistant_port(port: int, closed_note: str, probe=None, identify=None) -> Result:
    """수업 비서 포트: 닫혀 있으면 꺼진 것(⚠), 열려 있으면 정말 수업 비서가 답하는지 HTTP 로 물어 확인한다."""
    probe = probe or port_is_open                 # 호출할 때 찾아 쓴다(시험에서 바꿔 끼울 수 있게)
    identify = identify or identify_assistant
    title = f"{port}번 포트 (수업 비서)"
    if not probe(port):
        return Result(WARN, title, "닫혀 있어요", closed_note)
    server = identify(port)
    if server and server.startswith(ASSISTANT_SERVER_PREFIX):
        return Result(OK, title, "수업 비서가 켜져 있어요")
    detail = "열려 있는데 HTTP 로 답하지 않아요 — 수업 비서가 아니에요" if server is None else \
        f"열려 있는데 수업 비서가 아니에요 (서버 이름: {server[:40] or '없음'})"
    return Result(WARN, title, detail,
                  "다른 프로그램이 이 포트를 쓰고 있어요. 그 프로그램을 끄거나, 데이터 폴더의 config.json 에서 port 를 다른 숫자(예: 5181)로 바꾸세요")


def check_guide_folder(root: pathlib.Path, is_dir=lambda p: pathlib.Path(p).is_dir()) -> Result:
    if is_dir(root):
        return Result(OK, "지도서 폴더", "있음 (집 PC 처럼 지도서 PDF 를 바로 쓸 수 있어요)")
    return Result(OK, "지도서 폴더", "없어도 됨 — 지도서 PDF 는 집 PC 에만 두고, 학교 PC 는 만들어 둔 흐름·단원 개관만 써요")


# ──────────────────────────── 모아서 실행 ────────────────────────────

def _present_names(values: dict, environ: dict) -> set[str]:
    return {k for k, v in values.items() if v} | {k for k, v in environ.items() if v}


def run_checks() -> list[Result]:
    env = dict(os.environ)
    results: list[Result] = [check_python(), check_python_launchers()]
    req = SKILL_DIR / "requirements.txt"
    results += check_packages(req.read_text(encoding="utf-8-sig") if req.is_file() else "")
    results += [check_node(), check_gemini_cli(), check_chrome_exe()]

    data_path = skill_env.data_dir(SKILL, create=False)
    cfg, cfg_result = load_config(data_path, SKILL_DIR / "config.example.json")
    results.append(check_chrome_profile(cfg, env))

    results.append(check_central_env(skill_env.central_env_path()))
    try:
        main_values, gemini_values = skill_env.env_values(SKILL), skill_env.env_values("util-notebooklm")
    except Exception:  # noqa: BLE001  .env 를 못 읽어도 나머지 점검은 계속한다
        main_values, gemini_values = {}, {}
    # 서버(assistant_server.py)와 똑같이 판단한다: 값이 없으면 supabase, 그 외 값이면 옛 진도 서버(schedule_api)를 쓴다
    supabase_required = cfg.get("schedule_backend", "supabase") == "supabase"
    results += check_env_keys(_present_names(main_values, env), _present_names(gemini_values, env), supabase_required)

    results.append(cfg_result)
    results += check_data_dir(data_path)
    results.append(check_onedrive(env))

    # 포트 값이 숫자가 아니면 멈추지 않고 ❌ 로 알린다(그 값으로는 서버가 켜지지 않는다). 그 포트는 열어 보지 않는다.
    port, port_problem = parse_port(cfg, "port", DEFAULT_PORT)
    debug_port, debug_problem = parse_port(cfg, "debug_port", DEFAULT_DEBUG_PORT, falsy_is_default=True)
    if port_problem:
        results.append(port_problem)
    else:
        results.append(check_assistant_port(port, "서버가 꺼져 있어요(켜기 전이면 정상). 실행_수업비서.bat 을 실행하세요"))
    if debug_problem:
        results.append(debug_problem)
    else:
        results.append(check_port(debug_port, "수업용 크롬", "수업용 크롬이 안 떠 있어요(정상일 수 있음). 화면의 '수업 사이트 열기'를 누르면 이 포트로 열려요"))
    results.append(check_guide_folder(pathlib.Path(env.get("GUIDE_ROOT") or r"D:\지도서")))
    return results


def render(results: list[Result]) -> str:
    lines = ["── 학교 PC 점검 ─────────────────────────────"]
    for r in results:
        lines.append(f"{MARK[r.status]} {r.title}" + (f" — {r.detail}" if r.detail else ""))
        if r.status != OK and r.fix:
            lines.append(f"     → 고치기: {r.fix}")
    n = {s: sum(1 for r in results if r.status == s) for s in (OK, WARN, FAIL)}
    lines.append("──────────────────────────────────────────────")
    lines.append(f"✅ {n[OK]}  ⚠ {n[WARN]}  ❌ {n[FAIL]}")
    if n[FAIL]:
        lines.append("❌ 가 있으면 수업 비서가 제대로 안 돌아요. 위 '고치기'부터 하세요.")
    elif n[WARN]:
        lines.append("⚠ 는 해당 기능을 쓸 때만 필요해요. 급하지 않으면 넘어가도 돼요.")
    else:
        lines.append("모두 괜찮아요. 실행_수업비서.bat 을 켜세요.")
    return "\n".join(lines)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    results = run_checks()
    print(render(results))
    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
