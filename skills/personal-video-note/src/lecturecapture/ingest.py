from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import cv2


def video_metadata(video_path: Path) -> dict[str, float | int]:
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"OpenCV에서 영상을 열 수 없습니다: {video_path}")
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = frame_count / fps if fps > 0 else 0.0
        if width <= 0 or height <= 0:
            raise ValueError("영상의 너비/높이를 확인할 수 없습니다.")
        return {"fps": fps, "frame_count": frame_count, "width": width, "height": height, "duration": duration}
    finally:
        cap.release()


def youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host == "youtu.be":
        return parsed.path.strip("/").split("/")[0] or None
    if host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live"}:
            return parts[1]
    return None


def download_authorized_video(url: str, destination: Path, confirm_authorized: bool = False) -> Path:
    """Download a user-authorized public video via yt-dlp; never bypass access controls."""
    if not confirm_authorized:
        raise PermissionError("실행 전 --confirm-authorized를 지정하고 다운로드 권한을 확인하세요.")
    if youtube_video_id(url) is None:
        raise ValueError("지원하는 YouTube 영상 URL 형식이 아닙니다.")
    if shutil.which("yt-dlp") is None:
        raise RuntimeError('yt-dlp가 설치되어 있지 않습니다. `pip install -e ".[youtube]"`를 실행하세요.')

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Download only a regular available format; no cookies, DRM, login, or restriction bypass.
    template = str(destination.with_suffix("")) + ".%(ext)s"
    cmd = ["yt-dlp", "--no-playlist", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", template, url]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "알 수 없는 오류").strip()
        raise RuntimeError(f"yt-dlp 실행 실패: {message[-1500:]}")

    if destination.exists():
        return destination
    candidates = sorted(destination.parent.glob(destination.stem + ".*"), key=lambda p: p.stat().st_mtime, reverse=True)
    candidates = [p for p in candidates if p.suffix.lower() not in {".json", ".part", ".ytdl"}]
    if candidates:
        if candidates[0] != destination:
            candidates[0].replace(destination)
        return destination
    raise FileNotFoundError("다운로드 명령은 끝났지만 결과 파일을 찾을 수 없습니다.")
