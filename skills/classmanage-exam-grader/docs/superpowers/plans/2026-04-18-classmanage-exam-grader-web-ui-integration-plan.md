# Classmanage Exam Grader Web UI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `classmanage-exam-grader` around a FastAPI review UI while reusing the existing OCR, parsing, grading, analysis, and PDF annotation engines.

**Architecture:** Create a new `webapp/` package inside `skills/classmanage-exam-grader`, copy the approved UI templates and stylesheet from the prototype, then replace the prototype's simplified parsing/grading/annotation services with a thin adapter around `answer_key_parser.py`, `ocr_extractor.py`, `grader.py`, `analysis_merger.py`, and `pdf_annotator.py`. Persist batch state in `data/web/app.db` and store per-batch payload JSON/PDF artifacts under `data/web/batches/<batch_id>/...`, leaving the existing CLI files available as a secondary entry point.

**Tech Stack:** Python, FastAPI, Jinja2, SQLite, Pydantic, PyMuPDF, pytest, Gemini CLI

---

## File Map

### Create

- `skills/classmanage-exam-grader/README.md`
- `skills/classmanage-exam-grader/webapp/__init__.py`
- `skills/classmanage-exam-grader/webapp/main.py`
- `skills/classmanage-exam-grader/webapp/schemas.py`
- `skills/classmanage-exam-grader/webapp/store.py`
- `skills/classmanage-exam-grader/webapp/services/__init__.py`
- `skills/classmanage-exam-grader/webapp/services/pipeline.py`
- `skills/classmanage-exam-grader/webapp/templates/base.html`
- `skills/classmanage-exam-grader/webapp/templates/index.html`
- `skills/classmanage-exam-grader/webapp/templates/batch_detail.html`
- `skills/classmanage-exam-grader/webapp/templates/submission_review.html`
- `skills/classmanage-exam-grader/webapp/static/styles.css`
- `skills/classmanage-exam-grader/tests/webapp/test_homepage.py`
- `skills/classmanage-exam-grader/tests/webapp/test_batch_flow.py`
- `skills/classmanage-exam-grader/tests/webapp/test_pipeline.py`
- `skills/classmanage-exam-grader/tests/webapp/test_batch_status.py`
- `skills/classmanage-exam-grader/tests/webapp/test_upload_validation.py`
- `skills/classmanage-exam-grader/tests/webapp/test_review_updates.py`
- `skills/classmanage-exam-grader/tests/webapp/test_finalize_flow.py`
- `skills/classmanage-exam-grader/tests/webapp/test_store_migrations.py`

### Modify

- `skills/classmanage-exam-grader/.gitignore`
- `skills/classmanage-exam-grader/requirements.txt`

### Keep Untouched Unless a Test Forces a Small Adapter

- `skills/classmanage-exam-grader/grade_exam.py`
- `skills/classmanage-exam-grader/ocr_extractor.py`
- `skills/classmanage-exam-grader/answer_key_parser.py`
- `skills/classmanage-exam-grader/grader.py`
- `skills/classmanage-exam-grader/analysis_merger.py`
- `skills/classmanage-exam-grader/pdf_annotator.py`
- `skills/classmanage-exam-grader/llm_subjective_grader.py`

### Responsibilities

- `webapp/main.py`: FastAPI routes, template rendering, request validation, batch/submission view-model helpers
- `webapp/schemas.py`: Pydantic models for answer-key, student answers, review items, and reviewed submissions
- `webapp/store.py`: SQLite batch/submission metadata plus JSON payload persistence under `data/web/`
- `webapp/services/pipeline.py`: Thin adapter from uploaded files to the existing engine modules, plus final PDF generation bridge
- `webapp/templates/*.html`: Imported UI screens from the prototype
- `webapp/static/styles.css`: Imported UI look-and-feel from the prototype
- `tests/webapp/*.py`: TDD coverage for home page, batch creation, PDF routing, validation, review editing, finalization, and store migration
- `README.md`: Web-first run instructions with CLI kept as a fallback workflow

## Task 1: Bootstrap the Web App Shell

