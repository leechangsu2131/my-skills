from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import cv2
import numpy as np

from .deduplicate import dhash


@dataclass
class FrameSample:
    timestamp: float
    image: np.ndarray
    sharpness: float
    frame_hash: str


@dataclass
class FrameState:
    first_seen: float
    stable_from: float
    start_time: float
    end_time: float
    best_frame_time: float
    image: np.ndarray
    sharpness: float
    frame_hash: str


@dataclass
class _StateAccumulator:
    first: FrameSample
    first_gray: np.ndarray
    first_content: np.ndarray
    prev_gray: np.ndarray
    last_timestamp: float
    # Representative frame = the LAST frame that was visually still (no motion
    # versus the previous sample). For bullet-by-bullet animations this is the
    # completed slide, and it avoids picking a half-faded frame at the very end.
    representative: FrameSample
    sample_count: int = 1

    @property
    def reference_gray(self) -> np.ndarray:
        # Compare every incoming sample to the first frame of this state, not only
        # the previous sample, so gradual changes cannot drift through unnoticed.
        return self.first_gray

    def add(self, sample: FrameSample, gray: np.ndarray, quiet: bool) -> None:
        self.last_timestamp = sample.timestamp
        self.sample_count += 1
        self.prev_gray = gray
        if quiet:
            self.representative = sample


def _crop_frame(frame: np.ndarray, crop: tuple[int, int, int, int]) -> np.ndarray:
    x, y, width, height = crop
    frame_h, frame_w = frame.shape[:2]
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError(f"잘라내기 영역은 양수 크기와 0 이상의 좌표여야 합니다: {crop}")
    if x + width > frame_w or y + height > frame_h:
        raise ValueError(f"자르기 영역 {crop}가 영상 크기 {frame_w}x{frame_h}를 벗어납니다.")
    return frame[y:y + height, x:x + width].copy()


GRAY_SIZE = (320, 180)
DEFAULT_PIXEL_DELTA = 30


def _prepare_gray(image: np.ndarray, size: tuple[int, int] = GRAY_SIZE) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return cv2.resize(gray, size, interpolation=cv2.INTER_AREA)


def normalized_gray(image: np.ndarray) -> np.ndarray:
    """Grayscale thumbnail (int16) used by every pixel-ratio comparison."""
    return _prepare_gray(image).astype(np.int16)


def _ratio(first_gray: np.ndarray, second_gray: np.ndarray, pixel_delta: int) -> float:
    changed = np.abs(first_gray - second_gray) >= pixel_delta
    return float(np.count_nonzero(changed) * 100.0 / changed.size)


def _content_mask(gray: np.ndarray, pixel_delta: int) -> np.ndarray:
    """Pixels that differ from the slide background (median brightness)."""
    return np.abs(gray - np.median(gray)) >= pixel_delta


def _removed_ratio(ref_gray: np.ndarray, ref_content: np.ndarray, cur_gray: np.ndarray, pixel_delta: int) -> float:
    """Percentage of pixels that were slide content in the reference and are gone now.

    A bullet or line appearing only ADDS content (about 0 % removed). Switching to
    another slide that shares the template also REMOVES the old text, even when
    the total changed-pixel ratio is small (similar-length slides can differ by
    only ~1.3 %). Polarity-agnostic: works for light-on-dark and dark-on-light.
    """
    cur_content = _content_mask(cur_gray, pixel_delta)
    changed = np.abs(ref_gray - cur_gray) >= pixel_delta
    removed = ref_content & ~cur_content & changed
    return float(np.count_nonzero(removed) * 100.0 / removed.size)


def changed_pixel_ratio(first: np.ndarray, second: np.ndarray, pixel_delta: int = DEFAULT_PIXEL_DELTA) -> float:
    """Return percentage of normalized pixels changed by at least `pixel_delta`.

    The result is in [0, 100]. Text slides on a white background change only a
    few percent of their pixels between two different slides (about 2-3 % in our
    synthetic tests) while a bullet appearing changes well under 1 %.
    """
    if pixel_delta < 0 or pixel_delta > 255:
        raise ValueError("픽셀 밝기 차이 기준은 0~255 범위여야 합니다.")
    return _ratio(normalized_gray(first), normalized_gray(second), pixel_delta)


def _difference(first: np.ndarray, second: np.ndarray) -> float:
    """Backward-compatible private alias for changed-pixel percentage."""
    return changed_pixel_ratio(first, second)


def iter_video_samples(
    video_path: Path,
    crop: tuple[int, int, int, int],
    interval: float = 0.75,
) -> Iterator[FrameSample]:
    """Yield sampled frames in timestamp order without storing a whole video.

    OpenCV decodes sequentially. Only each selected frame is retained until the
    consumer has processed it, keeping memory usage independent of video length.
    """
    if interval <= 0:
        raise ValueError("샘플링 간격은 0보다 커야 합니다.")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"영상을 열 수 없습니다: {video_path}")

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if fps <= 0:
            raise ValueError("영상의 FPS를 확인할 수 없어 프레임을 샘플링할 수 없습니다.")
        step = max(1, int(round(fps * interval)))
        frame_index = 0
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            if frame_index % step == 0:
                cropped = _crop_frame(frame, crop)
                gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
                sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                timestamp = frame_index / fps
                yield FrameSample(timestamp, cropped, sharpness, dhash(cropped))
            frame_index += 1
    finally:
        cap.release()


