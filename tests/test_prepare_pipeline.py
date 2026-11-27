"""skills/teacherlesson-assistant/prepare_lessons.py 의 준비 과정 시험 (S1): is_running · write_status · lesson_pdf ·
pdf_text_source · prepare_one · main.

parse_flow·parse_day·lesson_section 은 test_prepare_lessons.py, parse_plan 은 test_parse_plan.py 에 있다.
Gemini·진도 서버·Supabase·실제 PDF 는 쓰지 않는다: Gemini 는 미리 정한 답을 차례로 돌려주는 가짜,
지도서 PDF 는 가짜 바이트, 데이터 폴더(흐름·상태 파일)는 임시 폴더. 소스는 고치지 않는다.
"""
import json
import pathlib
import sys
import time
import urllib.error
from unittest import mock

import pytest

import prepare_lessons as pl

app = pl.app


# ──────────────────────────── 공통 도우미 ────────────────────────────

def plan_answer(**over):
    data = {"lesson_type": "토의", "goal": "생각을 나눈다", "materials": ["활동지"],
            "steps": [{"name": "도입", "minutes": 5, "purpose": "열기"},
                      {"name": "생각 모으기", "minutes": 10, "purpose": "모으기"},
                      {"name": "토의", "minutes": 20, "purpose": "나누기"},
                      {"name": "정리", "minutes": 5, "purpose": "닫기"}],
            "homework": "", "pages": "p.2-4"}
    data.update(over)
    return json.dumps(data, ensure_ascii=False)


def detail_answer(names=("도입", "생각 모으기", "토의", "정리"), **over):
    steps = [{"name": n, "teacher_actions": [f"{n} 안내"], "student_actions": [f"{n} 활동"],
              "teacher_prompts": [f"{n} 발문"], "expected_responses": ["예시 답"]} for n in names]
    data = {"steps": steps}
    data.update(over)
    return json.dumps(data, ensure_ascii=False)


class FakeGemini:
    """nlm.gemini_ask 대신: 답(또는 오류)을 차례로 돌려주고 호출을 기록한다."""

    def __init__(self, *answers, model="가짜모델"):
        self.answers = list(answers)
        self.model = model
        self.calls = []

    def __call__(self, pdf, prompt, model=None, timeout=None, work=None, model_timeout=None):
        self.calls.append({"pdf_name": pathlib.Path(pdf).name, "prompt": prompt, "model": model,
                           "model_timeout": model_timeout, "pdf_text": pathlib.Path(pdf).read_bytes()[:20]})
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer, self.model


LESSON = {"record_key": "lesson-0001", "subject": "국어", "unit": "", "lesson": "1", "title": "생각 나누기",
          "publisher": "가출판", "period": 2}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """흐름·상태 파일을 임시 폴더로, 지도서 PDF 는 가짜로."""
    monkeypatch.setattr(app, "FLOWS", tmp_path / "flows")
    monkeypatch.setattr(pl, "STATUS", tmp_path / "prepare_status.json")
    monkeypatch.setattr(app, "NOTEBOOKLM", tmp_path / "notebooklm")
    monkeypatch.setattr(pl, "lesson_pdf", lambda cfg, key, dest: dest.write_bytes(b"%PDF-1.4 fake") or True)
    monkeypatch.setattr(pl, "pdf_text_source", lambda pdf: "")
    return tmp_path


def use_gemini(monkeypatch, gemini):
    monkeypatch.setattr(pl.nlm, "gemini_ask", gemini)
    return gemini


# ──────────────────────────── is_running · pid_alive ────────────────────────────

def running_status(**over):
    base = {"running": True, "started_ts": time.time(), "pid": 4242}
    base.update(over)
    return base


def test_is_running_true_only_for_fresh_live_flagged_status(monkeypatch):
    monkeypatch.setattr(pl, "pid_alive", lambda pid: True)
    assert pl.is_running(running_status())


@pytest.mark.parametrize("status", [
    {}, {"running": False, "started_ts": time.time(), "pid": 1},
    {"started_ts": time.time(), "pid": 1},
])
def test_is_running_false_without_running_flag(monkeypatch, status):
    monkeypatch.setattr(pl, "pid_alive", lambda pid: True)
    assert not pl.is_running(status)


def test_is_running_false_when_older_than_30_minutes(monkeypatch):
    monkeypatch.setattr(pl, "pid_alive", lambda pid: True)
    assert pl.STALE_SECONDS == 30 * 60
    assert not pl.is_running(running_status(started_ts=time.time() - pl.STALE_SECONDS - 5))
    assert pl.is_running(running_status(started_ts=time.time() - pl.STALE_SECONDS + 60))