**Files:**
- Modify: `skills/classmanage-exam-grader/requirements.txt`
- Modify: `skills/classmanage-exam-grader/.gitignore`
- Create: `skills/classmanage-exam-grader/webapp/__init__.py`
- Create: `skills/classmanage-exam-grader/webapp/main.py`
- Create: `skills/classmanage-exam-grader/webapp/schemas.py`
- Create: `skills/classmanage-exam-grader/webapp/store.py`
- Create: `skills/classmanage-exam-grader/webapp/templates/base.html`
- Create: `skills/classmanage-exam-grader/webapp/templates/index.html`
- Create: `skills/classmanage-exam-grader/webapp/templates/batch_detail.html`
- Create: `skills/classmanage-exam-grader/webapp/templates/submission_review.html`
- Create: `skills/classmanage-exam-grader/webapp/static/styles.css`
- Test: `skills/classmanage-exam-grader/tests/webapp/test_homepage.py`

- [ ] **Step 1: Write the failing shell/bootstrap tests**

```python
from fastapi.testclient import TestClient

from webapp.main import create_app


def test_homepage_renders_uploaded_batch_shell(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "Teacher Review Workstation" in response.text
    assert "batch" in response.text.lower()


def test_workspace_store_uses_data_web_directory(tmp_path) -> None:
    app = create_app(tmp_path)

    assert app.state.store.data_dir == tmp_path / "data" / "web"
    assert app.state.store.db_path == tmp_path / "data" / "web" / "app.db"
```

- [ ] **Step 2: Run the shell/bootstrap tests to verify they fail**

Run:

```bash
cd skills/classmanage-exam-grader
python -m pytest tests/webapp/test_homepage.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'webapp'`

- [ ] **Step 3: Add dependencies, ignore rules, copied UI assets, and a minimal app shell**

Update `skills/classmanage-exam-grader/requirements.txt` to:

```text
PyMuPDF>=1.27.0
fastapi>=0.116,<1
uvicorn>=0.35,<1
jinja2>=3.1,<4
python-multipart>=0.0.20,<1
pydantic>=2.11,<3
httpx>=0.28,<1
pytest>=8.3,<9
```

Update `skills/classmanage-exam-grader/.gitignore` to:

```gitignore
data/input/
data/extracted/
data/graded/
data/output/
data/web/
__pycache__/
*.pyc
```

Copy the UI assets from the approved prototype:

```powershell
New-Item -ItemType Directory -Force `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\webapp', `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\webapp\templates', `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\webapp\static', `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\tests\webapp' | Out-Null

Copy-Item 'C:\Users\user\.gemini\antigravity\scratch\repos\exam-feedback-studio\.worktrees\exam-feedback-mvp\app\templates\base.html' `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\webapp\templates\base.html'
Copy-Item 'C:\Users\user\.gemini\antigravity\scratch\repos\exam-feedback-studio\.worktrees\exam-feedback-mvp\app\templates\index.html' `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\webapp\templates\index.html'
Copy-Item 'C:\Users\user\.gemini\antigravity\scratch\repos\exam-feedback-studio\.worktrees\exam-feedback-mvp\app\templates\batch_detail.html' `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\webapp\templates\batch_detail.html'
Copy-Item 'C:\Users\user\.gemini\antigravity\scratch\repos\exam-feedback-studio\.worktrees\exam-feedback-mvp\app\templates\submission_review.html' `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\webapp\templates\submission_review.html'
Copy-Item 'C:\Users\user\.gemini\antigravity\scratch\repos\exam-feedback-studio\.worktrees\exam-feedback-mvp\app\static\styles.css' `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\webapp\static\styles.css'
Copy-Item 'C:\Users\user\.gemini\antigravity\scratch\repos\exam-feedback-studio\.worktrees\exam-feedback-mvp\app\schemas.py' `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\webapp\schemas.py'
Copy-Item 'C:\Users\user\.gemini\antigravity\scratch\repos\exam-feedback-studio\.worktrees\exam-feedback-mvp\app\store.py' `
  'C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader\webapp\store.py'
```

Create `skills/classmanage-exam-grader/webapp/__init__.py`:

```python
"""FastAPI web UI for classmanage-exam-grader."""
```

Adjust the copied `skills/classmanage-exam-grader/webapp/store.py` so `WorkspaceStore.__init__` uses the web-specific directory:

```python
class WorkspaceStore:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.data_dir = workspace / "data" / "web"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "app.db"
        self._init_db()
```

