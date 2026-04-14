# 📚 교사용 지도서 진도표 → 노션 업로더

`teacher-guide-subunit-splitter`가 생성한 `groups.json` 파일을 읽어
Notion에 과목별 **진도표(Curriculum Tracker)** 데이터베이스를 자동으로 생성합니다.

## 사전 준비

### 1. Notion Integration 생성

1. https://www.notion.so/profile/integrations 에 접속
2. **"새 API 통합"** 클릭 → 이름 입력 (예: `진도표 업로더`)
3. 생성된 **시크릿 키** (`secret_xxxxx`)를 복사

### 2. 노션 페이지에 Integration 연결

1. 진도표를 만들 노션 페이지 열기
2. 우측 상단 `⋯` 메뉴 → **연결(Connections)** → 위에서 만든 Integration 추가

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

## 실행

```bash
python app.py
```

### 사용 방법

1. **groups.json 선택** — 분할기가 생성한 `output/<PDF명>/groups.json` 파일 선택
2. **Notion API 키** — 위에서 복사한 시크릿 키 입력 (자동 저장됨)
3. **노션 페이지 URL** — 진도표를 만들 페이지 URL 입력
4. **미리보기** — 파싱 결과 확인
5. **노션에 업로드** — 클릭하면 DB가 생성됩니다!

### 생성되는 노션 DB 컬럼

| 컬럼 | 타입 | 설명 |
|---|---|---|
| 차시/주제 | title | 각 차시 제목 |
| 순서 | number | 차시 순서 |
| 단원 | select | 상위 단원 이름 (색상 태그) |
| 지도서 쪽수 | rich_text | 페이지 범위 (p.1-8) |
| 수업 상태 | status | 시작 전 / 진행 중 / 완료 |
| 수업 일자 | date | 교사가 직접 기입 |
| 출처 PDF | rich_text | 원본 PDF 파일명 |

> **팁:** 노션에서 보드(칸반) 뷰나 캘린더 뷰를 추가하면 수업 진행을 더 직관적으로 관리할 수 있습니다!