def test_is_running_false_when_process_is_gone(monkeypatch):
    monkeypatch.setattr(pl, "pid_alive", lambda pid: False)
    assert not pl.is_running(running_status())


def test_is_running_passes_the_saved_pid_and_defaults_to_zero(monkeypatch):
    seen = []
    monkeypatch.setattr(pl, "pid_alive", lambda pid: seen.append(pid) or True)
    pl.is_running(running_status(pid=77))
    pl.is_running({"running": True, "started_ts": time.time()})
    assert seen == [77, 0]


@pytest.mark.skipif(sys.platform == "win32", reason="윈도우에서는 진짜 프로세스 확인을 쓴다")
def test_pid_alive_assumes_alive_where_windows_api_is_missing():
    assert pl.pid_alive(12345) is True


# ──────────────────────────── write_status ────────────────────────────

def test_write_status_writes_json(env):
    pl.write_status({"date": "2026-11-27", "items": [{"subject": "국어"}]})
    assert json.loads(pl.STATUS.read_text(encoding="utf-8"))["items"][0]["subject"] == "국어"


def test_write_status_retries_after_permission_error(env, monkeypatch):
    sleeps = []
    monkeypatch.setattr(pl.time, "sleep", sleeps.append)
    real = app.write_json
    calls = {"n": 0}

    def flaky(path, value):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise PermissionError("읽는 중")
        real(path, value)
    monkeypatch.setattr(app, "write_json", flaky)
    pl.write_status({"ok": True})
    assert calls["n"] == 3
    assert sleeps == [0.2, 0.4]  # 기다리는 시간이 조금씩 늘어난다
    assert json.loads(pl.STATUS.read_text(encoding="utf-8")) == {"ok": True}


def test_write_status_gives_up_quietly_after_10_tries(env, monkeypatch):
    sleeps = []
    monkeypatch.setattr(pl.time, "sleep", sleeps.append)
    monkeypatch.setattr(app, "write_json", mock.Mock(side_effect=PermissionError("막힘")))
    pl.write_status({"ok": True})  # 예외 없이 끝난다(준비 작업 자체는 계속)
    assert app.write_json.call_count == 10
    assert len(sleeps) == 10


def test_write_status_does_not_swallow_other_errors(env, monkeypatch):
    monkeypatch.setattr(app, "write_json", mock.Mock(side_effect=ValueError("이상")))
    with pytest.raises(ValueError):
        pl.write_status({})


# ──────────────────────────── lesson_pdf ────────────────────────────

class FakeResponse:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_supabase(monkeypatch):
    """requests 가 없는 곳에서도 돌게 supabase_schedule 을 가짜 모듈로 바꾼다(자동 검사 repo-root 칸)."""
    fake = mock.Mock()
    monkeypatch.setitem(sys.modules, "supabase_schedule", fake)
    return fake


def test_lesson_pdf_from_supabase_writes_the_pdf(tmp_path, monkeypatch):
    supabase_schedule = fake_supabase(monkeypatch)
    monkeypatch.setattr(supabase_schedule, "pdf_for_lesson", lambda key: b"%PDF-1.7 " + key.encode())
    dest = tmp_path / "x.pdf"
    assert pl.lesson_pdf({}, "lesson-9", dest)  # schedule_backend 기본은 supabase
    assert dest.read_bytes() == b"%PDF-1.7 lesson-9"


@pytest.mark.parametrize("error", [FileNotFoundError("없음"), RuntimeError("설정"), ValueError("값"),
                                   urllib.error.URLError("연결")])
def test_lesson_pdf_failures_return_false_without_writing(tmp_path, monkeypatch, error):
    supabase_schedule = fake_supabase(monkeypatch)
    monkeypatch.setattr(supabase_schedule, "pdf_for_lesson", mock.Mock(side_effect=error))
    dest = tmp_path / "x.pdf"
    assert pl.lesson_pdf({"schedule_backend": "supabase"}, "k", dest) is False
    assert not dest.exists()


def test_lesson_pdf_rejects_data_that_is_not_a_pdf(tmp_path, monkeypatch):
    supabase_schedule = fake_supabase(monkeypatch)
    monkeypatch.setattr(supabase_schedule, "pdf_for_lesson", lambda key: "<html>오류 화면</html>".encode())
    dest = tmp_path / "x.pdf"
    assert pl.lesson_pdf({}, "k", dest) is False
    assert not dest.exists()


