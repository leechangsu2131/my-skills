from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp.schemas import ReviewItem, ReviewedSubmission
from webapp.services.pipeline import (
    build_reviewed_submission,
    finalize_submission_pdf,
    parse_answer_key_file,
    parse_student_file,
)
from webapp.store import BatchRecord, SubmissionRecord
from webapp.store import WorkspaceStore


APP_DIR = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(APP_DIR / "templates"))


def create_app(workspace: str | Path | None = None) -> FastAPI:
    root = Path(workspace or Path.cwd())
    store = WorkspaceStore(root)
    app = FastAPI(title="Classmanage Exam Grader")
    app.state.store = store
    app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

    @app.get("/")
    async def index(request: Request):
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            _build_index_context(request, store),
        )

    @app.post("/batches")
    async def create_batch(
        request: Request,
        blank_exam: UploadFile | None = File(None),
        answer_key: UploadFile | None = File(None),
        student_files: list[UploadFile] | None = File(None),
    ):
        blank_exam_name = _normalize_upload_name(blank_exam)
        if not blank_exam_name:
            return TEMPLATES.TemplateResponse(
                request,
                "index.html",
                _build_index_context(request, store, error_message="Blank exam PDF is required."),
                status_code=400,
            )

        answer_key_name = _normalize_upload_name(answer_key)
        if not answer_key_name:
            return TEMPLATES.TemplateResponse(
                request,
                "index.html",
                _build_index_context(request, store, error_message="Answer key file is required."),
                status_code=400,
            )

        valid_student_files = [upload for upload in (student_files or []) if _normalize_upload_name(upload)]
        if not valid_student_files:
            return TEMPLATES.TemplateResponse(
                request,
                "index.html",
                _build_index_context(request, store, error_message="Student exam files are required."),
                status_code=400,
            )

        title = Path(answer_key_name).stem
        batch = store.create_batch(title)
        batch_folder = Path(batch.folder)
        inputs_dir = batch_folder / "inputs"
        reviewed_dir = batch_folder / "reviewed"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        reviewed_dir.mkdir(parents=True, exist_ok=True)

        blank_exam_path = inputs_dir / blank_exam_name
        blank_exam_path.write_bytes(await blank_exam.read())
        store.update_batch_assets(batch.id, blank_exam_path=blank_exam_path, layout_status="pending")

        answer_key_path = inputs_dir / answer_key_name
        answer_key_path.write_bytes(await answer_key.read())
        try:
            parsed_answer_key = parse_answer_key_file(answer_key_path)

            if parsed_answer_key.get("exam_title"):
                store.update_batch_title(batch.id, parsed_answer_key["exam_title"])

            ocr_metadata_dir = batch_folder / "ocr"
            ocr_metadata_dir.mkdir(parents=True, exist_ok=True)
            store.update_batch_assets(
                batch.id,
                blank_exam_path=blank_exam_path,
                ocr_metadata_path=ocr_metadata_dir / "layout.json",
                layout_status="ready",
            )

            batch_error_messages: list[str] = []
            for index, upload in enumerate(valid_student_files, start=1):
                fallback_name = f"student-{index}{Path(upload.filename or '').suffix or '.json'}"
                student_path = inputs_dir / (_normalize_upload_name(upload) or fallback_name)
                student_path.write_bytes(await upload.read())
                try:
                    parsed_student = parse_student_file(
                        student_path,
                        blank_exam_path=blank_exam_path,
                        metadata_dir=ocr_metadata_dir,
                    )
                    reviewed = build_reviewed_submission(parsed_student, parsed_answer_key)
                    payload_path = reviewed_dir / f"{student_path.stem}_reviewed.json"
                    store.save_payload(payload_path, reviewed.model_dump(mode="json"))
                    store.add_submission(
                        batch_id=batch.id,
                        student_name=reviewed.student_name,
                        student_number=reviewed.student_number,
                        status="needs_review" if reviewed.review_count else "approved",
                        total_score=reviewed.total_score,
                        total_points=reviewed.total_points,
                        review_count=reviewed.review_count,
                        payload_path=payload_path,
                        source_pdf_path=student_path,
                    )
                except Exception as exc:
                    error_message = str(exc).strip() or exc.__class__.__name__
                    batch_error_messages.append(f"{student_path.name}: {error_message}")
                    payload_path = reviewed_dir / f"{student_path.stem}_failed.json"
                    store.save_payload(payload_path, {"error_message": error_message})
                    store.add_submission(
                        batch_id=batch.id,
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

            submissions = store.list_submissions(batch.id)
            if submissions and all(item.status == "failed" for item in submissions):
                store.update_batch_status(batch.id, "failed")
            elif any(item.status == "needs_review" for item in submissions):
                store.update_batch_status(batch.id, "needs_review")
            else:
                store.update_batch_status(batch.id, "approved")

            if batch_error_messages:
                _write_batch_error(batch_folder, "\n".join(batch_error_messages))
        except Exception as exc:
            error_message = str(exc).strip() or exc.__class__.__name__
            store.update_batch_status(batch.id, "failed")
            _write_batch_error(batch_folder, error_message)
            failed_batch = store.get_batch(batch.id)
            submissions = store.list_submissions(batch.id)
            return TEMPLATES.TemplateResponse(
                request,
                "batch_detail.html",
                {
                    "request": request,
                    "batch": _build_batch_view(store, failed_batch),
                    "submissions": [_build_submission_view(submission) for submission in submissions],
                    "error_message": error_message,
                },
                status_code=200,
            )

        return RedirectResponse(url=f"/batches/{batch.id}", status_code=303)

    @app.get("/batches/{batch_id}")
    async def batch_detail(request: Request, batch_id: str):
        batch = store.get_batch(batch_id)
        submissions = store.list_submissions(batch_id)
        return TEMPLATES.TemplateResponse(
            request,
            "batch_detail.html",
            {
                "request": request,
                "batch": _build_batch_view(store, batch),
                "submissions": [_build_submission_view(submission) for submission in submissions],
                "error_message": _read_batch_error(Path(batch.folder)),
            },
        )

    @app.get("/submissions/{submission_id}/review")
    async def submission_review(request: Request, submission_id: str):
        submission = store.get_submission(submission_id)
        batch = store.get_batch(submission.batch_id)
        payload = _load_review_payload(store, submission)
        return TEMPLATES.TemplateResponse(
            request,
            "submission_review.html",
            {
                "request": request,
                "batch": _build_batch_view(store, batch),
                "submission": _build_submission_view(submission),
                "items": [_build_item_view(item) for item in payload.items],
            },
        )

    @app.post("/submissions/{submission_id}/review")
    async def save_review(request: Request, submission_id: str) -> RedirectResponse:
        submission = store.get_submission(submission_id)
        form = await request.form()
        intent = str(form.get("intent", "save"))
        updated_payload, review_count = _apply_form_review_updates(store, submission, form)

        if intent == "approve" and review_count == 0:
            _finalize_submission(store, submission, updated_payload)
            return RedirectResponse(url=f"/batches/{submission.batch_id}", status_code=303)

        store.update_submission_status(
            submission.id,
            "needs_review" if review_count else "approved",
            review_count,
        )
        return RedirectResponse(url=f"/submissions/{submission_id}/review", status_code=303)

    @app.post("/submissions/{submission_id}/questions/{q_num}")
    async def update_review_item(
        submission_id: str,
        q_num: int,
        feedback_text: str = Form(...),
        review_status: str = Form(...),
    ) -> RedirectResponse:
        submission = store.get_submission(submission_id)
        payload = _load_review_payload(store, submission)
        updated_items = []
        for item in payload.items:
            if item.q_num == q_num:
                item = item.model_copy(
                    update={
                        "feedback_text": feedback_text,
                        "review_status": review_status,
                        "feedback_source": "teacher",
                        "feedback_confidence": 1.0,
                    }
                )
            updated_items.append(item)
        updated_payload = _recalculate_submission(payload.model_copy(update={"items": updated_items}))
        store.save_payload(Path(submission.payload_path), updated_payload.model_dump(mode="json"))
        store.update_submission_status(
            submission.id,
            "needs_review" if updated_payload.review_count else "approved",
            updated_payload.review_count,
        )
        return RedirectResponse(url=f"/submissions/{submission_id}/review", status_code=303)

    @app.get("/submissions/{submission_id}/download")
    async def download_submission_pdf(submission_id: str) -> FileResponse:
        submission = store.get_submission(submission_id)
        if not submission.output_pdf_path:
            raise RuntimeError("Finalized PDF is not available yet.")
        output_path = Path(submission.output_pdf_path)
        return FileResponse(output_path, media_type="application/pdf", filename=output_path.name)

    return app


def _build_index_context(request: Request, store: WorkspaceStore, error_message: str | None = None) -> dict[str, Any]:
    context: dict[str, Any] = {
        "request": request,
        "batches": [_build_batch_view(store, batch) for batch in store.list_batches()],
    }
    if error_message:
        context["error_message"] = error_message
    return context


def _normalize_upload_name(upload: UploadFile | None) -> str | None:
    if upload is None:
        return None
    filename = Path((upload.filename or "").strip()).name
    return filename or None


def _write_batch_error(batch_folder: Path, error_message: str) -> None:
    (batch_folder / "error.txt").write_text(error_message, encoding="utf-8")


def _read_batch_error(batch_folder: Path) -> str | None:
    error_path = batch_folder / "error.txt"
    if not error_path.exists():
        return None
    message = error_path.read_text(encoding="utf-8").strip()
    return message or None


def _build_batch_view(store: WorkspaceStore, batch: BatchRecord) -> dict[str, Any]:
    submissions = store.list_submissions(batch.id)
    if not submissions:
        status = "failed"
    elif any(row.status == "needs_review" for row in submissions):
        status = "needs_review"
    elif all(row.status == "approved" for row in submissions):
        status = "approved"
    else:
        status = batch.status
    return {
        "id": batch.id,
        "title": batch.title,
        "status": status,
        "submission_count": len(submissions),
        "review_submission_count": sum(1 for row in submissions if row.status == "needs_review"),
        "review_count": sum(row.review_count for row in submissions),
        "finalized_count": sum(1 for row in submissions if row.status == "finalized"),
    }


def _build_submission_view(submission: SubmissionRecord) -> dict[str, Any]:
    return {
        "id": submission.id,
        "batch_id": submission.batch_id,
        "student_name": submission.student_name,
        "student_number": submission.student_number,
        "status": submission.status,
        "review_status": submission.status,
        "total_score": submission.total_score,
        "total_points": submission.total_points,
        "review_count": submission.review_count,
        "output_pdf_path": submission.output_pdf_path,
        "error_message": submission.error_message,
    }


def _build_item_view(item: ReviewItem) -> dict[str, Any]:
    if item.feedback_confidence >= 0.9:
        confidence = "high"
    elif item.feedback_confidence < 0.5:
        confidence = "low"
    else:
        confidence = "medium"
    return {
        **item.model_dump(mode="json"),
        "max_points": item.points_possible,
        "confidence": confidence,
    }


def _load_review_payload(store: WorkspaceStore, submission: SubmissionRecord) -> ReviewedSubmission:
    return ReviewedSubmission.model_validate(store.load_payload(submission.payload_path))


def _apply_form_review_updates(
    store: WorkspaceStore,
    submission: SubmissionRecord,
    form: Any,
) -> tuple[ReviewedSubmission, int]:
    payload = _load_review_payload(store, submission)
    updated_items = []
    for item in payload.items:
        q_num = item.q_num
        feedback_text = str(form.get(f"feedback_{q_num}", item.feedback_text))
        review_status = str(form.get(f"review_status_{q_num}", item.review_status))
        points_earned = float(form.get(f"points_earned_{q_num}", item.points_earned))
        changed = (
            feedback_text != item.feedback_text
            or review_status != item.review_status
            or points_earned != item.points_earned
        )
        updated_items.append(
            item.model_copy(
                update={
                    "feedback_text": feedback_text,
                    "review_status": review_status,
                    "points_earned": points_earned,
                    "feedback_source": "teacher" if changed else item.feedback_source,
                    "feedback_confidence": 1.0 if changed else item.feedback_confidence,
                }
            )
        )
    updated_payload = _recalculate_submission(payload.model_copy(update={"items": updated_items}))
    store.save_payload(Path(submission.payload_path), updated_payload.model_dump(mode="json"))
    return updated_payload, updated_payload.review_count


def _recalculate_submission(payload: ReviewedSubmission) -> ReviewedSubmission:
    correct_count = sum(1 for item in payload.items if item.correct is True)
    wrong_count = sum(1 for item in payload.items if item.correct is False)
    review_count = sum(1 for item in payload.items if item.review_status == "needs_review")
    total_score = sum(item.points_earned for item in payload.items)
    return payload.model_copy(
        update={
            "total_score": total_score,
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "review_count": review_count,
        }
    )


def _finalize_submission(store: WorkspaceStore, submission: SubmissionRecord, payload: ReviewedSubmission) -> Path:
    batch = store.get_batch(submission.batch_id)
    batch_folder = Path(batch.folder)
    output_dir = batch_folder / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{Path(submission.source_pdf_path).stem}_feedback.pdf"
    result_path = finalize_submission_pdf(Path(submission.source_pdf_path), payload, output_path)
    store.update_submission_status(submission.id, "finalized", 0)
    store.update_submission_output(submission.id, result_path)
    return result_path


app = create_app()
