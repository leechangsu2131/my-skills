"""저장한 수업 녹음(WebM·MP4)을 클로바노트에 올릴 수 있는 MP3(또는 M4A)로 바꾼다 (T99).

설계: docs/plans/clova-export.md. 원본은 건드리지 않고 `<녹음 폴더>/export/` 에만 변환본을 만든다.
서버(assistant_server.py)와 따로 두어 가짜 ffmpeg 로 시험할 수 있게 했다.

- ffmpeg 는 설정 `ffmpeg_path` → PATH 순서로 찾는다. 없으면 설치 안내가 든 `FfmpegMissing`.
- 원본은 표준입력으로 흘려 넣고, 출력은 영문 임시 이름에 쓴 뒤 한글 이름으로 바꾼다(윈도우 한글 경로 걱정을 없앰).
- 이미 만든 변환본이 원본보다 새것이면 다시 만들지 않는다.
- 마지막으로 바뀐 지 30초가 안 된 파일은 '녹음 중'으로 본다(조각이 10초마다 붙음).
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import threading
import time
import uuid

QUIET_SECONDS = 30
TIMEOUT_SECONDS = 300
INSTALL_HELP = ("소리를 바꾸는 도구(ffmpeg)가 없어요. 명령 창에서 `winget install Gyan.FFmpeg` 를 실행해 설치한 뒤 "
                "수업 비서(실행_수업비서.bat)를 다시 켜 주세요. 이미 설치했다면 설정(config.json)의 ffmpeg_path 에 경로를 적을 수 있어요.")

# 말소리용이라 모노·24kHz·64kbps 면 충분하다(50분에 약 23MB).
FORMATS = {
    "mp3": {"suffix": ".mp3", "codec": ["-c:a", "libmp3lame"], "mime": "audio/mpeg"},
    "m4a": {"suffix": ".m4a", "codec": ["-c:a", "aac"], "mime": "audio/mp4"},
}


class ExportError(Exception):
    """변환 실패. 메시지는 화면에 그대로 보여 준다."""


class FfmpegMissing(ExportError):
    """ffmpeg 를 찾지 못함 — 메시지가 설치 안내."""


class StillRecording(ExportError):
    """아직 녹음 중이거나 방금 끝난 파일."""


_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(path: pathlib.Path) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(str(path), threading.Lock())


def find_ffmpeg(cfg: dict | None, which=shutil.which, is_file=lambda p: pathlib.Path(p).is_file()) -> str | None:
    """설정 ffmpeg_path(파일이 실제로 있을 때) → PATH 의 ffmpeg → 없으면 None."""
    configured = str((cfg or {}).get("ffmpeg_path") or "").strip()
    if configured and is_file(configured):
        return configured
    return which("ffmpeg")


def export_path(src, fmt: str = "mp3") -> pathlib.Path:
    """변환본 자리: 원본 옆 export/<원래이름>.<mp3|m4a>."""
    if fmt not in FORMATS:
        raise ValueError(f"지원하지 않는 형식: {fmt}")
    src = pathlib.Path(src)
    return src.parent / "export" / (src.stem + FORMATS[fmt]["suffix"])


def is_still_recording(src, now: float | None = None, quiet_seconds: float = QUIET_SECONDS) -> bool:
    """마지막으로 바뀐 지 quiet_seconds 초가 안 됐으면 녹음 중(또는 방금 끝남)으로 본다."""
    now = time.time() if now is None else now
    return now - pathlib.Path(src).stat().st_mtime < quiet_seconds


def build_command(ffmpeg: str, out: pathlib.Path, fmt: str = "mp3") -> list[str]:
    """원본은 표준입력(pipe:0)으로 받는다."""
    return [str(ffmpeg), "-v", "error", "-y", "-i", "pipe:0", "-vn", "-ac", "1", "-ar", "24000",
            *FORMATS[fmt]["codec"], "-b:a", "64k", str(out)]


def _last_line(raw) -> str:
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw or "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1][:300] if lines else "알 수 없는 오류"


def convert(src, fmt: str = "mp3", ffmpeg: str | None = None, timeout: float = TIMEOUT_SECONDS,
            runner=subprocess.run) -> pathlib.Path:
    """src 를 변환해 export/ 의 파일 경로를 돌려준다(이미 새것이 있으면 그대로)."""
    src = pathlib.Path(src)
    if fmt not in FORMATS:
        raise ExportError(f"지원하지 않는 형식이에요: {fmt}")
    if not src.is_file():
        raise ExportError("녹음 파일을 찾지 못했어요.")
    if not ffmpeg:
        raise FfmpegMissing(INSTALL_HELP)
    dest = export_path(src, fmt)
    with _lock_for(dest):
        if dest.is_file() and dest.stat().st_size > 0 and dest.stat().st_mtime >= src.stat().st_mtime:
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.parent / f"tmp_{uuid.uuid4().hex[:8]}{FORMATS[fmt]['suffix']}"
        try:
            with src.open("rb") as source:
                result = runner(build_command(ffmpeg, tmp, fmt), stdin=source, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, timeout=timeout,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode != 0:
                raise ExportError("변환에 실패했어요: " + _last_line(result.stderr))
            if not tmp.is_file() or tmp.stat().st_size == 0:
                raise ExportError("변환 결과 파일이 비어 있어요.")
            os.replace(tmp, dest)
        except subprocess.TimeoutExpired as exc:
            raise ExportError(f"변환이 {int(timeout)}초 안에 끝나지 않았어요.") from exc
        except OSError as exc:
            raise ExportError(f"변환 도구를 실행하지 못했어요: {exc}") from exc
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
    return dest
