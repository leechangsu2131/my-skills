"""로컬 실행용 .env 로더. 깃허브 액션에서는 .env가 없으니 그냥 건너뛴다."""
from __future__ import annotations

import os
from pathlib import Path

ENV_SOURCES: dict[str, Path] = {}  # 값을 실제로 채워 준 .env 파일 (이름 -> 파일)
ENV_DIRS: list[Path] = []  # 실제로 읽은 .env들이 있는 폴더 (상대경로 해석에 쓴다)
REPO_ROOT = Path(__file__).resolve().parent.parent


def expand(value: str) -> Path:
    """'~' (사용자 폴더)와 %USERPROFILE%, %OneDrive% 같은 환경변수를 풀어 준다.
    사용자명이 달라도 같은 .env 값으로 동작하게 하려는 것."""
    return Path(os.path.expandvars(os.path.expanduser(value.strip().strip('"').strip("'"))))


def resolve_path(value: str) -> Path:
    """절대경로는 그대로, 상대경로는 '실행한 폴더 -> 읽은 .env들의 폴더 -> 저장소 폴더' 순서로 찾는다.
    어디에도 없으면 첫 후보를 돌려줘서 오류 메시지에 쓰이게 한다."""
    p = expand(value)
    if p.is_absolute():
        return p
    candidates = [Path.cwd() / p, *(d / p for d in ENV_DIRS), REPO_ROOT / p]
    return next((c for c in candidates if c.exists()), candidates[0])


def _read_into_environ(f: Path) -> bool:
    try:
        text = f.read_text(encoding="utf-8-sig")  # 메모장 BOM 대응
    except UnicodeDecodeError:
        print(f"[env] 경고: {f} 가 UTF-8이 아닙니다. 메모장 '다른 이름으로 저장'에서 인코딩을 UTF-8로 저장하세요.")
        return False
    except OSError as e:
        print(f"[env] 경고: {f} 를 읽을 수 없습니다 ({type(e).__name__})")
        return False
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            if k not in os.environ:  # 먼저 읽은 값이 이긴다
                os.environ[k] = v.strip().strip('"').strip("'")
                ENV_SOURCES[k] = f
    return True


def find_cloud_env() -> Path | None:
    """OneDrive 아래 '96*' 폴더의 .env 를 찾는다 (예: OneDrive\\96. 인증\\.env).
    사용자명·OneDrive 폴더명(OneDrive - 학교 등)이 PC마다 달라도 찾도록 홈 폴더 기준으로 탐색한다."""
    roots: list[Path] = []
    for var in ("OneDriveCommercial", "OneDrive", "OneDriveConsumer"):
        if os.environ.get(var):
            roots.append(Path(os.environ[var]))
    try:
        roots += sorted(Path.home().glob("OneDrive*"))
    except OSError:
        pass
    for root in roots:
        try:
            for d in sorted(root.glob("96*")):
                f = d / ".env"
                if d.is_dir() and f.is_file():
                    return f
        except OSError:
            continue
    return None


def load_env() -> None:
    """① 현재 폴더의 .env  ② ENV_FILE 로 지정한 파일  ③ (②가 없으면) OneDrive\\96*\\.env 자동 탐색.
    있는 것을 모두 합치고, 같은 이름이 여럿이면 앞의 것이 이긴다.
    공용 폴더에 비밀을 두지 않으려면 ③만 쓰면 된다(폴더에 .env를 만들 필요 없음)."""
    ENV_DIRS.clear()
    ENV_SOURCES.clear()
    files: list[Path] = [Path.cwd() / ".env"]
    explicit = os.environ.get("ENV_FILE", "").strip()
    explicit_ok = False
    if explicit:
        p = expand(explicit)
        if p.is_file():
            files.append(p)
            explicit_ok = True
        else:  # 조용히 넘어가면 '값이 없다'는 오류만 나와 원인을 찾기 어렵다
            print(f"[env] 경고: ENV_FILE로 지정한 파일을 찾을 수 없습니다: {p}")
    if not explicit_ok:
        cloud = find_cloud_env()
        if cloud is not None:
            files.append(cloud)

    seen: set[Path] = set()
    loaded = 0
    for f in files:
        if not f.is_file():
            continue
        real = f.resolve()
        if real in seen:  # 두 경로가 같은 파일이면 한 번만
            continue
        seen.add(real)
        if _read_into_environ(f):
            ENV_DIRS.append(real.parent)
            loaded += 1
            print(f"[env] 불러옴: {f}")  # 깃허브 액션에는 .env가 없어 이 줄이 나오지 않는다
    if not loaded:
        print("[env] .env를 찾지 못했습니다: 이미 설정된 환경변수만 사용합니다")


def update_env_value(key: str, value: str) -> Path | None:
    """key 를 채워 준 .env 파일에서 그 줄 하나만 새 값으로 바꾼다. 다른 줄·주석·줄바꿈·BOM·따옴표는 그대로 둔다.
    그 파일이 없거나(예: 깃허브 액션) 줄을 못 찾으면 아무것도 바꾸지 않고 None."""
    f = ENV_SOURCES.get(key)
    if f is None or not f.is_file():
        return None
    raw = f.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    lines = text.splitlines(keepends=True)
    hit = False
    for i, line in enumerate(lines):
        body = line.rstrip("\r\n")
        k, sep, v = body.partition("=")
        if sep and not body.lstrip().startswith("#") and k.strip() == key:
            quote = v.strip()[:1] if v.strip()[:1] in "\"'" else ""
            lines[i] = f"{k}={quote}{value}{quote}" + line[len(body):]
            hit = True
            break  # 읽을 때 먼저 나온 줄이 이기므로 첫 줄만
    if not hit:
        return None
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_bytes((b"\xef\xbb\xbf" if bom else b"") + "".join(lines).encode("utf-8"))
    tmp.replace(f)  # 쓰다 끊겨도 원본이 깨지지 않게 교체 방식
    os.environ[key] = value
    return f
