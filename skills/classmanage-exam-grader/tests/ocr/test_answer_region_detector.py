from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

from packages.student_extraction.answer_region_detector import _resolve_yolo_class
from packages.student_extraction.answer_region_detector import build_answer_region_detector


def test_resolve_yolo_class_uses_installed_ultralytics(monkeypatch) -> None:
    fake_module = ModuleType("ultralytics")

    class FakeYolo:
        pass

    fake_module.YOLO = FakeYolo
    monkeypatch.setitem(sys.modules, "ultralytics", fake_module)

    assert _resolve_yolo_class() is FakeYolo


def test_resolve_yolo_class_does_not_inject_repo_path(monkeypatch, tmp_path: Path) -> None:
    repo_path = str(tmp_path / "ultralytics")
    Path(repo_path).mkdir()
    original_sys_path = list(sys.path)

    monkeypatch.delitem(sys.modules, "ultralytics", raising=False)

    assert _resolve_yolo_class(repo_path) is not None
    assert sys.path == original_sys_path


def test_build_answer_region_detector_accepts_question_crop_label_aliases() -> None:
    detector = build_answer_region_detector(
        {
            "answer_region_detector": {
                "mode": "opencv",
            }
        }
    )

    assert "choice_answer_region" in detector.class_aliases
    assert "short_answer_line" in detector.class_aliases
    assert "descriptive_answer_area" in detector.class_aliases
