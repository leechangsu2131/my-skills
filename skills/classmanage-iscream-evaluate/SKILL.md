---
name: i-scream 과목별 평가 자동 기록
description: Supabase에 축적된 학생 관찰 기록을 바탕으로 i-scream 과목별 평가 페이지에 자동으로 평가 내용을 기록합니다. 수동 로그인한 크롬에 CDP로 연결하여 Playwright로 자동화합니다.
category: education
risk: moderate
source: community
date_added: "2026-06-16"
tags: ["education", "korean", "evaluation", "classroom-management", "playwright", "automation"]
---

# i-scream 과목별 평가 자동 기록 (classmanage-iscream-evaluate)

## Overview

학기 동안 Supabase `class-manage` 테이블에 축적된 학생별 관찰 기록을 바탕으로,
**i-scream 과목별 평가** 페이지(`SubjectEvaluation.do`)에 자동으로 평가 내용을 기록하는 스킬입니다.

기존 `classmanage-record-viewer`의 데이터를 활용하며,
`classmanage-student-eval-generator`로 생성된 평가 문장도 입력으로 받을 수 있습니다.

## When to Use This Skill

- 학기말에 i-scream 과목별 평가를 기록해야 할 때
- "i-scream에 평가 기록해줘" 또는 "아이스크림에 과목별 평가 입력해줘"라고 요청할 때
- 다수 학생의 과목별 평가를 반복 입력해야 할 때

## 필요 조건

- Python 3.8 이상
- `playwright`, `flask`, `supabase`, `python-dotenv`
- i-scream 교사 계정 (수동 로그인)
- Supabase 연결 정보 (`classmanage-record-viewer`와 동일)

## 사용 방법

### 1. 초기 설정

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 환경 변수 세팅

`.env.example`을 `.env`로 복사 후 실제 값 입력:

```bash
cp .env.example .env
```

| 변수 | 설명 |
|------|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_ANON_KEY` | Supabase anon 키 |
| `ISCREAM_CDP_PORT` | CDP 원격 디버깅 포트 (기본 9222) |
| `FLASK_PORT` | 웹 UI 포트 (기본 5028) |

### 3. 시스템 실행 (올인원 런처)

```
launch_chrome_iscream.bat
```

이 배치 스크립트를 더블클릭하여 실행하면 다음 작업이 자동으로 수행됩니다:
1. 기존에 잠겨 있던 백그라운드 디버깅 크롬 프로세스를 정리합니다.
2. i-scream 사이트(`https://www.i-scream.co.kr`)가 포함된 디버깅용 새 크롬 창을 띄웁니다.
3. 잠시 후 대시보드 웹 UI(`http://localhost:5028`)를 브라우저에 자동으로 엽니다.
4. 현재 명령창에서 Flask 웹 서버가 바로 실행됩니다. (종료하려면 명령창에서 `Ctrl+C` 입력)

*크롬 창이 열리면 수동으로 i-scream 로그인 후, 과목별 평가 페이지(`SubjectEvaluation.do`)로 이동해 두세요. (이동 중 비밀번호 'dlckdtn3'을 요구하는 확인 페이지가 감지되면 시스템이 자동으로 입력하고 진입합니다.)*

### 4. DOM 셀렉터 검증 및 진단

i-scream 교과평가 페이지로 이동한 상태에서 아래 검증 스크립트를 실행하여 셀렉터 연결 상태를 자가 진단합니다:

```bash
python verify_selectors.py
```

- 현재 열려 있는 크롬 창과 디버그 포트 연결 상태를 점검합니다.
- 평가 입력에 필요한 과목 선택, 학생 목록, 텍스트창, 저장 버튼 등의 셀렉터가 실제 페이지 내에 존재하는지 검사합니다.
- 결과물로 `iscream_verification_screenshot.png`와 `iscream_verification_dom.html`을 생성해 주어 셀렉터 불일치 시 직접 점검 및 수정할 수 있게 돕습니다.
- 만약 셀렉터 구조 파악이 필요하다면 `explore_dom.py`를 실행하여 정밀 DOM 덤프를 수행합니다.

### 5. 웹 UI 사용 워크플로우

