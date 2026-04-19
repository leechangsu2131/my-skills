# Classmanage Exam Grader Paddle OCR Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Gemini-based student OCR path with a blank-exam-template-driven Paddle OCR pipeline while preserving the existing web review, grading, and PDF export flow.

**Architecture:** Keep the FastAPI web UI and existing grading engine intact, but require a blank exam PDF for every batch and use it to derive reusable question regions. Process each student PDF by aligning it to the blank template, cropping question regions, running Paddle OCR on those regions, and converting the result back into the existing `student_answers` contract.

**Tech Stack:** Python, FastAPI, Jinja2, SQLite, Pydantic, PyMuPDF, NumPy, OpenCV, PaddleOCR, pytest

---

## File Structure

**Create:**

- `skills/classmanage-exam-grader/ocr/__init__.py`
- `skills/classmanage-exam-grader/ocr/template_alignment.py`
- `skills/classmanage-exam-grader/ocr/question_layout.py`
- `skills/classmanage-exam-grader/ocr/paddle_backend.py`
- `skills/classmanage-exam-grader/tests/ocr/test_template_alignment.py`
- `skills/classmanage-exam-grader/tests/ocr/test_question_layout.py`
- `skills/classmanage-exam-grader/tests/ocr/test_paddle_backend.py`

**Modify:**

- `skills/classmanage-exam-grader/requirements.txt`
- `skills/classmanage-exam-grader/README.md`
- `skills/classmanage-exam-grader/ocr_extractor.py`
- `skills/classmanage-exam-grader/schemas/student_answers.schema.json`
- `skills/classmanage-exam-grader/webapp/main.py`
- `skills/classmanage-exam-grader/webapp/store.py`
- `skills/classmanage-exam-grader/webapp/schemas.py`
- `skills/classmanage-exam-grader/webapp/services/pipeline.py`
- `skills/classmanage-exam-grader/webapp/templates/index.html`
- `skills/classmanage-exam-grader/webapp/templates/batch_detail.html`
- `skills/classmanage-exam-grader/tests/webapp/test_batch_flow.py`
- `skills/classmanage-exam-grader/tests/webapp/test_batch_status.py`
- `skills/classmanage-exam-grader/tests/webapp/test_finalize_flow.py`
- `skills/classmanage-exam-grader/tests/webapp/test_pipeline.py`
- `skills/classmanage-exam-grader/tests/webapp/test_store_migrations.py`
- `skills/classmanage-exam-grader/tests/webapp/test_upload_validation.py`

**Responsibilities:**

- `webapp/main.py`: enforce `blank_exam` upload, batch orchestration, per-student failure isolation
- `webapp/store.py`: persist blank exam path, OCR metadata, submission-level errors, and schema migrations
- `webapp/services/pipeline.py`: bridge answer-key parsing, OCR extraction, confidence-aware review payload building
- `ocr_extractor.py`: stable entry point for student OCR extraction using the new OCR modules
- `ocr/template_alignment.py`: render PDFs and align student pages to the blank template
- `ocr/question_layout.py`: infer question anchors and reusable answer crop regions from the blank template
- `ocr/paddle_backend.py`: lazy PaddleOCR wrapper and crop recognition interface
- `tests/ocr/*`: lock down alignment, layout inference, and OCR backend contracts

### Task 1: Enforce Blank Exam Upload And Persist Batch Metadata

**Files:**
- Modify: `skills/classmanage-exam-grader/webapp/main.py`
- Modify: `skills/classmanage-exam-grader/webapp/store.py`
- Modify: `skills/classmanage-exam-grader/webapp/templates/index.html`
- Modify: `skills/classmanage-exam-grader/tests/webapp/test_upload_validation.py`
- Modify: `skills/classmanage-exam-grader/tests/webapp/test_batch_flow.py`
- Modify: `skills/classmanage-exam-grader/tests/webapp/test_store_migrations.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/webapp/test_upload_validation.py
def test_batch_creation_requires_blank_exam_file(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/batches",
        files=[
            ("answer_key", ("answer.json", json.dumps({"exam_title": "Quiz", "questions": []}), "application/json")),
            ("student_files", ("kim.json", json.dumps({"student_name": "Kim", "answers": []}), "application/json")),
        ],
    )

    assert response.status_code == 400
    assert "blank exam" in response.text.lower()
    assert app.state.store.list_batches() == []


# tests/webapp/test_store_migrations.py
def test_workspace_store_adds_batch_ocr_columns_for_existing_db(tmp_path) -> None:
    data_dir = tmp_path / "data" / "web"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "app.db"

    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
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
        """
    )
    connection.close()

    store = WorkspaceStore(tmp_path)
    with store._connect() as migrated:
        batch_columns = {row["name"] for row in migrated.execute("pragma table_info(batches)").fetchall()}

    assert {"blank_exam_path", "ocr_metadata_path", "layout_status"} <= batch_columns
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/webapp/test_upload_validation.py::test_batch_creation_requires_blank_exam_file tests/webapp/test_store_migrations.py::test_workspace_store_adds_batch_ocr_columns_for_existing_db -q`

