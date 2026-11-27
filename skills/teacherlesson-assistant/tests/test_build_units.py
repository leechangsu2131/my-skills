"""build_units.py 시험(S1): 진도표 → 단원 개관(JSON·PDF) 규칙 만들기.

    python -m pytest tests/test_build_units.py -v      (teacherlesson-assistant 폴더에서)

진짜 진도표(Supabase·시트)·지도서 PDF·데이터 폴더는 쓰지 않는다. 진도표는 목록으로 대신하고, PDF 는
쪽 글만 돌려주는 가짜 fitz 로, 단원 폴더(UNITS)는 임시 폴더로 바꾼다. 학생 정보는 없다.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import build_units as bu  # noqa: E402


def rows(*titles_numbers):
    return [{"차시": n, "수업내용": t} for n, t in titles_numbers]


# ═════════ lesson_no ═════════

@pytest.mark.parametrize("value,want", [("3", 3), (3, 3), ("3차시", 3), ("제 12 차시", 12), ("3~4", 3),
                                        ("", None), (None, None), ("가", None), ("0", 0)])
def test_lesson_no_takes_first_number(value, want):
    assert bu.lesson_no(value) == want


# ═════════ infer_lesson_numbers ═════════

def nums(*values):
    return bu.infer_lesson_numbers([{"차시": v} for v in values])


def test_infer_fills_gap_only_when_numbers_leave_exactly_enough_places():
    assert nums(1, "", "", 4) == [1, 2, 3, 4]
    assert nums(1, "", 4) == [1, None, 4]      # 사이에 2개 들어갈 자리인데 빈칸은 1개 → 어느 번호인지 모름
    assert nums(1, "", "", "", 4) == [1, None, None, None, 4]


def test_infer_extends_before_first_and_after_last_known_number():
    assert nums("", "", 3, 4) == [1, 2, 3, 4]
    assert nums(1, 2, "", "") == [1, 2, 3, 4]


def test_infer_does_not_go_below_one():
    assert nums("", "", "", 2) == [None, None, 1, 2]


def test_infer_without_any_number_stays_blank_and_keeps_known_ones():
    assert nums("", "", "") == [None, None, None]
    assert nums(2, 1, 5) == [2, 1, 5]
    assert bu.infer_lesson_numbers([]) == []


# ═════════ group_lessons ═════════

def test_group_merges_same_title_with_continuing_numbers_and_drops_single_to():
    got = bu.group_lessons(rows((1, "가"), (2, "가"), (3, "나"), (4, "나"), (5, "다")))
    assert got == [{"from": 1, "to": 2, "title": "가"}, {"from": 3, "to": 4, "title": "나"}, {"from": 5, "title": "다"}]


def test_group_does_not_merge_across_number_gap_or_different_title():
    got = bu.group_lessons(rows((1, "가"), (3, "가"), (4, "나")))
    assert got == [{"from": 1, "title": "가"}, {"from": 3, "title": "가"}, {"from": 4, "title": "나"}]


def test_group_strips_titles_and_skips_rows_with_no_number():
    got = bu.group_lessons([{"차시": "", "수업내용": "번호 없음"}, {"차시": 1, "수업내용": "  가  "}])
    assert got == [{"from": 1, "title": "가"}]


def test_group_uses_inferred_numbers():
    got = bu.group_lessons(rows((1, "도입"), ("", "활동"), (3, "정리")))
    assert [(g["from"], g["title"]) for g in got] == [(1, "도입"), (2, "활동"), (3, "정리")]


# ═════════ LESSON_START: 지도서마다 다른 '차시 시작' 표시 ═════════

@pytest.mark.parametrize("text", [
    "1차시 / 14차시 도입",              # 국어
    "2~3차시 / 14차시 활동",             # 국어(묶음)
    "1 4 이 단원의 차시 목표",            # 도덕: 1 4 … 차시 목표
    "12차시 1 분수",                     # 수학
    "10 12차시 분수",                    # 수학(쪽 번호가 앞)
    "2 2 차시 교과서 12~13쪽",           # 사회
    "2~3 4~5 차시 교과서",               # 사회(묶음)
])
def test_lesson_start_matches_publisher_markers(text):
    assert any(rx.search(text) for rx in bu.LESSON_START), text


@pytest.mark.parametrize("text", ["단원 개관", "단원의 계획", "12차시 쪽", "10 12차시 / 목표", "차시별 지도 계획"])
def test_lesson_start_ignores_overview_and_look_alikes(text):
    assert not any(rx.search(text) for rx in bu.LESSON_START), text


# ═════════ head ═════════

def test_head_strips_control_chars_collapses_spaces_and_cuts():
    class Page:
        def get_text(self):
            return "가\x00나​다\n\n  라\t마" + "바" * 300
    got = bu.head({0: Page()}, 0, 10)
    assert got == "가 나 다 라 마바바"[:10] and len(got) <= 10
    assert "\x00" not in got and "​" not in got


# ═════════ overview_pages (가짜 PDF) ═════════

class FakePage:
    def __init__(self, text):
        self.text = text

    def get_text(self):
        return self.text


class FakeDoc:
    def __init__(self, pages):
        self.pages = [FakePage(t) for t in pages]
        self.page_count = len(pages)
        self.closed = False

    def __getitem__(self, i):
        return self.pages[i]

    def close(self):
        self.closed = True


@pytest.fixture
def fake_fitz(monkeypatch):
    books = {}
    opened = []

    class F:
        @staticmethod
        def open(path=None):
            doc = FakeDoc(books[str(path)])
            opened.append(doc)
            return doc

    monkeypatch.setattr(bu, "fitz", F)
    return books, opened


def test_overview_ends_before_first_lesson_page(fake_fitz):
    books, opened = fake_fitz
    books["a.pdf"] = ["표지", "단원 개관", "단원 계획", "1차시 / 14차시 도입", "x"]
    assert bu.overview_pages(pathlib.Path("a.pdf")) == (0, 2)
    assert opened[0].closed


def test_overview_never_treats_cover_page_as_lesson(fake_fitz):
    books, _ = fake_fitz
    books["a.pdf"] = ["1차시 / 14차시 (표지에 있어도 건너뜀)", "1차시 / 14차시 도입"]
    assert bu.overview_pages(pathlib.Path("a.pdf")) == (0, 0)


def test_overview_without_marker_short_file_whole_long_file_first_six(fake_fitz):
    books, _ = fake_fitz
    books["short.pdf"] = ["x"] * 12
    books["long.pdf"] = ["x"] * 13
    assert bu.overview_pages(pathlib.Path("short.pdf")) == (0, 11)
    assert bu.overview_pages(pathlib.Path("long.pdf")) == (0, 5)


def test_overview_only_looks_at_first_40_pages(fake_fitz):
    books, _ = fake_fitz
    books["a.pdf"] = ["x"] * 45 + ["1차시 / 14차시"]
    assert bu.overview_pages(pathlib.Path("a.pdf")) == (0, 5)


# ═════════ plan_split ═════════

def write_groups(folder, groups):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "groups.json").write_text(json.dumps({"groups": groups}, ensure_ascii=False), encoding="utf-8")


def test_plan_split_finds_overview_pdf_of_the_unit(tmp_path):
    root = tmp_path / "수학"
    splits = root / "pdf_splits"
    splits.mkdir(parents=True)
    pdf = splits / "[수학]_subunit_02_6단원_그래프_p10-20.pdf"   # 분할기 이름: [책]_subunit_NN_<제목>_pS-E.pdf
    wanted = splits / "[수학]_subunit_01_단원개관_p3-9.pdf"
    for p in (pdf, wanted):
        p.write_bytes(b"x")
    write_groups(root, [{"index": 1, "detected_level": "plan", "parent_unit_title": "6. 그래프", "start_page": 3, "end_page": 9},
                        {"index": 2, "detected_level": "lesson", "parent_unit_title": "6. 그래프", "start_page": 10, "end_page": 20}])
    assert bu.plan_split(pdf, "6. 그래프") == wanted
    assert bu.plan_split(pdf, "다른 단원") is None


def test_plan_split_ignores_non_plan_groups_even_listed_first(tmp_path):
    splits = tmp_path / "pdf_splits"
    splits.mkdir()
    lesson_file = splits / "[수학]_subunit_01_6단원_가_p3-9.pdf"
    plan_file = splits / "[수학]_subunit_02_단원개관_p10-12.pdf"
    for f in (lesson_file, plan_file):
        f.write_bytes(b"x")
    groups = [{"index": 1, "detected_level": "lesson", "parent_unit_title": "6. 그래프", "start_page": 3, "end_page": 9},
              {"index": 2, "detected_level": "plan", "parent_unit_title": "6. 그래프", "start_page": 10, "end_page": 12}]
    write_groups(tmp_path, groups)
    assert bu.plan_split(splits / "a.pdf", "6. 그래프") == plan_file
    write_groups(tmp_path, groups[:1])  # 개관 묶음이 없으면 차시 묶음 파일이 있어도 None
    assert bu.plan_split(splits / "a.pdf", "6. 그래프") is None


def test_plan_split_looks_in_pdf_own_folder_too(tmp_path):
    folder = tmp_path / "수학"
    (folder / "pdf_splits").mkdir(parents=True)
    plan_file = folder / "pdf_splits" / "[수학]_subunit_01_단원개관_p3-9.pdf"
    plan_file.write_bytes(b"x")
    write_groups(folder, [{"index": 1, "detected_level": "plan", "parent_unit_title": "단원", "start_page": 3, "end_page": 9}])
    assert bu.plan_split(folder / "수학.pdf", "단원") == plan_file  # groups.json 이 책 PDF 와 같은 폴더에 있는 경우


def test_plan_split_returns_none_without_groups_or_with_broken_json(tmp_path):
    pdf = tmp_path / "pdf_splits" / "a.pdf"
    pdf.parent.mkdir()
    assert bu.plan_split(pdf, "단원") is None
    (tmp_path / "groups.json").write_text("{깨짐", encoding="utf-8")
    assert bu.plan_split(pdf, "단원") is None


def test_plan_split_ignores_group_whose_file_is_missing(tmp_path):
    root = tmp_path
    (root / "pdf_splits").mkdir()
    write_groups(root, [{"index": 1, "detected_level": "plan", "parent_unit_title": "단원", "start_page": 1, "end_page": 2}])
    assert bu.plan_split(root / "pdf_splits" / "a.pdf", "단원") is None


# ═════════ build ═════════

@pytest.fixture
def env(tmp_path, monkeypatch):
    """진도표 목록·단원 폴더를 가짜로. build() 가 쓰는 곳만 바꾼다."""
    units = tmp_path / "units"
    units.mkdir()
    monkeypatch.setattr(bu.app, "UNITS", units)
    state = {"records": []}
    monkeypatch.setattr(bu, "load_progress_records", lambda: state["records"])
    monkeypatch.setattr(bu.schedule, "_is_done", lambda r: bool(r.get("_done")))
    return state, units


def rec(subject, unit, n, title, row, pdf="", done=False):
    return {"과목": subject, "대단원": unit, "차시": n, "수업내용": title, "_row": row, "pdf파일": pdf, "_done": done}


def test_build_writes_lessons_json_and_reports_missing_pdf(env):
    state, units = env
    state["records"] = [rec("수학", "6. 그래프", 2, "나", 2), rec("수학", "6. 그래프", 1, "가", 1)]
    report = bu.build(only_open=False)
    data = json.loads((units / "수학__6._그래프.json").read_text(encoding="utf-8"))
    assert data["lessons"] == [{"from": 1, "title": "가"}, {"from": 2, "title": "나"}]  # _row 순서
    assert data["auto"] is True and "overview_pdf" not in data
    assert report == ["[수학] 6. 그래프: 차시 묶음 2개 · 지도서 PDF 없음(진도표 경로 확인)"]


def test_build_keeps_hand_written_fields(env):
    state, units = env
    path = units / "수학__6._그래프.json"
    path.write_text(json.dumps({"summary": "사람이 쓴 요약", "goals": ["목표"], "lessons": [{"from": 9}]}, ensure_ascii=False), encoding="utf-8")
    state["records"] = [rec("수학", "6. 그래프", 1, "가", 1)]
    bu.build(only_open=False)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["summary"] == "사람이 쓴 요약" and data["goals"] == ["목표"]
    assert data["lessons"] == [{"from": 1, "title": "가"}]


def test_build_only_open_skips_finished_units(env):
    state, units = env
    state["records"] = [rec("수학", "끝난", 1, "가", 1, done=True), rec("국어", "남은", 1, "가", 2, done=False),
                        rec("과학", "", 1, "단원 이름 없음", 3), rec("", "과목 없음", 1, "가", 4)]
    report = bu.build(only_open=True)
    assert [p.name for p in units.glob("*.json")] == ["국어__남은.json"]
    assert len(report) == 1 and report[0].startswith("[국어] 남은")
    assert len(bu.build(only_open=False)) == 2


def test_build_only_open_keeps_unit_with_some_lessons_left(env):
    state, units = env
    state["records"] = [rec("수학", "일부만", 1, "가", 1, done=True), rec("수학", "일부만", 2, "나", 2, done=False)]
    assert len(bu.build(only_open=True)) == 1 and (units / "수학__일부만.json").is_file()


def test_build_uses_plan_split_file_when_found(env, tmp_path, monkeypatch):
    state, units = env
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"x")
    plan = tmp_path / "개관_subunit_01_p3-9.pdf"
    plan.write_bytes(b"PLAN-BYTES")
    monkeypatch.setattr(bu, "plan_split", lambda p, unit: plan)
    state["records"] = [rec("수학", "6. 그래프", 1, "가", 1, pdf=str(pdf))]
    report = bu.build(only_open=False)
    assert (units / "수학__6._그래프.pdf").read_bytes() == b"PLAN-BYTES"
    data = json.loads((units / "수학__6._그래프.json").read_text(encoding="utf-8"))
    assert data["overview_pdf"] == "수학__6._그래프.pdf" and data["source"] == plan.name
    assert "분할본 단원 개관" in report[0]


def test_build_cuts_overview_pages_when_no_plan_split(env, tmp_path, monkeypatch):
    state, units = env
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"x")
    calls = {}

    class Part:
        def insert_pdf(self, doc, from_page, to_page):
            calls["range"] = (from_page, to_page)

        def save(self, path, **kw):
            pathlib.Path(path).write_bytes(b"CUT")
            calls["save"] = kw

        def close(self):
            calls["part_closed"] = True

    class Src:
        def close(self):
            calls["src_closed"] = True

    class F:
        open_count = 0

        @staticmethod
        def open(path=None):
            return Part() if path is None else Src()

    monkeypatch.setattr(bu, "fitz", F)
    monkeypatch.setattr(bu, "plan_split", lambda p, unit: None)
    monkeypatch.setattr(bu, "overview_pages", lambda p: (0, 2))
    state["records"] = [rec("국어", "4. 글", 1, "가", 1, pdf=str(pdf))]
    report = bu.build(only_open=False)
    assert calls["range"] == (0, 2) and calls["part_closed"] and calls["src_closed"]
    assert (units / "국어__4._글.pdf").read_bytes() == b"CUT"
    data = json.loads((units / "국어__4._글.json").read_text(encoding="utf-8"))
    assert data["source"] == "book.pdf p1-3"
    assert report[0].endswith("book.pdf p1-3")


def test_build_keeps_existing_source(env, tmp_path, monkeypatch):
    state, units = env
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"x")
    plan = tmp_path / "p.pdf"
    plan.write_bytes(b"P")
    (units / "수학__단원.json").write_text(json.dumps({"source": "사람이 적은 출처"}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(bu, "plan_split", lambda p, unit: plan)
    state["records"] = [rec("수학", "단원", 1, "가", 1, pdf=str(pdf))]
    bu.build(only_open=False)
    assert json.loads((units / "수학__단원.json").read_text(encoding="utf-8"))["source"] == "사람이 적은 출처"


def test_build_pdf_path_that_does_not_exist_is_reported_as_missing(env, tmp_path):
    state, units = env
    state["records"] = [rec("수학", "단원", 1, "가", 1, pdf=str(tmp_path / "없음.pdf"))]
    assert "지도서 PDF 없음" in bu.build(only_open=False)[0]


# ═════════ main ═════════

def test_main_skips_when_stamp_is_recent(env, monkeypatch, capsys):
    _, units = env
    stamp = units / ".last_build"
    stamp.write_text("방금", encoding="utf-8")
    monkeypatch.setattr(bu, "STAMP", stamp)
    monkeypatch.setattr(bu, "build", lambda only_open: pytest.fail("건너뛰어야 함"))
    monkeypatch.setattr(sys, "argv", ["build_units.py", "--if-older", "12"])
    bu.main()
    assert "건너뜀" in capsys.readouterr().out


def test_main_runs_and_writes_stamp(env, monkeypatch, capsys):
    _, units = env
    stamp = units / ".last_build"
    monkeypatch.setattr(bu, "STAMP", stamp)
    seen = []
    monkeypatch.setattr(bu, "build", lambda only_open: seen.append(only_open) or ["줄 하나"])
    monkeypatch.setattr(sys, "argv", ["build_units.py"])
    bu.main()
    assert seen == [True] and "줄 하나" in capsys.readouterr().out and stamp.is_file()
    monkeypatch.setattr(sys, "argv", ["build_units.py", "--all"])
    bu.main()
    assert seen == [True, False]
