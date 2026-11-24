"""학교 PC 점검 — 수업 비서를 쓰기 전에 이 PC 에 빠진 것이 없는지 한 번에 확인한다.

    python check_setup.py          (또는 점검_PC.bat 더블클릭)

항목마다 ✅(괜찮음) / ⚠(일부 기능만 안 됨·확인 필요) / ❌(꼭 고쳐야 함) 와 고치는 방법 한 줄을 보여 준다.
- 아무것도 설치·생성·수정하지 않는다(읽기만 한다). 서버·크롬도 켜지 않는다.
- 중앙 .env 의 값은 절대 출력하지 않는다. 키 "이름"이 있는지만 본다.
- 하나라도 ❌ 이면 종료 코드 1, 아니면 0.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass

SKILL_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(next(p / "_shared" for p in SKILL_DIR.parents if (p / "_shared" / "skill_env.py").is_file())))
import skill_env  # noqa: E402  (불러오기만으로는 폴더를 만들지 않는다)

SKILL = "teacherlesson-assistant"
OK, WARN, FAIL = "ok", "warn", "fail"
MARK = {OK: "✅", WARN: "⚠", FAIL: "❌"}

MIN_PYTHON = (3, 10)
RECOMMENDED_PYTHON = (3, 13)          # 수업 비서 bat 가 py -3.13 으로 돌린다
DEFAULT_PORT = 5180
DEFAULT_DEBUG_PORT = 9233
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
    try:
        if real.is_file():
            return json.loads(real.read_text(encoding="utf-8-sig")), Result(OK, "설정 파일 config.json", "읽음")
        cfg = json.loads(example_path.read_text(encoding="utf-8-sig")) if example_path.is_file() else {}
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
                      "실행_수업비서.bat 은 py -3.13 을 먼저 찾아요. 3.13 을 같이 설치해 두면 안전해요")
    return Result(OK, "Python 버전", text)


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


def check_env_keys(names: set[str], gemini_names: set[str]) -> list[Result]:
    """키 이름이 있는지만 본다. names 는 이미 '값이 비어 있지 않은 이름'만 담은 집합."""
    results: list[Result] = []
    if names & set(SUPABASE_URL_KEYS):
        results.append(Result(OK, "키 이름 SUPABASE_URL", "있음 (" + ", ".join(k for k in SUPABASE_URL_KEYS if k in names) + ")"))
    else:
        results.append(Result(FAIL, "키 이름 SUPABASE_URL", "SUPABASE_URL 도 NEXT_PUBLIC_SUPABASE_URL 도 없어요",
                              "중앙 .env 에 SUPABASE_URL=… 한 줄을 추가하세요(값은 슈파베이스 프로젝트 설정에서)"))
    if SUPABASE_SECRET_KEY in names:
        results.append(Result(OK, f"키 이름 {SUPABASE_SECRET_KEY}", "있음"))
    else:
        results.append(Result(FAIL, f"키 이름 {SUPABASE_SECRET_KEY}", "없어요",
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


def check_guide_folder(root: pathlib.Path, is_dir=lambda p: pathlib.Path(p).is_dir()) -> Result:
    if is_dir(root):
        return Result(OK, "지도서 폴더", "있음 (집 PC 처럼 지도서 PDF 를 바로 쓸 수 있어요)")
    return Result(OK, "지도서 폴더", "없어도 됨 — 지도서 PDF 는 집 PC 에만 두고, 학교 PC 는 만들어 둔 흐름·단원 개관만 써요")


# ──────────────────────────── 모아서 실행 ────────────────────────────

def _present_names(values: dict, environ: dict) -> set[str]:
    return {k for k, v in values.items() if v} | {k for k, v in environ.items() if v}


def run_checks() -> list[Result]:
    env = dict(os.environ)
    results: list[Result] = [check_python()]
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
    results += check_env_keys(_present_names(main_values, env), _present_names(gemini_values, env))

    results.append(cfg_result)
    results += check_data_dir(data_path)
    results.append(check_onedrive(env))

    port = int(cfg.get("port") or DEFAULT_PORT)
    debug_port = int(cfg.get("debug_port") or DEFAULT_DEBUG_PORT)
    results.append(check_port(port, "수업 비서", "서버가 꺼져 있어요(켜기 전이면 정상). 실행_수업비서.bat 을 실행하세요"))
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