Expected: FAIL because `/batches` does not accept `blank_exam`, and `WorkspaceStore` does not migrate the new batch columns.

- [ ] **Step 3: Write the minimal implementation**

```python
# webapp/store.py
@dataclass(slots=True)
class BatchRecord:
    id: str
    title: str
    status: str
    folder: str
    blank_exam_path: str | None = None
    ocr_metadata_path: str | None = None
    layout_status: str | None = None


def _migrate_schema(self, connection: sqlite3.Connection) -> None:
    batch_columns = {
        row["name"]
        for row in connection.execute("pragma table_info(batches)").fetchall()
    }
    if "blank_exam_path" not in batch_columns:
        connection.execute("alter table batches add column blank_exam_path text")
    if "ocr_metadata_path" not in batch_columns:
        connection.execute("alter table batches add column ocr_metadata_path text")
    if "layout_status" not in batch_columns:
        connection.execute("alter table batches add column layout_status text")

    submission_columns = {
        row["name"]
        for row in connection.execute("pragma table_info(submissions)").fetchall()
    }
    if "output_pdf_path" not in submission_columns:
        connection.execute("alter table submissions add column output_pdf_path text")


def update_batch_assets(
    self,
    batch_id: str,
    *,
    blank_exam_path: Path,
    ocr_metadata_path: Path | None = None,
    layout_status: str = "pending",
) -> None:
    with self._connect() as connection:
        connection.execute(
            "update batches set blank_exam_path = ?, ocr_metadata_path = ?, layout_status = ? where id = ?",
            (
                str(blank_exam_path),
                str(ocr_metadata_path) if ocr_metadata_path else None,
                layout_status,
                batch_id,
            ),
        )
```

```python
# webapp/main.py
@app.post("/batches")
async def create_batch(
    request: Request,
    blank_exam: UploadFile = File(...),
    answer_key: UploadFile = File(...),
    student_files: list[UploadFile] = File(...),
):
    blank_exam_name = _normalize_upload_name(blank_exam)
    if not blank_exam_name:
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            _build_index_context(request, store, error_message="Blank exam PDF is required."),
            status_code=400,
        )

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

    blank_exam_path = inputs_dir / blank_exam_name
    blank_exam_path.write_bytes(await blank_exam.read())
    store.update_batch_assets(batch.id, blank_exam_path=blank_exam_path, layout_status="pending")
```

```html
<!-- webapp/templates/index.html -->
<div class="form-field">
    <label for="blank_exam">빈 시험지 PDF</label>
    <input id="blank_exam" name="blank_exam" type="file" accept=".pdf" required>
    <p class="field-help">학생이 쓰지 않은 원본 시험지 PDF를 올려 문항 좌표와 정렬 기준으로 사용합니다.</p>
</div>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/webapp/test_upload_validation.py::test_batch_creation_requires_blank_exam_file tests/webapp/test_store_migrations.py::test_workspace_store_adds_batch_ocr_columns_for_existing_db -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/classmanage-exam-grader/webapp/main.py \
        skills/classmanage-exam-grader/webapp/store.py \
        skills/classmanage-exam-grader/webapp/templates/index.html \
        skills/classmanage-exam-grader/tests/webapp/test_upload_validation.py \
        skills/classmanage-exam-grader/tests/webapp/test_batch_flow.py \
        skills/classmanage-exam-grader/tests/webapp/test_store_migrations.py
git commit -m "feat: require blank exam upload for batches"
```

### Task 2: Extend OCR Payload Schema And Confidence-Aware Review Defaults

