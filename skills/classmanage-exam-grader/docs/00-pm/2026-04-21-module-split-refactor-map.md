# classmanage-exam-grader 모듈 분리 리팩터링 맵

## 목표

현재 프로젝트는 학생 답 추출, 정답지 추출, 채점, PDF 주석, 웹앱 orchestration이 루트 파일과 `webapp/services/pipeline.py`에 강하게 결합되어 있다.

이번 리팩터링의 목표는 다음 세 가지다.

1. 가장 중요한 엔진인 `학생 시험지 -> 빈 시험지 정합 -> 답 추출`을 독립 모듈로 분리한다.
2. 웹앱과 CLI가 엔진을 직접 엮지 않고, 안정된 계약(`contracts`) 위에서 동작하게 만든다.
3. 이후 기능 업그레이드를 `학생 답 추출`, `정답지 추출`, `채점`, `출력`, `웹앱` 단위로 따로 진행할 수 있게 만든다.

이번 1차 분리에서는 동작 변경보다 경계 정리를 우선한다.

## 최종 권장 구조

```text
classmanage-exam-grader/
  apps/
    web/
      main.py
      store.py
      templates/
      static/
      services/
    cli/
      grade_exam.py

  packages/
    contracts/
      __init__.py
      models.py
      schemas/
    student_extraction/
      __init__.py
      service.py
      paddle_backend.py
      pdf_text_layer.py
      question_layout.py
      student_pages.py
      template_alignment.py
    answer_key_extraction/
      __init__.py
      service.py
      pdf_parser.py
      json_loader.py
    grading/
      __init__.py
      service.py
      grader.py
      subjective.py
      analysis_merger.py
    annotation/
      __init__.py
      service.py
      pdf_annotator.py
    export/
      __init__.py
      html_reporter.py
      csv_exporter.py
      sheet_exporter.py
    shared/
      __init__.py
      config.py
      paths.py
      storage.py

  prompts/
  data/
  tests/
    contracts/
    student_extraction/
    answer_key_extraction/
    grading/
    annotation/
    export/
    apps/
      web/
      cli/
```

## 현재 파일 -> 새 위치 매핑

### 학생 답 추출 엔진

- `ocr_extractor.py`
  -> `packages/student_extraction/service.py`
- `ocr/paddle_backend.py`
  -> `packages/student_extraction/paddle_backend.py`
- `ocr/pdf_text_layer.py`
  -> `packages/student_extraction/pdf_text_layer.py`
- `ocr/question_layout.py`
  -> `packages/student_extraction/question_layout.py`
- `ocr/student_pages.py`
  -> `packages/student_extraction/student_pages.py`
- `ocr/template_alignment.py`
  -> `packages/student_extraction/template_alignment.py`

### 정답지 추출 엔진

- `answer_key_parser.py`
  -> `packages/answer_key_extraction/service.py`

1차 분리에서는 파일을 한 개로 유지해도 되지만, 2차에서 아래처럼 나누는 것이 좋다.

- `packages/answer_key_extraction/pdf_parser.py`
- `packages/answer_key_extraction/json_loader.py`

### 채점 엔진

- `grader.py`
  -> `packages/grading/grader.py`
- `analysis_merger.py`
  -> `packages/grading/analysis_merger.py`
- `llm_subjective_grader.py`
  -> `packages/grading/subjective.py`

### 출력 계층

- `pdf_annotator.py`
  -> `packages/annotation/pdf_annotator.py`
- `html_reporter.py`
  -> `packages/export/html_reporter.py`

향후 추가 예정:

- `packages/export/csv_exporter.py`
- `packages/export/sheet_exporter.py`

### 공통 계약 / 설정

- `webapp/schemas.py`
  -> `packages/contracts/models.py`
- `schemas/answer_key.schema.json`
  -> `packages/contracts/schemas/answer_key.schema.json`
- `schemas/student_answers.schema.json`
  -> `packages/contracts/schemas/student_answers.schema.json`
