"""받아쓰기 사전 화면용 저장·읽기(T111 ③) 시험 — assistant_server.stt_words_get / stt_words_save.

    python -m pytest tests/test_stt_words_api.py -v      (teacherlesson-assistant 폴더에서)

가짜 낱말과 임시 폴더만 쓴다. 저장한 파일은 transcribe.load_words 로 다시 읽어 받아쓰기가 쓰는 모양과 같은지 본다.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import assistant_server as app  # noqa: E402
import transcribe  # noqa: E402


@pytest.fixture
def path(tmp_path, monkeypatch):
    p = tmp_path / "stt_words.json"
    monkeypatch.setattr(app, "STT_WORDS_PATH", p)
    return p


def test_get_when_no_file(path):
    assert app.stt_words_get() == {"status": "success", "words": [], "fixes": {}, "notes": []}


def test_save_then_get_roundtrip_and_transcribe_reads_it(path):
    out = app.stt_words_save({"words": ["알림장", "학생A"], "fixes": {"알림 장": "알림장", "학생에이": "학생A"}})
    assert out["status"] == "success" and "2개" in out["message"]
    assert json.loads(path.read_text(encoding="utf-8")) == {"자주 쓰는 말": ["알림장", "학생A"], "고쳐 쓰기": {"알림 장": "알림장", "학생에이": "학생A"}}
    assert transcribe.load_words(path) == (["알림장", "학생A"], {"알림 장": "알림장", "학생에이": "학생A"})
    got = app.stt_words_get()
    assert got["words"] == ["알림장", "학생A"] and got["fixes"]["학생에이"] == "학생A"


def test_save_cleans_blank_duplicate_and_same_pairs(path):
    out = app.stt_words_save({"words": [" 가 ", "가", "", 3, None, "나"], "fixes": {" 가 ": " 나 ", "": "x", "같음": "같음", "다": 5}})
    assert out["words"] == ["가", "나"]
    assert out["fixes"] == {"가": "나"}


def test_empty_save_clears_dictionary(path):
    app.stt_words_save({"words": ["가"], "fixes": {"나": "다"}})
    app.stt_words_save({"words": [], "fixes": {}})
    assert transcribe.load_words(path) == ([], {})


@pytest.mark.parametrize("body", [{}, {"words": "가", "fixes": {}}, {"words": [], "fixes": []}, {"words": None, "fixes": None}])
def test_bad_shape_rejected_and_file_untouched(path, body):
    app.stt_words_save({"words": ["원래"], "fixes": {}})
    before = path.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="모양"):
        app.stt_words_save(body)
    assert path.read_text(encoding="utf-8") == before


def test_count_limits(path):
    with pytest.raises(ValueError, match="개까지"):
        app.stt_words_save({"words": [f"w{i}" for i in range(app.STT_MAX_WORDS + 1)], "fixes": {}})
    with pytest.raises(ValueError, match="개까지"):
        app.stt_words_save({"words": [], "fixes": {f"k{i}": "v" for i in range(app.STT_MAX_FIXES + 1)}})
    assert not path.exists()


def test_exact_limits_allowed(path):
    out = app.stt_words_save({"words": [f"w{i}" for i in range(app.STT_MAX_WORDS)], "fixes": {f"k{i}": "v" for i in range(app.STT_MAX_FIXES)}})
    assert len(out["words"]) == app.STT_MAX_WORDS and len(out["fixes"]) == app.STT_MAX_FIXES


def test_length_limit(path):
    with pytest.raises(ValueError, match="글자"):
        app.stt_words_save({"words": ["가" * (app.STT_MAX_LEN + 1)], "fixes": {}})
    with pytest.raises(ValueError, match="글자"):
        app.stt_words_save({"words": [], "fixes": {"가": "나" * (app.STT_MAX_LEN + 1)}})
    app.stt_words_save({"words": ["가" * app.STT_MAX_LEN], "fixes": {}})


def test_long_word_list_warns_hint_is_cut(path):
    words = [f"긴낱말{i:03d}" * 2 for i in range(40)]
    out = app.stt_words_save({"words": words, "fixes": {}})
    assert "앞쪽만" in out["message"]
    assert "앞쪽만" not in app.stt_words_save({"words": ["가"], "fixes": {}})["message"]


def test_get_reports_broken_parts_as_notes(path):
    path.write_text(json.dumps({"자주 쓰는 말": "가나", "고쳐 쓰기": {"가": "나"}}, ensure_ascii=False), encoding="utf-8")
    got = app.stt_words_get()
    assert got["words"] == [] and got["fixes"] == {"가": "나"}
    assert got["notes"] and "자주 쓰는 말" in got["notes"][0]


def test_get_when_file_is_not_json(path):
    path.write_text("{깨짐", encoding="utf-8")
    got = app.stt_words_get()
    assert got["words"] == [] and got["fixes"] == {} and got["notes"]


def test_html_and_server_wiring():
    skill = pathlib.Path(app.__file__).parent
    html = (skill / "web" / "index.html").read_text(encoding="utf-8")
    server = (skill / "assistant_server.py").read_text(encoding="utf-8")
    assert '<script src="/stt_words.js"></script>' in html and 'id="sttBox"' in html and 'id="sttSave"' in html
    assert 'url.path == "/stt_words.js"' in server and server.count('"/api/stt-words"') == 2
