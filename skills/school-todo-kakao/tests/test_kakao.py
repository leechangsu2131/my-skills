import json

import pytest

from schooltodo import kakao


class FakeResp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self.ok = status < 400
        self._body = body or {}

    def json(self):
        return self._body


def test_refresh_saves_rotated_refresh_token(monkeypatch, tmp_path):
    sent = {}

    def fake_post(url, data=None, headers=None, timeout=None):
        sent["data"] = data
        return FakeResp(200, {"access_token": "AT", "refresh_token": "NEW-RT"})

    monkeypatch.setattr(kakao.requests, "post", fake_post)
    f = tmp_path / "rt.txt"
    assert kakao.refresh_access_token("KEY", "OLD-RT", "SECRET", str(f)) == "AT"
    assert f.read_text() == "NEW-RT"
    assert sent["data"]["client_secret"] == "SECRET" and sent["data"]["grant_type"] == "refresh_token"


def test_refresh_without_rotation_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(kakao.requests, "post", lambda *a, **k: FakeResp(200, {"access_token": "AT"}))
    f = tmp_path / "rt.txt"
    kakao.refresh_access_token("KEY", "RT", "", str(f))
    assert not f.exists()


def test_expired_token_error_has_hint_and_no_secrets(monkeypatch):
    body = {"error": "invalid_grant", "error_code": "KOE322", "error_description": "expired_or_invalid_refresh_token"}
    monkeypatch.setattr(kakao.requests, "post", lambda *a, **k: FakeResp(400, body))
    with pytest.raises(kakao.KakaoError) as e:
        kakao.refresh_access_token("KEY", "SUPER-SECRET-RT")
    assert "KOE322" in str(e.value) and "SUPER-SECRET-RT" not in str(e.value)


def test_send_memo_builds_text_template(monkeypatch):
    seen = {}

    def fake_post(url, headers=None, data=None, timeout=None):
        seen.update(url=url, headers=headers, tpl=json.loads(data["template_object"]))
        return FakeResp(200, {"result_code": 0})

    monkeypatch.setattr(kakao.requests, "post", fake_post)
    kakao.send_memo("AT", "안녕", "https://example.com")
    assert seen["headers"]["Authorization"] == "Bearer AT"
    assert seen["tpl"]["object_type"] == "text" and seen["tpl"]["text"] == "안녕"