def test_lesson_pdf_old_server_uses_quoted_url_and_trims_slash(tmp_path, monkeypatch):
    seen = {}

    def fake_urlopen(url, timeout=None):
        seen.update(url=url, timeout=timeout)
        return FakeResponse("%PDF-1.4 옛 서버".encode())
    monkeypatch.setattr(pl.urllib.request, "urlopen", fake_urlopen)
    dest = tmp_path / "x.pdf"
    cfg = {"schedule_backend": "sheet", "schedule_api": "http://127.0.0.1:5000/"}
    assert pl.lesson_pdf(cfg, "lesson 1", dest)  # 띄어쓰기는 %20 으로
    assert seen == {"url": "http://127.0.0.1:5000/api/pdf/lesson%201", "timeout": 90}
    assert dest.read_bytes().startswith(b"%PDF-")


def test_lesson_pdf_old_server_down_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(pl.urllib.request, "urlopen", mock.Mock(side_effect=urllib.error.URLError("꺼짐")))
    assert pl.lesson_pdf({"schedule_backend": "sheet"}, "k", tmp_path / "x.pdf") is False


# ──────────────────────────── pdf_text_source ────────────────────────────

class FakePage:
    def __init__(self, text=None, error=None):
        self.text, self.error = text, error

    def get_text(self, mode):
        assert mode == "text"
        if self.error:
            raise self.error
        return self.text


class FakeDoc:
    def __init__(self, pages):
        self.pages = pages
        self.closed = False

    def __iter__(self):
        return iter(self.pages)

    def close(self):
        self.closed = True


def with_fitz(monkeypatch, opener):
    monkeypatch.setitem(sys.modules, "fitz", mock.Mock(open=opener))


def test_pdf_text_source_marks_pages_and_skips_blank_ones(monkeypatch):
    doc = FakeDoc([FakePage(" 첫 쪽 글 \n"), FakePage("   "), FakePage("셋째 쪽")])
    with_fitz(monkeypatch, lambda pdf: doc)
    text = pl.pdf_text_source(pathlib.Path("a.pdf"))
    assert text == "〔p.1〕\n첫 쪽 글\n\n〔p.3〕\n셋째 쪽"  # 쪽 번호는 원래 PDF 쪽 번호
    assert doc.closed


def test_pdf_text_source_scanned_pdf_gives_empty_text(monkeypatch):
    doc = FakeDoc([FakePage(""), FakePage("  ")])
    with_fitz(monkeypatch, lambda pdf: doc)
    assert pl.pdf_text_source(pathlib.Path("a.pdf")) == ""
    assert doc.closed


@pytest.mark.parametrize("error", [RuntimeError("깨진 PDF"), OSError("못 엶")])
def test_pdf_text_source_open_failure_gives_empty_text(monkeypatch, error):
    with_fitz(monkeypatch, mock.Mock(side_effect=error))
    assert pl.pdf_text_source(pathlib.Path("a.pdf")) == ""


def test_pdf_text_source_without_pymupdf_gives_empty_text(monkeypatch):
    monkeypatch.setitem(sys.modules, "fitz", None)  # import fitz → ImportError
    assert pl.pdf_text_source(pathlib.Path("a.pdf")) == ""


def test_pdf_text_source_read_failure_gives_empty_text_and_closes(monkeypatch):
    doc = FakeDoc([FakePage("좋은 쪽"), FakePage(error=RuntimeError("추출 실패"))])
    with_fitz(monkeypatch, lambda pdf: doc)
    assert pl.pdf_text_source(pathlib.Path("a.pdf")) == ""
    assert doc.closed


# ──────────────────────────── prepare_one ────────────────────────────

def test_prepare_one_writes_the_flow_file(env, monkeypatch):
    gemini = use_gemini(monkeypatch, FakeGemini(plan_answer(), detail_answer(), model="모델B"))
    state, msg = pl.prepare_one({}, dict(LESSON), [], "모델A")
    assert (state, msg) == ("ok", "4단계")
    flow = json.loads((app.FLOWS / "lesson-0001.json").read_text(encoding="utf-8"))
    assert flow["record_key"] == "lesson-0001" and flow["subject"] == "국어" and flow["publisher"] == "가출판"
    assert flow["title"] == "생각 나누기" and flow["lesson"] == "1" and flow["goal"] == "생각을 나눈다"
    assert flow["auto"]["by"] == "모델B"                      # 마지막에 답한 모델을 적는다
    assert flow["source"].startswith("지도서 p.2-4 · Gemini 자동")
    assert "pages" not in flow                                 # 쪽수는 source 로 옮겨짐
    assert [s["name"] for s in flow["steps"]] == ["도입", "생각 모으기", "토의", "정리"]
    assert flow["steps"][0]["do"].startswith("교사: ")        # 옛 화면 호환 칸
    assert [c["model"] for c in gemini.calls] == ["모델A", "모델B"]


