# OCR Grading Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the current alignment and overlay-review tool into a grading pipeline that accepts the existing Gemini-web JSON bundle (`questions + answers + total_points`), crops answer regions from aligned student pages, runs OCR, scores each response, supports low-confidence human review, and exports teacher-ready results.

**Architecture:** Keep the current external Gemini-web workflow as the upstream source of question boxes and answer keys. Continue using the saved assessment bundle as the project-level source of truth, then add deterministic project artifacts for `submissions`, `crops`, `ocr`, `grading`, and `exports` so each stage can be rerun without repeating alignment. Reuse the current FastAPI app and add a separate grading workflow instead of overloading `/review`, which should stay focused on alignment and answer-region verification.

**Tech Stack:** FastAPI, OpenCV, Pillow, PyMuPDF, PaddleOCR, JSON artifacts, Jinja2, `pytest` for new regression tests, `openpyxl` for Excel export, standard-library `csv`.

---

## File Structure

**Existing files to modify**
- `src/project_store.py`
  - Add project artifact directories for grading outputs.
- `webapp/main.py`
  - Add grading preparation, OCR, scoring, review, and export routes.
- `webapp/templates/index.html`
  - Tighten validation and status display for the combined Gemini bundle.
- `README.md`
  - Add the new grading workflow after implementation.
- `requirements.txt`
  - Add OCR/export dependencies.

**New backend modules**
- `src/assessment_bundle.py`
  - Validate and normalize the project-level Gemini bundle (`questions`, `answers`, `total_points`).
- `src/submission_store.py`
  - Build per-student manifests from aligned page filenames and persist grading JSON.
- `src/region_cropper.py`
  - Extract question crops from template/aligned pages using normalized boxes.
- `src/ocr_engine.py`
  - Wrap PaddleOCR calls and return normalized OCR candidates with confidence.
- `src/answer_normalizer.py`
  - Normalize objective and short-answer OCR strings before grading.
- `src/grader.py`
  - Compare normalized OCR output with answer-key entries and compute scores.
- `src/report_exporter.py`
  - Build CSV/XLSX export files and summary statistics.

**New templates**
- `webapp/templates/grading_overview.html`
  - Batch-style overview for all students in the current project.
- `webapp/templates/grading_student.html`
  - Human review page for one student with crops, OCR text, expected answer, and quick approve/fix controls.

**New tests**
- `tests/test_assessment_bundle.py`
- `tests/test_submission_store.py`
- `tests/test_region_cropper.py`
- `tests/test_answer_normalizer.py`
- `tests/test_grader.py`
- `tests/test_report_exporter.py`

**Project artifact layout to add**
- `<project>/artifacts/submissions/`
  - Per-student grading manifests such as `stu001.json`
- `<project>/artifacts/crops/reference/`
  - Blank-template crops per question
- `<project>/artifacts/crops/students/<student_id>/`
  - Student answer crops grouped by student
- `<project>/artifacts/exports/`
  - CSV/XLSX outputs

---

### Task 1: Formalize the Gemini-web assessment bundle

**Files:**
- Create: `src/assessment_bundle.py`
- Modify: `src/project_store.py`
- Modify: `webapp/main.py`
- Modify: `webapp/templates/index.html`
- Test: `tests/test_assessment_bundle.py`
- Test: `tests/test_project_store.py`

- [ ] **Step 1: Write the failing schema test**

```python
from src.assessment_bundle import normalize_assessment_bundle


def test_normalize_assessment_bundle_keeps_questions_answers_and_total_points():
    payload = {
        "questions": [
            {"number": 1, "page": 1, "type": "객관식", "box": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.1}},
        ],
        "answers": [
            {"number": 1, "page": 1, "answer": "②", "points": 5},
        ],
        "total_points": 5,
    }

    data = normalize_assessment_bundle(payload)

    assert data["questions"][0]["number"] == 1
    assert data["answers"][0]["answer"] == "②"
    assert data["total_points"] == 5
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_assessment_bundle.py -q`

Expected: `ModuleNotFoundError` or import failure for `src.assessment_bundle`

- [ ] **Step 3: Implement the bundle normalizer**

