from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp.schemas import ReviewItem, ReviewedSubmission
from webapp.services.pipeline import (
    build_reviewed_submission,
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
        answer_key: UploadFile = File(...),
        student_files: list[UploadFile] = File(...),
    ):
        valid_student_files = [upload for upload in student_files if _normalize_upload_name(upload)]
        title = Path(_normalize_upload_name(answer_key) or "answer_key").stem
        batch = store.create_batch(title)
        batch_folder = Path(batch.folder)
        inputs_dir = batch_folder / "inputs"
        reviewed_dir = batch_folder / "reviewed"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        reviewed_dir.mkdir(parents=True, exist_ok=True)

        answer_key_path = inputs_dir / (_normalize_upload_name(answer_key) or "answer_key.json")
        answer_key_path.write_bytes(await answer_key.read())
        parsed_answer_key = parse_answer_key_file(answer_key_path)

        if parsed_answer_key.get("exam_title"):
            store.update_batch_title(batch.id, parsed_answer_key["exam_title"])

        for index, upload in enumerate(valid_student_files, start=1):
            fallback_name = f"student-{index}{Path(upload.filename or '').suffix or '.json'}"
            student_path = inputs_dir / (_normalize_upload_name(upload) or fallback_name)
            student_path.write_bytes(await upload.read())
            parsed_student = parse_student_file(student_path)
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
                "error_message": None,
            },
        )

    @app.get("/submissions/{submission_id}/review")
    async def submission_review(request: Request, submission_id: str):
        submission = store.get_submission(submission_id)
        batch = store.get_batch(submission.batch_id)
        payload = ReviewedSubmission.model_validate(store.load_payload(submission.payload_path))
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

    return app


def _build_index_context(request: Request, store: WorkspaceStore, error_message: str | None = None) -> dict[str, Any]:
    context: dict[str, Any] = {
        "request": request,
        "batches": [_build_batch_view(store, batch) for batch in store.list_batches()],
    }
    if error_message:
        context["error_message"] = error_message
    return context


def _normalize_upload_name(upload: UploadFile) -> str | None:
    filename = Path((upload.filename or "").strip()).name
    return filename or None


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


app = create_app()
