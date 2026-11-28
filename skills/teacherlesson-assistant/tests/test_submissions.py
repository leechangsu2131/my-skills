"""✅ 제출 확인표(T108) 시험 — submissions.py 와 assistant_server 의 /api/submissions 처리.

    python -m pytest tests/test_submissions.py -v      (teacherlesson-assistant 폴더에서)

가짜 명단('학생A' 같은 예시)과 임시 폴더만 쓴다. 진짜 데이터 폴더·네트워크는 쓰지 않는다.
"""
import json
import pathlib
import sys
from datetime import date

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import assistant_server as app  # noqa: E402
import submissions as sub  # noqa: E402

D = date(2026, 11, 28)


@pytest.fixture
def base(tmp_path):
    return tmp_path / "submissions"


def test_create_then_load(base):
    rec = sub.create(base, "현장학습 동의서", 5)
    assert rec == {"title": "현장학습 동의서", "total": 5, "marks": {}}
    assert sub.load(base, "현장학습 동의서") == rec


def test_create_refuses_to_overwrite(base):
    sub.create(base, "동의서", 5)
    sub.mark(base, "동의서", 2, today=D)
    with pytest.raises(ValueError, match="이미"):
        sub.create(base, "동의서", 9)
    assert sub.load(base, "동의서")["total"] == 5
    assert sub.load(base, "동의서")["marks"] == {"2": "2026-11-28"}


@pytest.mark.parametrize("title", ["", "   ", "///", None])
def test_blank_title_rejected(base, title):
    with pytest.raises(ValueError, match="제목"):
        sub.create(base, title, 5)


@pytest.mark.parametrize("total", [0, -1, 61, "abc", None])
def test_total_range(base, total):
    with pytest.raises(ValueError, match="반 인원"):
        sub.create(base, "t", total)


def test_total_bounds_allowed(base):
    assert sub.create(base, "a", 1)["total"] == 1
    assert sub.create(base, "b", sub.MAX_TOTAL)["total"] == 60


def test_title_cannot_escape_folder(base, tmp_path):
    sub.create(base, "../../evil", 3)
    assert not (tmp_path / "evil.json").exists()
    assert [p.parent for p in base.glob("*.json")] == [base]


def test_mark_records_first_date_only(base):
    sub.create(base, "t", 5)
    sub.mark(base, "t", 3, today=D)
    rec = sub.mark(base, "t", "3", today=date(2026, 12, 1))
    assert rec["marks"] == {"3": "2026-11-28"}


def test_unmark(base):
    sub.create(base, "t", 5)
    sub.mark(base, "t", 3, today=D)
    assert sub.mark(base, "t", 3, done=False)["marks"] == {}
    assert sub.mark(base, "t", 4, done=False)["marks"] == {}


@pytest.mark.parametrize("no", [0, 6, -1, "x", None])
def test_mark_number_out_of_range(base, no):
    sub.create(base, "t", 5)
    with pytest.raises(ValueError):
        sub.mark(base, "t", no)
    assert sub.load(base, "t")["marks"] == {}


def test_mark_unknown_sheet(base):
    with pytest.raises(ValueError, match="찾을 수"):
        sub.mark(base, "없음", 1)


def test_missing_and_text(base):
    sub.create(base, "동의서", 6)
    for n in (1, 2, 4):
        sub.mark(base, "동의서", n, today=D)
    rec = sub.load(base, "동의서")
    assert sub.missing(rec) == [3, 5, 6]
    assert sub.missing_text(rec) == "동의서 아직 안 낸 번호: 3, 5, 6번"
    assert sub.summarize(rec) == {"title": "동의서", "total": 6, "done": 3, "missing": [3, 5, 6]}


def test_missing_text_when_all_done(base):
    sub.create(base, "t", 2)
    sub.mark(base, "t", 1, today=D)
    sub.mark(base, "t", 2, today=D)
    assert sub.missing_text(sub.load(base, "t")) == "t: 모두 냈어요."


def test_list_all_newest_first_and_skips_broken(base):
    sub.create(base, "a", 3)
    sub.create(base, "b", 3)
    (base / "broken.json").write_text("{not json", encoding="utf-8")
    (base / "wrong.json").write_text(json.dumps({"x": 1}), encoding="utf-8")
    import os
    os.utime(base / "a.json", (1000, 1000))
    assert [i["title"] for i in sub.list_all(base)] == ["b", "a"]


def test_list_all_missing_folder(tmp_path):
    assert sub.list_all(tmp_path / "none") == []


def test_roster_formats(tmp_path):
    f = tmp_path / "roster.txt"
    f.write_text("# 가짜 명단\n학생A\n\n학생B\n5 학생C\n6. 학생D\n", encoding="utf-8")
    assert sub.load_roster(f) == {1: "학생A", 2: "학생B", 5: "학생C", 6: "학생D"}


def test_roster_missing_file(tmp_path):
    assert sub.load_roster(tmp_path / "nope.txt") == {}


# ── 서버 연결 ──
@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "SUBMISSIONS", tmp_path / "submissions")
    monkeypatch.setattr(app, "ROSTER_PATH", tmp_path / "roster.txt")
    monkeypatch.setattr(app, "load_config", lambda: {"class_size": 4})
    return tmp_path


def test_server_create_mark_get(server):
    out = app.submissions_post({"action": "create", "title": "동의서"})  # 반 인원은 config 의 class_size
    assert out["record"]["total"] == 4
    out = app.submissions_post({"action": "mark", "title": "동의서", "no": 2})
    assert out["record"]["marks"].keys() == {"2"}
    assert out["missing"] == [1, 3, 4]
    assert out["missing_text"] == "동의서 아직 안 낸 번호: 1, 3, 4번"
    out = app.submissions_post({"action": "mark", "title": "동의서", "no": 2, "done": False})
    assert out["missing"] == [1, 2, 3, 4]


def test_server_list_has_class_size(server):
    app.submissions_post({"action": "create", "title": "a", "total": 3})
    out = app.submissions_get()
    assert out["class_size"] == 4
    assert [i["title"] for i in out["items"]] == ["a"]


def test_server_roster_only_when_file_exists(server):
    app.submissions_post({"action": "create", "title": "a", "total": 3})
    assert app.submissions_get("a")["roster"] == {}
    (server / "roster.txt").write_text("학생A\n학생B\n", encoding="utf-8")
    assert app.submissions_get("a")["roster"] == {"1": "학생A", "2": "학생B"}


def test_server_names_not_in_list_missing_text_or_errors(server):
    (server / "roster.txt").write_text("학생A\n학생B\n학생C\n", encoding="utf-8")
    app.submissions_post({"action": "create", "title": "a", "total": 3})
    assert "학생" not in json.dumps(app.submissions_get(), ensure_ascii=False)
    assert "학생" not in app.submissions_get("a")["missing_text"]
    with pytest.raises(ValueError) as e:
        app.submissions_post({"action": "mark", "title": "a", "no": 99})
    assert "학생" not in str(e.value)


def test_server_unknown_action_and_missing_sheet(server):
    with pytest.raises(ValueError):
        app.submissions_post({"action": "delete", "title": "a"})
    with pytest.raises(ValueError):
        app.submissions_get("없음")
