# classmanage-exam-grader

Local teacher workstation for grading scanned exams, reviewing drafted feedback, and exporting student-facing PDFs.

## Web UI (default)

```powershell
cd skills/classmanage-exam-grader
python -m pip install -r requirements.txt
python -m uvicorn webapp.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

`paddleocr` is included in `requirements.txt`, but you may also need a compatible `paddlepaddle` runtime for your local Python/OS combination before OCR can run.

## Batch Inputs

Each batch now requires:

1. One blank exam PDF.
2. One answer-key file.
3. One or more student exam files.

The blank exam is used as the alignment template for question-region OCR.

## What the web UI does

1. Upload a blank exam PDF, one answer-key file, and one or more student files.
2. Build a question layout from the blank exam and align each student page against it.
3. Run question-focused OCR, then grade with the existing engine.
4. Review low-confidence or subjective answers in the browser.
5. Finalize and download annotated student PDFs.

## CLI (secondary)

The original CLI pipeline is still available:

```powershell
cd skills/classmanage-exam-grader
python grade_exam.py all --students data/input/students/ --answer-key data/input/answer_key/answer.pdf
```

Use the CLI when you want direct batch scripting or to debug the legacy flow.
