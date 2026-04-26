# 2026-04-25 Korean Exam Paper Structure Reference

## Why This Exists

This project should treat standard Korean school exam structure as a first-class domain assumption rather than an incidental OCR detail.

When layout parsing, answer-region localization, or review payload behavior becomes ambiguous, prefer the structure below over raw OCR line order.

## Core Korean Exam Paper Rules

### 1. Two-column page flow is normal

- Many Korean school exam sheets are composed in a vertical two-column layout.
- Logical reading order is usually:
  - left column top to bottom
  - then right column top to bottom
- OCR or text extraction may interleave left and right columns, so question numbers can appear to jump unexpectedly.
- Reconstruct order using anchors such as:
  - `1.`, `2.`, `3.`
  - instruction blocks starting with `※`
  - grouped passage ranges like `(1~2)` or `(3~5)`

### 2. Meta block lives near the top

- The top area often contains exam metadata such as:
  - school or grade
  - subject
  - semester
  - exam type
- Do not treat this as question content even if OCR finds digits there.

### 3. Shared instruction and passage blocks matter

- A block starting with `※` often applies to multiple questions.
- Typical forms:
  - `※ 다음 글을 읽고 물음에 답하시오. (1~2)`
  - `※ 다음 자료를 보고 3~4번에 답하시오.`
- These blocks are not answer regions.
- They should help define question grouping and local reading context.

### 4. Question anchors are Arabic numerals plus period

- Question starts are usually `1.`, `2.`, `3.`.
- This is the strongest structural anchor when rebuilding layout.
- If OCR mixes columns or passages, trust question-number progression more than raw line order.

### 5. Score tags are metadata, not prompt text

- Score tags such as `[5점]` or `[3점]` often sit near the right edge of the question stem.
- They should not expand the semantic question prompt bbox.
- They should not be mistaken for answer regions or option content.

### 6. Multiple-choice options use circled numerals

- Standard Korean objective options usually use:
  - `①`, `②`, `③`, `④`, `⑤`
- In narrow columns, options may:
  - wrap to multiple lines
  - appear in two side-by-side rows
  - be split visually across the column width
- Therefore, option rows should be recognized by circled numerals, not by naive one-line assumptions.

### 7. Short-answer and descriptive items may expose answer shape

- Common answer cues include:
  - `(      )`
  - underlines
  - labeled blanks like `㉠`, `㉡`
- These cues can help infer answer-region type, but they should be interpreted inside question context, not in isolation.

## Practical Parsing Guidance For This Project

- Use question numbers and `※` blocks as layout anchors before trusting OCR order.
- Merge multi-line question stems when they stay inside the same question block.
- Exclude these from prompt bbox expansion when possible:
  - score tags like `[5점]`
  - option rows starting with `①` to `⑤`
  - the next question anchor
- Treat objective answer-region localization as a separate problem from OCR text recognition.
  - layout and prompt parsing decide where to look
  - answer-region detection decides what subregion is the actual response area
  - OCR reads only after those boundaries are stable

## Files That Should Respect This Reference

- `packages/student_extraction/question_layout.py`
- `packages/student_extraction/answer_regions.py`
- `packages/student_extraction/answer_region_detector.py`
- `packages/student_extraction/service.py`
- `tests/ocr/test_question_layout.py`
- `tests/ocr/test_answer_regions.py`

## Update Rule

If we learn a new recurring Korean exam pattern from real scans, add it here before or alongside code changes so the structural assumption is preserved for future work.
