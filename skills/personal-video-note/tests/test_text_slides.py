"""Regression tests for white-background text slides sharing one template.

These mimic real lecture decks: different slides differ by only ~2-3 % of the
pixels, bullets appearing differ by <1 %, and transitions may be dissolves.
"""
from pathlib import Path

import cv2
import numpy as np
import pytest

from lecturecapture.deduplicate import detect_duplicates_by_pixels
from lecturecapture.frames import (
    changed_pixel_ratio,
    detect_stable_states,
    iter_video_samples,
    normalized_gray,
)
from lecturecapture.pipeline import run_pipeline

W, H, FPS = 640, 360, 10


def _slide(title: str, bullets: list[str]) -> np.ndarray:
    img = np.full((H, W, 3), 255, np.uint8)
    cv2.rectangle(img, (0, 0), (W, 50), (120, 60, 20), -1)  # same header on every slide
    cv2.putText(img, title, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    for i, bullet in enumerate(bullets):
        cv2.putText(img, bullet, (40, 110 + i * 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    return img


A1 = _slide("Intro", ["Point one"])
A2 = _slide("Intro", ["Point one", "Point two"])
AF = _slide("Intro", ["Point one", "Point two", "Point three"])
B = _slide("Methods", ["Step alpha", "Step beta"])
C = _slide("Results", ["Chart here"])


class _Clip:
    def __init__(self) -> None:
        self.frames: list[np.ndarray] = []

    def hold(self, image: np.ndarray, seconds: float) -> None:
        self.frames.extend([image] * int(seconds * FPS))

    def fade(self, a: np.ndarray, b: np.ndarray, seconds: float) -> None:
        n = int(seconds * FPS)
        for k in range(n):
            t = (k + 1) / (n + 1)
            self.frames.append(cv2.addWeighted(a, 1 - t, b, t, 0))

    def write(self, path: Path) -> float:
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), FPS, (W, H))
        if not writer.isOpened():
            pytest.skip("MJPG VideoWriter unavailable")
        for frame in self.frames:
            writer.write(frame)
        writer.release()
        return len(self.frames) / FPS


def _states(path: Path, duration: float):
    samples = iter_video_samples(path, (0, 0, W, H), interval=0.75)
    return detect_stable_states(samples, duration)  # default parameters on purpose


def test_template_slides_differ_by_a_few_percent_and_bullets_by_less():
    # Documents why the old 8 % default merged every text slide into one.
    assert changed_pixel_ratio(AF, B) > 1.5
    assert changed_pixel_ratio(B, C) > 1.5
    assert changed_pixel_ratio(A1, A2) < 1.5
    assert changed_pixel_ratio(A2, AF) < 1.5


def test_hard_cuts_split_slides_and_animation_stays_one_slide(tmp_path: Path):
    clip = _Clip()
    clip.hold(A1, 4); clip.hold(A2, 4); clip.hold(AF, 6); clip.hold(B, 8); clip.hold(C, 8)
    path = tmp_path / "cut.avi"
    states = _states(path, clip.write(path))
    assert len(states) == 3
    assert [round(s.start_time) for s in states] == [0, 14, 22]


def test_representative_frame_is_the_completed_animation_state(tmp_path: Path):
    clip = _Clip()
    clip.hold(A1, 4); clip.hold(A2, 4); clip.hold(AF, 6); clip.hold(B, 8)
    path = tmp_path / "anim.avi"
    states = _states(path, clip.write(path))
    first = states[0]
    assert first.best_frame_time >= 8.0  # inside the final (completed) animation step
    assert changed_pixel_ratio(first.image, AF) < 0.5
    assert changed_pixel_ratio(first.image, A1) > 0.4


def test_slow_dissolves_do_not_create_extra_slides(tmp_path: Path):
    clip = _Clip()
    clip.hold(A1, 4); clip.hold(A2, 4); clip.hold(AF, 6)
    clip.fade(AF, B, 4); clip.hold(B, 8); clip.fade(B, C, 4); clip.hold(C, 8)
    path = tmp_path / "fade.avi"
    states = _states(path, clip.write(path))
    assert len(states) == 3
    # Representative frames must be clean slides, not blends.
    for state, clean in zip(states, [AF, B, C]):
        assert changed_pixel_ratio(state.image, clean) < 0.5


def test_duplicates_require_near_identical_pixels():
    entries = [("s1", normalized_gray(AF)), ("s2", normalized_gray(B)), ("s3", normalized_gray(C)), ("s4", normalized_gray(AF))]
    result = detect_duplicates_by_pixels(entries)
    assert result == {"s1": None, "s2": None, "s3": None, "s4": "s1"}


def test_pipeline_end_to_end_marks_reshown_slide_and_writes_diagnostics(tmp_path: Path):
    clip = _Clip()
    clip.hold(AF, 8); clip.hold(B, 8); clip.hold(AF, 8)
    video = tmp_path / "lecture.avi"
    clip.write(video)
    out = tmp_path / "out"
    run_pipeline(video, out, crop=(0, 0, W, H), diagnose=True)
    import json
    slides = json.loads((out / "project.json").read_text(encoding="utf-8"))["slides"]
    assert len(slides) == 3
    assert [s["duplicate_of"] for s in slides] == [None, None, "slide_0001"]
    rows = (out / "diagnostics.csv").read_text(encoding="utf-8").splitlines()
    assert rows[0] == "timestamp,ratio_prev,ratio_ref,removed_ref,state_index"
    assert len(rows) > 10


def test_similar_text_slides_with_tiny_total_difference_still_split(tmp_path: Path):
    # C -> A1 changes only ~1.3 % of the pixels (below the 1.5 % total threshold) but
    # replaces existing text; 20 repeats of A1/B/C must give 60 slides, not 41.
    clip = _Clip()
    for _ in range(20):
        clip.hold(A1, 10); clip.hold(B, 10); clip.hold(C, 10)
    path = tmp_path / "long.avi"
    duration = clip.write(path)
    states = _states(path, duration)
    assert len(states) == 60
    entries = [(f"s{i}", normalized_gray(s.image)) for i, s in enumerate(states)]
    duplicates = detect_duplicates_by_pixels(entries)
    assert sum(v is not None for v in duplicates.values()) == 57


def test_sensor_noise_and_compression_artifacts_do_not_split_slides(tmp_path: Path):
    rng = np.random.default_rng(7)

    def noisy(image: np.ndarray) -> np.ndarray:
        data = image.astype(np.int16) + rng.normal(0, 5, image.shape).astype(np.int16)
        data = np.clip(data, 0, 255).astype(np.uint8)
        ok, buf = cv2.imencode(".jpg", data, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        assert ok
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)

    clip = _Clip()
    for image, seconds in [(A1, 4), (A2, 4), (AF, 6), (B, 8), (C, 8)]:
        clip.frames.extend(noisy(image) for _ in range(int(seconds * FPS)))
    path = tmp_path / "noisy.avi"
    states = _states(path, clip.write(path))
    assert len(states) == 3
    assert [round(s.start_time) for s in states] == [0, 14, 22]


def test_pipeline_exports_subtitle_as_txt_and_srt_when_requested(tmp_path: Path):
    clip = _Clip()
    clip.hold(AF, 8)
    video = tmp_path / "one-slide.avi"
    clip.write(video)
    subtitle = tmp_path / "lecture.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:02,500\n오늘은 기초학력을 살펴봅니다.\n",
        encoding="utf-8",
    )
    reference = tmp_path / "정리수납 교안.hwpx"
    reference.write_bytes(b"test hwpx")
    out = tmp_path / "with-transcript"
    out.mkdir()
    (out / "summary.md").write_text("# Summary\n", encoding="utf-8")
    run_pipeline(
        video, out, crop=(0, 0, W, H), subtitle_path=subtitle,
        reference_paths=[reference], export_transcript_files=True,
    )
    assert "오늘은 기초학력을 살펴봅니다." in (out / "transcript.txt").read_text(encoding="utf-8-sig")
    assert "00:00:01,000 --> 00:00:02,500" in (out / "transcript.srt").read_text(encoding="utf-8-sig")
    assert (out / "attachments" / reference.name).read_bytes() == reference.read_bytes()
    assert f"[정리수납 교안.hwpx](<attachments/{reference.name}>)" in (out / "note.md").read_text(encoding="utf-8")
    assert "강의 요약 및 슬라이드별 정리 보기" in (out / "report.html").read_text(encoding="utf-8")
