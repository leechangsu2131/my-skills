# 🔍 EduSearch — 개인용 웹 스크래퍼 + 로컬 검색 시스템

여러 사이트를 돌아다니지 않고, **수집한 자료를 내 PC에서 한 번에 검색**하는 시스템입니다.

---

## 📁 파일 구조

```
edusearch/
├── scraper.py             ← 일반 웹 페이지 수집
├── indischool_scraper.py  ← 🍎 인디스쿨 전용 (자동 로그인+검색 지원)
├── nanuri_scraper.py      ← 📚 수업나누리 전용 (수동 로그인+자동 수집)
├── indexer.py             ← Whoosh 검색 인덱스 생성
├── search_app.py          ← 로컬 검색 웹앱 (부분어 검색 지원)
├── config.json            ← 일반 scraper용 설정 파일
├── .env                   ← 로그인 계정 정보 (생성 필요)
├── requirements.txt
├── data.db                ← SQLite DB (자동 생성)
└── index_dir/             ← 인덱스 폴더 (자동 생성)
```

---

## ⚙️ 1단계: 설치 및 기본 설정

```bash
pip install -r requirements.txt
```

**✅ 필수: `.env` 파일 설정 (인디스쿨/수업나누리용)**
1. `edusearch` 폴더 내에 `.env` 파일을 새로 생성하세요 (또는 `.env.example` 복사).
2. 다음과 같이 계정 정보를 입력 후 저장하세요 (절대 외부에 공유하지 마세요).
```env
INDISCHOOL_ID=내_아이디
INDISCHOOL_PW=내_비밀번호

SUBNURI_ID=입력하지_않아도_됨
SUBNURI_PW=입력하지_않아도_됨
```

**(선택) 일반 scraper.py 사용 시 ChromeDriver 설정:**
1. Chrome 버전에 맞는 ChromeDriver 설치 (`C:\chromedriver.exe`)
2. `config.json`의 `chromedriver_path` 수정

---

## 🚀 2단계: 자료 수집 (스크래핑)

원하는 사이트의 전용 스크래퍼를 골라서 실행합니다. 각 스크래퍼는 자동으로 `data.db`에 결과를 누적 저장합니다.

### 🍎 인디스쿨 수집 (자동 로그인)
터미널에 방치해도 알아서 로그인하고 수집합니다.
```bash
# 기본 사용법 (3페이지 수집)
python indischool_scraper.py --query "감각적 표현 시감상 3학년" --pages 3

# 브라우저 창을 띄워서 과정을 눈으로 확인하고 싶을 때
python indischool_scraper.py --query "시감상" --pages 2 --show
```

### 📚 수업나누리 수집 (수동 로그인)
보안 정책상 브라우저 창이 열리면 **직접 로그인**을 해야 합니다.
```bash
python nanuri_scraper.py --query "감각적 표현 시감상 3학년" --pages 3
```
1. 위 명령어 실행 시 Chrome 창이 열립니다.
2. 창에서 직접 수업나누리에 로그인합니다.
3. 터미널 창으로 돌아와 `Enter` 키를 누르면 수집이 시작됩니다.

### 🌐 일반 사이트 수집
`config.json`에 등록된 URL 주소들을 수집합니다.
```bash
python scraper.py
```

---

## 🔎 3단계: 검색 인덱스 생성 및 검색

### 1) 인덱스 생성 (수집 후 1회 실행)
DB에 모인 자료를 검색할 수 있게 변환합니다. 수집을 새로 했을 때마다 한 번씩 실행해주세요.
```bash
python indexer.py
```

### 2) 검색앱 실행 (계속 켜두기)
```bash
python search_app.py
```
→ 브라우저에서 **http://localhost:5000** 접속

**💡 검색 팁:** 
한국어 형태소를 고려한 *부분어 매칭*을 지원합니다. `감각`이라고만 검색해도 `감각적`, `감각표현` 등이 모두 유연하게 검색됩니다. 정확히 일치하는 구문을 찾으려면 `"감각적 표현"` 처럼 따옴표로 감싸세요.

---

## ⚠️ 주의사항 (필독)

## 🛠️ 확장 아이디어

| 아이디어 | 방법 |
|----------|------|
| **한국어 형태소 분석** | `pip install konlpy` 후 Okt 분석기 적용 |
| **URL 자동 수집** | Chrome 확장(SingleFile 등)으로 방문 페이지 자동 저장 |
| **정기 자동 수집** | Windows 작업 스케줄러로 `scraper.py` 매일 실행 |
| **태그/분류** | DB에 `tag` 컬럼 추가 후 수동 분류 |
| **전문 본문 저장** | `max_summary_chars` 늘리거나 PDF 다운로드 연동 |