```python
def normalize_assessment_bundle(payload: dict) -> dict:
    questions = payload.get("questions", [])
    answers = payload.get("answers", [])
    total_points = payload.get("total_points", 0)

    if not isinstance(questions, list):
        raise ValueError('"questions" must be a list')
    if not isinstance(answers, list):
        raise ValueError('"answers" must be a list')

    normalized_questions = []
    for item in questions:
        box = item.get("box") or {}
        normalized_questions.append(
            {
                "number": int(item.get("number", 0)),
                "page": int(item.get("page", 1)),
                "type": item.get("type", "객관식"),
                "box": {
                    "x": float(box["x"]),
                    "y": float(box["y"]),
                    "w": float(box["w"]),
                    "h": float(box["h"]),
                },
            }
        )

    normalized_answers = []
    for item in answers:
        normalized_answers.append(
            {
                "number": int(item.get("number", 0)),
                "page": int(item.get("page", 1)),
                "answer": str(item.get("answer", "")).strip(),
                "points": int(item.get("points", 0)),
                "type": item.get("type", "객관식"),
            }
        )

    return {
        "questions": normalized_questions,
        "answers": normalized_answers,
        "total_points": int(total_points or 0),
    }
```

- [ ] **Step 4: Run the schema test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_assessment_bundle.py -q`

Expected: `1 passed`

- [ ] **Step 5: Write the failing project-path test for grading artifacts**

```python
from src.project_store import create_project, project_paths


def test_project_paths_include_grading_artifact_directories(tmp_path):
    project = create_project(tmp_path, {"name": "수학2"})
    paths = project_paths(tmp_path / project["slug"])

    assert paths.artifacts_dir.name == "artifacts"
    assert paths.submissions_dir.name == "submissions"
    assert paths.exports_dir.name == "exports"
```

- [ ] **Step 6: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_project_store.py -q`

Expected: `AttributeError` for missing new path fields

- [ ] **Step 7: Add artifact directories to `ProjectPaths` and create them**

```python
@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    project_json: Path
    template_dir: Path
    answers_dir: Path
    student_pdf_dir: Path
    student_page_dir: Path
    aligned_dir: Path
    json_dir: Path
    yolo_dir: Path
    logs_dir: Path
    artifacts_dir: Path
    submissions_dir: Path
    crops_dir: Path
    exports_dir: Path
```

```python
artifacts_dir=project_dir / "artifacts",
submissions_dir=project_dir / "artifacts" / "submissions",
crops_dir=project_dir / "artifacts" / "crops",
exports_dir=project_dir / "artifacts" / "exports",
```

- [ ] **Step 8: Save normalized Gemini bundles through the existing `/api/regions` flow**

```python
from assessment_bundle import normalize_assessment_bundle


@app.post("/api/regions")
async def save_regions(request: Request):
    payload = json.loads(await request.body())
    normalized = normalize_assessment_bundle(payload)
    (paths.json_dir / "regions.json").write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"success": True, "count": len(normalized["questions"]), "answers": len(normalized["answers"])}
```

- [ ] **Step 9: Keep the dashboard JSON editor explicitly centered on the combined Gemini bundle**

```javascript
parsedAllData = {
  questions,
  answers: Array.isArray(data.answers) ? data.answers : [],
  total_points: Number(data.total_points || 0),
};
```

- [ ] **Step 10: Run focused regression tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_assessment_bundle.py tests/test_project_store.py -q`

Expected: all tests pass

- [ ] **Step 11: Commit**

```bash
git add src/assessment_bundle.py src/project_store.py webapp/main.py webapp/templates/index.html tests/test_assessment_bundle.py tests/test_project_store.py
git commit -m "feat: formalize Gemini assessment bundle"
```

---

### Task 2: Build student submission manifests and crop extraction

**Files:**
- Create: `src/submission_store.py`
- Create: `src/region_cropper.py`
- Modify: `webapp/main.py`
- Test: `tests/test_submission_store.py`
- Test: `tests/test_region_cropper.py`

- [ ] **Step 1: Write the failing manifest-grouping test**

```python
from src.submission_store import build_submission_manifest