def sample_video(video_path: Path, crop: tuple[int, int, int, int], interval: float = 0.75) -> tuple[list[FrameSample], float]:
    """Compatibility helper for callers/tests that explicitly need a sample list.

    The main pipeline uses `iter_video_samples` directly and does not accumulate
    every sampled frame in memory.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"영상을 열 수 없습니다: {video_path}")
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = frame_count / fps if fps > 0 else 0.0
    finally:
        cap.release()
    samples = list(iter_video_samples(video_path, crop, interval=interval))
    if not samples:
        raise ValueError("영상에서 프레임을 하나도 추출하지 못했습니다.")
    return samples, duration


def _to_state(acc: _StateAccumulator, end_time: float, min_stable_seconds: float) -> FrameState:
    start = acc.first.timestamp
    end = max(start, end_time)
    return FrameState(
        first_seen=start,
        stable_from=min(end, start + min_stable_seconds),
        start_time=start,
        end_time=end,
        best_frame_time=acc.representative.timestamp,
        image=acc.representative.image,
        sharpness=acc.representative.sharpness,
        frame_hash=acc.representative.frame_hash,
    )


def detect_stable_states(
    samples: Iterable[FrameSample],
    duration: float,
    change_threshold: float = 1.5,
    min_stable_seconds: float = 2.5,
    pixel_delta: int = DEFAULT_PIXEL_DELTA,
    stable_epsilon: float = 0.2,
    diagnostics: list[dict] | None = None,
    removal_threshold: float = 0.25,
) -> list[FrameState]:
    """Incrementally identify persistent screen states.

    A new state starts when EITHER the changed-pixel percentage versus the first
    frame of the current state exceeds `change_threshold`, OR the percentage of
    reference content that disappeared exceeds `removal_threshold` (this catches
    slide changes that look small in total but replace existing text, while
    bullets that merely appear do not trigger it). `min_stable_seconds` also acts as the
    transition filter: dissolves/fades create short intermediate states that are
    shorter than this value and are dropped.

    `stable_epsilon` is the changed-pixel percentage versus the previous sample
    below which a frame counts as "still"; the representative image of a state is
    its last still frame.

    If `diagnostics` is a list, one row per sample is appended (timestamp,
    ratio_prev, ratio_ref, state_index) so thresholds can be tuned on real videos.
    Only the active state's reference/representative frames are kept in memory.
    """
    if not 0 <= change_threshold <= 100:
        raise ValueError("화면 변화 픽셀 비율 기준은 0~100 사이여야 합니다.")
    if not 0 <= removal_threshold <= 100:
        raise ValueError("기존 내용 사라짐 픽셀 비율 기준은 0~100 사이여야 합니다.")
    if min_stable_seconds < 0:
        raise ValueError("안정 시간은 0 이상이어야 합니다.")
    if not 0 <= stable_epsilon <= 100:
        raise ValueError("정지 프레임 변화 픽셀 비율 기준은 0~100 사이여야 합니다.")
    if pixel_delta < 0 or pixel_delta > 255:
        raise ValueError("픽셀 밝기 차이 기준은 0~255 범위여야 합니다.")

    states: list[FrameState] = []
    longest_state: FrameState | None = None
    active: _StateAccumulator | None = None
    state_index = 0

    def finish(acc: _StateAccumulator, end: float) -> FrameState:
        return _to_state(acc, end, min_stable_seconds)

    def log(sample: FrameSample, ratio_prev: float, ratio_ref: float, removed: float) -> None:
        if diagnostics is not None:
            diagnostics.append({
                "timestamp": round(sample.timestamp, 3),
                "ratio_prev": round(ratio_prev, 4),
                "ratio_ref": round(ratio_ref, 4),
                "removed_ref": round(removed, 4),
                "state_index": state_index,
            })

    for sample in samples:
        gray = normalized_gray(sample.image)
        if active is None:
            state_index = 1
            active = _StateAccumulator(sample, gray, _content_mask(gray, pixel_delta), gray, sample.timestamp, sample)
            log(sample, 0.0, 0.0, 0.0)
            continue
        ratio_prev = _ratio(active.prev_gray, gray, pixel_delta)
        ratio_ref = _ratio(active.reference_gray, gray, pixel_delta)
        removed = _removed_ratio(active.first_gray, active.first_content, gray, pixel_delta)
        if ratio_ref > change_threshold or removed > removal_threshold:
            previous = finish(active, sample.timestamp)
            if longest_state is None or (previous.end_time - previous.start_time) > (longest_state.end_time - longest_state.start_time):
                longest_state = previous
            if previous.end_time - previous.start_time + 1e-6 >= min_stable_seconds:
                states.append(previous)
            state_index += 1
            active = _StateAccumulator(sample, gray, _content_mask(gray, pixel_delta), gray, sample.timestamp, sample)
        else:
            active.add(sample, gray, quiet=ratio_prev <= stable_epsilon)
        log(sample, ratio_prev, ratio_ref, removed)

    if active is not None:
        final_end = max(active.first.timestamp, duration, active.last_timestamp)
        previous = finish(active, final_end)
        if longest_state is None or (previous.end_time - previous.start_time) > (longest_state.end_time - longest_state.start_time):
            longest_state = previous
        if previous.end_time - previous.start_time + 1e-6 >= min_stable_seconds:
            states.append(previous)

    # A short/very dynamic clip may contain no state meeting the stability cutoff.
    # Keeping the longest one gives the reviewer something useful to inspect.
    if not states and longest_state is not None:
        return [longest_state]
    return states


def write_slide_images(states: list[FrameState], output_dir: Path, jpeg_quality: int = 92) -> list[str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    relative_paths: list[str] = []
    for idx, state in enumerate(states, start=1):
        filename = f"slide_{idx:04d}.jpg"
        path = output_dir / filename
        ok = cv2.imwrite(str(path), state.image, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
        if not ok:
            raise OSError(f"슬라이드 이미지 저장 실패: {path}")
        relative_paths.append(filename)
    return relative_paths
