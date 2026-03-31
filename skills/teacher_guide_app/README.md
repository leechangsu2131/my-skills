# 📚 교사용 지도서 PDF 관리 시스템

초등교사를 위한 지도서 PDF 캐시 & 차시별 추출 + AI 수업 요약 도구

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 📁 PDF 캐시 | 한 번 등록하면 재업로드 없이 영구 보관 |
| 🔍 차시 자동 인식 | 북마크 → 패턴 → Claude AI 순으로 목차 분석 |
| ✂️ 차시 추출 | "국어 3 1 2" 입력 → 해당 차시 PDF 즉시 추출 |
| 🤖 수업 내용 요약 | 학습목표·수업흐름·핵심내용 자동 정리 (API 키 필요) |
| 🔎 키워드 검색 | 단원/차시 키워드로 빠른 탐색 |

---

## 🚀 설치

### Windows
```
install.bat 더블클릭
```

### Mac / Linux
```bash
chmod +x install.sh && ./install.sh
```

### 수동 설치
```bash
pip install pypdf pdfplumber anthropic rich
```

---

## ⚙️ API 키 설정 (AI 요약 기능 사용 시)

앱 폴더의 `.env` 파일을 편집기로 열어서:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxx
```
> API 키 없이도 PDF 추출 기능은 정상 동작합니다.

---

## 📖 사용법

### 1단계: PDF 등록 (교과서당 최초 1회)
```bash
python app.py add 국어지도서.pdf 국어 3
python app.py add 수학지도서.pdf 수학 4
```

### 2단계: 매일 사용

#### 대화형 모드 (가장 편함)
```bash
python app.py

> 국어 3학년 1단원 2차시
> 수학 4 3 1
> 목록
> 종료
```

#### 직접 실행
```bash
python app.py get 국어 3 1 2       # PDF 추출 (+ 선택적 AI 요약)
python app.py analyze 국어 3 1 2   # AI 요약만
python app.py show 국어 3          # 차시 목록
python app.py search 국어 3 낱말   # 키워드 검색
python app.py edit 국어 3          # 페이지 범위 수정
```

---

## 🤖 AI 수업 요약 출력 예시

```
## 🎯 학습 목표
- 받아올림이 있는 세 자리 수의 덧셈을 이해한다

## 📋 수업 흐름
도입 → 수 모형 탐구 → 세로셈 연습 → 형성 평가

## 💡 핵심 내용
- 일의 자리부터 계산
- 합이 10 이상이면 윗자리로 받아올림

## ✏️ 주요 활동
- 조작 활동: 수 모형으로 받아올림 원리 탐구
- 짝 활동: 문제 만들고 풀기

## ⚠️ 지도 유의사항
- 받아올림 표시를 빠뜨리지 않도록 강조
```

---

## 📁 폴더 구조

```
teacher_guide_app/
├── app.py          ← 실행 파일
├── .env            ← API 키 설정
├── cache/          ← 자동 생성 (삭제 금지)
└── output/         ← 추출 결과 저장
```

---

## ❓ 차시 인식이 잘못됐을 때

`cache/교과_학년grade/meta.json` 을 직접 편집하거나:
```bash
python app.py edit 국어 3
```

지원 교과: 국어(국), 수학(수), 과학(과), 사회(사), 영어(영), 도덕(도), 음악(음), 미술(미), 체육(체), 실과(실)