- `schemas/grading_result.schema.json`
  -> `packages/contracts/schemas/grading_result.schema.json`
- `schemas/analysis.schema.json`
  -> `packages/contracts/schemas/analysis.schema.json`
- `config.json`
  -> 그대로 유지하되, 읽는 코드는 `packages/shared/config.py`로 이동

### 앱 계층

- `webapp/main.py`
  -> `apps/web/main.py`
- `webapp/store.py`
  -> `apps/web/store.py`
- `webapp/templates/*`
  -> `apps/web/templates/*`
- `webapp/static/*`
  -> `apps/web/static/*`
- `webapp/services/pipeline.py`
  -> `apps/web/services/pipeline.py`
- `grade_exam.py`
  -> `apps/cli/grade_exam.py`

## 테스트 파일 -> 새 위치 매핑

### 학생 답 추출

- `tests/ocr/test_ocr_extractor.py`
  -> `tests/student_extraction/test_service.py`
- `tests/ocr/test_paddle_backend.py`
  -> `tests/student_extraction/test_paddle_backend.py`
- `tests/ocr/test_pdf_text_layer.py`
  -> `tests/student_extraction/test_pdf_text_layer.py`
- `tests/ocr/test_question_layout.py`
  -> `tests/student_extraction/test_question_layout.py`
- `tests/ocr/test_student_pages.py`
  -> `tests/student_extraction/test_student_pages.py`
- `tests/ocr/test_template_alignment.py`
  -> `tests/student_extraction/test_template_alignment.py`

### 정답지 추출

- `tests/test_answer_key_parser.py`
  -> `tests/answer_key_extraction/test_service.py`

### 채점

- `tests/test_grader.py`
  -> `tests/grading/test_grader.py`

### 앱 계층

- `tests/webapp/test_batch_flow.py`
  -> `tests/apps/web/test_batch_flow.py`
- `tests/webapp/test_batch_status.py`
  -> `tests/apps/web/test_batch_status.py`
- `tests/webapp/test_finalize_flow.py`
  -> `tests/apps/web/test_finalize_flow.py`
- `tests/webapp/test_homepage.py`
  -> `tests/apps/web/test_homepage.py`
- `tests/webapp/test_pipeline.py`
  -> `tests/apps/web/test_pipeline.py`
- `tests/webapp/test_review_updates.py`
  -> `tests/apps/web/test_review_updates.py`
- `tests/webapp/test_store_migrations.py`
  -> `tests/apps/web/test_store_migrations.py`
- `tests/webapp/test_upload_validation.py`
  -> `tests/apps/web/test_upload_validation.py`

## 가장 먼저 고정할 공통 계약

다음 모델들은 웹앱 전용 모델처럼 보이지만, 실제로는 전체 시스템의 계약 역할을 한다.

- `AnswerKey`
- `AnswerKeyQuestion`
- `StudentAnswer`
- `StudentAnswerEntry`
- `ReviewedSubmission`
- `ReviewItem`

현재 원본은 `webapp/schemas.py`이다. 이 파일을 1차에서 `packages/contracts/models.py`로 옮기고, 웹앱에서는 여기서 import 하게 바꾼다.

이후 `GradingResult`, `AnnotatedSubmissionResult`, `ExportResult` 같은 출력 계약을 점진적으로 추가한다.

## 안정된 서비스 인터페이스

아래 함수 시그니처를 기준 계약으로 삼는다.

```python
from pathlib import Path

from packages.contracts.models import AnswerKey
from packages.contracts.models import ReviewedSubmission
from packages.contracts.models import StudentAnswer


def parse_answer_key(source_path: Path) -> AnswerKey:
    ...


def extract_student_answers(
    student_pdf: Path,
    *,
    blank_exam_pdf: Path,
    metadata_dir: Path | None = None,
    student_page_offset: int | None = None,
    auto_pick_student_pages: bool | None = None,
) -> StudentAnswer:
    ...


def build_reviewed_submission(
    student_answers: StudentAnswer,
    answer_key: AnswerKey,
) -> ReviewedSubmission:
    ...


def annotate_reviewed_submission_pdf(
    source_pdf: Path,
    payload: ReviewedSubmission,
    output_path: Path,
) -> Path:
    ...
```

