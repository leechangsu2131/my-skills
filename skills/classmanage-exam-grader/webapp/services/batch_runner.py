from __future__ import annotations

import threading
from pathlib import Path

from webapp.services.pipeline import (
    build_reviewed_submission,
    materialize_submission_source_pdf,
    parse_answer_key_file,
    parse_student_file_bundle,
)
from webapp.services.review_artifacts import attach_review_artifacts
from webapp.store import WorkspaceStore


def start_batch_processing(
    *,
    batch_id: str,
    store: WorkspaceStore,
    batch_folder: Path,
    blank_exam_path: Path,
    answer_key_path: Path,
    student_paths: list[Path],
    auto_pick_pages: bool,
    fixed_page_offset: int | None,
) -> None:
    worker = threading.Thread(
        target=process_batch,
        kwargs={
            "batch_id": batch_id,
            "store": store,
            "batch_folder": batch_folder,
            "blank_exam_path": blank_exam_path,
            "answer_key_path": answer_key_path,
            "student_paths": student_paths,
            "auto_pick_pages": auto_pick_pages,
            "fixed_page_offset": fixed_page_offset,
        },
        daemon=True,
    )
    worker.start()


def process_batch(
    *,
    batch_id: str,
    store: WorkspaceStore,
    batch_folder: Path,
    blank_exam_path: Path,
    answer_key_path: Path,
    student_paths: list[Path],
    auto_pick_pages: bool,
    fixed_page_offset: int | None,
) -> None:
    reviewed_dir = batch_folder / "reviewed"
    reviewed_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = batch_folder / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    try:
        parsed_answer_key = parse_answer_key_file(answer_key_path)

        if parsed_answer_key.get("exam_title"):
            store.update_batch_title(batch_id, parsed_answer_key["exam_title"])

        ocr_metadata_dir = batch_folder / "ocr"
        ocr_metadata_dir.mkdir(parents=True, exist_ok=True)
        store.update_batch_assets(
            batch_id,
            blank_exam_path=blank_exam_path,
            ocr_metadata_path=ocr_metadata_dir / "layout.json",
            layout_status="ready",
        )

        batch_error_messages: list[str] = []
        for student_path in student_paths:
            try:
                parsed_students = parse_student_file_bundle(
                    student_path,
                    answer_key=parsed_answer_key,
                    blank_exam_path=blank_exam_path,
                    metadata_dir=ocr_metadata_dir,
                    student_page_offset=fixed_page_offset,
                    auto_pick_student_pages=auto_pick_pages,
                )
                for group_index, parsed_student in enumerate(parsed_students, start=1):
                    group_suffix = f"_g{group_index:02d}" if len(parsed_students) > 1 else ""
                    try:
                        reviewed = build_reviewed_submission(parsed_student, parsed_answer_key)
                        payload_path = reviewed_dir / f"{student_path.stem}{group_suffix}_reviewed.json"
                        store.save_payload(payload_path, reviewed.model_dump(mode="json"))
                        submission_source_path = materialize_submission_source_pdf(
                            student_path,
                            parsed_student,
                            inputs_dir,
                        )
                        submission = store.add_submission(
                            batch_id=batch_id,
                            student_name=reviewed.student_name,
                            student_number=reviewed.student_number,
                            status="needs_review" if reviewed.review_count else "approved",
                            total_score=reviewed.total_score,
                            total_points=reviewed.total_points,
                            review_count=reviewed.review_count,
                            payload_path=payload_path,
                            source_pdf_path=submission_source_path,
                        )
                        reviewed_with_artifacts = attach_review_artifacts(
                            submission_id=submission.id,
                            payload=reviewed,
                            blank_exam_path=blank_exam_path,
                            source_pdf_path=submission_source_path,
                            artifact_dir=batch_folder / "artifacts" / submission.id,
                        )
                        if reviewed_with_artifacts.model_dump(mode="json") != reviewed.model_dump(mode="json"):
                            store.save_payload(payload_path, reviewed_with_artifacts.model_dump(mode="json"))
                    except Exception as exc:
                        error_message = str(exc).strip() or exc.__class__.__name__
                        student_label = str(parsed_student.get("student_name") or f"{student_path.stem} #{group_index}")
                        batch_error_messages.append(f"{student_label}: {error_message}")
                        payload_path = reviewed_dir / f"{student_path.stem}{group_suffix}_failed.json"
                        store.save_payload(payload_path, {"error_message": error_message})
                        store.add_submission(
                            batch_id=batch_id,
                            student_name=student_label,
                            student_number=None,
                            status="failed",
                            total_score=0,
                            total_points=float(parsed_answer_key.get("total_points", 0)),
                            review_count=0,
                            payload_path=payload_path,
                            source_pdf_path=student_path,
                            error_message=error_message,
                        )
            except Exception as exc:
                error_message = str(exc).strip() or exc.__class__.__name__
                batch_error_messages.append(f"{student_path.name}: {error_message}")
                payload_path = reviewed_dir / f"{student_path.stem}_failed.json"
                store.save_payload(payload_path, {"error_message": error_message})
                store.add_submission(
                    batch_id=batch_id,
                    student_name=student_path.stem,
                    student_number=None,
                    status="failed",
                    total_score=0,
                    total_points=float(parsed_answer_key.get("total_points", 0)),
                    review_count=0,
                    payload_path=payload_path,
                    source_pdf_path=student_path,
                    error_message=error_message,
                )

        submissions = store.list_submissions(batch_id)
        if submissions and all(item.status == "failed" for item in submissions):
            store.update_batch_status(batch_id, "failed")
        elif any(item.status == "needs_review" for item in submissions):
            store.update_batch_status(batch_id, "needs_review")
        else:
            store.update_batch_status(batch_id, "approved")

        if batch_error_messages:
            _write_batch_error(batch_folder, "\n".join(batch_error_messages))
        else:
            _clear_batch_error(batch_folder)
    except Exception as exc:
        error_message = str(exc).strip() or exc.__class__.__name__
        store.update_batch_status(batch_id, "failed")
        _write_batch_error(batch_folder, error_message)


def _write_batch_error(batch_folder: Path, error_message: str) -> None:
    (batch_folder / "error.txt").write_text(error_message, encoding="utf-8")


def _clear_batch_error(batch_folder: Path) -> None:
    error_path = batch_folder / "error.txt"
    if error_path.exists():
        error_path.unlink()
