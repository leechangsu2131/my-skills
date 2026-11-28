"""school_info.py(급식·날씨 한 줄) 시험 (T109). 실행: python -m pytest tests/test_school_info.py

인터넷·진짜 키는 쓰지 않는다. fetch 를 가짜로 바꾸고 임시 폴더에만 캐시를 쓴다.
"""
import json
import pathlib
import sys
import urllib.parse
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import school_info as si  # noqa: E402

DAY = date(2026, 11, 28)
ENV = {"NEIS_SCHOOL_CODE": "0000000", "NEIS_OFFICE_CODE": "X00",
       "TEACHERLESSON_ASSISTANT__LATITUDE": "37.5", "TEACHERLESSON_ASSISTANT__LONGITUDE": "127.0"}
MEAL = {"mealServiceDietInfo": [{"head": [{"list_total_count": 2}]}, {"row": [
    {"MMEAL_SC_NM": "조식", "DDISH_NM": "죽"},
    {"MMEAL_SC_NM": "중식", "DDISH_NM": "쌀밥<br/>된장국 (5.6.13)<br/>우유 2.<br/>배추김치 (9)"}]}]}
WEATHER = {"current": {"temperature_2m": 11.6, "weather_code": 0}}


class Fake:
    def __init__(self, meal=MEAL, weather=WEATHER, fail=False):
        self.meal, self.weather, self.fail, self.urls = meal, weather, fail, []

    def __call__(self, url):
        self.urls.append(url)
        if self.fail:
            raise OSError("offline")
        return self.meal if "neis.go.kr" in url else self.weather


def test_clean_menu_removes_allergy_numbers():
    assert si.clean_menu("쌀밥<br/>된장국 (5.6.13)<br/>우유 2.<br/>배추김치 (9)") == "쌀밥, 된장국, 우유, 배추김치"


def test_parse_meal_prefers_lunch():
    assert si.parse_meal(MEAL) == "쌀밥, 된장국, 우유, 배추김치"


def test_parse_meal_no_data_is_empty():
    assert si.parse_meal({"RESULT": {"CODE": "INFO-200"}}) == ""
    assert si.parse_meal(None) == ""


def test_weather_parse_and_icon():
    assert si.parse_weather(WEATHER) == {"temp": 12, "icon": "☀"}
    assert si.parse_weather({}) is None
    assert si.weather_icon(73) == "❄" and si.weather_icon(63) == "🌧" and si.weather_icon("x") == "🌡"


def test_get_info_builds_urls_and_caches(tmp_path):
    cache, f = tmp_path / "c.json", Fake()
    out = si.get_school_info(ENV, cache, DAY, f)
    assert out == {"status": "success", "date": "2026-11-28", "meal": "쌀밥, 된장국, 우유, 배추김치",
                   "weather": {"temp": 12, "icon": "☀"}}
    meal_q = urllib.parse.parse_qs(urllib.parse.urlparse(f.urls[0]).query)
    assert meal_q["SD_SCHUL_CODE"] == ["0000000"] and meal_q["MLSV_YMD"] == ["20261128"] and "KEY" not in meal_q
    n = len(f.urls)
    assert si.get_school_info(ENV, cache, DAY, f) == out and len(f.urls) == n  # 하루 한 번


def test_key_added_only_when_present(tmp_path):
    f = Fake()
    si.get_school_info({**ENV, "NEIS_API_KEY": "FAKEKEY"}, tmp_path / "c.json", DAY, f)
    assert urllib.parse.parse_qs(urllib.parse.urlparse(f.urls[0]).query)["KEY"] == ["FAKEKEY"]


def test_new_day_refetches(tmp_path):
    cache, f = tmp_path / "c.json", Fake()
    si.get_school_info(ENV, cache, DAY, f)
    n = len(f.urls)
    si.get_school_info(ENV, cache, date(2026, 11, 29), f)
    assert len(f.urls) > n


def test_offline_is_silent_and_not_cached(tmp_path):
    cache = tmp_path / "c.json"
    out = si.get_school_info(ENV, cache, DAY, Fake(fail=True))
    assert out == {"status": "success", "date": "2026-11-28", "meal": "", "weather": None}
    assert not cache.exists()  # 실패는 저장하지 않아 다음에 다시 시도
    f = Fake()
    assert si.get_school_info(ENV, cache, DAY, f)["meal"]


def test_missing_settings_makes_no_calls(tmp_path):
    f = Fake()
    out = si.get_school_info({}, tmp_path / "c.json", DAY, f)
    assert f.urls == [] and out["meal"] == "" and out["weather"] is None