Create `skills/classmanage-exam-grader/webapp/main.py`:

```python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
            {"request": request, "batches": []},
        )

    return app


app = create_app()
```

- [ ] **Step 4: Run the shell/bootstrap tests to verify they pass**

Run:

```bash
cd skills/classmanage-exam-grader
python -m pytest tests/webapp/test_homepage.py -q
```

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit the shell/bootstrap task**

```bash
git add requirements.txt .gitignore webapp tests/webapp/test_homepage.py
git commit -m "feat: add webapp shell and imported UI assets"
```

## Task 2: Add JSON Batch Creation and Review Payload Generation

**Files:**
- Create: `skills/classmanage-exam-grader/webapp/services/__init__.py`
- Create: `skills/classmanage-exam-grader/webapp/services/pipeline.py`
- Modify: `skills/classmanage-exam-grader/webapp/main.py`
- Test: `skills/classmanage-exam-grader/tests/webapp/test_batch_flow.py`

- [ ] **Step 1: Write the failing batch-flow test**

```python
import json

from fastapi.testclient import TestClient

from webapp.main import create_app


def test_uploading_json_inputs_creates_batch_and_review_page(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    answer_key_payload = {
        "exam_title": "Fractions Unit Quiz",
        "questions": [
            {
                "q_num": 1,
                "type": "multiple_choice",
                "answer": "3",
                "points": 5,
                "explanation": "Use a common denominator before comparing fractions.",
            }
        ],
    }
    student_payload = {
        "student_name": "Kim Minsu",
        "student_number": 7,
        "answers": [
            {"q_num": 1, "type": "multiple_choice", "answer": "2", "confidence": "high", "page": 1}
        ],
    }

    response = client.post(
        "/batches",
        files=[
            ("answer_key", ("answer_key.json", json.dumps(answer_key_payload), "application/json")),
            ("student_files", ("kim.json", json.dumps(student_payload), "application/json")),
        ],
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Fractions Unit Quiz" in response.text
    assert "Kim Minsu" in response.text

    store = app.state.store
    batch = store.list_batches()[0]
    submission = store.list_submissions(batch.id)[0]

    review_response = client.get(f"/submissions/{submission.id}/review")

    assert review_response.status_code == 200
    assert "Use a common denominator" in review_response.text
```

- [ ] **Step 2: Run the batch-flow test to verify it fails**

Run:

```bash
cd skills/classmanage-exam-grader
python -m pytest tests/webapp/test_batch_flow.py -q
```

Expected: FAIL with `404 Not Found` for `/batches` or `/submissions/.../review`

- [ ] **Step 3: Add the pipeline adapter and batch/review routes**

Create `skills/classmanage-exam-grader/webapp/services/__init__.py`:

```python
"""Service layer for the web UI adapter."""
```

Create `skills/classmanage-exam-grader/webapp/services/pipeline.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from analysis_merger import merge_analysis
from answer_key_parser import load_answer_key_json, parse_answer_key_pdf
from grader import grade_student, load_config
from ocr_extractor import extract_answers
from webapp.schemas import ReviewedSubmission, ReviewItem


def parse_answer_key_file(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        return load_answer_key_json(str(path))
    return parse_answer_key_pdf(str(path))


def parse_student_file(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return extract_answers(str(path))


def build_reviewed_submission(student_answers: dict, answer_key: dict) -> ReviewedSubmission:
    graded = grade_student(student_answers, answer_key, load_config())
    merged = merge_analysis(graded)
    items: list[ReviewItem] = []

    for detail in merged["details"]:
        feedback_text = detail.get("analysis") or f"Correct answer: {detail['correct_answer']}"
        review_status = "needs_review" if detail["correct"] is None else "approved"
        items.append(
            ReviewItem(
                q_num=detail["q_num"],
                correct=detail["correct"],
                student_answer=detail["student_answer"],
                correct_answer=detail["correct_answer"],
                points_earned=detail["points_earned"],
                points_possible=detail["points_possible"],
                feedback_text=feedback_text,
                feedback_source="analysis" if detail.get("analysis") else "system",
                feedback_confidence=0.95 if detail.get("analysis") else 0.5,
                review_status=review_status,
                page=student_answers.get("answers", [{}])[0].get("page") if student_answers.get("answers") else None,
                question_text=None,
                rubric=None,
            )
        )

    return ReviewedSubmission(
        student_name=merged["student_name"],
        student_number=merged.get("student_number"),
        exam_title=merged.get("exam_title"),
        total_score=merged["total_score"],
        total_points=merged["total_points"],
        correct_count=merged["correct_count"],
        wrong_count=merged["wrong_count"],
        review_count=merged["review_count"],
        items=items,
    )
```

