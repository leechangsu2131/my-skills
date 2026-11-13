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

def _env_candidates():
    """.env 후보 경로를 우선순위대로 돌려준다. 윈도우 사용자 이름이 달라도 찾도록 홈 폴더 기준으로 탐색."""
    seen = set()

    def uniq(path: Path):
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            return path
        return None

    raw = []
    if os.environ.get("ENV_FILE"):  # 직접 지정하고 싶을 때
        raw.append(Path(os.environ["ENV_FILE"]))

    roots = []
    for var in ("OneDriveCommercial", "OneDrive", "OneDriveConsumer"):
        if os.environ.get(var):
            roots.append(Path(os.environ[var]))
    home = Path.home()  # C:\Users\<어떤이름이든> 자동 인식
    try:
        roots += sorted(home.glob("OneDrive*"))
    except OSError:
        pass

    for root in roots:
        raw.append(root / "96. 인증" / ".env")
        try:
            raw += [d / ".env" for d in sorted(root.glob("96*")) if d.is_dir()]
        except OSError:
            pass

    raw.append(Path(__file__).parent / ".env")  # 마지막: 스크립트 옆 .env
    return [p for p in map(uniq, raw) if p]


def _load_dotenv() -> None:
    """로컬 실행용: 첫 번째로 발견된 .env를 읽어 환경변수로 등록. 깃허브 액션에서는 .env가 없으니 건너뜀."""
    for f in _env_candidates():
        try:
            if not f.is_file():
                continue
            text = f.read_text(encoding="utf-8-sig")  # 메모장 BOM 대응
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        print(f"[env] 불러옴: {f}")
        return


_load_dotenv()

PLAYLIST_URL = os.environ["PLAYLIST_URL"]
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "5"))  # 한 번에 처리할 새 영상 수
KAKAO_REST_API_KEY = os.environ["KAKAO_REST_API_KEY"]
KAKAO_CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET", "")
KAKAO_REFRESH_TOKEN = os.environ["KAKAO_REFRESH_TOKEN"]
# 선택: 친구에게도 보내기. 쉼표로 구분한 uuid (최대 5명). list_friends.py로 확인한다
FRIEND_UUIDS = [u.strip() for u in os.environ.get("KAKAO_FRIEND_UUIDS", "").split(",") if u.strip()][:5]

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


def _template(text: str, url: str) -> dict:
    return {
        "object_type": "text",
        "text": text[:200],  # 텍스트 템플릿 글자 수 제한
        "link": {"web_url": url, "mobile_web_url": url},
        "button_title": "영상 열기",
    }


def kakao_send(token: str, text: str, url: str, to_friends: bool = True) -> None:
    """나에게 보내기. KAKAO_FRIEND_UUIDS가 있으면 같은 내용을 친구에게도 보낸다(실패해도 전체는 계속)."""
    template = json.dumps(_template(text, url), ensure_ascii=False)
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers=headers,
        data={"template_object": template},
        timeout=30,
    )
    r.raise_for_status()

    if to_friends and FRIEND_UUIDS:
        fr = requests.post(
            "https://kapi.kakao.com/v1/api/talk/friends/message/default/send",
            headers=headers,
            data={"receiver_uuids": json.dumps(FRIEND_UUIDS), "template_object": template},
            timeout=30,
        )
        if not fr.ok:
            print(f"친구에게 보내기 실패 ({fr.status_code}): {fr.text}")


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


LANG_STAGES = [["ko", "ko-orig"], ["en", "en-orig"]]  # 한국어를 먼저, 없을 때만 영어 요청 (요청 수를 줄여 429 방지)
PREFERRED = ["ko", "ko-orig", "en", "en-orig"]


def _opts(langs: list[str]) -> dict:
    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": langs,
        "subtitlesformat": "vtt",
        "outtmpl": str(TMP / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "sleep_interval_subtitles": 3,  # 자막 요청 사이 대기
        "retries": 5,
        "extractor_retries": 3,
    }
    # 선택: 로그인 쿠키로 요청하면 차단이 줄어드는 경우가 있다
    if os.environ.get("YT_COOKIES_FILE"):
        opts["cookiefile"] = os.environ["YT_COOKIES_FILE"]
    elif os.environ.get("YT_COOKIES_FROM_BROWSER"):
        opts["cookiesfrombrowser"] = (os.environ["YT_COOKIES_FROM_BROWSER"],)
    return opts


def _download(url: str, langs: list[str]) -> None:
    """429(요청 과다)면 점점 길게 쉬었다가 최대 3번 시도한다."""
    for attempt in range(1, 4):
        try:
            with yt_dlp.YoutubeDL(_opts(langs)) as ydl:
                ydl.download([url])
            return
        except Exception as ex:
            if "429" in str(ex) and attempt < 3:
                wait = 60 * attempt
                print(f"429 요청 과다 - {wait}초 쉬었다가 다시 시도")
                time.sleep(wait)
                continue
            raise


def _read_saved_vtt(video_id: str) -> str | None:
    for lang in PREFERRED:
        f = TMP / f"{video_id}.{lang}.vtt"
        if f.exists():
            return vtt_to_text(f.read_text(encoding="utf-8"))
    return None


def fetch_transcript(video_id: str) -> str | None:
    """자막 텍스트 반환. 자막이 없으면 None. 요청 실패(차단 등)는 예외."""
    TMP.mkdir(exist_ok=True)
    for old in TMP.glob(f"{video_id}*"):
        old.unlink()
    url = f"https://www.youtube.com/watch?v={video_id}"
    for langs in LANG_STAGES:
        _download(url, langs)
        text = _read_saved_vtt(video_id)
        if text is not None:
            return text
    return None


def safe_name(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s)[:60]



def ids_from_saved_files() -> set[str]:
    """transcripts/ 폴더에 이미 저장된 자막 파일명에서 영상 ID를 읽는다 (state.json이 없어도 중복 방지)."""
    ids = set()
    for f in OUT_DIR.glob("*.txt"):
        m = re.search(r"_([A-Za-z0-9_-]{11})$", f.stem)
        if m:
            ids.add(m.group(1))
    return ids

# ---------- 메인 ----------
def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {"done": []}
    done = set(state["done"]) | ids_from_saved_files()

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
        print(f"{'저장' if text else '자막 없음'} + 카톡 전송 완료: {title}")
        done.add(vid)
        time.sleep(int(os.environ.get("SLEEP_BETWEEN", "8")))

    state["done"] = sorted(done)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    print(f"끝: 새 영상 {len(new)}개 중 실패 {failures}개 / 자막 폴더: {OUT_DIR}")

    if failures:
        kakao_send(token, f"자막 가져오기 {failures}건 실패 (유튜브 차단 가능성)", PLAYLIST_URL, to_friends=False)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