**Files:**
- Modify: `skills/classmanage-exam-grader/webapp/schemas.py`
- Modify: `skills/classmanage-exam-grader/schemas/student_answers.schema.json`
- Modify: `skills/classmanage-exam-grader/webapp/services/pipeline.py`
- Modify: `skills/classmanage-exam-grader/tests/webapp/test_pipeline.py`
- Modify: `skills/classmanage-exam-grader/tests/webapp/test_batch_status.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/webapp/test_pipeline.py
def test_parse_student_file_passes_blank_exam_to_extractor(tmp_path, monkeypatch) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    calls: dict[str, str] = {}

    def fake_extract_answers(path: str, *, blank_exam_path: str, metadata_dir=None):
        calls["path"] = path
        calls["blank_exam_path"] = blank_exam_path
        return {"student_name": "Lee Bora", "answers": []}

    monkeypatch.setattr("webapp.services.pipeline.extract_answers", fake_extract_answers)

    result = parse_student_file(student_pdf, blank_exam_path=blank_pdf)

    assert result["student_name"] == "Lee Bora"
    assert calls == {"path": str(student_pdf), "blank_exam_path": str(blank_pdf)}


def test_low_confidence_answer_defaults_to_review() -> None:
    answer_key = {
        "exam_title": "Quiz",
        "questions": [{"q_num": 1, "type": "short_answer", "answer": "12", "points": 5}],
    }
    student_answers = {
        "student_name": "Park",
        "answers": [
            {
                "q_num": 1,
                "type": "short_answer",
                "answer": "12",
                "confidence": "low",
                "requires_review": True,
                "page": 1,
            }
        ],
    }

    reviewed = build_reviewed_submission(student_answers, answer_key)

    assert reviewed.items[0].review_status == "needs_review"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/webapp/test_pipeline.py::test_parse_student_file_passes_blank_exam_to_extractor tests/webapp/test_pipeline.py::test_low_confidence_answer_defaults_to_review -q`

Expected: FAIL because `parse_student_file()` does not accept `blank_exam_path`, and `build_reviewed_submission()` ignores OCR review flags.

- [ ] **Step 3: Write the minimal implementation**

```python
# webapp/schemas.py
class StudentAnswerEntry(BaseModel):
    q_num: int
    type: QuestionType = "unknown"
    answer: str = ""
    confidence: ConfidenceLevel = "medium"
    page: int | None = None
    bbox: list[float] | None = None
    requires_review: bool = False
```

```json
// schemas/student_answers.schema.json
{
  "type": "object",
  "required": ["student_name", "answers"],
  "properties": {
    "student_name": { "type": "string" },
    "student_number": { "type": ["integer", "null"] },
    "exam_title": { "type": ["string", "null"] },
    "answers": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["q_num", "answer"],
        "properties": {
          "q_num": { "type": "integer" },
          "type": { "type": "string" },
          "answer": { "type": "string" },
          "confidence": { "type": "string", "enum": ["high", "medium", "low"] },
          "page": { "type": ["integer", "null"] },
          "bbox": {
            "type": ["array", "null"],
            "items": { "type": "number" },
            "minItems": 4,
            "maxItems": 4
          },
          "requires_review": { "type": "boolean" }
        }
      }
    }
  }
}
```

