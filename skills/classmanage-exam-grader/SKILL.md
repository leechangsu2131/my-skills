---
name: classmanage-exam-grader
description: Local-first exam grading workstation with blank-template alignment, grouped student PDF support, teacher review, and annotated feedback PDFs.
---

# classmanage-exam-grader

Use this project guide when you need to change exam grading behavior without re-reading the whole codebase.

## Read This First

- For product overview and runtime commands, read `README.md`.
- For Korean exam layout conventions that should guide parsing and answer-region decisions, read `docs/00-pm/2026-04-25-korean-exam-paper-structure-reference.md`.
- For actual implementation, prefer `packages/*`, `webapp/services/*`, and `webapp/templates/*`.
- Avoid starting from top-level compatibility files unless you are preserving legacy imports.

## Canonical Boundaries

- `apps/web/main.py`
  Stable web entrypoint only.
- `apps/cli/grade_exam.py`
  Stable CLI entrypoint only.
- `packages/contracts/`
  Shared models and contracts.
- `packages/student_extraction/`
  Blank exam alignment, grouped student PDFs, duplex trailing blank pages, OCR, and answer extraction.
- `packages/student_extraction/answer_region_detector.py`
  YOLO-first or OpenCV-fallback answer-region routing for objective questions.
- `packages/student_extraction/answer_regions.py`
  OpenCV heuristics for objective answer blanks and prompt-localized crops.
- `packages/answer_key_extraction/`
  Answer key parsing.
- `packages/grading/`
  Scoring and analysis merge.
- `packages/annotation/`
  Annotated feedback PDFs.
- `webapp/services/pipeline.py`
  Adapter between engine outputs and review/finalization payloads.
- `webapp/services/batch_runner.py`
  Batch orchestration, background processing, submission creation, and batch status transitions.
- `webapp/main.py`
  Routes, request validation, and page composition.

## Edit Map

If the task is about one of these areas, open only the matching files first.

- OCR quality, page alignment, grouped PDFs:
  `packages/student_extraction/`
- Objective answer box localization, YOLO/OpenCV handoff:
  `packages/student_extraction/answer_region_detector.py`
  `packages/student_extraction/answer_regions.py`
  `packages/student_extraction/service.py`
- Duplex scan trailing blank pages:
  `packages/student_extraction/student_pages.py`
- Answer key parsing:
  `packages/answer_key_extraction/service.py`
- Review payload fields:
  `packages/contracts/models.py`
  `webapp/services/pipeline.py`
- Batch timing, background jobs, upload latency:
  `webapp/services/batch_runner.py`
- Batch page rendering:
  `webapp/main.py`
  `webapp/templates/batch_detail.html`
- Review UI:
  `webapp/templates/submission_review.html`
- Final PDF output:
  `packages/annotation/`
  `webapp/services/pipeline.py`

## Rules For New Work

- Prefer editing `packages/*` or `webapp/services/*` over top-level wrapper files.
- Keep `webapp/main.py` thin. If logic grows, move it into `webapp/services/`.
- Keep data shape changes centered in `packages/contracts/models.py`.
- Add or update focused tests in `tests/` for the module you touched.
- Do not put new domain logic into `apps/*`; those are entrypoints.

## Current Behavioral Assumptions

- Batch input requires:
  - one blank exam PDF
  - one answer key
  - one or more student files
- Korean school exam structure should be treated as a parsing prior:
  - question anchors use `1.`, `2.`, `3.`
  - `※` blocks often describe shared passages
  - many pages use left-column-first, then right-column reading order
  - score tags like `[5점]` and option rows `①` to `⑤` should not be confused with the question stem itself
- Objective answer-region detection currently defaults to OpenCV heuristics.
- If `config.json` provides `answer_region_detector.mode` plus a valid YOLO weights path, and `ultralytics` is installed in the project `.venv`, multiple-choice answer regions will try YOLO first and fall back to OpenCV automatically.
- If you are preparing a YOLO detector, follow `docs/00-pm/2026-04-25-yolo-answer-region-training-workflow.md` and keep the dataset question-crop-based rather than full-page-based.
- Grouped student PDFs are supported when:
  - students are back-to-back at exactly `template_page_count`, or
  - students are duplex scanned at `template_page_count + 1` with a nearly blank trailing page
- Upload requests should return quickly; heavy OCR runs in the background through `webapp/services/batch_runner.py`

## Current OCR Focus

When the task is about "the crop is wrong" or "the answer area is not being found correctly", start here in order:

1. `packages/student_extraction/service.py`
2. `packages/student_extraction/answer_region_detector.py`
3. `packages/student_extraction/answer_regions.py`
4. `packages/student_extraction/question_layout.py`

Use OpenCV for:

- alignment and page cleanup
- geometric crop refinement
- line, contour, and fallback region detection

Use YOLOv8 for:

- locating objective answer blanks, answer boxes, checkboxes, or similar target regions

Current default is still OpenCV-only unless YOLO weights are explicitly configured.

## Verification Shortcuts

When changing only one area, prefer a focused test run first.

- Web batch behavior:
  `tests/webapp/test_batch_flow.py`
  `tests/webapp/test_upload_validation.py`
  `tests/webapp/test_batch_status.py`
- OCR page grouping:
  `tests/ocr/test_student_pages.py`
- Review payload behavior:
  `tests/webapp/test_pipeline.py`
  `tests/webapp/test_review_updates.py`

For full verification, run the main pytest suite from the project root.
