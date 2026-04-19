# Classmanage Exam Grader Paddle OCR Template Design

**Date:** 2026-04-19  
**Project:** `skills/classmanage-exam-grader`

## Goal

Replace the current Gemini CLI-centered OCR path with a blank-exam-template-driven Paddle OCR pipeline that improves recognition quality while preserving the existing web review flow, grading logic, and PDF feedback generation.

## Context

The current web UI and grading flow are in place, but the OCR stage is still biased toward whole-page extraction through Gemini CLI prompts. That creates two problems:

1. Recognition quality is inconsistent on student-written answers.
2. The pipeline ignores useful structure that already exists in the exam layout.

The new direction is to use a blank, unfilled exam PDF as a required template. That template becomes the source of truth for page alignment and per-question crop extraction. OCR then runs on those focused question regions instead of on the full page. The reference project `Point-Checker-main` is used for ideas around per-region extraction, page normalization, and question-focused recognition, but its Tkinter UI, YOLO training assets, and full app pipeline are not being imported into this v1. The local `Paddle` repository is the PaddlePaddle framework source tree, not a drop-in OCR app, so this design uses Paddle ecosystem OCR runtime within `classmanage-exam-grader` rather than vendoring that repository.

## Product Decisions

- Batch creation requires three inputs:
  - one blank exam PDF
  - one answer key file (`.json` or teacher PDF)
  - one or more student exam PDFs
- If any of those three input groups are missing, the batch must not start.
- Paddle OCR becomes the default OCR path for student answer extraction.
- Gemini CLI is removed from the primary student OCR path in v1.
- Existing grading, review, and PDF annotation modules stay in place unless they need small compatibility changes.
- `Point-Checker-main` contributes design ideas, not a wholesale code transplant.

## Architecture

The system remains a web-first teacher workstation. The upload and review experience stays in the current FastAPI app, while the OCR stage is reworked into a layout-aware pipeline:

1. Upload blank exam, answer key, and student exams.
2. Render blank exam pages to images.
3. Detect question anchors and build a reusable question layout map.
4. Render each student PDF to images.
5. Align each student page against the matching blank exam page.
6. Transform blank-template question regions into student-page coordinates.
7. Run Paddle OCR on the cropped question regions.
8. Convert OCR output into the existing `student_answers` schema.
9. Feed results into `grader.py`, `analysis_merger.py`, and `pdf_annotator.py`.
10. Send low-confidence or ambiguous items into the existing review UI.

This preserves the current back half of the product while replacing the recognition front half with a more structure-aware pipeline.

## Component Design

### `webapp/main.py`

- Require `blank_exam` upload during batch creation.
- Validate that `blank_exam`, `answer_key`, and at least one student file are all present.
- Show clear user-facing errors when any required file group is missing.

### `webapp/store.py`

- Extend stored batch metadata with:
  - `blank_exam_path`
  - optional OCR metadata path
  - optional alignment/layout status fields
- Keep per-submission failure tracking so one student can fail without killing the whole batch.

### `webapp/services/pipeline.py`

- Orchestrate the new OCR flow.
- Parse answer key as before.
- Build the question layout from the blank exam once per batch.
- Reuse that layout for every student in the batch.
- Convert OCR output into the existing reviewed submission payload.

### `ocr_extractor.py`

- Stop behaving like a Gemini prompt wrapper.
- Become a stable entry point for student answer extraction using the new OCR stack.
- Return the same high-level schema expected by the rest of the app:
  - `student_name`
  - `student_number`
  - `exam_title`
  - `answers[]` with `q_num`, `answer`, `type`, `confidence`, plus page/region metadata where available

### New module: `ocr/template_alignment.py`

- Render PDF pages into images.
- Normalize page size and coordinate space.
- Align each student page to the blank exam page using image-based registration.
- Output transform data that can map blank-template coordinates onto the student page.

This is where the project adopts the useful part of the Point-Checker mindset: normalize the sheet first, then read focused regions instead of OCRing the whole page blindly.

### New module: `ocr/question_layout.py`

