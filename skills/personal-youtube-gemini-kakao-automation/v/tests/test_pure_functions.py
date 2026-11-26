"""personal-youtube-gemini-kakao-automation 순수 함수 시험.

네트워크·실제 유튜브·Gemini·카카오·디스코드·비밀값 없이, 가짜 자료와 가짜 함수만 사용한다.
- main.py: 글 나누기, 제목·날짜 읽기, 자막(VTT) 정리, 백로그 대상 고르기, 설정 읽기,
  디스코드·카카오 보내기(requests.post 는 가짜)
- gemini_session.py: 경로·주소·로그인 화면 글 판별

소스는 고치지 않는다. 현재 동작과 다르게 기대하는 것은 xfail 로 표시하고 이유를 적었다.
`schedule`·`youtube_transcript_api` 는 설치돼 있지 않을 수 있어 가짜 모듈로 대신한다.
"""
import datetime
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import pytest

V_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V_DIR))

import gemini_session as gs  # noqa: E402


@pytest.fixture(scope="module")
def m():
    with pytest.MonkeyPatch.context() as mp:
        schedule = types.ModuleType("schedule")
        yta = types.ModuleType("youtube_transcript_api")
        yta.YouTubeTranscriptApi = type("YouTubeTranscriptApi", (), {})
        mp.setitem(sys.modules, "schedule", schedule)
        mp.setitem(sys.modules, "youtube_transcript_api", yta)
        spec = importlib.util.spec_from_file_location("t_chesley_main", V_DIR / "main.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield mod


def make_settings(m, **over):
    values = {}
    for f in m.Settings.__dataclass_fields__.values():
        t = str(f.type)
        if "bool" in t:
            values[f.name] = False
        elif "int" in t:
            values[f.name] = 0
        elif "list" in t:
            values[f.name] = []
        else:
            values[f.name] = ""
    values.update(title_prefix="[체슬리모닝브리프]", discord_max_message_length=1900, max_message_length=1000)
    values.update(over)
    return m.Settings(**values)


# ── split_message_chunks ───────────────────────────────────────

def test_split_empty_and_whitespace(m):
    assert m.split_message_chunks("", 100) == [""]
    assert m.split_message_chunks("   \n ", 100) == [""]


def test_split_short_text_unchanged_and_stripped(m):
    assert m.split_message_chunks("  안녕하세요  ", 100) == ["안녕하세요"]


def test_split_prefers_paragraph_break(m):
    text = "가" * 30 + "\n\n" + "나" * 30
    chunks = m.split_message_chunks(text, 40)
    assert chunks == ["가" * 30, "나" * 30]


def test_split_falls_back_to_newline_then_space_then_hard_cut(m):
    assert m.split_message_chunks("가" * 30 + "\n" + "나" * 30, 40) == ["가" * 30, "나" * 30]
    assert m.split_message_chunks("가" * 30 + " " + "나" * 30, 40) == ["가" * 30, "나" * 30]
    assert m.split_message_chunks("가" * 100, 40) == ["가" * 40, "가" * 40, "가" * 20]


def test_split_chunks_within_limit_and_content_kept(m):
    paragraphs = [("문단%d " % i) * 20 for i in range(30)]
    text = "\n\n".join(paragraphs)
    chunks = m.split_message_chunks(text, 120)
    assert all(len(c) <= 120 for c in chunks)
    assert "".join("".join(chunks).split()) == "".join(text.split())


# ── bool_env / 처리한 영상 목록 ────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    ("1", True), ("true", True), (" TRUE ", True), ("Yes", True), ("y", True), ("on", True),
    ("0", False), ("false", False), ("no", False), ("", False), ("아니오", False),
])
def test_bool_env_values(m, monkeypatch, raw, expected):
    monkeypatch.setenv("T10_FLAG", raw)
    assert m.bool_env("T10_FLAG", not expected) is expected


def test_bool_env_unset_uses_default(m, monkeypatch):
    monkeypatch.delenv("T10_FLAG", raising=False)
    assert m.bool_env("T10_FLAG", True) is True
    assert m.bool_env("T10_FLAG", False) is False


def test_processed_ids_roundtrip_sorted(m, tmp_path):
    p = tmp_path / "processed.json"
    m.save_processed_ids(str(p), {"b", "a", "c"})
    assert json.loads(p.read_text(encoding="utf-8")) == ["a", "b", "c"]
    assert m.load_processed_ids(str(p)) == {"a", "b", "c"}


