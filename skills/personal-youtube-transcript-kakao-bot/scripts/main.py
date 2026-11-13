"""유튜브 재생목록의 새 영상 자막을 가져와 저장하고, 카톡 '나에게 보내기'로 알려주는 스크립트."""
import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
import yt_dlp

def _load_dotenv() -> None:
    """로컬 실행용: 같은 폴더의 .env를 읽어 환경변수로 등록 (깃허브 액션에서는 .env가 없으니 건너뜀)."""
    f = Path(__file__).parent / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

PLAYLIST_URL = os.environ["PLAYLIST_URL"]
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "5"))  # 한 번에 처리할 새 영상 수
KAKAO_REST_API_KEY = os.environ["KAKAO_REST_API_KEY"]
KAKAO_CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET", "")
KAKAO_REFRESH_TOKEN = os.environ["KAKAO_REFRESH_TOKEN"]

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "transcripts"
STATE = ROOT / "state.json"
TMP = ROOT / "_tmp"
NEW_RT_FILE = ROOT / "new_refresh_token.txt"


# ---------- 카카오 ----------
def kakao_access_token() -> str:
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN,
    }
    if KAKAO_CLIENT_SECRET:
        data["client_secret"] = KAKAO_CLIENT_SECRET
    r = requests.post("https://kauth.kakao.com/oauth/token", data=data, timeout=30)
    r.raise_for_status()
    j = r.json()
    # 리프레시 토큰이 갱신되어 오면 워크플로가 Secrets에 다시 저장한다
    if j.get("refresh_token"):
        NEW_RT_FILE.write_text(j["refresh_token"])
    return j["access_token"]


def kakao_send(token: str, text: str, url: str) -> None:
    template = {
        "object_type": "text",
        "text": text[:200],  # 텍스트 템플릿 글자 수 제한
        "link": {"web_url": url, "mobile_web_url": url},
        "button_title": "영상 열기",
    }
    r = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=30,
    )
    r.raise_for_status()


# ---------- 유튜브 ----------
def list_playlist() -> list[dict]:
    opts = {"extract_flat": "in_playlist", "quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(PLAYLIST_URL, download=False)
    return [
        {"id": e["id"], "title": e.get("title") or e["id"]}
        for e in info.get("entries", [])
        if e and e.get("id")
    ]


def vtt_to_text(vtt: str) -> str:
    lines, prev = [], ""
    for line in vtt.splitlines():
        line = line.strip()
        if (
            not line
            or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE"))
            or "-->" in line
        ):
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and line != prev:
            lines.append(line)
            prev = line
    return "\n".join(lines)


def fetch_transcript(video_id: str) -> str | None:
    """자막 텍스트 반환. 자막이 없으면 None. 요청 실패(차단 등)는 예외."""
    TMP.mkdir(exist_ok=True)
    for old in TMP.glob(f"{video_id}*"):
        old.unlink()
    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["ko", "en"],
        "subtitlesformat": "vtt",
        "outtmpl": str(TMP / "%(id)s.%(ext)s"),
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
    for lang in ("ko", "en"):
        f = TMP / f"{video_id}.{lang}.vtt"
        if f.exists():
            return vtt_to_text(f.read_text(encoding="utf-8"))
    return None


def safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s)[:60]


# ---------- 메인 ----------
def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {"done": []}
    done = set(state["done"])

    new = [e for e in list_playlist() if e["id"] not in done][:MAX_PER_RUN]
    if not new:
        print("새 영상 없음")
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        return 0

    token = kakao_access_token()
    today = datetime.date.today().isoformat()
    failures = 0

    for e in new:
        vid, title = e["id"], e["title"]
        url = f"https://www.youtube.com/watch?v={vid}"
        try:
            text = fetch_transcript(vid)
        except Exception as ex:  # 차단, 네트워크 오류 등 -> 다음 실행 때 재시도
            print(f"실패 {vid}: {ex}")
            failures += 1
            continue

        if text:
            (OUT_DIR / f"{today}_{safe_name(title)}_{vid}.txt").write_text(
                f"{title}\n{url}\n\n{text}\n", encoding="utf-8"
            )
            msg = f"[자막 저장] {title}\n\n{text[:100]}..."
        else:
            msg = f"[자막 없음] {title}"
        kakao_send(token, msg, url)
        done.add(vid)
        time.sleep(3)

    state["done"] = sorted(done)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

    if failures:
        kakao_send(token, f"자막 가져오기 {failures}건 실패 (유튜브 차단 가능성)", PLAYLIST_URL)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
