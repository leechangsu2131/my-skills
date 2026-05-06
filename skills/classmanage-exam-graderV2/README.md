# ClassManage Exam Grader V2

시험지 템플릿과 학생 답안 스캔본을 정렬한 뒤, 문항 박스를 검수하고 OCR/자동 채점/교사 검토를 거쳐 마킹된 시험지 PDF를 만드는 로컬 웹 도구입니다.

현재 구현의 중심은 `webapp/main.py` 기반 FastAPI 서버입니다.  
Gemini/Claude 같은 외부 AI에서 생성한 문항 좌표 JSON을 붙여 넣어 사용하는 구조이며, 이 저장소 안에 AI API 직접 호출 로직은 없습니다.

## 현재 범위

- 템플릿 PDF 업로드 및 페이지별 PNG 분할
- 학생 PDF 업로드 및 페이지별 이미지 분할
- OpenCV 기반 학생 이미지 정렬
- Gemini/Claude 웹 결과 기반 문항 박스와 정답 번들(`regions.json`) 저장
- 페이지별 문항 박스 수동 편집
- 전체 오버레이 검수, 수동 위치 보정, YOLO 라벨 저장
- 학생별 답안 영역 crop 생성
- PaddleOCR 기반 답안 인식
- 정답 번들 기반 자동 채점
- 교사용 저신뢰/오답 검토 화면
- 채점 확정 결과를 학생 시험지 위에 빨간 연필 스타일로 마킹
- 학생별 마킹 PDF, 전체 통합 PDF, 학생별 PDF ZIP 다운로드

현재 포함되지 않은 것:

- AI API 직접 연동
- 웹 LLM에 ZIP을 올린 뒤 압축 내부 이미지를 직접 읽게 하는 모듈
- CSV/XLSX 성적표 export

## 실행 방법

가장 간단한 방법은 루트의 `실행.bat`를 실행하는 것입니다.

이 배치 파일은 다음을 수행합니다.

1. Python 3.11 가상환경(`.venv`) 생성
2. `requirements.txt` 설치
3. `uvicorn webapp.main:app --port 8080 --reload` 실행
4. 브라우저에서 `http://127.0.0.1:8080` 열기

직접 실행하려면:

```powershell
.venv\Scripts\python.exe -m uvicorn webapp.main:app --port 8080 --reload
```

## 디렉터리 구조

```text
classmanage-exam-graderV2/
├── 실행.bat
├── requirements.txt
├── README.md
├── data/
│   ├── answers/             # 업로드된 답안지 PDF 보관
│   ├── artifacts/
│   │   ├── crops/           # reference/student 답안 crop
│   │   ├── marked/          # 마킹 PNG/PDF/ZIP
│   │   └── submissions/     # 학생별 채점 manifest JSON
│   ├── json/                # regions.json
│   ├── students/
│   │   ├── aligned/         # 정렬 완료 학생 이미지
│   │   ├── raw/             # 업로드된 학생 PDF 원본
│   │   └── raw_pages/       # PDF 분할 후 학생 페이지 이미지
│   ├── template/            # blank_p1.png, blank_p2.png ...
│   └── yolo_labels/         # 최종 YOLO txt 라벨
├── logs/
├── src/
│   ├── aligner.py
│   ├── answer_normalizer.py
│   ├── assessment_bundle.py
│   ├── event_logger.py
│   ├── grader.py
│   ├── marked_exam_renderer.py
│   ├── ocr_engine.py
│   ├── pdf_handler.py
│   ├── project_store.py
│   ├── region_cropper.py
│   ├── submission_store.py
│   ├── data_manager.py
│   └── main.py              # 예전 CLI 중심 진입점
└── webapp/
    ├── main.py              # 현재 실제 서버 진입점
    ├── static/
    │   ├── editor.js
    │   └── review2.html
    └── templates/
        ├── index.html
        ├── grading_overview.html
        ├── grading_student.html
        ├── review.html
        └── submission_review.html
```

## 현재 워크플로

### 1. 템플릿 업로드

- `POST /api/upload/template`
- API는 이미지(`.jpg/.jpeg/.png`)와 PDF를 모두 받을 수 있습니다.
- 현재 UI는 템플릿 업로드를 PDF 기준으로 안내합니다.
- PDF 업로드 시 각 페이지를 300 DPI 수준 PNG로 저장하며 이름은 `blank_p1.png`, `blank_p2.png` 형식입니다.

