# ClassManage Exam Grader V2 - Integrated Execution Plan

이 문서는 기존 `task.md` 진행내역과 `ocr-grading-pipeline-implementation-plan.md`를 통합한 실행용 상위 계획이다.

## 빠른 이해 (아주 쉽게)

- M1: Gemini JSON 입력 형식을 고정하는 단계
- M2: 학생별 페이지와 문항 crop 재료를 만드는 단계
- M3: OCR로 글자를 읽는 단계
- M4: 정답과 비교해 자동 채점하는 단계
- M5: 애매한 문항만 사람 검토하는 단계
- M6: CSV/XLSX로 결과를 내보내는 단계

## 1) Current Baseline (완료된 기반)

- [x] 프로젝트 기반 저장 구조 도입 (`settings.json`, `project.json`, 프로젝트별 디렉토리)
- [x] 템플릿/학생 업로드 + 정렬 파이프라인
- [x] Step 2 문항 박스 편집 안정화
- [x] `/review` 전체 오버레이 검수 안정화
- [x] Gemini JSON 저장 흐름 + YOLO export 유지

## 2) Guiding Principles

- [ ] Gemini 웹 사용 흐름은 유지하고, 하류(ingest -> OCR -> 채점 -> 검토 -> 내보내기)만 확장
- [ ] `/review`는 정렬/영역 검수 전용으로 유지, 채점 UI는 `/grading`으로 분리
- [ ] 모든 단계 결과를 프로젝트 아티팩트(JSON/이미지)로 저장해 재실행 가능하게 설계
- [ ] 기존 YOLO 산출물 경로는 병행 유지

## 3) Milestone Plan (권장 구현 순서)

### M1. Assessment Bundle Contract 고정
- [x] `src/assessment_bundle.py` 추가 (questions/answers/total_points 정규화)
- [x] `/api/regions` 저장 시 normalize 적용
- [x] `index.html` JSON 검증/상태표시를 결합 번들 기준으로 고정
- [x] 테스트: `tests/test_assessment_bundle.py`, `tests/test_project_store.py`
- [x] 완료 기준: 잘못된 스키마는 저장 거부, 정상 번들은 일관 포맷으로 저장

### M2. Submission Manifest + Crop 생성
- [x] `src/submission_store.py` 추가 (학생별 페이지 그룹/manifest)
- [x] `src/region_cropper.py` 추가 (정규화 bbox -> 실제 crop)
- [x] `/api/grading/prepare` 추가 (manifest/crops 생성)
- [x] 테스트: `tests/test_submission_store.py`, `tests/test_region_cropper.py`
- [x] 완료 기준: 학생별/문항별 crop가 `artifacts` 아래 재현 가능하게 생성

### M3. OCR + 정답 정규화
- [x] `src/ocr_engine.py` 추가 (PaddleOCR adapter)
- [x] `src/answer_normalizer.py` 추가 (객관식/단답형 normalize)
- [x] `/api/grading/ocr` 추가 + low-confidence 자동 플래그
- [x] 의존성: `paddleocr`
- [x] 테스트: `tests/test_answer_normalizer.py`
- [x] 완료 기준: OCR 결과에 confidence/needs_review가 채워짐

### M4. 자동 채점
- [x] `src/grader.py` 추가 (문항별 채점 규칙)
- [x] `submission_store`에 학생 단위 집계(total_score/total_points) 반영
- [x] `/api/grading/score` 추가
- [x] 테스트: `tests/test_grader.py`
- [x] 완료 기준: 학생별 총점/문항별 정오가 재현 가능하게 저장

### M5. 교사용 검토 UI
- [ ] `webapp/templates/grading_overview.html` 추가
- [ ] `webapp/templates/grading_student.html` 추가
- [ ] `GET/POST /grading/student/{student_id}`로 수동 정정 반영
- [ ] 테스트: `tests/test_submission_store.py` 확장
- [ ] 완료 기준: 저신뢰 문항 교정 후 재저장/재집계 가능

### M6. 결과 내보내기
- [ ] `src/report_exporter.py` 추가 (CSV/XLSX)
- [ ] `/api/export/results`, `/api/export/{name}` 추가
- [ ] 의존성: `openpyxl`
- [ ] 테스트: `tests/test_report_exporter.py`
- [ ] 완료 기준: 교사 전달용 파일 생성 + 다운로드 가능

## 4) Artifact Layout (Target)

- [ ] `<project>/artifacts/submissions/`
- [ ] `<project>/artifacts/crops/reference/`
- [ ] `<project>/artifacts/crops/students/<student_id>/`
- [ ] `<project>/artifacts/exports/`

## 5) Test Gate (각 마일스톤 공통)

- [ ] 신규 단위 테스트 우선 작성 -> 실패 확인 -> 구현 -> 통과 확인
- [ ] 기존 회귀: `python -m unittest discover -s tests -q` 유지 통과
- [ ] 핵심 라우트 수동 점검: `/dashboard`, `/review`, `/grading`

## 6) Documentation Gate

- [ ] 각 마일스톤 완료 시 `README.md` 워크플로우 업데이트
- [ ] `docs/troubleshooting.md`에 장애/복구 포인트 누적

## 7) Immediate Next Action (지금 시작점)

- [x] M1 Step 1: `tests/test_assessment_bundle.py` 추가 (실패 테스트 먼저)
- [x] M1 Step 2: `src/assessment_bundle.py` 구현
- [x] M1 Step 3: `/api/regions` 정규화 적용
- [x] M1 Step 4: M1 관련 테스트 통과 및 회귀 테스트
