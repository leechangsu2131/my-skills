from lecturecapture.deduplicate import hash_distance, detect_duplicates


def test_hash_distance():
    assert hash_distance("0000", "0001") == 1


def test_duplicate_marking_does_not_delete_rows():
    slides = [
        {"slide_id": "s1", "frame_hash": "ffff"},
        {"slide_id": "s2", "frame_hash": "ffff"},
        {"slide_id": "s3", "frame_hash": "0000"},
    ]
    result = detect_duplicates(slides, max_distance=1)
    assert len(result) == 3
    assert result[1]["duplicate_of"] == "s1"
    assert result[2]["duplicate_of"] is None