- Analyze the blank exam pages to identify question anchor positions.
- Build per-question bounding regions that cover the expected answer area.
- Start with layout inference driven by OCR-visible question numbers and their ordering.
- Avoid pulling in YOLO models for v1.

### New module: `ocr/paddle_backend.py`

- Manage Paddle OCR initialization and execution.
- Run OCR on per-question crops.
- Return recognized text and confidence values.
- Expose a narrow interface so OCR runtime details do not leak into the rest of the app.

## Data Flow

### Batch-level flow

1. Teacher uploads blank exam PDF, answer key, and student exam PDFs.
2. System stores all files inside the batch workspace.
3. Blank exam pages are rendered and analyzed once.
4. A reusable question layout artifact is saved for the batch.
5. Each student PDF is processed independently against that layout.

### Student-level flow

1. Render student PDF pages to images.
2. Align each student page to the corresponding blank exam page.
3. Transform question crop boxes onto the student page.
4. Run Paddle OCR on each question crop.
5. Produce `student_answers`.
6. Grade using existing grading modules.
7. Build review payload with confidence-aware review defaults.

## Review Behavior

- High-confidence answers can default to approved.
- Low-confidence answers must default to `needs_review`.
- Blank or suspicious OCR results must also default to `needs_review`.
- Teacher edits remain the final authority before PDF export.

The current review UI remains the human safety net, but it now receives better structured OCR evidence.

## Failure Handling

### Batch-blocking failures

- Missing blank exam PDF
- Missing answer key
- Missing student files
- Blank exam layout extraction failure
- Paddle OCR runtime or model initialization failure

These stop the batch immediately and surface a clear error in the batch view.

### Submission-level failures

- Student page alignment failure
- Student PDF rendering failure
- OCR failure on a specific student

These mark only the affected submission as failed. Other submissions in the batch continue processing.

### Review-required outcomes

- OCR text returned with low confidence
- OCR result appears blank or malformed
- Question crop exists but extracted content is ambiguous

These are not hard failures. They route into teacher review.

## Scope for V1

Included in v1:

- blank exam PDF as a required upload
- Paddle OCR as the default student OCR engine
- PDF page rendering
- blank-to-student page alignment
- question-focused crop extraction
- confidence-aware review routing
- compatibility with existing grading and PDF feedback flow

Explicitly excluded from v1:

- importing Point-Checker Tkinter UI
- importing Point-Checker YOLO training pipeline wholesale
- bundling or modifying the local `Paddle` framework repository
- training a custom question detector
- real-time progress streaming
- asynchronous worker queues

## Testing Strategy

### Unit tests

- batch validation requires blank exam upload
- layout extraction returns stable question regions for a known blank template
- alignment transform maps blank coordinates into student coordinates
- OCR adapter returns expected normalized question payloads
- low-confidence OCR answers become `needs_review`

### Web/integration tests

- batch creation fails when blank exam is missing
- batch creation succeeds with blank exam, answer key, and student PDFs
- a student submission can fail without failing the entire batch
- reviewed submission payload still renders in the existing UI
- finalized PDF generation still works after the OCR pipeline change

## Migration Notes

- Existing web UI stays intact and only gains the required blank exam field.
- Existing grading schemas remain the compatibility target.
- The old Gemini-based OCR code can remain temporarily behind a fallback or legacy path during migration, but v1 product behavior treats Paddle OCR as the primary engine.
- Documentation and README instructions must be updated to reflect the new required inputs and runtime dependencies.

## Open Constraints

- Paddle OCR runtime setup on the local teacher workstation must be documented clearly.
- Question layout inference must favor maintainability over model complexity in v1.
- The design assumes blank exam and student submissions share the same page structure for a given batch.

## Summary

This design improves recognition by making the exam layout explicit instead of treating every page as an unstructured OCR target. The blank exam becomes the template, Paddle OCR handles question-focused text extraction, Point-Checker contributes structural ideas rather than heavy runtime dependencies, and the existing grading/review/export flow remains the stable backbone of the product.