def test_prepare_one_prompts_carry_lesson_info_and_cautions(env, monkeypatch):
    gemini = use_gemini(monkeypatch, FakeGemini(plan_answer(), detail_answer()))
    pl.prepare_one({}, dict(LESSON), ["발표 순서는 정하지 말 것"], "m")
    plan_prompt, detail_prompt = (c["prompt"] for c in gemini.calls)
    for prompt in (plan_prompt, detail_prompt):
        assert "「생각 나누기」" in prompt and "가출판" in prompt and "@{file}" in prompt
        assert "발표 순서는 정하지 말 것" in prompt
    assert "단계 뼈대" in detail_prompt and "생각 모으기" in detail_prompt  # 뼈대가 둘째 질문에 들어감


def test_prepare_one_without_pdf_fails_before_asking_gemini(env, monkeypatch):
    monkeypatch.setattr(pl, "lesson_pdf", lambda cfg, key, dest: False)
    gemini = use_gemini(monkeypatch, FakeGemini())
    state, msg = pl.prepare_one({}, dict(LESSON), [], "m")
    assert state == "fail" and "지도서 PDF 없음" in msg
    assert gemini.calls == []
    assert not app.FLOWS.exists()


def test_prepare_one_prefers_unit_section_text(env, monkeypatch):
    monkeypatch.setattr(pl, "lesson_section", lambda lesson: "구간 글 " * 80)
    monkeypatch.setattr(pl, "lesson_pdf", mock.Mock(side_effect=AssertionError("구간이 있으면 PDF 를 받지 않는다")))
    gemini = use_gemini(monkeypatch, FakeGemini(plan_answer(), detail_answer()))
    assert pl.prepare_one({}, dict(LESSON), [], "m")[0] == "ok"
    assert {c["pdf_name"] for c in gemini.calls} == {"lesson.md"}
    assert {c["model_timeout"] for c in gemini.calls} == {45}   # 작은 글이라 짧게 기다린다


def test_prepare_one_sends_extracted_text_when_long_enough_else_the_pdf(env, monkeypatch):
    gemini = use_gemini(monkeypatch, FakeGemini(plan_answer(), detail_answer(), plan_answer(), detail_answer()))
    monkeypatch.setattr(pl, "pdf_text_source", lambda pdf: "가" * 300)
    pl.prepare_one({}, dict(LESSON), [], "m")
    monkeypatch.setattr(pl, "pdf_text_source", lambda pdf: "가" * 299)
    pl.prepare_one({}, dict(LESSON), [], "m")
    assert [c["pdf_name"] for c in gemini.calls] == ["lesson.md", "lesson.md", "lesson.pdf", "lesson.pdf"]
    assert {c["model_timeout"] for c in gemini.calls} == {None}


def test_prepare_one_gemini_connection_error_stops_at_once(env, monkeypatch):
    gemini = use_gemini(monkeypatch, FakeGemini(RuntimeError("모든 모델 실패: quota")))
    state, msg = pl.prepare_one({}, dict(LESSON), [], "m")
    assert state == "fail" and msg.startswith("Gemini 연결 실패") and "quota" in msg
    assert len(gemini.calls) == 1                             # 같은 요청을 바로 되풀이하지 않는다
    assert not app.FLOWS.exists()


def test_prepare_one_bad_plan_is_asked_again_with_the_reason(env, monkeypatch):
    bad = plan_answer(steps=[{"name": "하나", "minutes": 40}])          # 단계 수 부족
    gemini = use_gemini(monkeypatch, FakeGemini(bad, plan_answer(), detail_answer()))
    assert pl.prepare_one({}, dict(LESSON), [], "m")[0] == "ok"
    assert len(gemini.calls) == 3
    assert "이전 응답 수정 요청" not in gemini.calls[0]["prompt"]
    assert "이전 응답 수정 요청: 단계 뼈대는 4~8개여야 함" in gemini.calls[1]["prompt"]