def test_build_submission_manifest_groups_pages_by_student():
    files = [
        "aligned_exam_stu001_p1.png",
        "aligned_exam_stu001_p2.png",
        "aligned_exam_stu002_p1.png",
    ]

    manifest = build_submission_manifest(files)

    assert list(manifest.keys()) == ["stu001", "stu002"]
    assert manifest["stu001"]["pages"][0]["page"] == 1
    assert manifest["stu001"]["pages"][1]["page"] == 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_submission_store.py -q`

Expected: import failure for `src.submission_store`

- [ ] **Step 3: Implement manifest grouping**

```python
STUDENT_PAGE_RE = re.compile(r"_stu(?P<student>\d+)_p(?P<page>\d+)\.png$", re.IGNORECASE)


def build_submission_manifest(file_names: list[str]) -> dict[str, dict]:
    grouped: dict[str, dict] = {}
    for name in sorted(file_names):
        match = STUDENT_PAGE_RE.search(name)
        if not match:
            continue
        student_id = f"stu{match.group('student')}"
        grouped.setdefault(student_id, {"student_id": student_id, "pages": []})
        grouped[student_id]["pages"].append(
            {"page": int(match.group("page")), "aligned_file": name}
        )
    return grouped
```

- [ ] **Step 4: Write the failing crop test**

```python
from src.region_cropper import crop_question_region


