from __future__ import annotations

import cv2
import numpy as np


def dhash(image: np.ndarray, hash_size: int = 8) -> str:
    """Difference hash as a short hexadecimal string."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    bits = resized[:, 1:] > resized[:, :-1]
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return f"{value:0{hash_size * hash_size // 4}x}"


def hash_distance(first: str, second: str) -> int:
    return (int(first, 16) ^ int(second, 16)).bit_count()


def detect_duplicates(slides: list[dict], max_distance: int = 5) -> list[dict]:
    """Legacy coarse duplicate marking from 64-bit dHash only.

    8x8 dHash cannot tell apart different text slides that share a template (their
    distance is typically 3-4), so the pipeline uses `detect_duplicates_by_pixels`.
    """
    prior: list[tuple[str, str]] = []
    for slide in slides:
        slide["duplicate_of"] = None
        for previous_id, previous_hash in prior:
            if hash_distance(slide["frame_hash"], previous_hash) <= max_distance:
                slide["duplicate_of"] = previous_id
                break
        if slide["duplicate_of"] is None:
            prior.append((slide["slide_id"], slide["frame_hash"]))
    return slides


def detect_duplicates_by_pixels(
    entries: list[tuple[str, np.ndarray]],
    max_changed_percent: float = 0.3,
    pixel_delta: int = 30,
) -> dict[str, str | None]:
    """Mark a slide as duplicate only if it is practically pixel-identical.

    `entries` is a list of (slide_id, normalized int16 grayscale thumbnail) in
    timeline order. Returns {slide_id: earlier_slide_id | None}. Nothing is
    deleted; different slides that merely share a template differ by ~2 % of the
    pixels or more, while a re-shown identical slide differs by ~0 %.
    """
    result: dict[str, str | None] = {}
    kept: list[tuple[str, np.ndarray]] = []
    for slide_id, thumb in entries:
        result[slide_id] = None
        for earlier_id, earlier in kept:
            changed = np.abs(thumb - earlier) >= pixel_delta
            if changed.size and np.count_nonzero(changed) * 100.0 / changed.size <= max_changed_percent:
                result[slide_id] = earlier_id
                break
        if result[slide_id] is None:
            kept.append((slide_id, thumb))
    return result