def test_prepare_one_bad_detail_keeps_the_plan_and_asks_only_detail_again(env, monkeypatch):
    bad_detail = detail_answer(names=("도입", "생각 모으기"))           # 단계 수가 뼈대와 다름
    gemini = use_gemini(monkeypatch, FakeGemini(plan_answer(), bad_detail, detail_answer()))
    assert pl.prepare_one({}, dict(LESSON), [], "m")[0] == "ok"
    kinds = ["단계 뼈대:" in c["prompt"] for c in gemini.calls]
    assert kinds == [False, True, True]                         # 뼈대는 한 번만 묻는다
    assert "상세 단계 수가 뼈대와 다름" in gemini.calls[2]["prompt"]


def test_prepare_one_gives_up_after_two_bad_answers_and_writes_nothing(env, monkeypatch):
    bad = plan_answer(steps=[])
    gemini = use_gemini(monkeypatch, FakeGemini(bad, bad))
    state, msg = pl.prepare_one({}, dict(LESSON), [], "m")
    assert state == "fail" and msg.startswith("Gemini 결과를 쓰지 못함: 단계 뼈대는 4~8개")
    assert len(gemini.calls) == 2
    assert not app.FLOWS.exists()


def test_prepare_one_flags_a_total_outside_35_to_45_minutes(env, monkeypatch):
    use_gemini(monkeypatch, FakeGemini(plan_answer(), detail_answer()))
    short = {"goal": "g", "materials": [], "homework": "", "pages": "p.1",
             "steps": [{"name": "하나", "minutes": 20}]}
    monkeypatch.setattr(pl, "parse_flow", lambda text, plan=None: dict(short, steps=list(short["steps"])))
    state, msg = pl.prepare_one({}, dict(LESSON), [], "m")
    assert state == "ok" and msg == "1단계 (시간 합계 20분 — 확인 필요)"


def test_prepare_one_keeps_slashes_and_spaces_out_of_the_file_name(env, monkeypatch):
    use_gemini(monkeypatch, FakeGemini(plan_answer(), detail_answer()))
    pl.prepare_one({}, dict(LESSON, record_key="a/b c"), [], "m")
    assert [p.name for p in app.FLOWS.iterdir()] == ["a_b_c.json"]


# ──────────────────────────── main ────────────────────────────

@pytest.fixture
def run_main(env, monkeypatch):
    """main() 을 가짜 일정·가짜 준비로 돌리고 (종료 코드, 마지막 상태 파일, 준비한 차시 키 목록)을 돌려준다."""
    monkeypatch.setattr(app, "load_config", lambda: {"subjects": {"국어": {"publisher": "가출판"}, "수학": {"publisher": "나출판"}}})
    monkeypatch.setattr(app, "CAUTIONS_PATH", env / "cautions.json")
    monkeypatch.setattr(pl, "pid_alive", lambda pid: True)
    monkeypatch.delenv("PREPARE_TOKEN", raising=False)

    def go(lessons, *argv, flows=None, prepare=None):
        flows = flows or {}
        monkeypatch.setattr(app, "fetch_schedule", lambda cfg, day: (lessons, "시험용"))
        monkeypatch.setattr(app, "find_flow", lambda lesson: flows.get(lesson.get("record_key")))
        prepared = []

        def fake_prepare(cfg, lesson, cautions, model):
            prepared.append((lesson["record_key"], cautions, model))
            return prepare(lesson) if prepare else ("ok", "4단계")
        monkeypatch.setattr(pl, "prepare_one", fake_prepare)
        monkeypatch.setattr(sys, "argv", ["prepare_lessons.py", "--date", "2026-11-27", *argv])
        code = pl.main()
        return code, json.loads(pl.STATUS.read_text(encoding="utf-8")), prepared
    return go


def two_lessons():
    return [{"period": 1, "subject": "국어", "title": "가", "record_key": "k1"},
            {"period": 2, "subject": "수학", "title": "나", "record_key": "k2"}]


def test_main_prepares_every_lesson_without_a_flow(run_main):
    code, status, prepared = run_main(two_lessons())
    assert code == 0
    assert [p[0] for p in prepared] == ["k1", "k2"]
    assert [i["status"] for i in status["items"]] == ["ok", "ok"]
    assert status["running"] is False and status["finished"] and status["date"] == "2026-11-27"
    assert all("초" in i["msg"] for i in status["items"])     # 걸린 시간이 붙는다