def test_processed_ids_missing_broken_or_wrong_type(m, tmp_path):
    assert m.load_processed_ids(str(tmp_path / "없음.json")) == set()
    bad = tmp_path / "bad.json"
    bad.write_text("{깨짐", encoding="utf-8")
    assert m.load_processed_ids(str(bad)) == set()
    obj = tmp_path / "obj.json"
    obj.write_text('{"a": 1}', encoding="utf-8")
    assert m.load_processed_ids(str(obj)) == set()


def test_processed_ids_converts_to_str_and_drops_empty(m, tmp_path):
    p = tmp_path / "p.json"
    p.write_text('["a", 3, "", null, 0]', encoding="utf-8")
    assert m.load_processed_ids(str(p)) == {"a", "3"}


# ── 제목 판별·날짜 읽기 ────────────────────────────────────────

def test_brief_title_prefixes_settings_first_without_duplicates(m):
    s = make_settings(m, title_prefix="[내 접두사]")
    prefixes = m._brief_title_prefixes(s)
    assert prefixes[0] == "[내 접두사]"
    assert prefixes.count("[체슬리모닝브리프]") == 1
    s2 = make_settings(m, title_prefix="[모닝브리프]")
    assert m._brief_title_prefixes(s2).count("[모닝브리프]") == 1
    assert m._brief_title_prefixes(make_settings(m, title_prefix=""))[0] == "[체슬리모닝브리프]"


@pytest.mark.parametrize("title, expected", [
    ("[체슬리모닝브리프] 7월 16일 시황", True),
    ("미 증시 마감 | 박세익 전무 & 체슬리투자자문 [모닝브리프 / 26.07.16]", True),
    ("Chesley Morning Brief 26.07.16", True),
    ("daily MORNING FUND MANAGER", True),
    ("별난 학습부장 모닝브리프", False),
    ("전혀 다른 영상", False),
    ("", False),
])
def test_title_has_brief_prefix(m, title, expected):
    assert m._title_has_brief_prefix(title, m._brief_title_prefixes(make_settings(m))) is expected


@pytest.mark.parametrize("title, expected", [
    ("[모닝브리프 / 26.07.16]", datetime.date(2026, 7, 16)),
    ("브리프 26/07/16", datetime.date(2026, 7, 16)),
    ("브리프 2026-07-16", datetime.date(2026, 7, 16)),
    ("브리프 2026.7.6", datetime.date(2026, 7, 6)),
    ("Brief 07/16/2026", datetime.date(2026, 7, 16)),
    ("Brief 07-16-26", datetime.date(2026, 7, 16)),
    ("날짜 없음", None),
    ("", None),
    ("브리프 26.13.45", None),
])
def test_parse_date_from_title(m, title, expected):
    assert m._parse_date_from_title(title) == expected


def test_title_has_date(m):
    d = datetime.date(2026, 7, 16)
    assert m._title_has_date("브리프 26.07.16", d)
    assert m._title_has_date("브리프 2026/07/16", d)
    assert m._title_has_date("brief 07/16/26", d)
    assert not m._title_has_date("브리프 26.07.17", d)
    assert not m._title_has_date("날짜 없음", d)


@pytest.mark.parametrize("raw, expected", [
    ("2026-07-16", datetime.date(2026, 7, 16)),
    ("20260716", datetime.date(2026, 7, 16)),
    ("  20260716  ", datetime.date(2026, 7, 16)),
    ("", None), ("   ", None), ("2026/07/16", None), ("abc", None), ("20261399", None),
])
def test_parse_yyyymmdd(m, raw, expected):
    assert m._parse_yyyymmdd(raw) == expected


@pytest.mark.parametrize("meta, expected", [
    ({"upload_date": "20260716"}, datetime.date(2026, 7, 16)),
    ({}, None),
    ({"upload_date": "2026-07-16"}, None),
    ({"upload_date": "2026071"}, None),
    ({"upload_date": "abcdefgh"}, None),
    ({"upload_date": "20261399"}, None),
    ({"upload_date": None}, None),
])
def test_upload_date_from_meta(m, meta, expected):
    assert m._upload_date_from_meta(meta) == expected


# ── yt-dlp 호출(subprocess 는 가짜) ────────────────────────────