이 인터페이스가 안정되면 웹앱과 CLI는 내부 구현이 바뀌어도 거의 수정하지 않아도 된다.

## import 변경 순서

리팩터링 중 가장 흔한 문제는 파일 이동보다 import 순환이다.
따라서 아래 순서대로 진행하는 것이 안전하다.

### 1단계: contracts 추출

1. `packages/contracts/models.py`를 만든다.
2. `webapp/schemas.py`의 모델을 여기로 복사한다.
3. 웹앱 파일들이 `webapp.schemas` 대신 `packages.contracts.models`를 import 하게 바꾼다.
4. 기존 `webapp/schemas.py`는 임시로 재-export만 하게 둔다.

예시:

```python
# webapp/schemas.py
from packages.contracts.models import AnswerKey
from packages.contracts.models import AnswerKeyQuestion
from packages.contracts.models import ReviewedSubmission
from packages.contracts.models import ReviewItem
from packages.contracts.models import StudentAnswer
from packages.contracts.models import StudentAnswerEntry
```

### 2단계: student_extraction 추출

1. `packages/student_extraction/`를 만든다.
2. `ocr/` 하위 파일들과 `ocr_extractor.py` 내용을 옮긴다.
3. `ocr_extractor.py`는 임시 호환 레이어로 남긴다.
4. 새 코드는 `packages.student_extraction.service`만 import 하게 바꾼다.

예시:

```python
# ocr_extractor.py
from packages.student_extraction.service import extract_answers
from packages.student_extraction.service import extract_batch
from packages.student_extraction.service import load_config
from packages.student_extraction.service import load_prompt
from packages.student_extraction.service import run_gemini_ocr
```

### 3단계: answer_key_extraction 추출

1. `packages/answer_key_extraction/service.py`를 만든다.
2. `answer_key_parser.py` 로직을 옮긴다.
3. `answer_key_parser.py`는 재-export 호환 파일로 남긴다.
4. 웹앱과 CLI는 새 경로를 직접 import 하게 바꾼다.

### 4단계: grading 추출

1. `grader.py`, `analysis_merger.py`, `llm_subjective_grader.py`를 `packages/grading/`로 옮긴다.
2. `packages/grading/service.py`를 만들고 외부 노출 함수는 여기로 모은다.
3. 웹앱/CLI는 `packages.grading.service`만 사용하게 바꾼다.

### 5단계: annotation / export 추출

1. `pdf_annotator.py`를 `packages/annotation/`으로 옮긴다.
2. `html_reporter.py`를 `packages/export/`로 옮긴다.
3. 웹앱/CLI는 각 `service.py`만 바라보게 바꾼다.

### 6단계: apps 분리

1. `webapp/`를 `apps/web/`로 이동한다.
2. `grade_exam.py`를 `apps/cli/grade_exam.py`로 이동한다.
3. 진입용 얇은 루트 래퍼만 남긴다.

예시:

```python
# grade_exam.py
from apps.cli.grade_exam import main

if __name__ == "__main__":
    raise SystemExit(main())
```

## 1차 리팩터링 체크리스트

이번 체크리스트는 "행동 변경 없이 구조만 분리"를 목표로 한다.

### A. contracts 단계

- [ ] `packages/contracts/models.py` 생성
- [ ] `webapp/schemas.py`의 모델 이동
- [ ] `webapp/main.py` import 변경
- [ ] `webapp/store.py` import 변경
- [ ] `webapp/services/pipeline.py` import 변경
- [ ] 테스트가 새 contracts 경로를 사용하도록 수정

### B. student_extraction 단계