### 2. 학생 파일 업로드

- `POST /api/upload/students`
- PDF는 현재 프로젝트의 `students/raw/`에 저장됩니다.
- 이미지 업로드도 API 차원에서는 허용되지만, 현재 메인 배치 파이프라인은 PDF 기준으로 동작합니다.

### 3. 배치 파이프라인 실행

- `POST /api/run_pipeline`
- 요청 본문에 학생 1명당 페이지 수인 `cycle` 값을 보냅니다.
- 내부적으로:
  - `students/raw_pages/`를 비웁니다.
  - `students/aligned/`를 비웁니다.
  - `src/pdf_handler.py`가 학생 PDF를 300 DPI PNG로 분할합니다.
  - 파일명은 `원본이름_stu001_p1.png` 같은 형식으로 생성됩니다.
  - 각 페이지는 대응하는 `blank_pN.png`를 찾아 정렬합니다.

### 4. 이미지 정렬 방식

현재 `src/aligner.py`는 다음 순서로 동작합니다.

1. 축소본(25%)에서 ORB 특징점 매칭
2. Lowe ratio test로 나쁜 매칭 제거
3. RANSAC homography로 원본 해상도 정렬
4. ORB 실패 시 외곽선(Contour) 기반 페이지 warp 시도
5. 그것도 실패하면 마지막으로 템플릿 크기만 맞춘 resize 저장

즉, 현재 정렬은 "ORB 우선, contour 보조, resize 최후 fallback" 구조입니다.

### 5. 문항 JSON 붙여넣기 및 저장

메인 대시보드(`/`)에서:

- 템플릿 기반 프롬프트를 복사
- Gemini/Claude 결과 JSON을 붙여넣기
- 검증 후 `regions.json`으로 저장

저장 위치:

- `data/json/regions.json`

형식은 현재 `{"questions": [...], "answers": [...], "total_points": 100}` 구조를 기준으로 사용합니다.

### 6. 페이지별 박스 편집

메인 대시보드의 편집 캔버스는 `webapp/static/editor.js`를 사용합니다.

현재 가능한 작업:

- 박스 선택
- 이동
- 크기 조절
- 신규 박스 그리기
- 삭제
- Undo / Redo
- 페이지별 `regions.json` 재저장

캔버스는 템플릿 원본 해상도를 유지한 채 동작하며, 화면 표시 크기와 내부 해상도가 달라도 좌표를 스케일 보정해서 처리합니다.

### 7. 전체 오버레이 검수

`/review`는 `webapp/static/review2.html`을 사용합니다.

이 화면에서는:

- 페이지별 학생 이미지 목록 확인
- 템플릿/학생 투명도 조절
- 여러 학생 동시 오버레이
- 특정 학생만 단독 보기
- 페이지 상태를 `ok` 또는 `warn`으로 표시

#### 검수 화면의 두 가지 모드

`offset` 모드:

- 학생 이미지를 마우스로 드래그해 위치를 미세 보정
- `POST /api/student/offset`로 `warpAffine` 저장
- `복구` 버튼으로 원본 raw 이미지에서 OpenCV 정렬을 다시 수행

`edit` 모드:

- 같은 화면 안에서 바로 문항 박스를 수정
- `editor.js`를 `cb` 캔버스에 붙여 사용
- 저장 시 현재 페이지 문항만 `regions.json`에 병합

### 8. YOLO 라벨 저장

검수가 끝나면 `POST /api/yolo_save`를 통해 학생 이미지별 YOLO txt를 생성합니다.

출력 위치:

- `data/yolo_labels/<학생파일명>.txt`

현재 클래스 id는 모두 `0`으로 저장됩니다.

### 9. OCR 채점 및 교사 검토

대시보드 5번 단계에서 순서대로 실행합니다.

1. `채점 준비`: 정렬된 학생 페이지와 문항 박스를 바탕으로 학생별 manifest와 답안 crop을 생성합니다.
2. `OCR 실행`: PaddleOCR로 crop 이미지를 읽고 신뢰도가 낮은 문항을 검토 대상으로 표시합니다.
3. `자동 채점`: `regions.json`의 `answers`와 OCR 결과를 비교해 문항별 정오와 총점을 저장합니다.
4. `결과 보기`: `/grading`에서 학생별 점수와 검토 필요 문항을 확인합니다.
5. 학생 상세 화면(`/grading/student/{student_id}`)에서 OCR 답안, 정답, 점수, 정오를 교사가 수정하고 저장할 수 있습니다.

