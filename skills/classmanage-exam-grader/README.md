# classmanage-exam-grader

Local-first exam grading workstation for scanned tests, teacher review, and annotated feedback PDFs.

## Start Here

This project has been refactored so new work should usually begin in these places:

- `apps/`
  Stable entrypoints only.
- `packages/`
  Canonical domain logic.
- `webapp/`
  FastAPI adapter, templates, and web-specific orchestration details.
- `tests/`
  Behavior and contract coverage.

Top-level files such as `ocr_extractor.py`, `grader.py`, and `answer_key_parser.py` still exist, but they are compatibility layers. Prefer `apps/*`, `packages/*`, and `webapp/*` for new work.

## Canonical Structure

```text
classmanage-exam-grader/
  apps/
    web/
    cli/
  packages/
    contracts/
    student_extraction/
    answer_key_extraction/
    grading/
    annotation/
    export/
  webapp/
    services/
    templates/
    static/
  tests/
  data/
  docs/
  prompts/
```

## Token-Efficient Edit Guide

If you are changing one feature, start with the smallest matching module instead of reading the whole repo.

For Korean exam-sheet structure conventions that should guide parsing, see `docs/00-pm/2026-04-25-korean-exam-paper-structure-reference.md`.

- Student scan alignment, OCR, grouped PDFs, duplex blank pages:
  `packages/student_extraction/`
- Objective answer-region localization and detector handoff:
  `packages/student_extraction/answer_region_detector.py`
  `packages/student_extraction/answer_regions.py`
  `packages/student_extraction/service.py`
- Answer key parsing from JSON or PDF:
  `packages/answer_key_extraction/`
- Scoring, merged analysis, subjective grading:
  `packages/grading/`
- Annotated feedback PDF generation:
  `packages/annotation/`
- Shared payload shape and review models:
  `packages/contracts/models.py`
- Web upload-to-grade adapter:
  `webapp/services/pipeline.py`
- Web batch background processing:
  `webapp/services/batch_runner.py`
- Web routes and page composition only:
  `webapp/main.py`
- Review page UI:
  `webapp/templates/submission_review.html`
- Batch dashboard UI:
  `webapp/templates/batch_detail.html`

Rule of thumb:

- Route problem: open `webapp/main.py`
- Batch timing / background processing problem: open `webapp/services/batch_runner.py`
- OCR quality problem: open `packages/student_extraction/`
- Grading logic problem: open `packages/grading/`
- Review payload problem: open `packages/contracts/models.py` and `webapp/services/pipeline.py`

## Current Runtime Flow

1. Upload one blank exam PDF, one answer key, and one or more student files.
2. `webapp/main.py` creates the batch and stores the uploads.
3. `webapp/services/batch_runner.py` processes the batch in the background.
4. `webapp/services/pipeline.py` adapts parsed answers into review payloads and final PDFs.
5. `packages/student_extraction/` handles OpenCV-based preprocessing, template alignment, grouped student PDFs, duplex trailing blank pages, OCR, answer-region localization, and fallback logic.
6. `packages/grading/` scores the answers.
7. Teachers review low-confidence items in the browser.
8. `packages/annotation/` writes final feedback PDFs.

## Answer Region Detection

The student extraction path now uses a hybrid answer-region strategy:

- OpenCV handles page cleanup, alignment, crop refinement, line detection, and heuristic objective-answer localization.
- A YOLOv8 hook exists for locating objective answer regions when a trained detector is available.
- The current default runtime mode is still `opencv`, so the system works without YOLO weights.
- When YOLO is configured, the detector runs first for multiple-choice answer regions and OpenCV remains the fallback.
- The OpenCV fallback now covers parenthesized blanks, horizontal answer lines, and rectangular choice boxes more explicitly than before.
- Question prompt parsing now tries to merge multi-line stems while ignoring score tags like `[5점]` and option rows such as `①` to `⑤`.

The handoff lives in:

- `packages/student_extraction/answer_region_detector.py`
- `packages/student_extraction/answer_regions.py`
- `packages/student_extraction/service.py`

Configuration lives in `config.json` under `answer_region_detector`.

Example:

```json
"answer_region_detector": {
  "mode": "opencv",
  "weights_path": "",
  "confidence": 0.25,
  "class_aliases": [
    "answer",
    "answer_area",
    "answer_blank",
    "choice_blank",
    "choice_box",
    "choice_answer_region",
    "checkbox",
    "objective_answer",
    "short_answer_line",
    "descriptive_answer_area"
  ]
}
```

To enable YOLO-backed answer-region detection, set:

- `mode` to `hybrid`, `yolo`, or `yolo_first`
- install `ultralytics` into the project `.venv` with `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
- `weights_path` to a trained detector checkpoint

For the local training workflow, use question-crop datasets rather than full-page exam images. The project now includes:

- `.\.venv\Scripts\python.exe -m apps.cli.init_answer_region_yolo_dataset`
- `.\.venv\Scripts\python.exe -m apps.cli.train_answer_region_yolo --device cpu --model yolov8n.pt`

The detailed workflow and class guidance live in `docs/00-pm/2026-04-25-yolo-answer-region-training-workflow.md`.

If YOLO is unavailable or returns no region, the pipeline falls back to the OpenCV path automatically.

## Supported Student PDF Patterns

Current extraction supports these common cases:

- One student PDF whose page count matches the blank exam.
- One student PDF longer than the blank exam, where the best matching contiguous page window should be auto-selected.
- One merged PDF containing multiple students back-to-back when each student contributes exactly `template_page_count` pages.
- One merged PDF containing multiple students from duplex scanning when each student contributes `template_page_count + 1` pages and the last page is nearly blank.

It does not yet fully solve every arbitrary mixed scan. For example, heavily interleaved cover sheets or variable-length student bundles may still need more rules.

## Web UI

Recommended launch:

```powershell
cd C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader
Use the launcher batch file in the project root, or run the command below directly.
```

Or directly:

```powershell
cd C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader
.venv\Scripts\python.exe -m uvicorn apps.web.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The upload request now returns quickly and the heavy OCR work runs in the background. The batch detail page auto-refreshes while the batch is in `processing`.

The launcher batch file creates `.venv` and installs the Python packages used by OpenCV, PaddleOCR, and YOLO from `requirements.txt`.

## CLI

The canonical CLI entrypoint is:

```powershell
cd C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\classmanage-exam-grader
.venv\Scripts\python.exe -m apps.cli.grade_exam all --students data/input/students/ --answer-key data/input/answer_key/answer.pdf
```

Legacy `python grade_exam.py ...` still works, but new usage should prefer `apps.cli.grade_exam`.

## Batch Inputs

Each batch requires:

1. One blank exam PDF.
2. One answer key file.
3. One or more student exam files.

The blank exam is the layout and alignment template. Student answers are extracted against that structure.

## Current Status

Current behavior is best thought of as:

- Subjective questions: review-oriented, usually showing the broader question area.
- Objective questions: OpenCV-based prompt/blank localization with a YOLO-ready extension point.
- Production-safe default: no YOLO dependency required.

Known limitation:

- Some Korean multiple-choice formats that end with a thin `(   )` blank are still not fully reliable under the pure OpenCV fallback path.
- The next accuracy step is to train a YOLOv8 answer-region detector and point `answer_region_detector.weights_path` at that model.

## Background Processing Boundary

To keep the code modular:

- `webapp/main.py` should stay thin.
- `webapp/services/batch_runner.py` owns batch scheduling, submission creation, status transitions, and batch error recording.
- `webapp/services/pipeline.py` owns conversion between engine outputs and web payloads.

If `webapp/main.py` starts growing again, move orchestration logic into `webapp/services/` instead of adding more behavior directly to routes.

## Local Folders

Not every top-level folder is part of the application architecture.

- `data/` stores real batch data.
- `.venv/` is the local Python runtime.
- `.gemini/` and `.bkit/` are local tool metadata.
- `.tmp/`, `.pytest_cache/`, `__pycache__/`, and `.codex_tmp_*` are disposable local artifacts.

## Compatibility Layers

These paths still exist so older imports and commands do not break immediately:

- `ocr_extractor.py`
- `answer_key_parser.py`
- `grader.py`
- `analysis_merger.py`
- `pdf_annotator.py`
- `html_reporter.py`

Treat them as wrappers, not the preferred place for new implementation work.
