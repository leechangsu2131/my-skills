import sys
from pathlib import Path

from PIL import Image


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from region_cropper import crop_question_region  # type: ignore


def test_crop_question_region_uses_normalized_box(tmp_path):
    image = Image.new("RGB", (100, 100), "white")
    image_path = tmp_path / "page.png"
    image.save(image_path)

    out_path = tmp_path / "crop.png"
    crop_question_region(
        image_path=image_path,
        box={"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.2},
        out_path=out_path,
    )

    cropped = Image.open(out_path)
    assert cropped.size == (30, 20)
