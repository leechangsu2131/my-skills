# Teacher Guide PDF Splitter

This project detects split ranges from front-matter topic lists, lesson-plan tables, overview pages, and local unit plan pages, then splits a teacher-guide PDF into smaller PDFs.

## Install

```bash
pip install -r requirements.txt
```

For tests and skill validation helpers:

```bash
pip install -r requirements-dev.txt
```

## Run the desktop app

```bash
python app.py
```

Use the app like this:

1. Select a teacher-guide PDF.
2. Choose an output folder.
3. Choose `단원 단위만 분할` or `차시/세부 제재까지 분할`.
4. Click `미리보기` to inspect detected ranges.
5. Click `분할 저장` to create split PDFs.

## Run from the command line

Preview only:

```bash
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --dry-run
```

Create split PDFs:

```bash
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --save
```

Request more detailed splits:

```bash
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --split-level detail --dry-run
```

Force TOC-first parsing:

```bash
python scripts/split_subunits_from_plan_table.py --pdf "teacher-guide.pdf" --out-dir "output" --strategy toc --dry-run
```

## Options

- `--strategy`: `auto`, `toc`, `plan`, or `overview`
- `--split-level`: `unit` or `detail`
- `--scan-pages`: how many front pages to inspect for TOC or lesson-plan structure
- `--page-offset`: manual adjustment after automatic page calibration
- `--z-col`: force the guide-page column index when plan-table auto detection is wrong

`overview` is useful for guide PDFs that start directly with unit pages and mark new units with headings such as `단원 개관` or `제재 개관`.

When a title extracted from a TOC or plan page looks truncated or OCR-noisy, the splitter now repairs only that group name from the destination start-page heading instead of relying on subject-specific title exceptions.

## Output

- `output/<pdf-name>/groups.json`: detected sections, detailed groups, final split groups, and the strategy used
- `output/<pdf-name>/pdf_splits/`: generated split PDFs