def test_meal_failure_keeps_weather(tmp_path):
    def fetch(url):
        if "neis.go.kr" in url:
            raise OSError("x")
        return WEATHER
    out = si.get_school_info(ENV, tmp_path / "c.json", DAY, fetch)
    assert out["meal"] == "" and out["weather"]["temp"] == 12


def test_broken_cache_file_is_ignored(tmp_path):
    cache = tmp_path / "c.json"
    cache.write_text("{깨짐", encoding="utf-8")
    assert si.get_school_info(ENV, cache, DAY, Fake())["meal"]
    assert json.loads(cache.read_text(encoding="utf-8"))["date"] == "2026-11-28"


def test_old_key_names_still_work_but_shared_wins(tmp_path):
    old = {"TEACHERLESSON_ASSISTANT__SCHOOL_CODE": "1111111", "TEACHERLESSON_ASSISTANT__OFFICE_CODE": "Y00",
           "NEIS_OPEN_API_KEY": "OLDKEY"}
    f = Fake()
    si.get_school_info(old, tmp_path / "a.json", DAY, f)
    q = urllib.parse.parse_qs(urllib.parse.urlparse(f.urls[0]).query)
    assert q["SD_SCHUL_CODE"] == ["1111111"] and q["KEY"] == ["OLDKEY"]
    f2 = Fake()
    si.get_school_info({**old, **ENV, "NEIS_API_KEY": "NEWKEY"}, tmp_path / "b.json", DAY, f2)
    q2 = urllib.parse.parse_qs(urllib.parse.urlparse(f2.urls[0]).query)
    assert q2["SD_SCHUL_CODE"] == ["0000000"] and q2["KEY"] == ["NEWKEY"]


def test_env_values_from_central_env_reaches_weather_and_old_names(tmp_path, monkeypatch):
    """서버가 만드는 모양(skill_env.env_values: 스킬 앞머리를 뗀 사전)으로도 읽혀야 한다(검토 🔴)."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_shared"))
    import skill_env
    envfile = tmp_path / ".env"
    envfile.write_text("TEACHERLESSON_ASSISTANT__LATITUDE=37.5\nTEACHERLESSON_ASSISTANT__LONGITUDE=127.0\n"
                       "TEACHERLESSON_ASSISTANT__SCHOOL_CODE=1111111\nTEACHERLESSON_ASSISTANT__OFFICE_CODE=Y00\n",
                       encoding="utf-8")
    monkeypatch.setenv("MY_SKILLS_ENV", str(envfile))
    env = skill_env.env_values("teacherlesson-assistant")
    f = Fake()
    out = si.get_school_info(env, tmp_path / "c.json", DAY, f)
    assert out["weather"] == {"temp": 12, "icon": "☀"}            # 날씨 호출이 일어남
    meal_q = urllib.parse.parse_qs(urllib.parse.urlparse(f.urls[0]).query)
    assert meal_q["SD_SCHUL_CODE"] == ["1111111"]                   # 옛 이름 급식도 읽힘


def test_changing_settings_same_day_refetches(tmp_path):
    cache = tmp_path / "c.json"
    f = Fake()
    out = si.get_school_info({}, cache, DAY, f)                    # 설정 없이 한 번 켠 날
    assert out["weather"] is None and f.urls == []
    si.get_school_info(ENV, cache, DAY, f)                         # 같은 날 설정을 채움 → 다시 받아야 함
    assert f.urls and si.get_school_info(ENV, cache, DAY, f)["weather"]["temp"] == 12
    n = len(f.urls)
    si.get_school_info(ENV, cache, DAY, f)
    assert len(f.urls) == n                                         # 설정이 같으면 하루 한 번


def test_neis_error_response_is_not_cached(tmp_path):
    cache = tmp_path / "c.json"
    bad = Fake(meal={"RESULT": {"CODE": "ERROR-337", "MESSAGE": "x"}})
    out = si.get_school_info(ENV, cache, DAY, bad)
    assert out["meal"] == "" and out["weather"] and not cache.exists()
    # 급식이 없는 날(INFO-200)은 정상 빈 값 — 저장한다
    none_day = Fake(meal={"RESULT": {"CODE": "INFO-200"}})
    si.get_school_info(ENV, cache, DAY, none_day)
    assert cache.exists()


def test_clean_menu_keeps_digits_in_dish_names():
    assert si.clean_menu("비타500<br/>쌀밥 5.6.<br/>우유 2.") == "비타500, 쌀밥, 우유"