Replace `skills/classmanage-exam-grader/webapp/main.py` with the prototype route structure, but swap in the existing-engine adapter:

```python
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
from webapp.store import BatchRecord, SubmissionRecord, WorkspaceStore


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
    confidence = "high" if item.feedback_confidence >= 0.9 else "medium"
    return {**item.model_dump(mode="json"), "max_points": item.points_possible, "confidence": confidence}


app = create_app()
```

- [ ] **Step 4: Run the batch-flow test to verify it passes**

Run:

```bash
cd skills/classmanage-exam-grader
python -m pytest tests/webapp/test_batch_flow.py -q
```

Expected: PASS with `1 passed`

- [ ] **Step 5: Commit the batch-flow task**

```bash
git add webapp tests/webapp/test_batch_flow.py
git commit -m "feat: add web batch creation and review payload flow"
```

## Task 3: Wire PDF Inputs, Validation, and Batch Error States

**Files:**
- Modify: `skills/classmanage-exam-grader/webapp/services/pipeline.py`
- Modify: `skills/classmanage-exam-grader/webapp/main.py`
- Test: `skills/classmanage-exam-grader/tests/webapp/test_pipeline.py`
- Test: `skills/classmanage-exam-grader/tests/webapp/test_upload_validation.py`
- Test: `skills/classmanage-exam-grader/tests/webapp/test_batch_status.py`

- [ ] **Step 1: Write the failing PDF-routing and error-state tests**

```python
from io import BytesIO
import json

from fastapi.testclient import TestClient

from webapp.main import _build_batch_view, create_app
from webapp.services.pipeline import parse_answer_key_file, parse_student_file


def test_pipeline_uses_existing_pdf_engine_for_pdf_inputs(tmp_path, monkeypatch) -> None:
    answer_pdf = tmp_path / "answer.pdf"
    student_pdf = tmp_path / "student.pdf"
    answer_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        "webapp.services.pipeline.parse_answer_key_pdf",
        lambda path: {"exam_title": "PDF Quiz", "questions": []},
    )
    monkeypatch.setattr(
        "webapp.services.pipeline.extract_answers",
        lambda path: {"student_name": "Lee Bora", "answers": []},
    )

    assert parse_answer_key_file(answer_pdf)["exam_title"] == "PDF Quiz"
    assert parse_student_file(student_pdf)["student_name"] == "Lee Bora"


def test_batch_creation_requires_at_least_one_student_file(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/batches",
        files=[
            ("answer_key", ("answer.json", BytesIO(json.dumps({"exam_title": "Quiz", "questions": []}).encode("utf-8")), "application/json")),
            ("student_files", (" ", BytesIO(b""), "application/octet-stream")),
        ],
    )

    assert response.status_code == 400
    assert "student" in response.text.lower()
    assert app.state.store.list_batches() == []


def test_failed_batch_detail_persists_error_message(tmp_path, monkeypatch) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    monkeypatch.setattr("webapp.main.parse_student_file", lambda _path: (_ for _ in ()).throw(RuntimeError("student parse failed")))

    client.post(
        "/batches",
        files=[
            ("answer_key", ("answer.json", json.dumps({"exam_title": "Quiz", "questions": []}), "application/json")),
            ("student_files", ("student.json", json.dumps({"student_name": "Kim", "answers": []}), "application/json")),
        ],
        follow_redirects=True,
    )

    batch = app.state.store.list_batches()[0]
    detail_response = client.get(f"/batches/{batch.id}")

    assert detail_response.status_code == 200
    assert "student parse failed" in detail_response.text


def test_batch_with_no_submissions_is_marked_failed_in_view(tmp_path) -> None:
    app = create_app(tmp_path)
    batch = app.state.store.create_batch("Empty Batch")

    batch_view = _build_batch_view(app.state.store, batch)

    assert batch_view["status"] == "failed"
```

