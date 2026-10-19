import pytest

from lecturecapture.crop import parse_crop
from lecturecapture.ingest import youtube_video_id


def test_parse_crop():
    assert parse_crop("10, 20, 300, 200") == (10, 20, 300, 200)
    with pytest.raises(ValueError):
        parse_crop("-1,0,100,100")


def test_youtube_video_id_variants():
    assert youtube_video_id("https://www.youtube.com/watch?v=AbCdEf12345&t=10") == "AbCdEf12345"
    assert youtube_video_id("https://youtu.be/AbCdEf12345") == "AbCdEf12345"
    assert youtube_video_id("https://www.youtube.com/shorts/AbCdEf12345") == "AbCdEf12345"
    assert youtube_video_id("https://example.com/watch?v=AbCdEf12345") is None
