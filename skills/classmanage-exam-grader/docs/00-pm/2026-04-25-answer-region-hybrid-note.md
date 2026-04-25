# 2026-04-25 Answer Region Hybrid Note

## Why This Note Exists

The earlier refactor notes split the project mainly around contracts, engines, and adapters. Since then, objective answer-region localization has become important enough to deserve its own explicit boundary inside `packages/student_extraction/`.

## New Practical Boundary

These files now work together as one answer-region subsystem:

- `packages/student_extraction/answer_region_detector.py`
- `packages/student_extraction/answer_regions.py`
- `packages/student_extraction/service.py`

## Responsibility Split

- OpenCV:
  - page cleanup
  - alignment support
  - contour and line helpers
  - heuristic fallback crops
- YOLOv8:
  - locating objective answer blanks
  - locating answer boxes or check regions
  - eventually replacing fragile prompt-end blank heuristics on harder templates

## Current Shipping State

- The codebase now supports a `YOLO first -> OpenCV fallback` structure for multiple-choice answer regions.
- Default config still uses `opencv` mode.
- A trained YOLO checkpoint is still needed before the detector path becomes active in production.

## Refactor Guidance

Future refactors should not bury answer-region logic entirely inside OCR helpers. Treat it as a dedicated submodule of student extraction, because it sits between:

1. page alignment
2. crop generation
3. OCR execution
4. teacher review quality