```python
# webapp/services/pipeline.py
def parse_student_file(path: Path, *, blank_exam_path: Path | None = None, metadata_dir: Path | None = None) -> dict:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if blank_exam_path is None:
        raise ValueError("blank_exam_path is required for PDF student parsing")
    return extract_answers(str(path), blank_exam_path=str(blank_exam_path), metadata_dir=metadata_dir)


def build_reviewed_submission(student_answers: dict, answer_key: dict) -> ReviewedSubmission:
    graded = grade_student(student_answers, answer_key, load_config())
    merged = merge_analysis(graded)
    questions_by_q = {question["q_num"]: question for question in answer_key.get("questions", [])}
    answers_by_q = {answer["q_num"]: answer for answer in student_answers.get("answers", [])}
    confidence_map = {"high": 0.95, "medium": 0.7, "low": 0.35}

    items: list[ReviewItem] = []
    for detail in merged["details"]:
        question = questions_by_q.get(detail["q_num"], {})
        student_entry = answers_by_q.get(detail["q_num"], {})
        needs_review = bool(student_entry.get("requires_review")) or detail["correct"] is None

        items.append(
            ReviewItem(
                q_num=detail["q_num"],
                correct=detail["correct"],
                student_answer=detail["student_answer"],
                correct_answer=detail["correct_answer"],
                points_earned=detail["points_earned"],
                points_possible=detail["points_possible"],
                feedback_text=question.get("explanation") or question.get("rubric") or detail.get("analysis") or "",
                feedback_source="answer_key" if question.get("explanation") or question.get("rubric") else "system",
                feedback_confidence=confidence_map.get(student_entry.get("confidence", "medium"), 0.5),
                review_status="needs_review" if needs_review else "approved",
                page=student_entry.get("page"),
                question_text=question.get("question_text"),
                rubric=question.get("rubric"),
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
        review_count=sum(1 for item in items if item.review_status == "needs_review"),
        items=items,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/webapp/test_pipeline.py::test_parse_student_file_passes_blank_exam_to_extractor tests/webapp/test_pipeline.py::test_low_confidence_answer_defaults_to_review -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/classmanage-exam-grader/webapp/schemas.py \
        skills/classmanage-exam-grader/schemas/student_answers.schema.json \
        skills/classmanage-exam-grader/webapp/services/pipeline.py \
        skills/classmanage-exam-grader/tests/webapp/test_pipeline.py \
        skills/classmanage-exam-grader/tests/webapp/test_batch_status.py
git commit -m "feat: add confidence-aware OCR payload contract"
```

### Task 3: Build Template Alignment And Question Layout Modules

**Files:**
- Create: `skills/classmanage-exam-grader/ocr/__init__.py`
- Create: `skills/classmanage-exam-grader/ocr/template_alignment.py`
- Create: `skills/classmanage-exam-grader/ocr/question_layout.py`
- Create: `skills/classmanage-exam-grader/tests/ocr/test_template_alignment.py`
- Create: `skills/classmanage-exam-grader/tests/ocr/test_question_layout.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/ocr/test_template_alignment.py
import cv2
import numpy as np

from ocr.template_alignment import align_page_images


def test_align_page_images_returns_homography_for_translated_page() -> None:
    template = np.full((300, 300), 255, dtype=np.uint8)
    cv2.putText(template, "1", (40, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.8, 0, 3)
    cv2.rectangle(template, (70, 60), (240, 120), 0, 2)

    student = np.full((300, 300), 255, dtype=np.uint8)
    cv2.putText(student, "1", (55, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.8, 0, 3)
    cv2.rectangle(student, (85, 70), (255, 130), 0, 2)

    result = align_page_images(template, student)

    assert result.matrix.shape == (3, 3)
    assert result.score > 0
```

```python
# tests/ocr/test_question_layout.py
from ocr.question_layout import build_question_layout


def test_build_question_layout_sorts_question_regions_by_page_then_number() -> None:
    detections_by_page = {
        0: [
            {"text": "2.", "confidence": 0.99, "bbox": [40, 130, 80, 160]},
            {"text": "1.", "confidence": 0.99, "bbox": [40, 40, 80, 70]},
        ]
    }
    page_sizes = {0: (600, 800)}

    layout = build_question_layout(detections_by_page, page_sizes)

    assert [item.q_num for item in layout.items] == [1, 2]
    assert layout.items[0].page_index == 0
    assert layout.items[0].answer_bbox[1] < layout.items[1].answer_bbox[1]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/ocr/test_template_alignment.py tests/ocr/test_question_layout.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'ocr'`.

- [ ] **Step 3: Write the minimal implementation**

```python
# ocr/template_alignment.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import fitz
import numpy as np


@dataclass(slots=True)
class AlignmentResult:
    matrix: np.ndarray
    score: float
    width: int
    height: int


def render_pdf_pages(pdf_path: Path, dpi: int = 160) -> list[np.ndarray]:
    document = fitz.open(pdf_path)
    pages: list[np.ndarray] = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for page in document:
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
        pages.append(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY))
    document.close()
    return pages


def align_page_images(template_page: np.ndarray, student_page: np.ndarray) -> AlignmentResult:
    orb = cv2.ORB_create(1500)
    kp1, des1 = orb.detectAndCompute(template_page, None)
    kp2, des2 = orb.detectAndCompute(student_page, None)
    if des1 is None or des2 is None:
        raise ValueError("Unable to find alignment features on one of the pages")

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(matcher.match(des1, des2), key=lambda item: item.distance)
    if len(matches) < 8:
        raise ValueError("Not enough feature matches to align the student page")

    src = np.float32([kp1[m.queryIdx].pt for m in matches[:40]]).reshape(-1, 1, 2)
    dst = np.float32([kp2[m.trainIdx].pt for m in matches[:40]]).reshape(-1, 1, 2)
    matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if matrix is None:
        raise ValueError("Homography estimation failed")

    inliers = float(mask.sum()) if mask is not None else 0.0
    return AlignmentResult(matrix=matrix, score=inliers / max(len(matches[:40]), 1), width=student_page.shape[1], height=student_page.shape[0])
```

