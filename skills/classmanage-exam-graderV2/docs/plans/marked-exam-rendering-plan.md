# Marked Exam Rendering Plan

## Goal

교사가 학생별 채점 상세 화면에서 답안을 확인하고 정답/오답을 확정한 뒤, 학생 시험지 원본에 가까운 정렬 이미지 위에 채점 표시를 남긴 PNG/PDF를 생성한다.

## Scope

- 문제번호 OCR 또는 문제번호 위치 추정은 하지 않는다.
- 현재 submission JSON에 저장된 학생 답안 영역(`box`)을 기준으로 표시한다.
- 확정된 항목만 마킹한다. `needs_review`가 남아 있는 문항은 표시하지 않는다.
- 정답은 답안 영역을 크게 감싸는 빨간색 `O`, 오답은 답안 영역을 가로지르는 빨간색 `/`로 표시한다.
- 채점 표시는 여러 번 겹쳐 그려 빨간색 연필 느낌을 낸다.
- 학생별 첫 페이지 상단 중앙에만 학생 ID와 점수(`total_score / total_points`)를 크게 표시한다.

## Artifact Layout

```text
artifacts/
  marked/
    students/
      stu001/
        stu001_p1_marked.png
        stu001_p2_marked.png
        stu001_marked.pdf
    marked_exams_all.zip
    marked_exams_combined.pdf
```

## Implementation

- `src/marked_exam_renderer.py`
  - `mark_submission_pages(paths, student_id)`로 한 학생의 페이지별 마킹본을 생성한다.
  - `mark_all_submissions(paths)`로 전체 학생의 마킹본을 생성한다.
  - `build_student_marked_pdf(paths, student_id)`로 학생별 PDF를 생성한다.
  - `build_all_marked_pdfs_zip(paths)`로 전체 학생 PDF ZIP을 생성한다.
  - `build_all_marked_pdf(paths)`로 모든 학생 페이지를 하나의 통합 PDF로 생성한다.
- `src/project_store.py`
  - `ProjectPaths.marked_dir`를 추가한다.
- `webapp/main.py`
  - `POST /api/grading/mark/{student_id}`
  - `POST /api/grading/mark-all`
  - `GET /api/grading/marked/{student_id}/pdf`
  - `GET /api/grading/marked/{student_id}/download`
  - `GET /api/grading/marked/all/pdf`
  - `GET /api/grading/marked/all/download`
  - `GET /api/grading/marked/status`
- `webapp/templates/index.html`
  - 대시보드 6번 단계로 `마킹본 만들기`를 추가한다.
  - 전체 생성, 학생별 미리보기/개별 다운로드, 전체 통합 PDF, 학생별 PDF ZIP을 제공한다.
- `webapp/templates/grading_student.html`
  - 학생별 `마킹본 생성` 버튼과 생성된 PNG 링크를 표시한다.
- `webapp/templates/grading_overview.html`
  - `전체 마킹본 생성` 버튼과 학생별 생성 페이지 수를 표시한다.

## Verification

- `tests/test_marked_exam_renderer.py`
  - 답안 영역 상단에 빨간 채점 표시가 그려지는지 검증한다.
  - 검토 필요 항목은 마킹하지 않는지 검증한다.
- `tests/test_grading_student_page.py`
  - 학생별 마킹 생성 API가 PNG 파일을 생성하는지 검증한다.
  - 학생별 PDF와 전체 ZIP 다운로드가 동작하는지 검증한다.
  - 전체 통합 PDF 다운로드가 동작하는지 검증한다.
  - 점수 표시가 첫 페이지에만 크게 렌더링되는지 검증한다.
  - 대시보드에 6번 마킹본 만들기 단계가 렌더링되는지 검증한다.
