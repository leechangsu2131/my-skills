from pathlib import Path

from lecturecapture.notes import write_markdown_note


def test_markdown_note_has_obsidian_embeds_manual_metadata_and_transcript(tmp_path: Path):
    project = {
        "project_id": "sample-lecture",
        "source_video": "C:/videos/sample.mp4",
        "source_url": None,
        "duration": 62.4,
        "metadata": {"course": "학급 경영 연수", "lecturer": "홍길동", "completed_on": "2026-10-12", "pdf_path": "attachments/handout.pdf"},
        "slides": [{
            "slide_id": "slide_0001",
            "image_path": "slides/slide_0001.jpg",
            "start_time": 10,
            "end_time": 20,
            "best_frame_time": 12,
            "duplicate_of": None,
            "transcript": [{"start": 11, "end": 14, "text": "학생의 배경지식을 확인합니다."}],
        }],
    }
    note = write_markdown_note(project, tmp_path)
    content = note.read_text(encoding="utf-8")
    assert 'course: "학급 경영 연수"' in content
    assert "![slide_0001](slides/slide_0001.jpg)" in content
    assert "학생의 배경지식을 확인합니다." in content
    assert "[00:00:11.000]" in content
    assert "#### 슬라이드별 요약" in content
    assert "[PDF 열기](attachments/handout.pdf)" in content
    assert "#### 내 생각" in content


def test_markdown_note_links_to_persistent_summary_sidecar(tmp_path: Path):
    (tmp_path / "summary.md").write_text("# Lecture summary\n", encoding="utf-8")
    project = {
        "project_id": "sample", "source_video": "sample.mp4", "duration": 10,
        "metadata": {},
        "slides": [{"slide_id": "slide_0001", "image_path": "slides/slide_0001.jpg", "start_time": 0, "end_time": 10}],
    }
    content = write_markdown_note(project, tmp_path).read_text(encoding="utf-8")
    assert "[전체 요약과 슬라이드별 정리 보기](summary.md)" in content
    assert "[이 슬라이드 요약 보기](summary.md#slide_0001)" in content
    assert "강의 전체의 핵심 내용을" not in content