def test_crop_question_region_uses_normalized_box(tmp_path):
    image = Image.new("RGB", (100, 100), "white")
    image_path = tmp_path / "page.png"
    image.save(image_path)

    out_path = tmp_path / "crop.png"
    crop_question_region(
        image_path=image_path,
        box={"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.2},
        out_path=out_path,
    )

    cropped = Image.open(out_path)
    assert cropped.size == (30, 20)
```

- [ ] **Step 5: Run the crop test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_region_cropper.py -q`

Expected: import failure for `src.region_cropper`

- [ ] **Step 6: Implement crop extraction**

```python
from PIL import Image


def crop_question_region(image_path: Path, box: dict, out_path: Path) -> None:
    image = Image.open(image_path)
    width, height = image.size
    left = int(box["x"] * width)
    top = int(box["y"] * height)
    right = int((box["x"] + box["w"]) * width)
    bottom = int((box["y"] + box["h"]) * height)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.crop((left, top, right, bottom)).save(out_path)
```

- [ ] **Step 7: Add a grading-preparation endpoint that writes manifests and crops**

```python
@app.post("/api/grading/prepare")
async def prepare_grading():
    bundle = load_assessment_bundle(_paths().json_dir / "regions.json")
    students = list_students_from_aligned(_paths().aligned_dir)
    manifests = write_submission_manifests(_paths(), students, bundle["questions"])
    generate_reference_crops(_paths(), bundle["questions"])
    generate_student_crops(_paths(), manifests, bundle["questions"])
    return {"success": True, "students": len(manifests)}
```

- [ ] **Step 8: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_submission_store.py tests/test_region_cropper.py -q`

Expected: all tests pass

- [ ] **Step 9: Commit**

```bash
git add src/submission_store.py src/region_cropper.py webapp/main.py tests/test_submission_store.py tests/test_region_cropper.py
git commit -m "feat: add submission manifests and crop extraction"
```

---

### Task 3: Add OCR and answer normalization

**Files:**
- Create: `src/ocr_engine.py`
- Create: `src/answer_normalizer.py`
- Modify: `requirements.txt`
- Modify: `webapp/main.py`
- Test: `tests/test_answer_normalizer.py`

- [ ] **Step 1: Write the failing normalization tests**

```python
from src.answer_normalizer import normalize_objective_answer, normalize_short_answer


def test_normalize_objective_answer_maps_common_ocr_variants():
    assert normalize_objective_answer("2)") == "②"
    assert normalize_objective_answer("O") == "○"


def test_normalize_short_answer_strips_noise():
    assert normalize_short_answer("  -12 cm ") == "-12cm"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_answer_normalizer.py -q`

Expected: import failure for `src.answer_normalizer`

- [ ] **Step 3: Implement answer normalization**

```python
OBJECTIVE_MAP = {
    "1": "①", "2": "②", "3": "③", "4": "④", "5": "⑤",
    "1)": "①", "2)": "②", "3)": "③", "4)": "④", "5)": "⑤",
}


def normalize_objective_answer(text: str) -> str:
    raw = str(text or "").strip().replace(" ", "")
    return OBJECTIVE_MAP.get(raw, raw)


def normalize_short_answer(text: str) -> str:
    raw = str(text or "").strip().replace(" ", "")
    return raw.lower()
```

- [ ] **Step 4: Add PaddleOCR dependency**

```text
opencv-python
numpy
Pillow
PyMuPDF
fastapi
uvicorn
jinja2
python-multipart
pytest
paddleocr
```

- [ ] **Step 5: Wrap PaddleOCR behind a single adapter**

```python
from paddleocr import PaddleOCR


class OcrEngine:
    def __init__(self) -> None:
        self._reader = PaddleOCR(use_angle_cls=True, lang="korean")

    def read_text(self, image_path: Path) -> dict:
        result = self._reader.ocr(str(image_path), cls=True)
        texts = []
        for line in result[0] if result else []:
            texts.append({"text": line[1][0], "confidence": float(line[1][1])})
        return {"candidates": texts}
```

- [ ] **Step 6: Add an OCR endpoint over prepared student crops**

```python
@app.post("/api/grading/ocr")
async def run_ocr():
    engine = OcrEngine()
    updated = run_ocr_for_project(_paths(), engine)
    return {"success": True, "updated": updated}
```

- [ ] **Step 7: Mark low-confidence items for human review immediately**

```python
if best_confidence < 0.75 or normalized_answer == "":
    item["needs_review"] = True
    item.setdefault("review_reasons", []).append("low_ocr_confidence")
```

- [ ] **Step 8: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_answer_normalizer.py -q`

Expected: all tests pass

- [ ] **Step 9: Commit**

```bash
git add src/ocr_engine.py src/answer_normalizer.py requirements.txt webapp/main.py tests/test_answer_normalizer.py
git commit -m "feat: add OCR and answer normalization"
```

---

### Task 4: Implement automatic scoring against the saved answer key

**Files:**
- Create: `src/grader.py`
- Modify: `src/submission_store.py`
- Modify: `webapp/main.py`
- Test: `tests/test_grader.py`

- [ ] **Step 1: Write the failing grading tests**

```python
from src.grader import grade_submission_item


def test_grade_submission_item_scores_objective_match():
    item = {"question_number": 1, "recognized_answer": "②"}
    answer = {"number": 1, "answer": "②", "points": 5, "type": "객관식"}

    result = grade_submission_item(item, answer)

    assert result["is_correct"] is True
    assert result["points_earned"] == 5


def test_grade_submission_item_flags_short_answer_mismatch():
    item = {"question_number": 2, "recognized_answer": "x=3"}
    answer = {"number": 2, "answer": "x=4", "points": 4, "type": "단답형"}

    result = grade_submission_item(item, answer)

    assert result["is_correct"] is False
    assert result["points_earned"] == 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_grader.py -q`

Expected: import failure for `src.grader`

- [ ] **Step 3: Implement the grading rules**

```python
from answer_normalizer import normalize_objective_answer, normalize_short_answer


def grade_submission_item(item: dict, answer: dict) -> dict:
    answer_type = answer.get("type", "객관식")
    if answer_type == "객관식":
        expected = normalize_objective_answer(answer.get("answer", ""))
        actual = normalize_objective_answer(item.get("recognized_answer", ""))
    else:
        expected = normalize_short_answer(answer.get("answer", ""))
        actual = normalize_short_answer(item.get("recognized_answer", ""))

    is_correct = expected == actual
    return {
        "expected_answer": expected,
        "recognized_answer": actual,
        "is_correct": is_correct,
        "points_possible": int(answer.get("points", 0)),
        "points_earned": int(answer.get("points", 0)) if is_correct else 0,
    }
```

- [ ] **Step 4: Add submission-level scoring aggregation**

```python
def score_submission(submission: dict, answers: list[dict]) -> dict:
    answers_by_key = {(a["page"], a["number"]): a for a in answers}
    total = 0
    earned = 0
    for item in submission["items"]:
        answer = answers_by_key[(item["page"], item["question_number"])]
        scored = grade_submission_item(item, answer)
        item.update(scored)
        total += scored["points_possible"]
        earned += scored["points_earned"]
    submission["total_points"] = total
    submission["total_score"] = earned
    return submission
```

- [ ] **Step 5: Add a scoring endpoint**

```python
@app.post("/api/grading/score")
async def score_grading_results():
    bundle = load_assessment_bundle(_paths().json_dir / "regions.json")
    count = score_project_submissions(_paths(), bundle["answers"])
    return {"success": True, "students": count}
```

- [ ] **Step 6: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_grader.py -q`

Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add src/grader.py src/submission_store.py webapp/main.py tests/test_grader.py
git commit -m "feat: add automatic scoring"
```

---

### Task 5: Add the teacher review UI for low-confidence answers

**Files:**
- Create: `webapp/templates/grading_overview.html`
- Create: `webapp/templates/grading_student.html`
- Modify: `webapp/main.py`
- Modify: `src/submission_store.py`
- Test: `tests/test_submission_store.py`

- [ ] **Step 1: Write the failing store test for review filtering**

```python
from src.submission_store import list_students_needing_review


def test_list_students_needing_review_only_returns_flagged_students():
    submissions = [
        {"student_id": "stu001", "needs_review_count": 2},
        {"student_id": "stu002", "needs_review_count": 0},
    ]

    flagged = list_students_needing_review(submissions)

    assert [row["student_id"] for row in flagged] == ["stu001"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_submission_store.py -q`

Expected: missing helper failure

- [ ] **Step 3: Add grading routes without overloading `/review`**

```python
@app.get("/grading")
async def grading_overview(request: Request):
    submissions = load_all_submission_results(_paths())
    return TEMPLATES.TemplateResponse(
        request=request,
        name="grading_overview.html",
        context={"project": refresh_project_metadata(_ensure_current_project(), touch=False), "submissions": submissions},
    )


@app.get("/grading/student/{student_id}")
async def grading_student(request: Request, student_id: str):
    submission = load_submission_result(_paths(), student_id)
    return TEMPLATES.TemplateResponse(
        request=request,
        name="grading_student.html",
        context={"submission": submission, "student_id": student_id},
    )
```

- [ ] **Step 4: Build the overview template around the current project model**

```html
<section class="panel">
  <h2>검토 대기 학생</h2>
  {% for row in submissions %}
    <article class="queue-item">
      <div>
        <strong>{{ row.student_id }}</strong>
        <span>{{ row.needs_review_count }}문항 검토 필요</span>
      </div>
      <a class="btn" href="/grading/student/{{ row.student_id }}">검토 열기</a>
    </article>
  {% endfor %}
</section>
```

- [ ] **Step 5: Build the per-student review page around crop + OCR + expected answer**

```html
{% for item in submission.items %}
  <article class="question-card">
    <h3>{{ item.page }}페이지 {{ item.question_number }}번</h3>
    <img src="{{ item.student_crop_url }}" alt="student crop">
    <p>OCR: {{ item.recognized_answer }}</p>
    <p>정답: {{ item.expected_answer }}</p>
    <input type="text" name="manual_answer_{{ item.item_id }}" value="{{ item.recognized_answer }}">
    <button type="submit" name="mark_correct" value="{{ item.item_id }}">정답 처리</button>
    <button type="submit" name="mark_wrong" value="{{ item.item_id }}">오답 처리</button>
  </article>
{% endfor %}
```

- [ ] **Step 6: Add POST handling for manual corrections**

```python
@app.post("/grading/student/{student_id}")
async def save_grading_student(request: Request, student_id: str):
    form = await request.form()
    submission = apply_manual_review(_paths(), student_id, form)
    save_submission_result(_paths(), submission)
    return RedirectResponse(url=f"/grading/student/{student_id}", status_code=303)
```

- [ ] **Step 7: Manually verify the grading pages in the browser**

Run: open `/grading`, click one student, verify crop image, OCR text, expected answer, score controls, and save round-trip

Expected: the page loads without console errors and manual corrections persist

- [ ] **Step 8: Commit**

```bash
git add webapp/main.py webapp/templates/grading_overview.html webapp/templates/grading_student.html src/submission_store.py tests/test_submission_store.py
git commit -m "feat: add teacher review workflow"
```

---

### Task 6: Export per-student scores and project statistics

**Files:**
- Create: `src/report_exporter.py`
- Modify: `requirements.txt`
- Modify: `webapp/main.py`
- Test: `tests/test_report_exporter.py`

- [ ] **Step 1: Write the failing export test**

```python
from src.report_exporter import build_summary_rows


def test_build_summary_rows_includes_score_and_accuracy():
    submissions = [
        {"student_id": "stu001", "total_score": 18, "total_points": 20},
        {"student_id": "stu002", "total_score": 12, "total_points": 20},
    ]

    rows = build_summary_rows(submissions)

    assert rows[0]["student_id"] == "stu001"
    assert rows[0]["accuracy"] == 90.0
    assert rows[1]["accuracy"] == 60.0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_report_exporter.py -q`

Expected: import failure for `src.report_exporter`

- [ ] **Step 3: Implement summary-row and question-stat builders**

```python
def build_summary_rows(submissions: list[dict]) -> list[dict]:
    rows = []
    for submission in submissions:
        total_points = submission.get("total_points", 0) or 0
        total_score = submission.get("total_score", 0) or 0
        accuracy = round((total_score / total_points) * 100, 1) if total_points else 0.0
        rows.append(
            {
                "student_id": submission["student_id"],
                "total_score": total_score,
                "total_points": total_points,
                "accuracy": accuracy,
            }
        )
    return rows
```

- [ ] **Step 4: Add Excel dependency**

```text
openpyxl
```

- [ ] **Step 5: Export CSV first, XLSX second**

```python
def export_csv(rows: list[dict], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
```

```python
def export_xlsx(summary_rows: list[dict], question_rows: list[dict], out_path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "scores"
    ws.append(list(summary_rows[0].keys()))
    for row in summary_rows:
        ws.append(list(row.values()))
    wb.save(out_path)
```

- [ ] **Step 6: Add export routes**

```python
@app.post("/api/export/results")
async def export_results():
    files = generate_project_exports(_paths())
    return {"success": True, "files": files}


@app.get("/api/export/{name}")
async def download_export(name: str):
    path = _paths().exports_dir / name
    return FileResponse(str(path))
```

- [ ] **Step 7: Keep PDF export last and optional until XLSX is trusted**

```python
def export_pdf_placeholder() -> dict:
    return {"enabled": False, "reason": "Implement after XLSX layout is accepted by teachers"}
```

- [ ] **Step 8: Run focused tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_report_exporter.py -q`

Expected: all tests pass

- [ ] **Step 9: Commit**

```bash
git add src/report_exporter.py requirements.txt webapp/main.py tests/test_report_exporter.py
git commit -m "feat: add grading exports"
```

---

## Implementation Order Summary

1. Lock the Gemini-web JSON contract so `questions + answers + total_points` are always valid and saved consistently.
2. Build deterministic per-student manifests and crop artifacts from aligned pages.
3. Add OCR and normalization over those crops.
4. Score OCR output against the saved answer key.
5. Add a dedicated teacher review workflow for low-confidence items.
6. Export scores and summary statistics after reviewed scores become trustworthy.

## Notes For This Repository

- Treat the external Gemini-web prompt flow as **already operational**, not as a missing feature. The new work starts at stable ingestion and downstream use of that JSON.
- Do **not** merge grading UI into `/review`. `/review` is already the alignment and region-verification tool. Add a separate grading flow such as `/grading`.
- Prefer new `grading_*.html` templates over wiring the current `batch_detail.html` and `submission_review.html` directly. Those templates can be mined for layout ideas, but their current data model assumes routes and entities that this repository does not yet expose.
- Keep YOLO export intact. It is a parallel artifact path and should not block OCR/grading implementation.