class FakeRun:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def test_yt_dlp_command(m):
    s = make_settings(m, yt_no_check_certificates=True)
    cmd = m._yt_dlp_command(s, "--dump-json", "URL")
    assert cmd[0] == sys.executable and cmd[1:3] == ["-m", "yt_dlp"]
    assert "--no-check-certificates" in cmd and cmd[-2:] == ["--dump-json", "URL"]
    s2 = make_settings(m, yt_no_check_certificates=False)
    assert "--no-check-certificates" not in m._yt_dlp_command(s2, "x")


def test_fetch_flat_playlist_parses_lines(m, monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return FakeRun(0, '{"id": "a", "title": "T1"}\n\n깨진줄\n{"id": "b"}\n')

    monkeypatch.setattr(m.subprocess, "run", fake_run)
    s = make_settings(m, channel_url="https://www.youtube.com/@fake/")
    entries = m._fetch_flat_playlist(s, "/streams", limit=7)
    assert [e["id"] for e in entries] == ["a", "b"]
    assert seen["cmd"][-1] == "https://www.youtube.com/@fake/streams"
    assert seen["cmd"][seen["cmd"].index("--playlist-end") + 1] == "7"


def test_fetch_flat_playlist_failure_returns_empty(m, monkeypatch, capsys):
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: FakeRun(1, "", "boom"))
    assert m._fetch_flat_playlist(make_settings(m, channel_url="https://x/@f"), "/videos") == []
    assert "boom" in capsys.readouterr().out


def test_fetch_video_metadata(m, monkeypatch):
    s = make_settings(m)
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: FakeRun(0, '{"title": "T"}'))
    assert m._fetch_video_metadata(s, "vid") == {"title": "T"}
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: FakeRun(1, "", "err"))
    assert m._fetch_video_metadata(s, "vid") is None
    monkeypatch.setattr(m.subprocess, "run", lambda *a, **k: FakeRun(0, "JSON 아님"))
    assert m._fetch_video_metadata(s, "vid") is None


# ── 영상 찾기 ──────────────────────────────────────────────────

def test_find_live_video_for_date_by_title(m, monkeypatch):
    entries = [{"id": "", "title": "[모닝브리프 / 26.07.16]"}, {"id": "v1", "title": "[모닝브리프 / 26.07.16]"}]
    monkeypatch.setattr(m, "_fetch_flat_playlist", lambda s, suffix, limit=20: entries if suffix == "/streams" else [])
    monkeypatch.setattr(m, "_fetch_video_metadata", lambda s, vid: None)
    found = m.find_live_video_for_date(make_settings(m), datetime.date(2026, 7, 16))
    assert found == ("v1", "[모닝브리프 / 26.07.16]")


def test_find_live_video_for_date_by_metadata(m, monkeypatch):
    monkeypatch.setattr(m, "_fetch_flat_playlist", lambda s, suffix, limit=20: [{"id": "v9", "title": "English title"}])
    monkeypatch.setattr(
        m, "_fetch_video_metadata",
        lambda s, vid: {"upload_date": "20260716", "title": "Chesley Morning Brief"},
    )
    found = m.find_live_video_for_date(make_settings(m), datetime.date(2026, 7, 16))
    assert found == ("v9", "Chesley Morning Brief")


def test_find_live_video_for_date_not_found(m, monkeypatch):
    monkeypatch.setattr(m, "_fetch_flat_playlist", lambda s, suffix, limit=20: [{"id": "v1", "title": "관계 없는 영상"}])
    monkeypatch.setattr(m, "_fetch_video_metadata", lambda s, vid: {"upload_date": "20260101", "title": "다른 영상"})
    assert m.find_live_video_for_date(make_settings(m), datetime.date(2026, 7, 16)) is None


def test_find_todays_live_video_id(m, monkeypatch):
    monkeypatch.setattr(m, "find_todays_live_video", lambda s: ("vx", "t"))
    assert m.find_todays_live_video_id(make_settings(m)) == "vx"
    monkeypatch.setattr(m, "find_todays_live_video", lambda s: None)
    assert m.find_todays_live_video_id(make_settings(m)) is None


# ── collect_backlog_targets ────────────────────────────────────

def test_sample_dates_weekdays():
    # 아래 시험이 기대하는 요일(2026-07-18 토요일, 07-19 일요일)이 맞는지 확인
    assert datetime.date(2026, 7, 17).weekday() == 4
    assert datetime.date(2026, 7, 18).weekday() == 5
    assert datetime.date(2026, 7, 19).weekday() == 6