- [ ] `packages/student_extraction/` 생성
- [ ] `ocr/` 하위 모듈 이동
- [ ] `ocr_extractor.py`를 호환 래퍼로 축소
- [ ] `webapp/services/pipeline.py`가 새 service만 호출하게 수정
- [ ] `grade_exam.py`가 새 service만 호출하게 수정
- [ ] 관련 테스트 이동 및 import 수정

### C. answer_key_extraction 단계

- [ ] `packages/answer_key_extraction/service.py` 생성
- [ ] `answer_key_parser.py` 로직 이동
- [ ] JSON 로딩/텍스트 PDF 파싱/예비 Gemini 경로를 내부 함수로 정리
- [ ] `webapp/services/pipeline.py` import 변경
- [ ] `grade_exam.py` import 변경
- [ ] 테스트 이동 및 import 수정

### D. grading 단계

- [ ] `packages/grading/` 생성
- [ ] `grader.py` 이동
- [ ] `analysis_merger.py` 이동
- [ ] `llm_subjective_grader.py` 이동
- [ ] 외부 공개 함수 `service.py` 작성
- [ ] 웹앱과 CLI의 import를 service 기준으로 통일

### E. annotation / export 단계

- [ ] `packages/annotation/` 생성
- [ ] `packages/export/` 생성
- [ ] `pdf_annotator.py` 이동
- [ ] `html_reporter.py` 이동
- [ ] 이후 CSV/XLSX/시트 export용 파일 자리만 먼저 확보

### F. apps 단계

- [ ] `apps/web/` 생성
- [ ] `webapp/` 이동
- [ ] `apps/cli/grade_exam.py` 생성
- [ ] 루트 엔트리 파일들은 얇은 호환 래퍼로 유지
- [ ] 실행 스크립트와 README 경로 갱신

## 1차에서 하지 않을 것

다음은 1차 리팩터링 범위에서 제외한다.

- `repo` 분리
- 배포 방식 변경
- 데이터베이스 구조 재설계
- OCR 알고리즘 개선
- 채점 기준 변경
- 새로운 export 포맷 구현
- 웹 UX 개편

이번 단계는 오직 "경계 정리와 import 방향 정리"에 집중한다.

## 리팩터링 후 기대 효과

### 토큰 절감

- 학생 OCR을 고칠 때 `student_extraction`만 보면 된다.
- 정답지 추출 개선 시 `answer_key_extraction`만 읽으면 된다.
- 웹 수정 시 엔진 전체를 다시 읽지 않아도 된다.

### 기능 독립 업그레이드

- `student_extraction`만 따로 PaddleOCR vNext 실험 가능
- `answer_key_extraction`만 다른 parser로 교체 가능
- `export`만 따로 시트 연동 강화 가능

### 테스트 범위 축소

- 엔진 변경 시 해당 패키지 테스트만 우선 돌릴 수 있다.
- 앱 계층 테스트와 엔진 테스트를 분리할 수 있다.

## 실제 시작 순서 제안

바로 착수할 때는 아래 순서가 가장 안전하다.

1. `packages/contracts/models.py` 생성
2. `webapp/schemas.py`를 재-export 파일로 전환
3. `packages/student_extraction/` 생성 및 `ocr/` 이동
4. `ocr_extractor.py`를 래퍼로 축소
5. `packages/answer_key_extraction/` 생성 및 `answer_key_parser.py` 이동
6. `packages/grading/` 생성
7. `packages/annotation/`, `packages/export/` 생성
8. 마지막에 `apps/web/`, `apps/cli/`로 진입점 정리

## 판단 요약

현재 프로젝트는 지금 나누는 게 맞다.
특히 가장 중요한 `학생 시험지 답 추출`을 최상위 독립 모듈로 두는 판단이 옳다.
다만 분리 기준은 "웹 / CLI / OCR" 같은 표면 기능보다, `contracts / engine / adapter` 구조로 잡는 편이 장기적으로 훨씬 안정적이다.