- [ ] **Step 2: Run the PDF-routing and error-state tests to verify they fail**

Run:

```bash
cd skills/classmanage-exam-grader
python -m pytest tests/webapp/test_pipeline.py tests/webapp/test_upload_validation.py tests/webapp/test_batch_status.py -q
```

Expected: FAIL with missing validation, missing batch error rendering, or missing PDF branch coverage

- [ ] **Step 3: Add validation and batch-level error handling**

Update `skills/classmanage-exam-grader/webapp/services/pipeline.py` so page numbers come from the matched answer entry rather than the first answer:

```python
def build_reviewed_submission(student_answers: dict, answer_key: dict) -> ReviewedSubmission:
    graded = grade_student(student_answers, answer_key, load_config())
    merged = merge_analysis(graded)
    answers_by_q = {entry["q_num"]: entry for entry in student_answers.get("answers", [])}
    items: list[ReviewItem] = []

    for detail in merged["details"]:
        source_entry = answers_by_q.get(detail["q_num"], {})
        feedback_text = detail.get("analysis") or f"Correct answer: {detail['correct_answer']}"
        review_status = "needs_review" if detail["correct"] is None else "approved"
        items.append(
            ReviewItem(
                q_num=detail["q_num"],
                correct=detail["correct"],
                student_answer=detail["student_answer"],
                correct_answer=detail["correct_answer"],
                points_earned=detail["points_earned"],
                points_possible=detail["points_possible"],
                feedback_text=feedback_text,
                feedback_source="analysis" if detail.get("analysis") else "system",
                feedback_confidence=0.95 if detail.get("analysis") else 0.5,
                review_status=review_status,
                page=source_entry.get("page"),
                question_text=None,
                rubric=None,
            )
        )
```

Update `skills/classmanage-exam-grader/webapp/main.py` to reject empty student uploads and surface batch errors:

```python
    @app.post("/batches")
    async def create_batch(
        request: Request,
        answer_key: UploadFile = File(...),
        student_files: list[UploadFile] = File(...),
    ):
        valid_student_files = [upload for upload in student_files if _normalize_upload_name(upload)]
        if not valid_student_files:
            return TEMPLATES.TemplateResponse(
                request,
                "index.html",
                _build_index_context(request, store, error_message="Student exam files are required."),
                status_code=400,
            )

        title = Path(_normalize_upload_name(answer_key) or "answer_key").stem
        batch = store.create_batch(title)
        batch_folder = Path(batch.folder)
        inputs_dir = batch_folder / "inputs"
        reviewed_dir = batch_folder / "reviewed"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        reviewed_dir.mkdir(parents=True, exist_ok=True)

        answer_key_path = inputs_dir / (_normalize_upload_name(answer_key) or "answer_key.json")
        answer_key_path.write_bytes(await answer_key.read())

        try:
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
```

Add the batch error helpers to `skills/classmanage-exam-grader/webapp/main.py`:

```python
def _write_batch_error(batch_folder: Path, error_message: str) -> None:
    (batch_folder / "error.txt").write_text(error_message, encoding="utf-8")


def _read_batch_error(batch_folder: Path) -> str | None:
    error_path = batch_folder / "error.txt"
    if not error_path.exists():
        return None
    message = error_path.read_text(encoding="utf-8").strip()
    return message or None
```

Update the batch-detail route to read persisted errors:

```python
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
```

- [ ] **Step 4: Run the PDF-routing and error-state tests to verify they pass**

Run:

```bash
cd skills/classmanage-exam-grader
python -m pytest tests/webapp/test_pipeline.py tests/webapp/test_upload_validation.py tests/webapp/test_batch_status.py -q
```

Expected: PASS with `4 passed`

- [ ] **Step 5: Commit the validation/error task**

```bash
git add webapp tests/webapp/test_pipeline.py tests/webapp/test_upload_validation.py tests/webapp/test_batch_status.py
git commit -m "feat: add pdf routing and batch error handling"
```

## Task 4: Add Teacher Review Editing, Finalization, and PDF Download

**Files:**
- Modify: `skills/classmanage-exam-grader/webapp/main.py`
- Modify: `skills/classmanage-exam-grader/webapp/services/pipeline.py`
- Test: `skills/classmanage-exam-grader/tests/webapp/test_review_updates.py`
- Test: `skills/classmanage-exam-grader/tests/webapp/test_finalize_flow.py`