@pytest.fixture
def backlog_env(m, monkeypatch, tmp_path):
    monkeypatch.delenv("BACKLOG_FORCE", raising=False)
    monkeypatch.delenv("BACKLOG_SKIP_EXISTING_SUMMARY", raising=False)
    streams = [
        {"id": "v17", "title": "[모닝브리프 / 26.07.17]"},
        {"id": "v14", "title": "[모닝브리프 / 26.07.14]"},
        {"id": "v18", "title": "[모닝브리프 / 26.07.18]"},   # 토요일
        {"id": "vx", "title": "별난 학습부장 모닝브리프 26.07.15"},  # 제외 글자
    ]
    videos = [
        {"id": "v14", "title": "[모닝브리프 / 26.07.14]"},   # /streams 와 겹침
        {"id": "v10", "title": "[모닝브리프 / 26.07.10]"},   # 범위 밖
        {"id": "vz", "title": "일반 영상 26.07.15"},          # 접두사 없음, /videos 라 무시
    ]
    monkeypatch.setattr(
        m, "_fetch_flat_playlist",
        lambda s, suffix, limit=20: streams if suffix == "/streams" else videos,
    )
    monkeypatch.setattr(m, "_fetch_video_metadata", lambda s, vid: None)
    return make_settings(m, summary_save_dir=str(tmp_path / "summaries"), channel_url="https://x/@f")


def run_backlog(m, s, processed=(), include_weekends=True):
    return m.collect_backlog_targets(
        s, datetime.date(2026, 7, 13), datetime.date(2026, 7, 19), set(processed), include_weekends
    )


def test_backlog_sorted_oldest_first_deduped_in_range(m, backlog_env):
    result = run_backlog(m, backlog_env)
    assert [(d.isoformat(), vid) for d, vid, _ in result] == [
        ("2026-07-14", "v14"), ("2026-07-17", "v17"), ("2026-07-18", "v18"),
    ]


def test_backlog_excludes_weekends_when_asked(m, backlog_env):
    result = run_backlog(m, backlog_env, include_weekends=False)
    assert [vid for _, vid, _ in result] == ["v14", "v17"]


def test_backlog_skips_processed_unless_forced(m, backlog_env, monkeypatch):
    assert [vid for _, vid, _ in run_backlog(m, backlog_env, processed={"v14"})] == ["v17", "v18"]
    monkeypatch.setenv("BACKLOG_FORCE", "true")
    assert [vid for _, vid, _ in run_backlog(m, backlog_env, processed={"v14"})] == ["v14", "v17", "v18"]


def test_backlog_skips_existing_large_summary(m, backlog_env, monkeypatch):
    out = Path(backlog_env.summary_save_dir)
    out.mkdir(parents=True)
    (out / "2026-07-14_v14.md").write_text("가" * 500, encoding="utf-8")   # 400바이트 넘음 → 건너뜀
    (out / "2026-07-17_v17.md").write_text("짧음", encoding="utf-8")       # 짧으면 다시 만듦
    assert [vid for _, vid, _ in run_backlog(m, backlog_env)] == ["v17", "v18"]
    monkeypatch.setenv("BACKLOG_SKIP_EXISTING_SUMMARY", "false")
    assert [vid for _, vid, _ in run_backlog(m, backlog_env)] == ["v14", "v17", "v18"]


def test_backlog_resolves_unmarked_stream_title_by_metadata(m, monkeypatch, tmp_path):
    monkeypatch.delenv("BACKLOG_FORCE", raising=False)
    monkeypatch.delenv("BACKLOG_SKIP_EXISTING_SUMMARY", raising=False)
    monkeypatch.setattr(
        m, "_fetch_flat_playlist",
        lambda s, suffix, limit=20: [{"id": "ve", "title": "English only title"}] if suffix == "/streams" else [],
    )
    monkeypatch.setattr(
        m, "_fetch_video_metadata",
        lambda s, vid: {"title": "Chesley Morning Brief", "upload_date": "20260715"},
    )
    s = make_settings(m, summary_save_dir=str(tmp_path / "s"))
    result = run_backlog(m, s)
    assert [(d.isoformat(), vid) for d, vid, _ in result] == [("2026-07-15", "ve")]


# ── 요약 저장 · 자막(VTT) 정리 ─────────────────────────────────

