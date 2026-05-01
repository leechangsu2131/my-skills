# Troubleshooting

## 2026-04-28 Rollback Recovery

### Symptoms
- Template exists but dashboard still shows template missing or asks replacement.
- Step 1 prompt and workflow changes were not reflected.
- Review edit mode (`/review`) caused missing boxes, cursor mismatch, or editor errors.
- PNG migration behaved inconsistently due to mixed `.jpg` and `.png` paths.

### Root Causes
- Several files were reverted to older `.jpg`-based paths and legacy UI logic.
- `review2.html` had reverse synchronization (`_qs -> pageQuestions`) causing stale/empty state.
- `editor.js` still referenced `preview-canvas` directly in some paths, breaking shared use.
- Project metadata scanner still counted `blank_*.jpg` only.

### Restored Changes
- `webapp/templates/index.html`
  - Removed Step 0 answer-key upload card and client upload handler.
  - Restored PNG fallback (`blank_p1.png`).
  - Restored prompt format to use template images + answer-key PDF attachment.
  - Added `answers` and `total_points` handling in validation and save path.
- `webapp/static/review2.html`
  - Restored PNG template/page matching.
  - Removed reverse sync on offset mode.
  - Edit mode now rebuilds `freshQuestions` from source `questions`.
  - Added defensive `_qs` check and stable save merge.
  - Re-added `editor.js` script include.
- `webapp/static/editor.js`
  - Restored dynamic canvas selection via `window._currentEditorCanvas`.
  - Added safe handling when optional host DOM nodes are absent.
  - Draw preview now uses current editor canvas, not hardcoded `preview-canvas`.
  - If background image is provided, canvas internal size follows source image size.
- `webapp/main.py`
  - Restored template/pipeline/restore flows to PNG template naming.
  - Updated regex and template path resolution to `.png`.
  - Template serving now returns proper image media type for file extension.
- `src/project_store.py`
  - Template metadata scan restored to `blank_*.png`.
- `src/pdf_handler.py`
  - PDF split output restored to `.png`.
- `src/main.py`
  - Legacy template filename default changed to `blank.png`.
- `tests/test_project_store.py`
  - Test fixture template names restored to `.png`.

### Verification
- `python -m unittest discover -s tests -q`
- Result: `OK` (all tests pass)

## 2026-04-30 채점 시 2페이지 이후 정답 매칭 불가 오류

### Symptoms
- `regions.json`에 정답을 등록하고 자동 채점을 돌렸으나, 2페이지 이후의 문항들이 정답 데이터를 찾지 못해 채점 불가(오답 처리)됨.
- `regions.json` 내 `answers` 배열의 문항들에 `page` 속성이 없어, 서버에서 기본값인 `page: 1`로 전부 강제 매핑됨.

### Root Causes
- 정답지(PDF) 원본에는 보통 해당 문제가 몇 페이지에 있는지에 대한 정보가 없기 때문에, Gemini가 `answers` 추출 시 `page`를 넣기 어려움. (억지로 요구하면 환각 발생 위험)
- 채점 매칭 로직(`submission_store.py`)에서 문항을 매칭할 때 `(page, number)` 튜플로만 엄격하게 검색하여, 실제 문항(page=2)과 저장된 정답(page=1) 간 불일치가 발생.

### Fix
- 프롬프트 쪽에 `page`를 억지로 요구하지 않음.
- `src/submission_store.py`의 `score_submission` 함수를 수정하여, `(page, number)`로 매칭을 시도해보고 실패할 경우 **문항 번호(`number`)만으로 다시 매칭(fallback)** 하도록 로직 개선. (대부분의 시험은 문항 번호가 고유함)