- [ ] **Step 1: Write the failing review/finalization tests**

```python
import json

import fitz
from fastapi.testclient import TestClient

from webapp.main import create_app


def test_teacher_review_edit_persists_feedback_changes(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    answer_key_payload = {
        "exam_title": "Linear Equations",
        "questions": [
            {"q_num": 1, "type": "multiple_choice", "answer": "4", "points": 5, "explanation": "Substitute the value back into the equation."}
        ],
    }
    student_payload = {
        "student_name": "Choi Hana",
        "answers": [{"q_num": 1, "type": "multiple_choice", "answer": "2", "confidence": "high", "page": 1}],
    }

    client.post(
        "/batches",
        files=[
            ("answer_key", ("answer_key.json", json.dumps(answer_key_payload), "application/json")),
            ("student_files", ("student.json", json.dumps(student_payload), "application/json")),
        ],
        follow_redirects=True,
    )

    store = app.state.store
    batch = store.list_batches()[0]
    submission = store.list_submissions(batch.id)[0]

    response = client.post(
        f"/submissions/{submission.id}/questions/1",
        data={
            "feedback_text": "Teacher note: isolate the variable first, then check by substitution.",
            "review_status": "approved",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    payload = store.load_payload(submission.payload_path)
    assert payload["items"][0]["feedback_source"] == "teacher"
    assert payload["items"][0]["review_status"] == "approved"


def test_review_approve_intent_finalizes_student_pdf(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    answer_key_payload = {
        "exam_title": "Linear Equations",
        "questions": [
            {"q_num": 1, "type": "multiple_choice", "answer": "4", "points": 5, "explanation": "Substitute the value back into the equation."}
        ],
    }
    student_payload = {
        "student_name": "Choi Hana",
        "answers": [{"q_num": 1, "type": "multiple_choice", "answer": "2", "confidence": "high", "page": 1}],
    }

    client.post(
        "/batches",
        files=[
            ("answer_key", ("answer_key.json", json.dumps(answer_key_payload), "application/json")),
            ("student_files", ("student.json", json.dumps(student_payload), "application/json")),
        ],
        follow_redirects=True,
    )

    store = app.state.store
    batch = store.list_batches()[0]
    submission = store.list_submissions(batch.id)[0]

    response = client.post(
        f"/submissions/{submission.id}/review",
        data={
            "feedback_1": "Teacher note: isolate the variable first, then check by substitution.",
            "points_earned_1": "0",
            "review_status_1": "approved",
            "intent": "approve",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    updated = store.get_submission(submission.id)
    assert updated.status == "finalized"

    output_files = list((tmp_path / "data" / "web" / "batches" / batch.id / "output").glob("*.pdf"))
    assert len(output_files) == 1

    with fitz.open(output_files[0]) as document:
        assert document.page_count >= 2

    download_response = client.get(f"/submissions/{submission.id}/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
```

- [ ] **Step 2: Run the review/finalization tests to verify they fail**

Run:

```bash
cd skills/classmanage-exam-grader
python -m pytest tests/webapp/test_review_updates.py tests/webapp/test_finalize_flow.py -q
```

Expected: FAIL with `404 Not Found` for the review POST routes or missing `output_pdf_path`

- [ ] **Step 3: Implement review mutation and final PDF generation through the existing annotator**

Extend `skills/classmanage-exam-grader/webapp/services/pipeline.py` with PDF finalization helpers:

```python
import fitz

from pdf_annotator import annotate_pdf


def finalize_submission_pdf(source_path: Path, payload: ReviewedSubmission, output_path: Path) -> Path:
    real_source = source_path
    if real_source.suffix.lower() != ".pdf":
        real_source = _build_placeholder_source_pdf(output_path.parent.parent / "_generated" / f"{source_path.stem}_source.pdf", payload)

    grading_result = {
        "student_name": payload.student_name,
        "student_number": payload.student_number,
        "exam_title": payload.exam_title,
        "total_score": payload.total_score,
        "total_points": payload.total_points,
        "correct_count": payload.correct_count,
        "wrong_count": payload.wrong_count,
        "review_count": payload.review_count,
        "accuracy": round((payload.correct_count / max(payload.correct_count + payload.wrong_count, 1)) * 100, 1),
        "details": [
            {
                "q_num": item.q_num,
                "correct": item.correct,
                "student_answer": item.student_answer,
                "correct_answer": item.correct_answer,
                "points_earned": item.points_earned,
                "points_possible": item.points_possible,
                "analysis": item.feedback_text,
            }
            for item in payload.items
        ],
    }
    return annotate_pdf(str(real_source), grading_result, str(output_path), load_config())


def _build_placeholder_source_pdf(path: Path, payload: ReviewedSubmission) -> Path:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), f"Student: {payload.student_name}", fontsize=16)
    page.insert_text((72, 96), f"Score: {payload.total_score}/{payload.total_points}", fontsize=12)
    y = 132
    for item in payload.items:
        page.insert_text((72, y), f"Q{item.q_num} answer: {item.student_answer or '(blank)'}", fontsize=11)
        y += 18
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path)
    document.close()
    return path
```

Extend `skills/classmanage-exam-grader/webapp/main.py` with review-save, finalize, and download routes:

```python
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse

from webapp.services.pipeline import (
    build_reviewed_submission,
    finalize_submission_pdf,
    parse_answer_key_file,
    parse_student_file,
)
```

```python
    @app.post("/submissions/{submission_id}/review")
    async def save_review(request: Request, submission_id: str) -> RedirectResponse:
        submission = store.get_submission(submission_id)
        form = await request.form()
        intent = str(form.get("intent", "save"))
        updated_payload, review_count = _apply_form_review_updates(store, submission, form)

        if intent == "approve" and review_count == 0:
            _finalize_submission(store, submission, updated_payload)
            return RedirectResponse(url=f"/batches/{submission.batch_id}", status_code=303)

        store.update_submission_status(submission.id, "needs_review" if review_count else "approved", review_count)
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
            submission_id,
            "needs_review" if updated_payload.review_count else "approved",
            updated_payload.review_count,
        )
        return RedirectResponse(url=f"/submissions/{submission_id}/review", status_code=303)


    @app.get("/submissions/{submission_id}/download")
    async def download_submission_pdf(submission_id: str) -> FileResponse:
        submission = store.get_submission(submission_id)
        output_path = Path(submission.output_pdf_path)
        return FileResponse(output_path, media_type="application/pdf", filename=output_path.name)
```

Add the review helpers to `skills/classmanage-exam-grader/webapp/main.py`:

```python
def _load_review_payload(store: WorkspaceStore, submission: SubmissionRecord) -> ReviewedSubmission:
    return ReviewedSubmission.model_validate(store.load_payload(submission.payload_path))


def _apply_form_review_updates(store: WorkspaceStore, submission: SubmissionRecord, form: Any) -> tuple[ReviewedSubmission, int]:
    payload = _load_review_payload(store, submission)
    updated_items = []
    for item in payload.items:
        q_num = item.q_num
        feedback_text = str(form.get(f"feedback_{q_num}", item.feedback_text))
        review_status = str(form.get(f"review_status_{q_num}", item.review_status))
        points_earned = float(form.get(f"points_earned_{q_num}", item.points_earned))
        changed = feedback_text != item.feedback_text or review_status != item.review_status or points_earned != item.points_earned
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
```

- [ ] **Step 4: Run the review/finalization tests to verify they pass**

Run:

```bash
cd skills/classmanage-exam-grader
python -m pytest tests/webapp/test_review_updates.py tests/webapp/test_finalize_flow.py -q
```

Expected: PASS with `2 passed`

- [ ] **Step 5: Commit the review/finalization task**

```bash
git add webapp tests/webapp/test_review_updates.py tests/webapp/test_finalize_flow.py
git commit -m "feat: add teacher review updates and pdf finalization"
```

## Task 5: Lock in Store Migration Safety and Web-First Docs

**Files:**
- Modify: `skills/classmanage-exam-grader/webapp/store.py`
- Create: `skills/classmanage-exam-grader/tests/webapp/test_store_migrations.py`
- Create: `skills/classmanage-exam-grader/README.md`

- [ ] **Step 1: Write the failing store-migration regression test**