```python
# ocr/question_layout.py
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(slots=True)
class QuestionRegion:
    q_num: int
    page_index: int
    anchor_bbox: list[float]
    answer_bbox: list[float]


@dataclass(slots=True)
class QuestionLayout:
    items: list[QuestionRegion]


QUESTION_RE = re.compile(r"^(\d+)[\.\)]?$")


def build_question_layout(detections_by_page: dict[int, list[dict]], page_sizes: dict[int, tuple[int, int]]) -> QuestionLayout:
    items: list[QuestionRegion] = []
    for page_index, detections in detections_by_page.items():
        anchors = []
        for detection in detections:
            match = QUESTION_RE.match(str(detection["text"]).strip())
            if match:
                anchors.append((int(match.group(1)), detection["bbox"]))

        anchors.sort(key=lambda item: (item[1][1], item[0]))
        page_width, page_height = page_sizes[page_index]
        for idx, (q_num, bbox) in enumerate(anchors):
            next_top = anchors[idx + 1][1][1] if idx + 1 < len(anchors) else page_height - 20
            answer_bbox = [bbox[2] + 12, max(bbox[1] - 8, 0), page_width - 24, min(next_top - 8, page_height - 1)]
            items.append(QuestionRegion(q_num=q_num, page_index=page_index, anchor_bbox=bbox, answer_bbox=answer_bbox))

    items.sort(key=lambda item: (item.page_index, item.q_num))
    return QuestionLayout(items=items)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ocr/test_template_alignment.py tests/ocr/test_question_layout.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/classmanage-exam-grader/ocr/__init__.py \
        skills/classmanage-exam-grader/ocr/template_alignment.py \
        skills/classmanage-exam-grader/ocr/question_layout.py \
        skills/classmanage-exam-grader/tests/ocr/test_template_alignment.py \
        skills/classmanage-exam-grader/tests/ocr/test_question_layout.py
git commit -m "feat: add blank template alignment and layout modules"
```

### Task 4: Add PaddleOCR Backend And Rewrite `ocr_extractor.py`

**Files:**
- Create: `skills/classmanage-exam-grader/ocr/paddle_backend.py`
- Modify: `skills/classmanage-exam-grader/ocr_extractor.py`
- Modify: `skills/classmanage-exam-grader/requirements.txt`
- Create: `skills/classmanage-exam-grader/tests/ocr/test_paddle_backend.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/ocr/test_paddle_backend.py
import importlib

import numpy as np
import pytest

from ocr.paddle_backend import PaddleOcrBackend


def test_paddle_backend_raises_clear_error_when_runtime_missing(monkeypatch) -> None:
    def fake_import(name: str):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", fake_import)

    backend = PaddleOcrBackend()
    with pytest.raises(RuntimeError, match="PaddleOCR"):
        backend.detect_text(np.zeros((32, 32), dtype=np.uint8))
```

```python
# tests/webapp/test_pipeline.py
def test_pdf_student_extraction_returns_layout_aware_answers(tmp_path, monkeypatch) -> None:
    blank_pdf = tmp_path / "blank.pdf"
    student_pdf = tmp_path / "student.pdf"
    blank_pdf.write_bytes(b"%PDF-1.4")
    student_pdf.write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(
        "ocr_extractor.extract_answers",
        lambda path, *, blank_exam_path, metadata_dir=None: {
            "student_name": "Moon",
            "answers": [{"q_num": 1, "answer": "42", "confidence": "high", "page": 1, "requires_review": False}],
        },
    )

    result = parse_student_file(student_pdf, blank_exam_path=blank_pdf)

    assert result["answers"][0]["answer"] == "42"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/ocr/test_paddle_backend.py tests/webapp/test_pipeline.py::test_pdf_student_extraction_returns_layout_aware_answers -q`

