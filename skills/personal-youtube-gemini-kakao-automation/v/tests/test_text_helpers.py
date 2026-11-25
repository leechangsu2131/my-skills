from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import main


def test_vtt_to_text_removes_timestamps_tags_and_duplicate_cues(tmp_path):
    source = tmp_path / "sample.vtt"
    source.write_text(
        """WEBVTT

Kind: captions
Language: ko

1
00:00:01.000 --> 00:00:02.000 align:start
<c>첫 번째 문장</c>

2
00:00:02.000 --> 00:00:03.000
첫 번째 문장

3
00:00:03.000 --> 00:00:04.000
<00:00:03.000><c>두 번째 문장</c>
""",
        encoding="utf-8",
    )

    assert main._vtt_to_text(str(source)) == "첫 번째 문장 두 번째 문장"


def test_vtt_to_text_returns_empty_for_metadata_only_file(tmp_path):
    source = tmp_path / "metadata.vtt"
    source.write_text(
        "WEBVTT\n\nKind: captions\nLanguage: ko\n00:00:00.000 --> 00:00:01.000\n",
        encoding="utf-8",
    )

    assert main._vtt_to_text(str(source)) == ""


def test_split_message_chunks_respects_limit_and_keeps_words():
    message = "첫 문단입니다 여기까지.\n\n두 번째 문단입니다.\n세 번째 문장입니다."
    chunks = main.split_message_chunks(message, 16)

    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 16 for chunk in chunks)
    assert " ".join(chunks).split() == message.replace("\n", " ").split()


def test_split_message_chunks_handles_empty_and_short_messages():
    assert main.split_message_chunks("   ", 20) == [""]
    assert main.split_message_chunks("짧은 메시지", 20) == ["짧은 메시지"]


def test_build_gem_prompt_keeps_full_transcript_and_title():
    transcript = "첫 문장입니다. 두 번째 문장입니다."

    prompt = main.build_gem_prompt(transcript, "오늘의 수업", True)

    assert "오늘의 수업" in prompt
    assert transcript in prompt
    assert "절대 짧게 요약하지 마세요" in prompt
    assert main.build_gem_prompt(transcript, "오늘의 수업", False) == transcript


def test_validate_gemini_response_uses_fake_login_detector(monkeypatch):
    monkeypatch.setattr(main, "looks_like_login_wall_text", lambda text: False)
    main.validate_gemini_response("충분히 긴 가짜 응답입니다.", 5)

    monkeypatch.setattr(main, "looks_like_login_wall_text", lambda text: True)
    with pytest.raises(main.GeminiLoginRequired):
        main.validate_gemini_response("로그인 화면", 5)


def test_validate_gemini_response_rejects_short_response(monkeypatch):
    monkeypatch.setattr(main, "looks_like_login_wall_text", lambda text: False)

    with pytest.raises(RuntimeError, match="too short"):
        main.validate_gemini_response("짧음", 10)


def test_kakao_message_uses_fake_http_and_utf8_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        text = "ok"

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(main.requests, "post", fake_post)
    settings = SimpleNamespace(disable_ssl_verify=False)

    response = main.send_kakao_message(
        settings,
        token="fake-kakao-token",
        message="가나다라마바사",
        max_length=4,
    )

    payload = json.loads(captured["data"]["template_object"])
    assert response.status_code == 200
    assert captured["url"].endswith("/v2/api/talk/memo/default/send")
    assert captured["headers"]["Authorization"] == "Bearer fake-kakao-token"
    assert payload["text"] == "가나다"
    assert captured["verify"] is True


def test_discord_message_sends_chunks_through_fake_transport(monkeypatch):
    sent = []

    class FakeResponse:
        status_code = 204
        text = ""

    def fake_post(settings, content):
        sent.append(content)
        return FakeResponse()

    monkeypatch.setattr(main, "_discord_post_content", fake_post)
    monkeypatch.setattr(main.time, "sleep", lambda _seconds: None)
    settings = SimpleNamespace(discord_max_message_length=12)

    response = main.send_discord_message(settings, "첫 번째 문장입니다. 두 번째 문장입니다.")

    assert response.status_code == 204
    assert len(sent) > 1
    assert all(len(chunk) <= 2000 for chunk in sent)
    assert sent[0].startswith("**[1/")
    assert sent[-1].startswith(f"**[{len(sent)}/{len(sent)}]**")
