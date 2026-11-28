"""급식·날씨 작은 칸 (T109, ISSUE-052 ④).

화면 위쪽에 "🍱 오늘 메뉴 · ☀ 12°" 한 줄을 보여 주려고 오늘 급식과 날씨를 가져온다.

- 급식: NEIS 교육정보 개방 포털 급식 API. 중앙 .env 의 공용 키를 읽는다.
    NEIS_SCHOOL_CODE=   (행정표준코드, 학교 하나)
    NEIS_OFFICE_CODE=   (시도교육청 코드)
    NEIS_API_KEY=       (선택. 없으면 키 없이 부른다)
  (옛 이름 TEACHERLESSON_ASSISTANT__SCHOOL_CODE·__OFFICE_CODE·NEIS_OPEN_API_KEY 도 공용 키가 없을 때만 받아 준다)
- 날씨: 키가 필요 없는 open-meteo. 좌표는 .env 에 적는다.
    TEACHERLESSON_ASSISTANT__LATITUDE=  /  TEACHERLESSON_ASSISTANT__LONGITUDE=
- 하루에 한 번만 가져와 내 문서\\my-skills-data\\teacherlesson-assistant\\school_info_cache.json 에 둔다.
- 설정이 없거나 인터넷이 안 되면 그 칸만 비워 둔다(오류를 화면에 띄우지 않는다).
- 급식 메뉴 뒤의 알레르기 번호 "(5.6)" 는 지운다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date

PREFIX = "TEACHERLESSON_ASSISTANT__"
MEAL_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 4


def fetch_json(url: str):
    """주소에서 JSON 을 받는다. 시험에서는 이 함수를 가짜로 바꾼다."""
    req = urllib.request.Request(url, headers={"User-Agent": "teacherlesson-assistant"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        return json.loads(res.read().decode("utf-8"))


def clean_menu(raw: str) -> str:
    """'쌀밥<br/>된장국 (5.6.13)' → '쌀밥, 된장국' (알레르기 번호 지움)."""
    text = re.sub(r"<br\s*/?>", "\n", raw or "", flags=re.I)
    dishes = []
    for line in text.split("\n"):
        line = re.sub(r"\(\s*[\d.\s,]+\s*\)", "", line)   # (5.6) 같은 번호 묶음
        # 끝에 붙은 알레르기 번호("우유 2." · "쌀밥5.6." · "빵 5"). 메뉴 이름의 숫자("비타500")는 지우지 않는다
        line = re.sub(r"(?<=[가-힣a-zA-Z])(?:\s*\d{1,2}(?:\.\d{1,2})+\.?|\s*\d{1,2}\.|\s+\d{1,2})$", "", line.strip())
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            dishes.append(line)
    return ", ".join(dishes)


def parse_meal(data) -> str:
    """API 응답에서 점심(없으면 첫 번째 식사) 메뉴 글을 뽑는다. 없으면 ''."""
    if not isinstance(data, dict):
        return ""
    rows = []
    for block in data.get("mealServiceDietInfo") or []:
        if isinstance(block, dict) and isinstance(block.get("row"), list):
            rows = [r for r in block["row"] if isinstance(r, dict)]
    if not rows:
        return ""
    pick = next((r for r in rows if "중식" in str(r.get("MMEAL_SC_NM", ""))), rows[0])
    return clean_menu(str(pick.get("DDISH_NM", "")))


def weather_icon(code) -> str:
    """open-meteo 날씨 코드(WMO) → 그림 글자."""
    try:
        code = int(code)
    except (TypeError, ValueError):
        return "🌡"
    if code == 0:
        return "☀"
    if code in (1, 2):
        return "🌤"
    if code == 3:
        return "☁"
    if code in (45, 48):
        return "🌫"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "🌧"
    if code in (71, 73, 75, 77, 85, 86):
        return "❄"
    if code in (95, 96, 99):
        return "⛈"
    return "🌡"


def parse_weather(data):
    """open-meteo 응답 → {"temp": 12, "icon": "☀"}. 못 읽으면 None."""
    try:
        cur = data["current"]
        return {"temp": round(float(cur["temperature_2m"])), "icon": weather_icon(cur.get("weather_code"))}
    except (KeyError, TypeError, ValueError):
        return None


def _setting(env: dict, name: str) -> str:
    """서버는 skill_env.env_values 로 앞머리(TEACHERLESSON_ASSISTANT__)를 뗀 이름을 주고, 윈도우 환경변수는 앞머리가 붙은 채 온다. 둘 다 받는다."""
    return str(env.get(name) or env.get(PREFIX + name) or "").strip()


def _neis(env: dict, shared: str, old: str) -> str:
    """공용 키(NEIS_…)를 먼저, 없으면 옛 이름(앞머리 붙은 것, 뗀 것 모두)."""
    return str(env.get(shared) or env.get(old) or env.get(old.removeprefix(PREFIX)) or "").strip()


def fetch_meal(day: date, env: dict, fetch=None) -> str:
    school = _neis(env, "NEIS_SCHOOL_CODE", PREFIX + "SCHOOL_CODE")
    office = _neis(env, "NEIS_OFFICE_CODE", PREFIX + "OFFICE_CODE")
    if not school or not office:
        return ""
    params = {"Type": "json", "pIndex": 1, "pSize": 10, "ATPT_OFCDC_SC_CODE": office,
              "SD_SCHUL_CODE": school, "MLSV_YMD": day.strftime("%Y%m%d")}
    key = _neis(env, "NEIS_API_KEY", "NEIS_OPEN_API_KEY")
    if key:
        params["KEY"] = key
    data = (fetch or fetch_json)(MEAL_URL + "?" + urllib.parse.urlencode(params))
    result = data.get("RESULT") if isinstance(data, dict) else None
    code = str(result.get("CODE", "")) if isinstance(result, dict) else ""
    if code.startswith("ERROR"):  # 서버가 오류를 정상 응답으로 줄 때(INFO-200 '자료 없음'은 정상) — 빈 급식을 저장하지 않는다
        raise ValueError(code)
    return parse_meal(data)


def fetch_weather(env: dict, fetch=None):
    lat, lon = _setting(env, "LATITUDE"), _setting(env, "LONGITUDE")
    try:
        float(lat), float(lon)
    except ValueError:
        return None
    params = {"latitude": lat, "longitude": lon, "current": "temperature_2m,weather_code",
              "timezone": "Asia/Seoul"}
    return parse_weather((fetch or fetch_json)(WEATHER_URL + "?" + urllib.parse.urlencode(params)))


def _read_cache(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _signature(env: dict) -> str:
    """캐시가 어떤 설정으로 받은 값인지(학교·교육청·좌표). 키는 넣지 않고, 파일에는 해시만 둔다."""
    parts = [_neis(env, "NEIS_SCHOOL_CODE", PREFIX + "SCHOOL_CODE"), _neis(env, "NEIS_OFFICE_CODE", PREFIX + "OFFICE_CODE"),
             _setting(env, "LATITUDE"), _setting(env, "LONGITUDE")]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


def get_school_info(env: dict, cache_path, today: date | None = None, fetch=None) -> dict:
    """오늘 급식·날씨. 하루 한 번만 가져오고 실패한 칸은 None 으로 둔다.

    돌려주는 값: {"status": "success", "date": "2026-11-28", "meal": "쌀밥, 된장국" | "", "weather": {...} | None}
    """
    today = today or date.today()
    iso = today.isoformat()
    cached = _read_cache(cache_path)
    sig = _signature(env)
    if cached.get("date") == iso and cached.get("done") and cached.get("sig") == sig:  # 설정을 고치면 같은 날에도 다시 받는다
        return {"status": "success", "date": iso, "meal": cached.get("meal", ""), "weather": cached.get("weather")}
    meal, weather, ok = "", None, True
    try:
        meal = fetch_meal(today, env, fetch)
    except Exception:  # 인터넷·서버 문제는 조용히 넘어간다
        ok = False
    try:
        weather = fetch_weather(env, fetch)
    except Exception:
        ok = False
    result = {"status": "success", "date": iso, "meal": meal, "weather": weather}
    if ok:  # 실패가 있으면 저장하지 않아 다음에 다시 시도한다
        try:
            cache_path.write_text(json.dumps({**result, "done": True, "sig": sig}, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    return result
