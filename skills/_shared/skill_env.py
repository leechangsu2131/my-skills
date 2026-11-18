"""my-skills 공통 환경 로더 (모든 스킬이 이 파일 하나로 비밀값·개인데이터 경로를 찾는다).

■ 중앙 .env (토큰·비밀번호·시트ID 등 모든 설정)
    %OneDriveCommercial%\\96. 인증\\.env   ← 윈도우 계정 이름이 달라도 자동으로 찾음
    찾는 순서: MY_SKILLS_ENV 환경변수 → %OneDriveCommercial% → %OneDrive% → ~/OneDrive - gyo6.net
    못 찾으면(예: GitHub Actions) 조용히 건너뛰고 OS 환경변수만 사용한다.

■ 개인정보·결과물 폴더 (깃에 올리지 않는 데이터)
    <내 문서>\\my-skills-data\\<스킬이름>\\
    중앙 .env에 MY_SKILLS_DATA_DIR 를 적으면 그 위치를 대신 쓴다.

■ 값 문법
    KEY=value                       모든 스킬 공통
    UTIL_DISCORD_MEMO__KEY=value    해당 스킬에서만 KEY를 이 값으로 덮어씀 (스킬폴더명 대문자, - → _)
    %OneDrive%, %USERPROFILE% 같은 %변수% 는 실행 PC 기준으로 펼쳐진다.

■ 사용법 (스크립트 맨 위)
    import sys, pathlib; sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
    from skill_env import load_env, data_dir
    load_env()                      # 호출한 파일 위치로 스킬 이름을 자동 판별
    out = data_dir() / "result"     # → 내 문서\\my-skills-data\\<스킬>\\result

이미 설정된 OS 환경변수는 덮어쓰지 않는다 (CI 시크릿 우선). override=True 로 바꿀 수 있다.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ONEDRIVE_FOLDER_NAME = "OneDrive - gyo6.net"
CENTRAL_ENV_RELATIVE = Path("96. 인증") / ".env"
DATA_FOLDER_NAME = "my-skills-data"

_PERCENT_VAR = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")
_loaded_path: Path | None = None


# ──────────────────────────── 위치 찾기 ────────────────────────────

def central_env_path() -> Path | None:
    """중앙 .env 파일 경로 (없으면 None)."""
    candidates: list[Path] = []
    override = os.environ.get("MY_SKILLS_ENV")
    if override:
        candidates.append(Path(_expand(override)))
    for var in ("OneDriveCommercial", "OneDrive"):
        base = os.environ.get(var)
        if base:
            candidates.append(Path(base) / CENTRAL_ENV_RELATIVE)
    candidates.append(Path.home() / ONEDRIVE_FOLDER_NAME / CENTRAL_ENV_RELATIVE)
    for path in candidates:
        if path.is_file():
            return path
    return None


def documents_dir() -> Path:
    """현재 윈도우 계정의 '내 문서' 폴더 (OneDrive 리디렉션도 반영)."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            import uuid

            folder_id = uuid.UUID("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}")  # FOLDERID_Documents
            guid = (ctypes.c_byte * 16).from_buffer_copy(folder_id.bytes_le)
            out = ctypes.c_wchar_p()
            shell32 = ctypes.windll.shell32
            shell32.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.HANDLE,
                                                     ctypes.POINTER(ctypes.c_wchar_p)]
            if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) == 0:
                path = Path(out.value)
                ctypes.windll.ole32.CoTaskMemFree(out)
                return path
        except Exception:
            pass
    return Path.home() / "Documents"


def skill_name_for(file: str | os.PathLike | None) -> str | None:
    """skills/<이름>/... 경로에서 <이름>을 돌려준다."""
    if not file:
        return None
    skills_root = Path(__file__).resolve().parent.parent  # .../my-skills/skills
    try:
        rel = Path(file).resolve().relative_to(skills_root)
    except ValueError:
        return None
    return rel.parts[0] if len(rel.parts) > 1 else None


def _caller_file(depth: int = 2) -> str | None:
    try:
        return sys._getframe(depth).f_globals.get("__file__")
    except ValueError:
        return None


# ──────────────────────────── 파싱 ────────────────────────────

def _expand(value: str) -> str:
    """%VAR% (존재하는 것만) 와 선행 ~ 를 펼친다. $ 는 비밀번호에 쓰일 수 있어 건드리지 않는다."""
    value = _PERCENT_VAR.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if value.startswith("~"):
        value = os.path.expanduser(value)
    return value


def _parse(path: Path) -> dict[str, str]:
    try:
        from dotenv import dotenv_values  # 따옴표·여러 줄 값을 정확히 처리
        raw = dotenv_values(path, encoding="utf-8-sig")
        return {k: (v or "") for k, v in raw.items() if k}
    except ImportError:
        pass
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        result[key] = value
    return result


def env_values(skill: str | None = None) -> dict[str, str]:
    """중앙 .env 값을 (스킬별 덮어쓰기 적용 후) dict로 돌려준다. os.environ은 건드리지 않는다."""
    if skill is None:
        skill = skill_name_for(_caller_file())
    path = central_env_path()
    if path is None:
        return {}
    raw = _parse(path)
    prefix = (skill or "").upper().replace("-", "_") + "__" if skill else None
    merged: dict[str, str] = {}
    scoped: dict[str, str] = {}
    for key, value in raw.items():
        if "__" in key:
            if prefix and key.startswith(prefix):
                scoped[key[len(prefix):]] = value
            continue
        merged[key] = value
    merged.update(scoped)
    return {k: _expand(v) for k, v in merged.items()}


# ──────────────────────────── 공개 API ────────────────────────────

def load_env(*_ignored_paths, skill: str | None = None, override: bool = False, verbose: bool = False, **_ignored) -> Path | None:
    """중앙 .env를 os.environ에 올린다. 예전 load_dotenv(경로) 호출과 호환되도록 위치 인자는 무시한다."""
    global _loaded_path
    if skill is None:
        skill = skill_name_for(_caller_file())
    values = env_values(skill)
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value
    _loaded_path = central_env_path()
    if verbose:
        print(f"[env] {'불러옴: ' + str(_loaded_path) if _loaded_path else '중앙 .env 없음 (OS 환경변수만 사용)'}")
    return _loaded_path


def data_dir(skill: str | None = None, *sub: str, create: bool = True) -> Path:
    """개인정보·결과물 저장 폴더: <내 문서>/my-skills-data/<스킬>/<sub...>"""
    if skill is None:
        skill = skill_name_for(_caller_file()) or "_misc"
    base = os.environ.get("MY_SKILLS_DATA_DIR") or env_values(skill).get("MY_SKILLS_DATA_DIR")
    root = Path(_expand(base)) if base else documents_dir() / DATA_FOLDER_NAME
    path = root.joinpath(skill, *sub)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


if __name__ == "__main__":
    # 진단용: python skills/_shared/skill_env.py [스킬이름]
    name = sys.argv[1] if len(sys.argv) > 1 else None
    p = central_env_path()
    print("중앙 .env :", p or "찾지 못함")
    print("데이터 폴더:", data_dir(name or "_misc", create=False))
    keys = sorted(env_values(name))
    print(f"키 {len(keys)}개 ({name or '공통'}):", ", ".join(keys))
