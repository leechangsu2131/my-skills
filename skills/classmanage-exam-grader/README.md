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
