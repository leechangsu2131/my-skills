import numpy as np

from ocr.student_pages import select_student_pages_for_template


def test_equal_length_returns_same_stack() -> None:
    blank = [np.zeros((10, 10), dtype=np.uint8)]
    student = [np.ones((10, 10), dtype=np.uint8)]
    out, meta = select_student_pages_for_template(blank, student, auto_pick=True)
    assert len(out) == 1
    assert out[0] is student[0]
    assert meta["mode"] == "equal_length"
    assert meta["student_page_offset"] == 0


def test_auto_picks_highest_alignment_window(monkeypatch) -> None:
    blank = [np.zeros((20, 20), dtype=np.uint8)]
    student = [
        np.zeros((20, 20), dtype=np.uint8),
        np.ones((20, 20), dtype=np.uint8),
        np.full((20, 20), 2, dtype=np.uint8),
    ]

    class _Score:
        def __init__(self, value: float) -> None:
            self.score = value

    def fake_align(_blank, student_page):
        if student_page is student[1]:
            return _Score(0.95)
        return _Score(0.1)

    monkeypatch.setattr("ocr.student_pages.align_page_images", fake_align)

    out, meta = select_student_pages_for_template(blank, student, auto_pick=True)

    assert meta["mode"] == "auto_window"
    assert meta["student_page_offset"] == 1
    assert out[0] is student[1]


def test_fixed_offset_slices_stack() -> None:
    blank = [np.zeros((5, 5), dtype=np.uint8), np.zeros((5, 5), dtype=np.uint8)]
    student = [np.ones((5, 5), dtype=np.uint8) for _ in range(5)]

    out, meta = select_student_pages_for_template(
        blank,
        student,
        fixed_offset=2,
        auto_pick=False,
    )

    assert len(out) == 2
    assert meta["mode"] == "fixed_offset"
    assert meta["student_page_offset"] == 2
    assert out[0] is student[2]


def test_student_shorter_than_template_raises() -> None:
    blank = [np.zeros((5, 5), dtype=np.uint8) for _ in range(3)]
    student = [np.ones((5, 5), dtype=np.uint8) for _ in range(2)]

    try:
        select_student_pages_for_template(blank, student, auto_pick=True)
    except ValueError as exc:
        assert "fewer pages" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")