def test_save_summary_file_writes_header_and_cleans_noise(m, tmp_path):
    s = make_settings(m, summary_save_dir=str(tmp_path / "out"))
    path = m.save_summary_file(s, datetime.date(2026, 7, 16), "vid123", "제목", "Gemini said\n\n본문 내용")
    assert os.path.basename(path) == "2026-07-16_vid123.md"
    text = Path(path).read_text(encoding="utf-8")
    assert text.startswith("# 제목\n")
    assert "- video_id: vid123" in text
    assert "- url: https://www.youtube.com/watch?v=vid123" in text
    assert "Gemini said" not in text and text.rstrip().endswith("본문 내용")


def test_save_summary_file_without_noise_keeps_body(m, tmp_path):
    s = make_settings(m, summary_save_dir=str(tmp_path))
    path = m.save_summary_file(s, datetime.date(2026, 7, 16), "v", "T", "  첫 줄\n둘째 줄  ")
    assert Path(path).read_text(encoding="utf-8").endswith("첫 줄\n둘째 줄\n")


def test_vtt_to_text(m, tmp_path):
    vtt = tmp_path / "a.vtt"
    vtt.write_text(
        "WEBVTT\nKind: captions\nLanguage: ko\n\nNOTE 메모\n\n1\n"
        "00:00:01.000 --> 00:00:03.000\n<00:00:01.500><c>안녕하세요</c> 여러분\n\n"
        "2\n00:00:03.000 --> 00:00:05.000\n안녕하세요 여러분\n\n"
        "00:00:05.000 --> 00:00:07.000\n오늘 시황입니다\n",
        encoding="utf-8",
    )
    assert m._vtt_to_text(str(vtt)) == "안녕하세요 여러분 오늘 시황입니다"


def test_vtt_to_text_empty_file(m, tmp_path):
    vtt = tmp_path / "e.vtt"
    vtt.write_text("WEBVTT\n", encoding="utf-8")
    assert m._vtt_to_text(str(vtt)) == ""


def test_vtt_to_text_keeps_repeated_real_speech(m, tmp_path):
    # ISSUE-001 해결: 떨어져서 되풀이된 말은 남긴다.
    vtt = tmp_path / "r.vtt"
    vtt.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n네\n\n00:00:03.000 --> 00:00:04.000\n좋습니다\n\n"
        "00:00:05.000 --> 00:00:06.000\n네\n", encoding="utf-8")
    assert m._vtt_to_text(str(vtt)) == "네 좋습니다 네"


def test_vtt_to_text_rolling_auto_caption_overlap_still_collapsed(m, tmp_path):
    # 자동 자막: 앞 큐의 둘째 줄이 다음 큐의 첫째 줄로 겹쳐 나온다 → 한 번만 남는다.
    vtt = tmp_path / "roll.vtt"
    vtt.write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n안녕하세요\n오늘은\n\n"
        "00:00:03.000 --> 00:00:05.000\n오늘은\n시황입니다\n\n"
        "00:00:05.000 --> 00:00:07.000\n시황입니다\n마칩니다\n", encoding="utf-8")
    assert m._vtt_to_text(str(vtt)) == "안녕하세요 오늘은 시황입니다 마칩니다"


# ── Gemini 응답 검사 · 프롬프트 ────────────────────────────────

def test_validate_gemini_response_ok(m):
    m.validate_gemini_response("정상적인 긴 요약 " * 100, 400)


def test_validate_gemini_response_login_wall(m):
    with pytest.raises(m.GeminiLoginRequired):
        m.validate_gemini_response("로그인하여 계속하세요", 10)
    with pytest.raises(m.GeminiLoginRequired):
        m.validate_gemini_response("   ", 10)


def test_validate_gemini_response_too_short(m):
    with pytest.raises(RuntimeError) as e:
        m.validate_gemini_response("짧은 요약입니다", 400)
    assert "too short" in str(e.value)


def test_build_gem_prompt(m):
    assert m.build_gem_prompt("원문", "제목", False) == "원문"
    prompt = m.build_gem_prompt("원문 스크립트", "7월 16일 브리프", True)
    assert "7월 16일 브리프" in prompt and prompt.endswith("원문 스크립트")
    assert prompt.startswith("[긴급 지시사항")


# ── gemini_session ─────────────────────────────────────────────

def test_resolve_data_path(tmp_path):
    base = str(tmp_path)
    assert gs.resolve_data_path("./a/../b.json", base) == os.path.normpath(os.path.join(base, "b.json"))
    absolute = str(tmp_path / "abs.json")
    assert gs.resolve_data_path(absolute, "/다른/곳") == os.path.normpath(absolute)