```python
import sqlite3

from webapp.store import WorkspaceStore


def test_workspace_store_adds_missing_output_pdf_path_column_for_existing_db(tmp_path) -> None:
    data_dir = tmp_path / "data" / "web"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "app.db"

    connection = sqlite3.connect(db_path)
    connection.executescript(
        '''
        create table batches (
            id text primary key,
            title text not null,
            status text not null,
            folder text not null
        );
        create table submissions (
            id text primary key,
            batch_id text not null,
            student_name text not null,
            student_number integer,
            status text not null,
            total_score real not null,
            total_points real not null,
            review_count integer not null,
            payload_path text not null,
            source_pdf_path text not null
        );
        '''
    )
    connection.close()

    store = WorkspaceStore(tmp_path)

    with store._connect() as migrated:
        columns = {
            row["name"]
            for row in migrated.execute("pragma table_info(submissions)").fetchall()
        }

    assert "output_pdf_path" in columns
    assert store.db_path == tmp_path / "data" / "web" / "app.db"
```

- [ ] **Step 2: Run the migration test to verify it fails if the copied store is incomplete**

Run:

```bash
cd skills/classmanage-exam-grader
python -m pytest tests/webapp/test_store_migrations.py -q
```

Expected: PASS if Task 1's copied+patched store is already correct. If it fails, stop and fix `webapp/store.py` before moving on.

- [ ] **Step 3: Normalize the store file and add web-first docs**

Make sure `skills/classmanage-exam-grader/webapp/store.py` still contains the migration hook from the prototype:

```python
    def _migrate_schema(self, connection: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in connection.execute("pragma table_info(submissions)").fetchall()
        }
        if "output_pdf_path" not in columns:
            connection.execute("alter table submissions add column output_pdf_path text")
```

Create `skills/classmanage-exam-grader/README.md`:

````markdown
# classmanage-exam-grader

Local teacher workstation for grading scanned exams, reviewing drafted feedback, and exporting student-facing PDFs.

## Web UI (default)

```powershell
cd skills/classmanage-exam-grader
python -m pip install -r requirements.txt
python -m uvicorn webapp.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## What the web UI does

1. Upload one answer-key file and one or more student files.
2. Run the existing OCR/parsing/grading engine behind the scenes.
3. Review low-confidence or subjective answers in the browser.
4. Finalize and download annotated student PDFs.

## CLI (secondary)

The original CLI pipeline is still available:

```powershell
cd skills/classmanage-exam-grader
python grade_exam.py all --students data/input/students/ --answer-key data/input/answer_key/answer.pdf
```

Use the CLI when you want direct batch scripting or to debug the legacy flow.
````

- [ ] **Step 4: Run the focused migration test and then the full suite**

Run:

```bash
cd skills/classmanage-exam-grader
python -m pytest tests/webapp/test_store_migrations.py -q
python -m pytest tests/test_grader.py tests/webapp -q
```

Expected:

- `tests/webapp/test_store_migrations.py`: PASS
- full suite: PASS with no skipped web tests

- [ ] **Step 5: Commit the migration/docs task**

```bash
git add webapp/store.py tests/webapp/test_store_migrations.py README.md
git commit -m "docs: add web-first exam grader instructions"
```

## Execution Notes

- Reuse the imported prototype templates and stylesheet as-is first. Only fix template variables if tests force it.
- Keep all engine calls inside `webapp/services/pipeline.py`; do not scatter direct imports from `answer_key_parser.py` or `pdf_annotator.py` throughout route handlers.
- Do not rewrite `grader.py` or `pdf_annotator.py` unless a web test exposes a real adapter gap.
- Prefer JSON upload tests for deterministic coverage. Use monkeypatching instead of invoking Gemini CLI in automated tests.
- If the imported UI has text-encoding glitches, fix those in a dedicated follow-up commit after the main flow is green.

## Verification Checklist

- [ ] Home page renders with imported UI assets
- [ ] Store uses `data/web/app.db`
- [ ] JSON uploads create batches and review pages
- [ ] PDF suffixes route to the existing parser/OCR engine functions
- [ ] Empty student uploads fail with a visible validation message
- [ ] Batch errors persist to `error.txt` and render in `batch_detail.html`
- [ ] Teacher review edits persist to the payload JSON
- [ ] Final approval writes a feedback PDF and exposes a download route
- [ ] Existing `tests/test_grader.py` still passes
- [ ] New README documents the web-first workflow
