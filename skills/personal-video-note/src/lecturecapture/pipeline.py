from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path

from .align import align_transcript_to_slides
from .deduplicate import detect_duplicates_by_pixels
from .frames import DEFAULT_PIXEL_DELTA, detect_stable_states, iter_video_samples, normalized_gray, write_slide_images
from .ingest import video_metadata
from .models import Project, SlideEvent, TranscriptSegment
from .notes import write_markdown_note
from .report import write_report
from .storage import atomic_write_json
from .subtitles import parse_subtitles
from .transcribe import transcribe_video
from .transcript_export import export_transcript


DUPLICATE_MAX_CHANGED_PERCENT = 0.3


def _safe_project_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9가-힣._-]+", "-", value).strip("-._")
    return cleaned or "lecture-project"


def run_pipeline(
    video_path: Path,
    output_dir: Path,
    crop: tuple[int, int, int, int],
    interval: float = 0.75,
    change_threshold: float = 1.5,
    min_stable_seconds: float = 2.5,
    pixel_delta: int = DEFAULT_PIXEL_DELTA,
    removal_threshold: float = 0.25,
    diagnose: bool = False,
    subtitle_path: Path | None = None,
    transcribe: bool = False,
    whisper_model: str = "large-v3",
    language: str | None = "ko",
    source_url: str | None = None,
    course: str = "",
    lecturer: str = "",
    completed_on: str = "",
    pdf_path: Path | None = None,
    reference_paths: list[Path] | None = None,
    export_transcript_files: bool = False,
    initial_prompt: str | None = None,
    hotwords: str | None = None,
) -> Path:
    video_path, output_dir = Path(video_path).resolve(), Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    slide_dir = output_dir / "slides"
    backups_dir = output_dir / "backups"

    metadata = video_metadata(video_path)
    x, y, width, height = crop
    if x + width > int(metadata["width"]) or y + height > int(metadata["height"]):
        raise ValueError(f"선택 영역 {crop}가 영상 크기 {metadata['width']}x{metadata['height']}를 벗어납니다.")

    # Use a generator end-to-end: sampled frames are consumed incrementally, not
    # accumulated for the full duration of a lecture.
    duration = float(metadata["duration"])
    sample_stream = iter_video_samples(video_path, crop, interval=interval)
    diagnostics: list[dict] | None = [] if diagnose else None
    states = detect_stable_states(
        sample_stream, duration, change_threshold, min_stable_seconds,
        pixel_delta=pixel_delta, diagnostics=diagnostics, removal_threshold=removal_threshold,
    )
    if diagnostics is not None:
        with (output_dir / "diagnostics.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["timestamp", "ratio_prev", "ratio_ref", "removed_ref", "state_index"])
            writer.writeheader()
            writer.writerows(diagnostics)
    # Remove only the previous generated thumbnails so a shorter rerun cannot leave stale slides.
    if slide_dir.exists():
        for previous_image in slide_dir.glob("slide_*.jpg"):
            previous_image.unlink()
    image_names = write_slide_images(states, slide_dir)

    slide_events: list[SlideEvent] = []
    for idx, (state, image_name) in enumerate(zip(states, image_names), start=1):
        slide_events.append(SlideEvent(
            slide_id=f"slide_{idx:04d}",
            image_path=f"slides/{image_name}",
            first_seen=state.first_seen,
            stable_from=state.stable_from,
            best_frame_time=state.best_frame_time,
            start_time=state.start_time,
            end_time=state.end_time,
            duration=max(0.0, state.end_time - state.start_time),
            sharpness=state.sharpness,
            frame_hash=state.frame_hash,
            occurrences=[state.start_time],
        ))

    # Duplicates are marked from pixel differences of the representative images and
    # never deleted, so the timeline stays intact for review.
    thumbs = [(slide.slide_id, normalized_gray(state.image)) for slide, state in zip(slide_events, states)]
    duplicate_map = detect_duplicates_by_pixels(thumbs, DUPLICATE_MAX_CHANGED_PERCENT, pixel_delta)
    for slide in slide_events:
        slide.duplicate_of = duplicate_map.get(slide.slide_id)

    warnings: list[str] = []
    transcript: list[TranscriptSegment] = []
    if subtitle_path and not transcribe:
        transcript = parse_subtitles(subtitle_path)
        if not transcript:
            warnings.append("자막 파일은 읽었지만 유효한 자막 구간을 찾지 못했습니다.")
    elif transcribe:
        transcript = transcribe_video(
            video_path, model_size=whisper_model, language=language,
            initial_prompt=initial_prompt, hotwords=hotwords,
        )
    if export_transcript_files:
        export_transcript(transcript, output_dir)
    align_transcript_to_slides(slide_events, transcript)
    if not transcript:
        warnings.append("연결된 자막/전사 텍스트가 없습니다. SRT/VTT를 지정하거나 --transcribe를 사용하세요.")

    saved_pdf_relative: str | None = None
    if pdf_path is not None:
        pdf_path = Path(pdf_path).expanduser().resolve()
        if not pdf_path.is_file():
            raise FileNotFoundError(f"강의 PDF 파일을 찾을 수 없습니다: {pdf_path}")
        attachments_dir = output_dir / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)
        pdf_destination = attachments_dir / pdf_path.name
        if pdf_path != pdf_destination.resolve():
            shutil.copy2(pdf_path, pdf_destination)
        saved_pdf_relative = f"attachments/{pdf_destination.name}"

    saved_reference_files: list[dict[str, str]] = []
    if reference_paths:
        attachments_dir = output_dir / "attachments"
        attachments_dir.mkdir(parents=True, exist_ok=True)
        used_names: set[str] = set()
        for reference_path in reference_paths:
            reference_path = Path(reference_path).expanduser().resolve()
            if not reference_path.is_file():
                raise FileNotFoundError(f"참고 자료 파일을 찾을 수 없습니다: {reference_path}")
            destination_name = reference_path.name
            suffix = 2
            while destination_name.casefold() in used_names:
                destination_name = f"{reference_path.stem}-{suffix}{reference_path.suffix}"
                suffix += 1
            used_names.add(destination_name.casefold())
            reference_destination = attachments_dir / destination_name
            if reference_path != reference_destination.resolve():
                shutil.copy2(reference_path, reference_destination)
            saved_reference_files.append({
                "name": destination_name,
                "path": f"attachments/{destination_name}",
            })

    project = Project(
        schema_version=2,
        project_id=_safe_project_id(output_dir.name),
        source_video=str(video_path),
        source_url=source_url,
        duration=float(duration),
        fps=float(metadata["fps"]),
        width=int(metadata["width"]),
        height=int(metadata["height"]),
        crop={"x": x, "y": y, "width": width, "height": height},
        parameters={
            "sample_interval_seconds": interval,
            "change_threshold": change_threshold,
            "min_stable_seconds": min_stable_seconds,
            "hash": "dHash-64 (reference only)",
            "duplicate_method": "changed_pixel_ratio_percent",
            "duplicate_max_changed_percent": DUPLICATE_MAX_CHANGED_PERCENT,
            "change_metric": "changed_pixel_ratio_percent",
            "pixel_intensity_delta": pixel_delta,
            "removal_threshold": removal_threshold,
            "representative_frame": "last_still_frame_of_state",
            "streaming_frames": True,
            "transcript_export_enabled": export_transcript_files,
            "whisper_initial_prompt": (initial_prompt or "").strip(),
            "whisper_hotwords": (hotwords or "").strip(),
        },
        slides=slide_events,
        transcript=transcript,
        warnings=warnings,
        metadata={
            "course": course.strip(),
            "lecturer": lecturer.strip(),
            "completed_on": completed_on.strip(),
            "pdf_path": saved_pdf_relative or "",
            "reference_files": saved_reference_files,
        },
    )
    data = project.to_dict()
    atomic_write_json(output_dir / "project.json", data, backup_dir=backups_dir)
    write_report(data, output_dir)
    write_markdown_note(data, output_dir)
    return output_dir / "report.html"
