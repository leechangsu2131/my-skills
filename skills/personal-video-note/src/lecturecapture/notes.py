from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def _yaml_string(value: Any) -> str:
    """Quote strings safely for simple YAML front matter."""
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def format_time(seconds: float | int | None) -> str:
    seconds = max(0, int(float(seconds or 0)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_time_precise(seconds: float | int | None) -> str:
    value = max(0.0, float(seconds or 0))
    whole = int(value)
    base = format_time(whole)
    milliseconds = int(round((value - whole) * 1000))
    if milliseconds >= 1000:
        base = format_time(whole + 1)
        milliseconds = 0
    return f"{base}.{milliseconds:03d}"


def _youtube_timestamp_url(source_url: str, seconds: float) -> str:
    parsed = urlparse(source_url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["t"] = [f"{max(0, int(seconds))}s"]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def write_markdown_note(project: dict[str, Any], output_dir: Path) -> Path:
    """Write an Obsidian-friendly note with image embeds and per-slide workpads.

    Automatic multimodal summarization is intentionally not attempted here. The
    note combines each image with its aligned speech and leaves a clearly labeled
    summary field so the workflow can be reviewed or completed with a chosen model.
    """
    output_dir = Path(output_dir)
    metadata = project.get("metadata") or {}
    title = metadata.get("course") or project.get("project_id") or "강의 노트"
    has_summary = (output_dir / "summary.md").is_file()
    lines: list[str] = [
        "---",
        f"title: {_yaml_string(title)}",
        f"course: {_yaml_string(metadata.get('course', ''))}",
        f"lecturer: {_yaml_string(metadata.get('lecturer', ''))}",
        f"completed_on: {_yaml_string(metadata.get('completed_on', ''))}",
        f"source_video: {_yaml_string(project.get('source_video', ''))}",
        f"source_url: {_yaml_string(project.get('source_url', ''))}",
        f"duration_seconds: {int(float(project.get('duration', 0) or 0))}",
        "tags: [lecturecapture, lecture-notes]",
        "---",
        "",
        f"# {title}",
        "",
        "## 강의 정보",
        f"- 과정명: {metadata.get('course') or '미입력'}",
        f"- 강사: {metadata.get('lecturer') or '미입력'}",
        f"- 이수 일자: {metadata.get('completed_on') or '미입력'}",
        f"- 영상 길이: {format_time(project.get('duration', 0))}",
    ]

    attachment_pdf = metadata.get("pdf_path")
    if attachment_pdf:
        pdf_path = Path(str(attachment_pdf))
        lines.extend([f"- 강의 PDF: [PDF 열기]({pdf_path.as_posix()})"])
    for reference in metadata.get("reference_files", []):
        reference_path = str(reference.get("path", "")).replace("\\", "/")
        reference_name = str(reference.get("name") or Path(reference_path).name)
        if reference_path:
            lines.append(f"- 참고 자료: [{reference_name}](<{reference_path}>)")
    lines.extend([
        "",
        "> 이 노트는 개인 학습 정리용입니다. 슬라이드 이미지와 발언 연결은 자동 추출 결과이므로 중요한 내용은 원본과 대조하세요.",
        "",
    ])
    lines.extend(["## 전체 요약"])
    if has_summary:
        lines.extend(["[전체 요약과 슬라이드별 정리 보기](summary.md)", ""])
    else:
        lines.extend(["<!-- 강의 전체의 핵심 내용을 3~7문장으로 정리하세요. -->", ""])
    lines.extend(["## 슬라이드별 노트", ""])

    slides = project.get("slides") or []
    source_url = project.get("source_url")
    transcript_total = 0
    for slide_index, slide in enumerate(slides, start=1):
        slide_id = slide.get("slide_id", f"slide_{slide_index:04d}")
        image_path = (slide.get("image_path") or "").replace("\\", "/")
        start = float(slide.get("start_time", 0) or 0)
        end = float(slide.get("end_time", 0) or 0)
        lines.extend([
            f"### {slide_index}. {slide_id}",
            "",
        ])
        if image_path:
            lines.append(f"![{slide_id}]({image_path})")
            lines.append("")
        if source_url:
            link = _youtube_timestamp_url(str(source_url), start)
            lines.append(f"- 구간: [{format_time(start)}–{format_time(end)}]({link})")
        else:
            lines.append(f"- 구간: {format_time(start)}–{format_time(end)}")
        lines.append(f"- 대표 프레임 시각: {format_time(slide.get('best_frame_time', start))}")
        if slide.get("duplicate_of"):
            lines.append(f"- 중복 후보: {slide['duplicate_of']} (자동 삭제되지 않음)")
        lines.extend(["", "#### 연결된 발언", ""])
        segments = slide.get("transcript") or []
        if segments:
            for segment in segments:
                segment_start = format_time_precise(segment.get("start", 0))
                text = str(segment.get("text", "")).replace("\n", " ").strip()
                if text:
                    lines.append(f"> **[{segment_start}]** {text}")
                    transcript_total += 1
        else:
            lines.append("<!-- 이 구간에 연결된 자막/전사 텍스트가 없습니다. -->")
        lines.extend(["", "#### 슬라이드별 요약"])
        if has_summary:
            lines.append(f"[이 슬라이드 요약 보기](summary.md#{slide_id})")
        else:
            lines.append("<!-- 슬라이드의 핵심 주장, 개념, 예시를 발언 내용과 함께 2~4문장으로 요약하세요. -->")
        lines.extend([
            "", "#### 내 생각", "- 새롭게 알게 된 점:", "- 수업/업무에 적용할 점:",
            "- 더 확인할 질문:", "", "---", "",
        ])

    if not slides:
        lines.extend(["슬라이드가 추출되지 않았습니다. `project.json`의 경고와 영상 영역 설정을 확인하세요.", ""])
    lines.extend([
        "## 검토 메모",
        "- [ ] 슬라이드 누락/중복을 확인함",
        "- [ ] 중요 발언의 시간대와 문장을 원본과 대조함",
        "- [ ] 슬라이드별 요약을 작성하거나 선택한 요약 도구로 보완함",
        "",
        f"<!-- 생성 정보: 슬라이드 {len(slides)}개, 연결된 발언 {transcript_total}개 -->",
        "",
    ])

    path = output_dir / "note.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
