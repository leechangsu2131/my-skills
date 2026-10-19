from pathlib import Path

import cv2
import numpy as np

from lecturecapture.frames import detect_stable_states, iter_video_samples, write_slide_images


def _make_synthetic_video(path: Path) -> None:
    """Create a small clip: slide A, one transient flash, slide B."""
    width, height, fps = 160, 90, 20
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("OpenCV MJPG VideoWriter is unavailable in this environment")
    try:
        for index in range(fps * 4):
            t = index / fps
            frame = np.full((height, width, 3), 245, dtype=np.uint8)
            if t < 2.0:
                cv2.rectangle(frame, (12, 12), (72, 70), (20, 20, 20), -1)
                cv2.putText(frame, "A", (25, 56), cv2.FONT_HERSHEY_SIMPLEX, 1, (245, 245, 245), 2)
            elif t < 2.5:
                # A short transition flash should not become a retained slide.
                frame[:] = (100, 100, 100)
            else:
                cv2.rectangle(frame, (88, 15), (148, 74), (20, 20, 20), -1)
                cv2.putText(frame, "B", (103, 58), cv2.FONT_HERSHEY_SIMPLEX, 1, (245, 245, 245), 2)
            writer.write(frame)
    finally:
        writer.release()


def test_synthetic_video_stream_keeps_stable_slides_and_drops_short_flash(tmp_path: Path):
    video = tmp_path / "synthetic.avi"
    _make_synthetic_video(video)
    samples = iter_video_samples(video, (0, 0, 160, 90), interval=0.5)
    states = detect_stable_states(samples, duration=4.0, change_threshold=8.0, min_stable_seconds=1.0)

    assert len(states) == 2
    assert states[0].start_time == 0
    assert states[0].end_time == 2.0
    assert states[1].start_time == 2.5
    assert states[1].end_time >= 3.5
    images = write_slide_images(states, tmp_path / "slides")
    assert images == ["slide_0001.jpg", "slide_0002.jpg"]
    assert (tmp_path / "slides" / images[0]).is_file()
    assert (tmp_path / "slides" / images[1]).is_file()


def test_reference_frame_comparison_detects_gradual_change():
    from lecturecapture.deduplicate import dhash
    from lecturecapture.frames import FrameSample

    base = np.zeros((90, 160, 3), dtype=np.uint8)
    samples = [FrameSample(0.0, base, 0.0, dhash(base))]
    # A rectangle grows slowly. Each step changes only a small number of pixels,
    # but relative to the original reference frame the accumulated change grows.
    for i, t in enumerate((0.5, 1.0, 1.5, 2.0, 2.5, 3.0), start=1):
        image = base.copy()
        cv2.rectangle(image, (0, 0), (i * 8, 89), (255, 255, 255), -1)
        samples.append(FrameSample(t, image, float(i), dhash(image)))
    states = detect_stable_states(samples, duration=3.5, change_threshold=8.0, min_stable_seconds=0.5)

    # This specifically protects against comparing only consecutive samples.
    assert len(states) >= 2
    assert states[0].start_time == 0.0
    assert states[1].start_time == 1.0
