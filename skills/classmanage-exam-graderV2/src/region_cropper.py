from __future__ import annotations

from pathlib import Path

from PIL import Image


def crop_question_region(image_path: Path, box: dict, out_path: Path) -> None:
    image = Image.open(image_path)
    width, height = image.size

    left = max(0, int(float(box["x"]) * width))
    top = max(0, int(float(box["y"]) * height))
    right = min(width, int((float(box["x"]) + float(box["w"])) * width))
    bottom = min(height, int((float(box["y"]) + float(box["h"])) * height))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.crop((left, top, right, bottom)).save(out_path)