def test_main_skips_lessons_without_record_key_and_keeps_existing_flows(run_main):
    lessons = two_lessons() + [{"period": 3, "subject": "국어", "title": "행사", "record_key": ""}]
    flows = {"k1": {"auto": {"by": "m"}}, "k2": {"goal": "교사가 고침"}}
    code, status, prepared = run_main(lessons, flows=flows)
    assert code == 0 and prepared == []
    got = {i["record_key"]: (i["status"], i["msg"]) for i in status["items"]}
    assert got["k1"] == ("have", "이미 준비됨")
    assert got["k2"] == ("have", "이미 준비됨(직접 고친 흐름)")
    assert got[""] == ("skip", "진도표 수업이 아님")


def test_main_redo_recreates_auto_flows_but_never_hand_edited_ones(run_main):
    flows = {"k1": {"auto": {"by": "m"}}, "k2": {"goal": "교사가 고침"}}
    _, status, prepared = run_main(two_lessons(), "--redo", flows=flows)
    assert [p[0] for p in prepared] == ["k1"]
    assert [i["status"] for i in status["items"]] == ["ok", "have"]


def test_main_failure_gives_exit_code_2_and_keeps_going(run_main):
    code, status, prepared = run_main(two_lessons(), prepare=lambda l: ("fail", "지도서 PDF 없음") if l["record_key"] == "k1" else ("ok", "4단계"))
    assert code == 2
    assert [p[0] for p in prepared] == ["k1", "k2"]
    assert [i["status"] for i in status["items"]] == ["fail", "ok"]


def test_main_unexpected_error_in_one_lesson_does_not_stop_the_rest(run_main):
    def boom(lesson):
        if lesson["record_key"] == "k1":
            raise KeyError("x" * 500)
        return "ok", "4단계"
    code, status, prepared = run_main(two_lessons(), prepare=boom)
    assert code == 2
    assert status["items"][0]["status"] == "fail" and status["items"][0]["msg"].startswith("오류: ")
    assert len(status["items"][0]["msg"]) < 260                 # 긴 오류는 잘라서 보여 준다
    assert status["items"][1]["status"] == "ok"


def test_main_passes_publisher_cautions_and_model_to_prepare_one(run_main, env):
    (env / "cautions.json").write_text(json.dumps({"가출판|국어": [{"text": "국어 주의"}], "가출판|*": [{"text": "공통 주의"}]},
                                                  ensure_ascii=False), encoding="utf-8")
    _, _, prepared = run_main(two_lessons(), "--model", "내모델")
    assert prepared[0] == ("k1", ["국어 주의", "공통 주의"], "내모델")
    assert prepared[1] == ("k2", [], "내모델")                  # 나출판·수학 주의점은 없음


def test_main_refuses_when_another_run_is_in_progress(run_main, env):
    pl.STATUS.write_text(json.dumps({"running": True, "started_ts": time.time(), "pid": 1, "date": "2026-11-26"}), encoding="utf-8")
    code, status, prepared = run_main(two_lessons())
    assert code == 1 and prepared == []
    assert status["running"] is True and status["date"] == "2026-11-26"   # 남의 상태를 덮어쓰지 않는다


def test_main_continues_when_the_running_status_is_mine_or_stale(run_main, env, monkeypatch):
    # 수업 비서 화면이 '🌙 수업 준비' 단추로 띄운 것: 같은 토큰이면 내 상태
    pl.STATUS.write_text(json.dumps({"running": True, "started_ts": time.time(), "pid": 1, "token": "T1"}), encoding="utf-8")
    monkeypatch.setenv("PREPARE_TOKEN", "T1")
    assert run_main(two_lessons())[0] == 0
    # 30분이 지났거나 프로세스가 사라진 옛 상태는 무시
    monkeypatch.delenv("PREPARE_TOKEN")
    pl.STATUS.write_text(json.dumps({"running": True, "started_ts": time.time() - 3600, "pid": 1}), encoding="utf-8")
    assert run_main(two_lessons())[0] == 0


def test_main_empty_token_never_counts_as_mine(run_main, env):
    pl.STATUS.write_text(json.dumps({"running": True, "started_ts": time.time(), "pid": 1, "token": ""}), encoding="utf-8")
    assert run_main(two_lessons())[0] == 1


def test_main_with_no_lessons_still_finishes_cleanly(run_main):
    code, status, prepared = run_main([])
    assert code == 0 and prepared == [] and status["items"] == [] and status["running"] is False
