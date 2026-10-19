import numpy as np
import pytest

from lecturecapture.deduplicate import dhash
from lecturecapture.frames import FrameSample, detect_stable_states


def test_stable_state_detection_keeps_long_states_and_filters_short_transient():
    a = np.zeros((80, 120, 3), dtype=np.uint8)
    b = np.full((80, 120, 3), 220, dtype=np.uint8)
    transient = np.full((80, 120, 3), 80, dtype=np.uint8)
    samples = []
    for timestamp, image in [
        (0.0, a), (0.5, a), (1.0, a), (1.5, a),
        (2.0, transient), (2.5, b), (3.0, b), (3.5, b), (4.0, b),
    ]:
        samples.append(FrameSample(timestamp, image, float(timestamp), dhash(image)))
    states = detect_stable_states(samples, duration=4.5, change_threshold=8.0, min_stable_seconds=1.0)
    assert len(states) == 2
    assert states[0].first_seen == 0.0
    assert states[1].first_seen == 2.5
    assert states[1].stable_from == 3.5


def test_empty_samples_return_empty_states():
    assert detect_stable_states([], duration=0) == []


@pytest.mark.parametrize(
    "options, message",
    [
        ({"removal_threshold": -0.1}, "기존 내용 사라짐"),
        ({"removal_threshold": 100.1}, "기존 내용 사라짐"),
        ({"stable_epsilon": -0.1}, "정지 프레임 변화"),
        ({"stable_epsilon": 100.1}, "정지 프레임 변화"),
    ],
)
def test_invalid_pixel_thresholds_are_rejected(options, message):
    with pytest.raises(ValueError, match=message):
        detect_stable_states([], duration=0, **options)