Expected: FAIL because `PaddleOcrBackend` does not exist and `ocr_extractor.extract_answers()` still uses the Gemini path.

- [ ] **Step 3: Write the minimal implementation**

```python
# ocr/paddle_backend.py
from __future__ import annotations

import importlib

import cv2
import numpy as np


class PaddleOcrBackend:
    def __init__(self, *, lang: str = "korean", use_angle_cls: bool = True) -> None:
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                module = importlib.import_module("paddleocr")
            except ModuleNotFoundError as exc:
                raise RuntimeError("PaddleOCR runtime is not installed. Install paddleocr and paddlepaddle before starting the web app.") from exc
            self._engine = module.PaddleOCR(lang=self.lang, use_angle_cls=self.use_angle_cls, show_log=False)
        return self._engine

    def detect_text(self, image: np.ndarray) -> list[dict]:
        rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB) if image.ndim == 2 else image
        results = self._get_engine().ocr(rgb, cls=self.use_angle_cls)
        detections: list[dict] = []
        for line in results[0] if results else []:
            bbox, (text, confidence) = line
            xs = [point[0] for point in bbox]
            ys = [point[1] for point in bbox]
            detections.append(
                {
                    "text": text,
                    "confidence": float(confidence),
                    "bbox": [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))],
                }
            )
        return detections
```

```python
# ocr_extractor.py
from __future__ import annotations

import json
from pathlib import Path

from ocr.paddle_backend import PaddleOcrBackend
from ocr.question_layout import build_question_layout
from ocr.template_alignment import align_page_images, render_pdf_pages

SKILL_DIR = Path(__file__).parent
CONFIG_PATH = SKILL_DIR / "config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def extract_answers(pdf_path: str, *, blank_exam_path: str, metadata_dir: str | Path | None = None) -> dict:
    backend = PaddleOcrBackend(lang=load_config().get("paddle_ocr_language", "korean"))
    blank_pages = render_pdf_pages(Path(blank_exam_path))
    student_pages = render_pdf_pages(Path(pdf_path))

    detections_by_page: dict[int, list[dict]] = {}
    page_sizes: dict[int, tuple[int, int]] = {}
    for page_index, blank_page in enumerate(blank_pages):
        detections = backend.detect_text(blank_page)
        detections_by_page[page_index] = detections
        page_sizes[page_index] = (blank_page.shape[1], blank_page.shape[0])

    layout = build_question_layout(detections_by_page, page_sizes)
    answers = []
    for region in layout.items:
        student_page = student_pages[region.page_index]
        blank_page = blank_pages[region.page_index]
        alignment = align_page_images(blank_page, student_page)
        x1, y1, x2, y2 = map(int, region.answer_bbox)
        crop = student_page[y1:y2, x1:x2]
        lines = backend.detect_text(crop)
        text = " ".join(line["text"] for line in lines).strip()
        confidence = max((line["confidence"] for line in lines), default=0.0)
        answers.append(
            {
                "q_num": region.q_num,
                "answer": text,
                "confidence": "high" if confidence >= 0.85 else "medium" if confidence >= 0.6 else "low",
                "page": region.page_index + 1,
                "bbox": region.answer_bbox,
                "requires_review": confidence < 0.6 or not text,
                "alignment_score": alignment.score,
            }
        )

    return {"student_name": Path(pdf_path).stem, "answers": answers}
```

```text
# requirements.txt
numpy>=2,<3
opencv-python-headless>=4.10,<5
paddleocr>=2.9,<3
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/ocr/test_paddle_backend.py tests/webapp/test_pipeline.py::test_pdf_student_extraction_returns_layout_aware_answers -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/classmanage-exam-grader/ocr/paddle_backend.py \
        skills/classmanage-exam-grader/ocr_extractor.py \
        skills/classmanage-exam-grader/requirements.txt \
        skills/classmanage-exam-grader/tests/ocr/test_paddle_backend.py \
        skills/classmanage-exam-grader/tests/webapp/test_pipeline.py
git commit -m "feat: add paddle ocr extraction backend"
```

### Task 5: Integrate Template OCR Into Batch Processing And Isolate Student Failures