def test_extract_gem_id():
    assert gs.extract_gem_id("https://gemini.google.com/gem/abc123") == "abc123"
    assert gs.extract_gem_id("https://gemini.google.com/gem/abc123/") == "abc123"


@pytest.mark.parametrize("url, expected", [
    ("https://accounts.google.com/v3/signin/identifier", True),
    ("https://accounts.google.com/ServiceLogin?x=1", True),
    ("https://gemini.google.com/gem/abc123", False),
    ("https://gemini.google.com/app", False),
])
def test_is_google_login_url(url, expected):
    assert gs.is_google_login_url(url) is expected


@pytest.mark.parametrize("text", [
    "Sign in to continue", "계정에 로그인", "로그인하여 계속", "see accounts.google.com", "", "   ",
])
def test_looks_like_login_wall_text_true(text):
    assert gs.looks_like_login_wall_text(text) is True


def test_looks_like_login_wall_text_false_for_normal_summary():
    assert gs.looks_like_login_wall_text("## 오늘의 시황\n코스피는 상승 마감했습니다.") is False


@pytest.mark.parametrize("text", [
    "오늘 영상은 은행 앱 로그인 보안 이슈와 시장 영향을 정리합니다. " * 10,
    "The catalog in stock rose sharply. " * 10,
])
def test_looks_like_login_wall_text_normal_long_summary_is_not_wall(text):
    # ISSUE-002 해결: 긴 글은 정상 요약으로 본다.
    assert gs.looks_like_login_wall_text(text) is False


def test_looks_like_login_wall_text_short_catalog_in_is_not_wall():
    # 낱말 경계: 'catalog in' 안의 'log in' 에는 걸리지 않는다.
    assert gs.looks_like_login_wall_text("The catalog in stock rose.") is False


@pytest.mark.parametrize("text", ["Please Log in to continue", "SIGN IN", "계정에 로그인하세요"])
def test_looks_like_login_wall_text_short_wall_still_detected(text):
    assert gs.looks_like_login_wall_text(text) is True


def test_login_wall_max_chars_boundary():
    at_limit = "로그인" + "가" * (gs.LOGIN_WALL_MAX_CHARS - 3)
    over_limit = at_limit + "가"
    assert gs.looks_like_login_wall_text(at_limit) is True
    assert gs.looks_like_login_wall_text(over_limit) is False


# ── 디스코드·카카오 보내기(requests.post 는 가짜) ───────────────

class FakeResp:
    def __init__(self, status_code=204, text=""):
        self.status_code, self.text = status_code, text


@pytest.fixture
def posts(m, monkeypatch):
    calls = []
    codes = {"seq": []}

    def fake_post(url, **kw):
        calls.append({"url": url, **kw})
        code = codes["seq"].pop(0) if codes["seq"] else 204
        return FakeResp(code)

    monkeypatch.setattr(m.requests, "post", fake_post)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    return types.SimpleNamespace(calls=calls, codes=codes)


def test_request_verify_ssl(m):
    assert m._request_verify_ssl(make_settings(m, disable_ssl_verify=True)) is False
    assert m._request_verify_ssl(make_settings(m, disable_ssl_verify=False)) is True


def test_send_discord_single_message_has_no_prefix(m, posts):
    s = make_settings(m, discord_webhook="https://discord.example/webhook/fake", discord_max_message_length=100)
    m.send_discord_message(s, "짧은 메시지")
    assert len(posts.calls) == 1
    assert json.loads(posts.calls[0]["data"].decode("utf-8")) == {"content": "짧은 메시지"}


def test_send_discord_long_message_is_numbered_and_within_2000(m, posts):
    s = make_settings(m, discord_webhook="https://discord.example/webhook/fake", discord_max_message_length=1900)
    text = ("가나다 " * 700).strip()   # 약 2,799자
    m.send_discord_message(s, text)
    contents = [json.loads(c["data"].decode("utf-8"))["content"] for c in posts.calls]
    assert len(contents) == 2
    assert contents[0].startswith("**[1/2]**\n") and contents[1].startswith("**[2/2]**\n")
    assert all(len(c) <= 2000 for c in contents)


def test_send_discord_stops_on_error_status(m, posts):
    posts.codes["seq"] = [500]
    s = make_settings(m, discord_webhook="https://discord.example/webhook/fake", discord_max_message_length=50)
    resp = m.send_discord_message(s, "가 " * 100)
    assert resp.status_code == 500 and len(posts.calls) == 1


