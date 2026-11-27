"""옛 진도 서버(teacherlesson-schedule)를 쓸 때, 그 서버의 JSON 오류 문장이 수업 비서 화면까지 그대로 가는지 (T100 ②, ISSUE-005).

진도 서버가 `ScheduleError` 를 `{"status":"error","message":…}` + HTTP 500 으로 돌려주면,
`assistant_server.progress()` 는 그 JSON 을 그대로 넘기고(화면 쪽은 `j.message` 를 토스트로 보여 준다),
JSON 이 아닌 오류 화면이면 "진도 서버 오류 <코드>" 로 바꾼다. 네트워크·서버 없이 urlopen 을 가짜로 바꿔 돈다.
"""
import io
import json
import pathlib
import sys
import urllib.error
from unittest.mock import patch

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import assistant_server as app  # noqa: E402


@pytest.fixture(autouse=True)
def legacy_backend(monkeypatch):
    monkeypatch.setattr(app, "load_config", lambda: {"schedule_backend": "legacy", "schedule_api": "http://127.0.0.1:5000"})


def http_error(code, body: bytes):
    return urllib.error.HTTPError("http://127.0.0.1:5000/api/x", code, "err", {}, io.BytesIO(body))


@pytest.mark.parametrize("action", ["done", "extend", "push", "catch-up"])
def test_json_error_message_from_schedule_server_is_passed_through(action):
    body = json.dumps({"status": "error", "message": "진도표 머리글이 맞지 않습니다."}, ensure_ascii=False).encode("utf-8")
    with patch.object(app.urllib.request, "urlopen", side_effect=http_error(500, body)):
        result = app.progress(action, {"subject": "수학"})
    assert result == {"status": "error", "message": "진도표 머리글이 맞지 않습니다."}


def test_non_json_error_page_becomes_a_short_korean_message():
    with patch.object(app.urllib.request, "urlopen", side_effect=http_error(500, b"<html>Internal Server Error</html>")):
        result = app.progress("push", {"subject": "수학"})
    assert result == {"status": "error", "message": "진도 서버 오류 500"}


def test_server_down_message():
    with patch.object(app.urllib.request, "urlopen", side_effect=urllib.error.URLError("refused")):
        result = app.progress("done", {"subject": "수학"})
    assert result["status"] == "error" and "꺼져" in result["message"]
