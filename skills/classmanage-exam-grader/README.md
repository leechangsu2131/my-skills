# classmanage-exam-grader

Local teacher workstation for grading scanned exams, reviewing drafted feedback, and exporting student-facing PDFs.

## Canonical Structure

The project is now organized around these canonical directories:

- `apps/`
  Thin entrypoints for the web UI and CLI.
- `packages/contracts/`
  Shared models and data contracts.
- `packages/student_extraction/`
  Blank-template alignment, page selection, OCR, and student answer extraction.
- `packages/answer_key_extraction/`
  Answer-key JSON/PDF parsing.
- `packages/grading/`
  Grading, analysis merge, and subjective grading helpers.
- `packages/annotation/`
  PDF feedback generation entrypoint.
- `packages/export/`
  Dashboard/export entrypoint.

Legacy top-level modules such as `ocr_extractor.py`, `answer_key_parser.py`, `grader.py`, and `analysis_merger.py` remain only as compatibility wrappers. New code should prefer `apps/*` and `packages/*`.

If you are browsing the repo, start here:

```text
classmanage-exam-grader/
  apps/
  packages/
  tests/
  data/
  docs/
  prompts/
  schemas/
```

These are the folders that define the current architecture. The rest are either compatibility layers or local runtime folders.

## Web UI (default)

```powershell
cd skills/classmanage-exam-grader
python -m pip install -r requirements.txt
python -m uvicorn apps.web.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

`paddleocr` is included in `requirements.txt`, but you may also need a compatible `paddlepaddle` runtime for your local Python/OS combination before OCR can run.

## Batch Inputs

Each batch now requires:

1. One blank exam PDF.
2. One answer-key file.
3. One or more student exam files.

The blank exam is used as the alignment template for question-region OCR.

If a student PDF is **longer** than the blank (e.g. cover sheet or extra scans in one batch), use the web form’s **스캔 PDF 페이지 맞춤**: *자동* picks the contiguous window that best aligns to the template; *수동* sets a 0-based **시작 페이지** index. The CLI mirrors this via `python -m apps.cli.grade_exam ocr --blank-exam ...`.

Question-region layout extraction now lives in `packages/student_extraction/question_layout.py`, so OCR anchor parsing, deduplication, and answer-box construction all run through one dependency-light layout pipeline.

## What the web UI does

1. Upload a blank exam PDF, one answer-key file, and one or more student files.
2. Build a question layout from the blank exam and align each student page against it.
3. Prefer PDF text-layer extraction for digital PDFs, then fall back to PaddleOCR for scan-only regions.
4. Grade with the existing engine.
5. Review low-confidence or subjective answers in the browser.
6. Finalize and download annotated student PDFs.

## CLI (secondary)

The canonical CLI entrypoint is:

```powershell
cd skills/classmanage-exam-grader
python -m apps.cli.grade_exam all --students data/input/students/ --answer-key data/input/answer_key/answer.pdf
```

The legacy `python grade_exam.py ...` command still works, but new usage should prefer `apps.cli.grade_exam`.

## Local Folders

Not every top-level folder is part of the application architecture:

- `data/` stores real batch inputs/outputs.
- `.venv/` is the local Python runtime.
- `.gemini/` and `.bkit/` are local tool/runtime metadata.
- `.tmp/`, `.pytest_cache/`, `__pycache__/`, and `.codex_tmp_*` are disposable local artifacts and can be removed safely.

## Compatibility Layers

Some older paths still exist so existing commands and imports do not break immediately:

- `ocr/` re-exports the student-extraction implementation from `packages/student_extraction/`.
- `webapp/` holds the current FastAPI implementation details, while `apps/web/main.py` is the stable app entrypoint.
- Top-level modules like `ocr_extractor.py`, `answer_key_parser.py`, `grader.py`, `analysis_merger.py`, `pdf_annotator.py`, and `html_reporter.py` remain as compatibility or transition modules.

For new work, prefer `apps/*` and `packages/*` over the legacy entrypoints above.
