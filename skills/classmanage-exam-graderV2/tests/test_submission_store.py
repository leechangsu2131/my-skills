import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from submission_store import build_submission_manifest  # type: ignore


def test_build_submission_manifest_groups_pages_by_student():
    files = [
        "aligned_exam_stu001_p1.png",
        "aligned_exam_stu001_p2.png",
        "aligned_exam_stu002_p1.png",
    ]

    manifest = build_submission_manifest(files)

    assert list(manifest.keys()) == ["stu001", "stu002"]
    assert manifest["stu001"]["pages"][0]["page"] == 1
    assert manifest["stu001"]["pages"][1]["page"] == 2