**Files:**
- Modify: `skills/classmanage-exam-grader/webapp/main.py`
- Modify: `skills/classmanage-exam-grader/webapp/store.py`
- Modify: `skills/classmanage-exam-grader/webapp/services/pipeline.py`
- Modify: `skills/classmanage-exam-grader/webapp/templates/batch_detail.html`
- Modify: `skills/classmanage-exam-grader/tests/webapp/test_batch_flow.py`
- Modify: `skills/classmanage-exam-grader/tests/webapp/test_batch_status.py`
- Modify: `skills/classmanage-exam-grader/tests/webapp/test_finalize_flow.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/webapp/test_batch_flow.py
def test_one_failed_student_does_not_fail_successful_submissions(tmp_path, monkeypatch) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    calls = {"count": 0}

    def fake_parse_student_file(path, *, blank_exam_path, metadata_dir=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"student_name": "Kim", "answers": [{"q_num": 1, "answer": "3", "confidence": "high"}]}
        raise RuntimeError("alignment failed")

    monkeypatch.setattr("webapp.main.parse_student_file", fake_parse_student_file)
    monkeypatch.setattr(
        "webapp.main.build_reviewed_submission",
        lambda student_answers, answer_key: ReviewedSubmission(
            student_name=student_answers["student_name"],
            total_score=5,
            total_points=5,
            correct_count=1,
            wrong_count=0,
            review_count=0,
            items=[],
        ),
    )

    response = client.post(
        "/batches",
        files=[
            ("blank_exam", ("blank.pdf", b"%PDF-1.4", "application/pdf")),
            ("answer_key", ("answer.json", json.dumps({"exam_title": "Quiz", "questions": []}), "application/json")),
            ("student_files", ("kim.pdf", b"%PDF-1.4", "application/pdf")),
            ("student_files", ("lee.pdf", b"%PDF-1.4", "application/pdf")),
        ],
        follow_redirects=True,
    )

    batch = app.state.store.list_batches()[0]
    submissions = app.state.store.list_submissions(batch.id)

    assert response.status_code == 200
    assert len(submissions) == 2
    assert {item.status for item in submissions} == {"approved", "failed"}
    assert "alignment failed" in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/webapp/test_batch_flow.py::test_one_failed_student_does_not_fail_successful_submissions -q`

Expected: FAIL because the current batch route wraps the whole student loop in one `try/except` and aborts the entire batch on the first student error.

- [ ] **Step 3: Write the minimal implementation**

```python
# webapp/store.py
@dataclass(slots=True)
class SubmissionRecord:
    id: str
    batch_id: str
    student_name: str
    student_number: int | None
    status: str
    total_score: float
    total_points: float
    review_count: int
    payload_path: str
    source_pdf_path: str
    output_pdf_path: str | None = None
    error_message: str | None = None


if "error_message" not in submission_columns:
    connection.execute("alter table submissions add column error_message text")
```

```python
# webapp/main.py
answer_key_path = inputs_dir / (_normalize_upload_name(answer_key) or "answer_key.json")
answer_key_path.write_bytes(await answer_key.read())
parsed_answer_key = parse_answer_key_file(answer_key_path)

ocr_metadata_dir = batch_folder / "ocr"
ocr_metadata_dir.mkdir(parents=True, exist_ok=True)
store.update_batch_assets(batch.id, blank_exam_path=blank_exam_path, ocr_metadata_path=ocr_metadata_dir / "layout.json", layout_status="ready")

batch_error_messages: list[str] = []
for index, upload in enumerate(valid_student_files, start=1):
    fallback_name = f"student-{index}{Path(upload.filename or '').suffix or '.pdf'}"
    student_path = inputs_dir / (_normalize_upload_name(upload) or fallback_name)
    student_path.write_bytes(await upload.read())

    try:
        parsed_student = parse_student_file(student_path, blank_exam_path=blank_exam_path, metadata_dir=ocr_metadata_dir)
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
        batch_error_messages.append(f"{student_path.name}: {exc}")
        store.add_submission(
            batch_id=batch.id,
            student_name=student_path.stem,
            student_number=None,
            status="failed",
            total_score=0,
            total_points=parsed_answer_key.get("total_points", 0),
            review_count=0,
            payload_path=reviewed_dir / f"{student_path.stem}_failed.json",
            source_pdf_path=student_path,
            error_message=str(exc),
        )

if batch_error_messages and all(item.status == "failed" for item in store.list_submissions(batch.id)):
    store.update_batch_status(batch.id, "failed")
elif any(item.status == "needs_review" for item in store.list_submissions(batch.id)):
    store.update_batch_status(batch.id, "needs_review")
else:
    store.update_batch_status(batch.id, "approved")

if batch_error_messages:
    _write_batch_error(batch_folder, "\n".join(batch_error_messages))
```

