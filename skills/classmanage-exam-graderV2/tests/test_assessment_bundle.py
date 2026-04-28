import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from assessment_bundle import merge_assessment_bundle, normalize_assessment_bundle  # type: ignore


def test_normalize_assessment_bundle_keeps_questions_answers_and_total_points():
    payload = {
        "questions": [
            {"number": 1, "page": 1, "type": "객관식", "box": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.1}},
        ],
        "answers": [
            {"number": 1, "page": 1, "answer": "②", "points": 5},
        ],
        "total_points": 5,
    }

    data = normalize_assessment_bundle(payload)

    assert data["questions"][0]["number"] == 1
    assert data["answers"][0]["answer"] == "②"
    assert data["total_points"] == 5


def test_merge_assessment_bundle_answers_only_keeps_existing_boxes():
    existing = {
        "questions": [
            {"number": 1, "page": 1, "type": "객관식", "box": {"x": 0.9, "y": 0.8, "w": 0.1, "h": 0.1}},
        ],
        "answers": [],
        "total_points": 0,
    }
    incoming = {
        "questions": [
            {"number": 1, "page": 1, "type": "객관식", "box": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.1}},
        ],
        "answers": [
            {"number": 1, "page": 1, "answer": "②", "points": 5, "type": "객관식"},
        ],
        "total_points": 5,
    }

    merged = merge_assessment_bundle(existing, incoming, "answers_only")

    assert merged["questions"][0]["box"]["x"] == 0.9
    assert merged["answers"][0]["answer"] == "②"
    assert merged["total_points"] == 5