1. 올인원 런처로 연 웹 UI 대시보드([http://localhost:5028](http://localhost:5028))에 접속합니다.
2. Supabase에서 학생 기록이 자동으로 로드되어 좌측 목록에 보입니다.
3. 입력 대상 학생들을 체크하고 **[평가문 생성]** 버튼을 클릭합니다.
4. 생성된 초안의 텍스트와 누적 관찰 내역을 최종 확인 및 직접 수정합니다.
5. 우측 상단의 **Dry Run (테스트)** 토글을 켠 상태로 **[자동 입력 시작]**을 눌러 시뮬레이션 로그가 올바르게 작동하는지 검증합니다.
6. 이상이 없으면 Dry Run을 끄고 실제 **자동 입력**을 실행합니다.

### 6. 평가기준 자동 클릭 기능 (성취기준 연동)

이 스킬은 단순히 텍스트만 입력하는 것에 그치지 않고, 학교 현장의 평가 기록 기준 충족을 위해 i-scream 페이지 내의 **평가기준(성취기준) 자동 연동**을 함께 자동 수행합니다:
- **학생 체크박스 단일 선택**: 현재 입력할 학생의 체크박스(`input#ai-student{idx}`)만 명확히 체크하고, 다른 모든 학생의 체크박스는 일괄 해제 처리하여 평가가 혼선되지 않도록 방지합니다.
- **성취평가기준 2개 자동 클릭**: 우측 평가기준 테이블을 분석하여, 아직 해당 학생에게 선택되지 않은(부모 `tr`에 `highlight` 클래스가 없는) 평가기준 버튼(`button.al`)을 최대 2개 자동 클릭(토글 활성화)합니다.
- **최종 평가문 기입**: 2개의 평가기준 선택으로 텍스트 영역이 활성화되면, Supabase 혹은 LLM 요약으로 가공된 커스텀 평가문(`eval_text`)을 textarea에 덮어써 최종 기록합니다.

### 7. CLI 실행
```bash
# 시뮬레이션 (실제 저장 안 함)
python iscream_evaluate.py --dry-run

# 미리보기 후 확인 대기
python iscream_evaluate.py --preview

# 특정 학생만
python iscream_evaluate.py --student 김민준

# 특정 과목만
python iscream_evaluate.py --subject 수학

# 특정 학생 + 특정 과목
python iscream_evaluate.py --student 김민준 --subject 수학
```

## 아키텍처

```
┌──────────────────────────────────────┐
│  사용자 브라우저 (localhost:5028)      │
│  ┌──────────────────────────────┐    │
│  │  웹 UI (index.html)           │    │
│  │  - 학생/과목 선택              │    │
│  │  - 평가 미리보기/편집          │    │
│  │  - 실시간 로그 (SSE)           │    │
│  └────────────┬─────────────────┘    │
└───────────────┼──────────────────────┘
                │ HTTP API
┌───────────────┼──────────────────────┐
│  Flask 서버 (app.py, 포트 5028)       │
│  ┌────────────┴─────────────────┐    │
│  │  supabase_fetch.py (데이터)   │    │
│  │  eval_builder.py (가공)       │    │
│  │  iscream_evaluate.py (자동화) │    │
│  └────────────┬─────────────────┘    │
└───────────────┼──────────────────────┘
                │ CDP (포트 9222)
┌───────────────┼──────────────────────┐
│  사용자 크롬 (수동 로그인 완료)        │
│  i-scream.co.kr/SubjectEvaluation.do │
└──────────────────────────────────────┘
```

## 데이터 흐름

```
Supabase class-manage 테이블
    ↓  supabase_fetch.py
학생별 기록 (학생이름, 과목, 날짜, 내용, 긍정도...)
    ↓  eval_builder.py
과목별 평가 데이터 [{student, subject, eval_text}]
    ↓  iscream_evaluate.py (Playwright CDP)
i-scream 과목별 평가 페이지에 자동 입력
```

## 주의사항

- i-scream은 교육용 사이트이므로 과도한 자동 접근은 삼가주세요
- `--dry-run`으로 먼저 테스트를 권장합니다
- DOM 셀렉터는 사이트 업데이트 시 변경될 수 있으므로 `explore_dom.py`로 재확인하세요
- 실제 저장 전 반드시 미리보기로 평가 내용을 확인하세요
- CDP 연결을 위해 `launch_chrome_iscream.bat`으로 실행한 크롬만 사용합니다

## 개발 및 디버깅 역사 (ing.md)

- 이 스킬의 개발/디버깅 과정과 자가 진단 결과는 [ing.md](file:///C:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/classmanage-iscream-evaluate/ing.md) 파일에 상세히 기록되어 있습니다. 오류 수정이 필요한 경우 이 문서를 확인하세요.

## Related Skills

- `@classmanage-record-viewer` — 학생 기록 조회 뷰어 (데이터 원천)
- `@classmanage-student-eval-generator` — LLM 기반 평가 문장 생성
- `@classmanage-student-classifier` — 수업 기록 자동 분류
- `@admin-edufine` — 에듀파인 기안 자동화 (CDP 패턴 원본)