```html
<!-- webapp/templates/batch_detail.html -->
{% if row_status == "failed" and row.error_message %}
    <span class="table-secondary">실패 사유: {{ row.error_message }}</span>
{% endif %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/webapp/test_batch_flow.py::test_one_failed_student_does_not_fail_successful_submissions tests/webapp/test_batch_status.py tests/webapp/test_finalize_flow.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/classmanage-exam-grader/webapp/main.py \
        skills/classmanage-exam-grader/webapp/store.py \
        skills/classmanage-exam-grader/webapp/services/pipeline.py \
        skills/classmanage-exam-grader/webapp/templates/batch_detail.html \
        skills/classmanage-exam-grader/tests/webapp/test_batch_flow.py \
        skills/classmanage-exam-grader/tests/webapp/test_batch_status.py \
        skills/classmanage-exam-grader/tests/webapp/test_finalize_flow.py
git commit -m "feat: isolate student OCR failures within batches"
```

### Task 6: Update Documentation And Run Full Verification

**Files:**
- Modify: `skills/classmanage-exam-grader/README.md`
- Modify: `skills/classmanage-exam-grader/webapp/templates/index.html`
- Modify: `skills/classmanage-exam-grader/tests/webapp/test_batch_flow.py`
- Modify: `skills/classmanage-exam-grader/tests/webapp/test_upload_validation.py`

- [ ] **Step 1: Write the failing documentation-oriented regression test**

```python
# tests/webapp/test_batch_flow.py
def test_home_page_mentions_blank_exam_requirement(tmp_path) -> None:
    app = create_app(tmp_path)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "빈 시험지" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/webapp/test_batch_flow.py::test_home_page_mentions_blank_exam_requirement -q`

Expected: FAIL until the template copy is updated everywhere.

- [ ] **Step 3: Write minimal implementation**

````markdown
# README.md
## Web UI (default)

```powershell
cd skills/classmanage-exam-grader
python -m pip install -r requirements.txt
python -m uvicorn webapp.main:app --reload
```

Each batch now requires:

1. one blank exam PDF
2. one answer key file (`.json` or teacher PDF)
3. one or more student exam PDFs

The blank exam is used as the alignment template for question-region OCR.
````

```html
<!-- webapp/templates/index.html -->
<ol class="workflow-list">
    <li>빈 시험지 PDF, 정답지, 학생 시험지를 함께 업로드합니다.</li>
    <li>빈 시험지를 기준으로 문항 레이아웃과 페이지 정렬을 계산합니다.</li>
    <li>문항별 OCR 결과 중 애매한 항목만 교사가 검토합니다.</li>
</ol>
```

- [ ] **Step 4: Run the full verification suite**

Run: `python -m pytest tests/test_grader.py tests/webapp tests/ocr -q`

Expected: PASS with all web and OCR regression tests green.

- [ ] **Step 5: Commit**

```bash
git add skills/classmanage-exam-grader/README.md \
        skills/classmanage-exam-grader/webapp/templates/index.html \
        skills/classmanage-exam-grader/tests/webapp/test_batch_flow.py \
        skills/classmanage-exam-grader/tests/webapp/test_upload_validation.py \
        skills/classmanage-exam-grader/tests/ocr
git commit -m "docs: document paddle ocr template workflow"
```

## Self-Review Checklist

- Spec coverage:
  - blank exam required: Task 1
  - batch/store metadata: Task 1 and Task 5
  - OCR schema and review routing: Task 2
  - template alignment and layout extraction: Task 3
  - Paddle OCR backend: Task 4
  - web integration and per-student failures: Task 5
  - docs and verification: Task 6
- Placeholder scan:
  - no placeholder markers remain
  - each task includes concrete tests, commands, and code snippets
- Type consistency:
  - `blank_exam_path` is used consistently across `webapp.main`, `webapp.services.pipeline`, and `ocr_extractor`
  - `requires_review` is the explicit review-routing flag across OCR payloads and review payload construction

## Notes For Execution

- Keep PaddleOCR imports lazy so test runs do not require the runtime.
- Prefer deterministic unit tests that use synthetic images or monkeypatched OCR results instead of real OCR inference.
- Do not remove the current review UI flow; the goal is to improve the OCR input quality without rewriting the review product.
