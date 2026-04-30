import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from ocr_engine import OcrEngine, extract_ocr_candidates  # type: ignore


def test_extract_ocr_candidates_reads_paddleocr_v3_dict_result():
    result = [
        {
            "rec_texts": ["2)", "x=3"],
            "rec_scores": [0.91, 0.73],
        }
    ]

    assert extract_ocr_candidates(result) == [
        {"text": "2)", "confidence": 0.91},
        {"text": "x=3", "confidence": 0.73},
    ]


def test_extract_ocr_candidates_reads_legacy_tuple_result():
    result = [
        [
            [[[0, 0], [10, 0], [10, 10], [0, 10]], ("O", 0.88)],
            [[[0, 0], [10, 0], [10, 10], [0, 10]], ["4", "0.84"]],
        ]
    ]

    assert extract_ocr_candidates(result) == [
        {"text": "O", "confidence": 0.88},
        {"text": "4", "confidence": 0.84},
    ]


def test_ocr_engine_prefers_predict_when_available(tmp_path):
    image = tmp_path / "crop.png"
    image.write_bytes(b"fake")

    class FakeReader:
        def __init__(self):
            self.called = None

        def predict(self, path):
            self.called = ("predict", path)
            return [{"rec_texts": ["5"], "rec_scores": [0.95]}]

        def ocr(self, path):
            raise AssertionError("predict should be preferred for PaddleOCR 3.x")

    reader = FakeReader()
    engine = OcrEngine(reader=reader)

    assert engine.read_text(image) == {"candidates": [{"text": "5", "confidence": 0.95}]}
    assert reader.called == ("predict", str(image))