### 10. 마킹본 만들기

대시보드 6번 단계 또는 `/grading` 화면에서 실행합니다.

- 마킹 기준은 문제번호 위치가 아니라 학생 답안 영역(`box`)입니다.
- 정답은 답안 영역을 크게 감싸는 빨간색 원으로 표시합니다.
- 오답은 답안 영역을 크게 가로지르는 빨간색 `/`로 표시합니다.
- 빨간 연필 느낌을 내기 위해 선을 여러 번 겹쳐 그립니다.
- 점수는 학생별 첫 페이지 맨 위 중앙에만 크게 표시합니다.
- 산출물:
  - 학생별 마킹 PNG: `artifacts/marked/students/<student_id>/*_marked.png`
  - 학생별 PDF: `artifacts/marked/students/<student_id>/<student_id>_marked.pdf`
  - 전체 통합 PDF: `artifacts/marked/marked_exams_combined.pdf`
  - 학생별 PDF ZIP: `artifacts/marked/marked_exams_all.zip`

## 주요 API

- `GET /` : 메인 대시보드
- `GET /review` : 전체 오버레이 검수 화면
- `GET /grading` : 채점 결과 목록
- `GET /grading/student/{student_id}` : 학생별 채점 상세/교사 검토
- `POST /grading/student/{student_id}` : 학생별 수동 채점 저장
- `GET /grading/gemini-review` : 저신뢰 문항 Gemini 재판독 보조 화면
- `POST /api/upload/template`
- `POST /api/upload/answers`
- `POST /api/upload/students`
- `POST /api/run_pipeline`
- `GET /api/regions`
- `POST /api/regions`
- `GET /api/templates`
- `GET /api/template/{name}`
- `GET /api/students`
- `GET /api/student/{name}`
- `DELETE /api/student/{name}`
- `POST /api/student/offset`
- `POST /api/student/restore`
- `POST /api/yolo_save`
- `POST /api/grading/prepare`
- `POST /api/grading/ocr`
- `GET /api/grading/ocr/status`
- `POST /api/grading/score`
- `POST /api/grading/mark/{student_id}`
- `POST /api/grading/mark-all`
- `GET /api/grading/marked/status`
- `GET /api/grading/marked/{student_id}/pdf`
- `GET /api/grading/marked/{student_id}/download`
- `GET /api/grading/marked/all/pdf`
- `GET /api/grading/marked/all/download`
- `POST /api/log`

보조 상태 확인용:

- `GET /api/files/status`
- `GET /api/thumbnail`
- `GET /api/student/{name}/raw`

## 현재 구현 기준 주의사항

- 학생 이미지 업로드 API는 열려 있지만, 현재 메인 파이프라인은 `raw_pdfs`를 기준으로 `raw_images`를 다시 생성합니다. 안정적인 사용 흐름은 PDF 업로드 기준입니다.
- 템플릿의 특정 페이지(`blank_pN.png`)가 없으면 현재 서버는 `blank_p1.png`로 fallback 합니다.
- 웹 LLM이 ZIP 압축 해제 후 내부 이미지를 직접 읽는 흐름은 안정성이 낮아 구현을 보류했습니다.
- 마킹본은 원본 PDF에 직접 주석을 쓰는 방식이 아니라, 정렬된 학생 페이지 이미지 위에 마킹을 그린 뒤 PDF로 묶는 방식입니다.
- `src/main.py`는 예전 CLI 흐름의 흔적이 남아 있고, 실제 운영 진입점은 `webapp/main.py`입니다.
- `data/json_labels/` 같은 일부 폴더와 `webapp/templates/` 안의 일부 파일은 현재 주 흐름에서 직접 사용되지 않거나 예전 실험 흔적일 수 있습니다.

## 현재 의존성

`requirements.txt` 기준:

- `opencv-python`
- `numpy`
- `Pillow`
- `PyMuPDF`
- `fastapi`
- `uvicorn`
- `jinja2`
- `python-multipart`
- `pytest`
- `paddleocr`
