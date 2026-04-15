---
name: exam-grader
description: "Gemini CLI로 학생 시험지 PDF를 OCR하여 자동 채점하고, 결과를 원본 PDF에 기입하는 자동화 시스템"
---

# 시험 채점 자동화 (Gemini CLI + PDF)

학생 시험지 PDF를 Gemini CLI의 멀티모달 분석으로 OCR → 채점 → PDF 결과 기입까지 자동화합니다.

## 📁 파일 구조

```
exam-grader/
├── grade_exam.py               ← 메인 CLI (전체 파이프라인)
├── ocr_extractor.py            ← Gemini CLI OCR 모듈
├── answer_key_parser.py        ← 답안지 파서
├── grader.py                   ← 채점 엔진
├── analysis_merger.py          ← 외부 LLM 분석 병합
├── pdf_annotator.py            ← PDF 결과 기입
├── config.json                 ← 설정
├── prompts/                    ← Gemini CLI 프롬프트
│   ├── ocr_student_exam.txt
│   └── ocr_answer_key.txt
├── schemas/                    ← JSON 스키마
└── data/                       ← 작업 데이터 (git 제외)
    ├── input/students/         ← 학생 시험지 PDF
    ├── input/answer_key/       ← 답안지 PDF
    ├── extracted/              ← OCR 결과 JSON
    ├── graded/                 ← 채점 결과 JSON
    └── output/                 ← 채점 완료 PDF
```

---

## 🚀 빠른 시작

### 1. 사전 조건

```powershell
# Gemini CLI (이미 설치됨)
gemini --version

# PyMuPDF (이미 설치됨)
pip install PyMuPDF
```

### 2. 시험지 준비

- 학생 시험지 PDF를 `data/input/students/`에 넣기
- 답안지 PDF를 `data/input/answer_key/`에 넣기

### 3. 원클릭 실행

```powershell
cd skills/exam-grader
python grade_exam.py all --students data/input/students/ --answer-key data/input/answer_key/answer.pdf
```

### 4. 결과 확인

- `data/output/` 에서 `{학생명}_채점완료.pdf` 확인
- `data/output/_grading_summary.json` 에서 전체 요약 확인

---

## 📋 단계별 실행

```powershell
# 1단계: 학생 시험지 OCR
python grade_exam.py ocr --students data/input/students/

# 2단계: 답안지 파싱 (PDF 또는 대화형)
python grade_exam.py parse-key --answer-key data/input/answer_key/answer.pdf
python grade_exam.py parse-key --interactive  # 수동 입력

# 3단계: 채점
python grade_exam.py grade

# 4단계: 분석 병합 (선택)
python grade_exam.py merge --analysis analysis.json

# 5단계: PDF 기입
python grade_exam.py annotate --students data/input/students/
```

---

## 🔗 외부 LLM 분석 연동

다른 LLM이 오답 분석 파일을 제공하면 채점 결과에 병합할 수 있습니다.

### 분석 파일 형식 (`analysis.json`)

```json
{
  "analyst": "Claude 4",
  "analyses": [
    {
      "q_num": 5,
      "analysis": "곱셈의 교환법칙을 적용하지 못함",
      "category": "개념오류",
      "suggestion": "곱셈의 성질 복습 필요"
    }
  ]
}
```

스키마: `schemas/analysis.schema.json`

---

## ⚙️ 설정 (`config.json`)

| 항목 | 설명 | 기본값 |
|------|------|--------|
| `gemini_model` | 사용할 Gemini 모델 | `gemini-2.5-flash` |
| `annotation.correct_mark` | 정답 표시 | ⭕ |
| `annotation.wrong_mark` | 오답 표시 | ❌ |
| `annotation.add_summary_page` | 성적표 페이지 추가 | `true` |
| `grading.case_sensitive` | 대소문자 구분 | `false` |
| `grading.normalize_numbers` | 숫자 정규화 | `true` |
| `grading.descriptive_auto_grade` | 서술형 자동채점 | `false` |

---

## 🔄 워크플로우 연동

### hitalk-score 연동 (향후)

채점 완료 후 구글시트에 점수를 기입하고 하이톡으로 학부모에게 전송:

```
grade_exam.py all → 구글시트 기입 → hitalk_sender.py
```

---

## ⚠️ 주의사항

- 서술형 문제는 자동 채점하지 않습니다 (`descriptive_auto_grade: false`)
- OCR 결과는 반드시 확인 후 사용하세요 (특히 손글씨)
- Gemini CLI 일일 한도에 주의하세요
- 학생 개인정보가 포함된 데이터는 git에 올리지 마세요
