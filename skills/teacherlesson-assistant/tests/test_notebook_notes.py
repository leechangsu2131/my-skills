"""split_notes.py · notebook_sources.py 시험(S1).

    python -m pytest tests -v      (teacherlesson-assistant 폴더에서)

진짜 PDF·데이터 폴더·네트워크는 쓰지 않는다. PDF 는 쪽 글만 돌려주는 가짜(fitz 대역)로, 저장 폴더는 임시 폴더로 바꾼다.
학생 정보는 없다(예시는 '수학 6단원' 같은 과목·단원 이름뿐).
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import assistant_server as app  # noqa: E402
import notebook_sources as ns  # noqa: E402
import split_notes as sn  # noqa: E402


# ── 가짜 PDF ──

class FakePage:
    def __init__(self, text):
        self.text = text

    def get_text(self):
        return self.text


class FakeDoc:
    def __init__(self, pages):
        self.pages = [FakePage(t) for t in pages]
        self.page_count = len(pages)

    def __getitem__(self, i):
        return self.pages[i]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def fake_pdf(monkeypatch):
    """경로 → 쪽 글 목록 을 등록하면 fitz.open(경로) 가 가짜 문서를 준다."""
    books = {}

    class FakeFitz:
        @staticmethod
        def open(path):
            return FakeDoc(books[str(path)])

    monkeypatch.setattr(ns, "fitz", FakeFitz)
    monkeypatch.setattr(ns.nlm, "fitz", lambda: FakeFitz)
    return books


# ═════════ split_notes.split ═════════

def test_split_cuts_at_lesson_headings_and_drops_text_before_first():
    text = "앞에 붙은 인사말\n## [수학 6단원] 4차시 그림그래프\n내용 하나\n## [수학 6단원] 5차시 마무리\n내용 둘\n"
    got = sn.split(text)
    assert [(g[0], g[1], g[2], g[3]) for g in got] == [("수학", "6단원", 4, 4), ("수학", "6단원", 5, 5)]
    assert "앞에 붙은 인사말" not in got[0][4]
    assert got[0][4].startswith("## [수학 6단원] 4차시")
    assert "내용 둘" not in got[0][4] and "내용 둘" in got[1][4]


@pytest.mark.parametrize("sep", ["~", "∼", "-", " ~ "])
def test_split_lesson_range_separators(sep):
    got = sn.split(f"## [국어 4단원] 3{sep}4차시 읽기\n본문")
    assert got[0][2:4] == (3, 4)


def test_split_accepts_bold_heading():
    got = sn.split("**[사회 2단원] 1차시 우리 고장**\n본문")
    assert got and got[0][:4] == ("사회", "2단원", 1, 1)


def test_split_ignores_headings_without_mark_and_plain_lines():
    assert sn.split("## 그냥 제목\n[수학 6단원] 4차시 (제목 줄이 아님)\n내용") == []
    assert sn.split("") == []


def test_split_heading_without_mark_stays_inside_previous_part():
    got = sn.split("## [수학 6단원] 4차시 가\n본문\n## 소제목\n더 있는 본문\n## [수학 6단원] 5차시 나\n끝")
    assert len(got) == 2
    assert "소제목" in got[0][4] and "더 있는 본문" in got[0][4]


# ═════════ split_notes.main ═════════

@pytest.fixture
def notes_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "NOTEBOOKLM", tmp_path / "notebooklm")
    return tmp_path / "notebooklm"


def test_main_writes_one_note_per_lesson_including_ranges(tmp_path, notes_dir):
    src = tmp_path / "받은.md"
    src.write_text("## [국어 4단원] 3~4차시 읽기\n본문\n## [국어 4단원] 5차시 쓰기\n다음", encoding="utf-8")
    sn.main([str(src)])
    notes = notes_dir / "국어" / "notes"
    assert sorted(p.name for p in notes.iterdir()) == ["4단원_3차시.md", "4단원_4차시.md", "4단원_5차시.md"]
    three, four = (notes / "4단원_3차시.md").read_text(encoding="utf-8"), (notes / "4단원_4차시.md").read_text(encoding="utf-8")
    assert three == four and three.startswith("<!-- 받은.md 에서 자름 -->")
    assert "다음" not in three


def test_main_overwrites_same_name_note(tmp_path, notes_dir):
    src = tmp_path / "a.md"
    src.write_text("## [수학 6단원] 4차시 가\n옛 내용", encoding="utf-8")
    sn.main([str(src)])
    src.write_text("## [수학 6단원] 4차시 가\n새 내용", encoding="utf-8")
    sn.main([str(src)])
    out = (notes_dir / "수학" / "notes" / "6단원_4차시.md").read_text(encoding="utf-8")
    assert "새 내용" in out and "옛 내용" not in out


def test_main_file_without_marks_says_so_and_writes_nothing(tmp_path, notes_dir, capsys):
    src = tmp_path / "x.md"
    src.write_text("## 제목만 있어요\n내용", encoding="utf-8")
    sn.main([str(src)])
    assert "차시' 제목을 찾지 못했어요" in capsys.readouterr().out
    assert not notes_dir.exists()


def test_main_without_paths_prints_help(capsys):
    sn.main([])
    assert "split_notes.py" in capsys.readouterr().out


def test_main_reads_utf8_bom(tmp_path, notes_dir):
    src = tmp_path / "bom.md"
    src.write_bytes("\ufeff## [수학 6단원] 1차시 가\n내용".encode("utf-8"))
    sn.main([str(src)])
    assert (notes_dir / "수학" / "notes" / "6단원_1차시.md").is_file()


def test_main_subject_with_path_characters_is_renamed_by_safe_name(tmp_path, notes_dir):
    src = tmp_path / "bad.md"
    src.write_text("## [../../밖 1단원] 1차시 가\n내용", encoding="utf-8")
    # 표시 정규식은 공백·] 만 막으므로 '../../밖' 이 과목으로 들어올 수 있다. safe_name 이 '/' 를 바꿔 폴더 밖으로 못 나간다.
    sn.main([str(src)])
    assert not (tmp_path / "밖").exists()
    for p in tmp_path.rglob("*.md"):
        assert p == src or notes_dir in p.parents


def test_main_skips_note_whose_path_resolves_outside_notes_folder(tmp_path, notes_dir, monkeypatch, capsys):
    """safe_name 이 막지 못한 경우(예: 바깥으로 가는 링크)를 대비한 마지막 검사."""
    outside = tmp_path / "밖" / "x.md"
    monkeypatch.setattr(app, "lesson_note_path", lambda subject, label, n: outside)
    src = tmp_path / "a.md"
    src.write_text("## [수학 6단원] 4차시 가\n내용", encoding="utf-8")
    sn.main([str(src)])
    assert "건너뜀" in capsys.readouterr().out
    assert not outside.exists()


# ═════════ notebook_sources: 순수 함수 ═════════

@pytest.mark.parametrize("row,want", [
    ({"시작페이지": "25", "끝페이지": "28"}, (25, 28)),
    ({"시작페이지": 25, "끝페이지": ""}, (25, 25)),
    ({"시작페이지": " 7 "}, (7, 7)),
    ({"시작페이지": "", "끝페이지": "9"}, None),
    ({"시작페이지": "가", "끝페이지": "9"}, None),
    ({"시작페이지": "0", "끝페이지": "3"}, None),
    ({"시작페이지": "9", "끝페이지": "3"}, None),
    ({}, None),
])
def test_page_range(row, want):
    assert ns.page_range(row) == want


def test_is_split_looks_for_pdf_splits_folder_name_only():
    assert ns.is_split(r"D:\지도서\수학\pdf_splits\a.pdf".replace("\\", "/")) is True
    assert ns.is_split("/x/PDF_Splits/a.pdf") is True
    assert ns.is_split("/x/pdf_splits_old/a.pdf") is False
    assert ns.is_split("/x/pdf_splits.pdf") is False
    assert ns.is_split("") is False


def test_book_start_reads_page_from_split_file_name():
    P = pathlib.Path
    assert ns.book_start(P("수학_subunit_01_p25-28.pdf")) == 25
    assert ns.book_start(P("수학.pdf")) is None
    assert ns.book_start(P("수학_p25-28.pdf.bak")) is None


def test_where_text():
    b = [{"pages": (25, 28)}, {"pages": (29, 30)}]
    assert ns.where_text("/a/pdf_splits/x.pdf", b) == "지도서 p.25~30"
    assert ns.where_text("/a/pdf_splits/x.pdf", [{"pages": None}]) == "지도서 x.pdf"
    assert ns.where_text("/a/국어3-1.pdf", b) == "지도서 국어3-1.pdf"


def test_heading_merges_range_and_dedups_titles():
    groups = [{"from": 1, "to": 2, "title": "가"}, {"from": 3, "to": 4, "title": "나"}, {"from": 4, "to": 4, "title": "가"}]
    assert ns.heading("[수학 6단원]", groups, "지도서 p.1") == "## [수학 6단원] 1~4차시 가 / 나 (지도서 p.1)"
    assert ns.heading("[수학 6단원]", [{"from": 2, "to": 2, "title": ""}], "") == "## [수학 6단원] 2차시"


def test_heading_tag_roundtrips_through_split_notes_mark():
    """소스에 심는 제목 모양이 받은 글을 자르는 정규식(split_notes.MARK)에 맞아야 NotebookLM 질문이 이어진다."""
    tag = app.lesson_tag("수학", "6. 그림그래프")
    for groups in ([{"from": 4, "to": 4, "title": "그림그래프"}], [{"from": 3, "to": 4, "title": "가"}]):
        m = sn.MARK.search(ns.heading(tag, groups, "지도서 p.1"))
        assert m and (m.group(1), m.group(2)) == ("수학", "6단원")
        assert (int(m.group(3)), int(m.group(4) or m.group(3))) == (groups[0]["from"], groups[0]["to"])


# ── lesson_groups ──

def rows(*items):
    return [{"차시": n, "수업내용": t, "pdf파일": p} for n, t, p in items]


def test_lesson_groups_merges_same_title_and_pdf_when_numbers_continue(tmp_path):
    f = str(tmp_path / "a.pdf")
    got = ns.lesson_groups(rows((1, "가", f), (2, "가", f), (3, "나", f)))
    assert [(g["from"], g["to"], g["title"]) for g in got] == [(1, 2, "가"), (3, 3, "나")]


def test_lesson_groups_does_not_merge_across_gap_or_other_pdf(tmp_path):
    a, b = str(tmp_path / "a.pdf"), str(tmp_path / "b.pdf")
    got = ns.lesson_groups(rows((1, "가", a), (2, "가", b), (5, "가", b)))
    assert [(g["from"], g["to"]) for g in got] == [(1, 1), (2, 2), (5, 5)]


def test_lesson_groups_skips_rows_without_any_number_and_fills_inferred(tmp_path):
    f = str(tmp_path / "a.pdf")
    got = ns.lesson_groups(rows(("", "개관", f), (2, "가", f), ("", "나", f), (4, "다", f)))
    assert [(g["from"], g["title"]) for g in got] == [(1, "개관"), (2, "가"), (3, "나"), (4, "다")]
    assert ns.lesson_groups(rows(("", "가", f), ("", "나", f))) == []


def test_lesson_groups_keeps_page_range_of_first_row(tmp_path):
    f = str(tmp_path / "a.pdf")
    r = [{"차시": 1, "수업내용": "가", "pdf파일": f, "시작페이지": "10", "끝페이지": "12"}]
    assert ns.lesson_groups(r)[0]["pages"] == (10, 12)


# ═════════ notebook_sources: PDF 를 읽는 함수 (가짜 fitz) ═════════

def test_slice_sec_labels_pages_and_clamps_to_file(fake_pdf):
    fake_pdf["x.pdf"] = ["a", "b", "c", "d"]
    sec = ns.slice_sec("## h", "x.pdf", 1, 99, 25)
    assert sec["pages"] == [(1, 25), (2, 26), (3, 27)]
    assert ns.slice_sec("## h", "x.pdf", -3, 1, 1)["pages"] == [(0, 1), (1, 2)]
    assert sec["heading"] == "## h" and sec["note"] == ""


def test_by_korean_markers_cuts_at_first_page_showing_each_lesson(fake_pdf):
    fake_pdf["k.pdf"] = ["단원 개관", "1차시 / 14차시 도입", "계속", "2~3차시 / 14차시 활동", "계속", "계속"]
    b = [{"from": 1, "to": 1, "title": "가"}, {"from": 2, "to": 3, "title": "나"}]
    secs = ns.by_korean_markers("[국어 4단원]", b, "k.pdf")
    assert [s["heading"] for s in secs] == [
        "## [국어 4단원] 단원 개관 (지도서 파일 p.1~1)",
        "## [국어 4단원] 1차시 가 (지도서 파일 p.2~3)",
        "## [국어 4단원] 2~3차시 나 (지도서 파일 p.4~6)",
    ]
    assert [p[0] for p in secs[1]["pages"]] == [1, 2]
    assert [p[0] for p in secs[2]["pages"]] == [3, 4, 5]


def test_by_korean_markers_uses_first_page_when_lesson_number_repeats(fake_pdf):
    fake_pdf["k.pdf"] = ["1차시 / 14차시", "다시 1차시 / 14차시 (머리글)", "2차시 / 14차시"]
    b = [{"from": 1, "to": 1, "title": "가"}, {"from": 2, "to": 2, "title": "나"}]
    secs = ns.by_korean_markers("[국어 4단원]", b, "k.pdf")
    assert len(secs) == 2  # 개관 없음: 1차시가 첫 쪽
    assert [p[0] for p in secs[0]["pages"]] == [0, 1]


def test_by_korean_markers_attaches_lesson_without_marker_to_previous(fake_pdf):
    fake_pdf["k.pdf"] = ["1차시 / 14차시", "x", "3차시 / 14차시", "y"]
    b = [{"from": 1, "to": 1, "title": "가"}, {"from": 2, "to": 2, "title": "나"}, {"from": 3, "to": 3, "title": "다"}]
    secs = ns.by_korean_markers("[국어 4단원]", b, "k.pdf")
    assert [s["heading"].split(" (")[0] for s in secs] == ["## [국어 4단원] 1~2차시 가 / 나", "## [국어 4단원] 3차시 다"]


def test_by_korean_markers_falls_back_to_stage_markers(fake_pdf):
    fake_pdf["m.pdf"] = ["개관", "이 차시는 '다가가기' 학습으로", "계속", "이 차시는 '살펴보기' 학습으로", "계속"]
    b = [{"from": 1, "to": 1, "title": "가"}, {"from": 2, "to": 2, "title": "나"}]
    secs = ns.by_korean_markers("[국어 3.5]", b, "m.pdf")
    assert [s["heading"].split(" (")[0] for s in secs] == ["## [국어 3.5] 단원 개관", "## [국어 3.5] 1차시 가", "## [국어 3.5] 2차시 나"]
    assert [p[0] for p in secs[1]["pages"]] == [1, 2]


def test_by_stage_markers_needs_stage_count_equal_to_lesson_count(fake_pdf):
    fake_pdf["m.pdf"] = ["이 차시는 '다가가기' 학습으로", "이 차시는 '다가가기' 학습으로", "이 차시는 '살펴보기' 학습으로"]
    two = [{"from": 1}, {"from": 2}]
    assert [p for p, _ in ns.by_stage_markers("m.pdf", two)] == [0, 2]  # 같은 단계 이름이 이어지면 한 번만
    assert ns.by_stage_markers("m.pdf", [{"from": 1}, {"from": 2}, {"from": 3}]) == []


def test_by_korean_markers_without_any_marker_gives_one_whole_section(fake_pdf):
    fake_pdf["k.pdf"] = ["표시 없음", "표시 없음"]
    secs = ns.by_korean_markers("[국어 4단원]", [{"from": 1, "to": 1, "title": "가"}, {"from": 2, "to": 2, "title": "나"}], "k.pdf")
    assert len(secs) == 1
    assert "차시 표시 못 찾음" in secs[0]["heading"]
    assert [p[0] for p in secs[0]["pages"]] == [0, 1]


# ── sections_for ──

def group(frm, to, title, pdf, pages=None):
    return {"from": frm, "to": to, "title": title, "pdf": pdf, "pages": pages}


def test_sections_for_missing_pdf_leaves_note_not_crash(tmp_path):
    secs = ns.sections_for("[수학 6단원]", "6. 그래프", [group(1, 1, "가", str(tmp_path / "없음.pdf")), group(2, 2, "나", "")])
    assert [s["pdf"] for s in secs] == ["", ""]
    assert "없음.pdf" in secs[0]["note"] and "경로 없음" in secs[1]["note"]
    assert all(s["pages"] == [] for s in secs)


def test_sections_for_whole_book_with_page_ranges_makes_one_section_per_lesson(tmp_path, fake_pdf):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"x")
    fake_pdf[str(pdf)] = [f"쪽{i}" for i in range(1, 31)]
    secs = ns.sections_for("[수학 6단원]", "6. 그래프", [group(1, 1, "가", str(pdf), (25, 26)), group(2, 2, "나", str(pdf), (27, 28))])
    assert [s["heading"] for s in secs] == ["## [수학 6단원] 1차시 가 (지도서 p.25~26)", "## [수학 6단원] 2차시 나 (지도서 p.27~28)"]
    assert secs[0]["pages"] == [(24, 25), (25, 26)]


def test_sections_for_split_file_is_whole_with_book_page_labels(tmp_path, fake_pdf):
    folder = tmp_path / "pdf_splits"
    folder.mkdir()
    pdf = folder / "a_p25-27.pdf"
    pdf.write_bytes(b"x")
    fake_pdf[str(pdf)] = ["a", "b", "c"]
    secs = ns.sections_for("[수학 6단원]", "6. 그래프", [group(1, 3, "가", str(pdf), (25, 27))])
    assert len(secs) == 1
    assert secs[0]["heading"] == "## [수학 6단원] 1~3차시 가 (지도서 p.25~27)"
    assert [lab for _, lab in secs[0]["pages"]] == [25, 26, 27]


def test_sections_for_adds_plan_section_first_only_if_not_a_lesson_file(tmp_path, fake_pdf, monkeypatch):
    folder = tmp_path / "pdf_splits"
    folder.mkdir()
    lesson, plan = folder / "l_p25-27.pdf", folder / "plan_p20-24.pdf"
    for p in (lesson, plan):
        p.write_bytes(b"x")
    fake_pdf[str(lesson)], fake_pdf[str(plan)] = ["a", "b", "c"], ["p", "q"]
    monkeypatch.setattr(ns.bu, "plan_split", lambda pdf, unit: plan)
    secs = ns.sections_for("[수학 6단원]", "6. 그래프", [group(1, 3, "가", str(lesson), (25, 27))])
    assert [s["heading"] for s in secs] == ["## [수학 6단원] 단원 개관", "## [수학 6단원] 1~3차시 가 (지도서 p.25~27)"]
    assert [lab for _, lab in secs[0]["pages"]] == [20, 21]
    # 개관 파일이 이미 차시 파일 중 하나면 또 넣지 않는다
    monkeypatch.setattr(ns.bu, "plan_split", lambda pdf, unit: lesson)
    assert len(ns.sections_for("[수학 6단원]", "6. 그래프", [group(1, 3, "가", str(lesson), (25, 27))])) == 1


def test_sections_for_whole_unit_pdf_without_pages_splits_by_lesson_markers(tmp_path, fake_pdf):
    """쪽 번호 없이 같은 PDF 를 쓰는 차시들은 한 묶음이 되어 쪽 머리의 '차시 / N차시' 표시로 나뉜다(국어)."""
    pdf = tmp_path / "국어.pdf"
    pdf.write_bytes(b"x")
    fake_pdf[str(pdf)] = ["개관", "1차시 / 14차시", "x", "2차시 / 14차시", "y"]
    secs = ns.sections_for("[국어 4단원]", "4. 글", [group(1, 1, "가", str(pdf)), group(2, 2, "나", str(pdf))])
    assert [s["heading"].split(" (")[0] for s in secs] == ["## [국어 4단원] 단원 개관", "## [국어 4단원] 1차시 가", "## [국어 4단원] 2차시 나"]


def test_sections_for_single_group_without_pages_is_whole_file(tmp_path, fake_pdf):
    pdf = tmp_path / "국어.pdf"
    pdf.write_bytes(b"x")
    fake_pdf[str(pdf)] = ["a", "b"]
    secs = ns.sections_for("[국어 4단원]", "4. 글", [group(1, 1, "가", str(pdf))])
    assert len(secs) == 1 and secs[0]["heading"] == "## [국어 4단원] 1차시 가 (지도서 국어.pdf)"
    assert [lab for _, lab in secs[0]["pages"]] == [1, 2]