def test_send_discord_bot_message_headers_and_stop(m, posts):
    posts.codes["seq"] = [200, 403]
    s = make_settings(m, discord_bot_token="BOT_FAKE", discord_channel_id="123", discord_max_message_length=50)
    resp = m.send_discord_bot_message(s, "가 " * 100)
    assert resp.status_code == 403 and len(posts.calls) == 2
    assert posts.calls[0]["url"].endswith("/channels/123/messages")
    assert posts.calls[0]["headers"]["Authorization"] == "Bot BOT_FAKE"
    assert posts.calls[0]["json"]["content"].startswith("**[1/")


def test_send_kakao_message_truncates_to_max_length(m, posts):
    m.send_kakao_message(make_settings(m), "TOKEN_FAKE", "가" * 50, 10)
    call = posts.calls[0]
    assert call["headers"]["Authorization"] == "Bearer TOKEN_FAKE"
    template = json.loads(call["data"]["template_object"])
    assert template["text"] == "가" * 10 and template["object_type"] == "text"


def test_send_kakao_with_refresh_retries_once_on_401(m, posts, monkeypatch):
    posts.codes["seq"] = [401, 200]
    refreshed = []
    monkeypatch.setattr(m, "get_kakao_access_token", lambda s: "OLD")
    monkeypatch.setattr(m, "refresh_kakao_access_token", lambda s: refreshed.append(1) or "NEW")
    s = make_settings(m, kakao_rest_api_key="REST_FAKE", max_message_length=100)
    resp = m.send_kakao_message_with_refresh(s, "안녕")
    assert resp.status_code == 200 and refreshed == [1]
    assert [c["headers"]["Authorization"] for c in posts.calls] == ["Bearer OLD", "Bearer NEW"]


def test_send_kakao_with_refresh_no_retry_without_rest_key(m, posts, monkeypatch):
    posts.codes["seq"] = [401]
    monkeypatch.setattr(m, "get_kakao_access_token", lambda s: "OLD")
    monkeypatch.setattr(m, "refresh_kakao_access_token", lambda s: pytest.fail("갱신하면 안 됨"))
    resp = m.send_kakao_message_with_refresh(make_settings(m, max_message_length=100), "안녕")
    assert resp.status_code == 401 and len(posts.calls) == 1


def test_get_kakao_access_token_prefers_settings_token(m, monkeypatch):
    monkeypatch.setattr(m, "refresh_kakao_access_token", lambda s: "FROM_FILE")
    assert m.get_kakao_access_token(make_settings(m, kakao_token="TOK")) == "TOK"
    assert m.get_kakao_access_token(make_settings(m, kakao_token="")) == "FROM_FILE"


def test_send_notification_dispatch(m, monkeypatch):
    sent = []
    monkeypatch.setattr(m, "send_discord_message", lambda s, msg: sent.append("discord") or "r1")
    monkeypatch.setattr(m, "send_discord_bot_message", lambda s, msg: sent.append("bot") or "r2")
    monkeypatch.setattr(m, "send_kakao_message_with_refresh", lambda s, msg: sent.append("kakao") or "r3")
    assert m.send_notification(make_settings(m, send_target="discord", discord_webhook="https://x"), "a") == "r1"
    assert m.send_notification(make_settings(m, send_target="discord_bot"), "a") == "r2"
    assert m.send_notification(make_settings(m, send_target="kakao"), "a") == "r3"
    assert sent == ["discord", "bot", "kakao"]


def test_send_notification_discord_without_webhook_skips(m, monkeypatch, capsys):
    monkeypatch.setattr(m, "send_discord_message", lambda s, msg: pytest.fail("보내면 안 됨"))
    resp = m.send_notification(make_settings(m, send_target="discord", discord_webhook=""), "a")
    assert resp.status_code == 204
    assert "skipping" in capsys.readouterr().out


# ── load_settings ──────────────────────────────────────────────

