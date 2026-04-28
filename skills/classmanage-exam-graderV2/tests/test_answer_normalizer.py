import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from answer_normalizer import normalize_objective_answer, normalize_short_answer  # type: ignore


def test_normalize_objective_answer_maps_common_ocr_variants():
    assert normalize_objective_answer("2)") == "②"
    assert normalize_objective_answer("O") == "○"


def test_normalize_short_answer_strips_noise():
    assert normalize_short_answer("  -12 cm ") == "-12cm"