SETTING_KEYS = [
    "CHANNEL_URL", "TITLE_PREFIX", "GEMINI_GEM_URL", "SEND_TARGET", "DISCORD_WEBHOOK",
    "DISCORD_BOT_TOKEN", "DISCORD_CHANNEL_ID", "KAKAO_TOKEN", "KAKAO_REST_API_KEY",
    "KAKAO_REDIRECT_URI", "KAKAO_TOKEN_FILE", "PROCESSED_FILE", "RUN_TIME", "PLAYWRIGHT_PROFILE_DIR",
    "GEMINI_STORAGE_STATE_FILE", "SUMMARY_SAVE_DIR", "BACKLOG_SAVE_ONLY", "AUTO_LOGIN_WAIT_SEC",
    "HEADLESS", "TRANSCRIPT_LANGS", "RESPONSE_TIMEOUT_MS", "KAKAO_MAX_MESSAGE_LENGTH",
    "TRANSCRIPT_RETRY_INTERVAL_SEC", "TRANSCRIPT_MAX_TRIES", "GEMINI_INPUT_MAX_CHARS", "ONLY_WEEKDAYS",
    "YT_NO_CHECK_CERTIFICATES", "DISABLE_SSL_VERIFY", "GEMINI_DEBUG_HOLD_MS", "GEMINI_FORCE_PRO",
    "GEMINI_USE_GEM_PROMPT", "GEMINI_GEM_EXPECTED_NAME", "GEMINI_MIN_RESPONSE_CHARS",
    "DISCORD_MAX_MESSAGE_LENGTH",
]


@pytest.fixture
def clean_env(m, monkeypatch):
    """중앙 .env 를 읽지 않게 하고, 설정 관련 환경변수를 모두 비운다."""
    monkeypatch.setattr(m, "load_env", lambda *a, **k: None)
    for k in SETTING_KEYS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("CHANNEL_URL", "https://www.youtube.com/@fake")
    monkeypatch.setenv("GEMINI_GEM_URL", "https://gemini.google.com/gem/abc123?hl=ko")
    monkeypatch.setenv("DISCORD_WEBHOOK", "https://discord.example/webhook/fake")


def test_load_settings_defaults(m, clean_env):
    s = m.load_settings()
    assert s.send_target == "discord"
    assert s.gemini_gem_url == "https://gemini.google.com/gem/abc123"   # ?뒤 제거
    assert s.run_time == "16:00" and s.language_priority == ["ko", "en"]
    assert s.max_message_length == 1000 and s.discord_max_message_length == 1900
    assert s.headless is False and s.only_weekdays is True and s.gemini_force_pro is True
    assert s.kakao_redirect_uri == "https://example.com"


def test_load_settings_paths_resolved_under_script_dir(m, clean_env):
    s = m.load_settings()
    assert os.path.isabs(s.processed_file) and os.path.isabs(s.summary_save_dir) and os.path.isabs(s.profile_dir)
    assert os.path.basename(s.processed_file) == "processed.json"
    assert os.path.dirname(s.processed_file) == os.path.normpath(m.SCRIPT_DIR)


def test_load_settings_parses_languages_and_lowercases_target(m, clean_env, monkeypatch):
    monkeypatch.setenv("TRANSCRIPT_LANGS", "ko, en ,,ja")
    monkeypatch.setenv("SEND_TARGET", "DISCORD")
    s = m.load_settings()
    assert s.language_priority == ["ko", "en", "ja"] and s.send_target == "discord"


@pytest.mark.parametrize("missing", ["CHANNEL_URL", "GEMINI_GEM_URL"])
def test_load_settings_requires_channel_and_gem(m, clean_env, monkeypatch, missing):
    monkeypatch.delenv(missing)
    with pytest.raises(ValueError, match=missing):
        m.load_settings()


def test_load_settings_discord_requires_webhook_unless_save_only(m, clean_env, monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK")
    with pytest.raises(ValueError, match="DISCORD_WEBHOOK"):
        m.load_settings()
    monkeypatch.setenv("BACKLOG_SAVE_ONLY", "true")
    assert m.load_settings().discord_webhook == ""


def test_load_settings_discord_bot_and_kakao_requirements(m, clean_env, monkeypatch):
    monkeypatch.setenv("SEND_TARGET", "discord_bot")
    with pytest.raises(ValueError, match="DISCORD_BOT_TOKEN"):
        m.load_settings()
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "BOT_FAKE")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "123")
    assert m.load_settings().discord_channel_id == "123"
    monkeypatch.setenv("SEND_TARGET", "kakao")
    with pytest.raises(ValueError, match="KAKAO"):
        m.load_settings()
    monkeypatch.setenv("KAKAO_REST_API_KEY", "REST_FAKE")
    assert m.load_settings().send_target == "kakao"
