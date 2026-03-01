---
name: pdf-book-translator
description: "PDF 원서를 챕터 단위로 잘라 Gemini Gems로 자동 번역하고 Discord로 전송합니다. 하루 한 챕터씩 영어 원문과 번역본을 Discord 채널에서 읽을 수 있습니다."
---

# PDF 원서 챕터 번역기 (Gemini Gems + Discord)

영문 PDF를 챕터별로 분리하고 **Playwright로 Gemini Gems 웹을 자동화**하여 번역 후 Discord 채널로 전송합니다.

## 📁 파일 구조

```
scripts/
├── .env                    ← 설정 (PDF 경로, Gems URL, Discord Webhook)
├── .env.example            ← 설정 예시
├── toc.json                ← 목차 (자동 생성됨)
├── output/                 ← 추출/번역 결과 저장
│   ├── chapter_01.txt
│   └── chapter_01_translated.txt
│
├── 01_setup_toc.py         ← [1단계] 목차 생성
├── extract_chapter.py      ← [2단계] PDF 텍스트 추출
├── 02_gems_translate.js    ← [3단계] Gems 자동 번역 (Playwright)
├── 03_send_discord.py      ← [4단계] Discord 전송
└── run_daily.py            ← 전체 파이프라인 원클릭 실행
```

---

## 🚀 최초 설정 (1회만)

### 1. 환경 설정
```powershell
cd scripts
copy .env.example .env
# .env 파일 편집: PDF_PATH, GEMS_URL, DISCORD_WEBHOOK_URL 입력
```

### 2. 패키지 설치
```powershell
pip install -r requirements.txt
npm run setup   # Playwright + Chromium 설치
```

### 3. Google 로그인 세션 저장
```powershell
node 02_gems_translate.js --auth
# 브라우저 열리면 Google 로그인 → Enter
```

### 4. 목차 만들기
```powershell
# 자동 감지 (챕터 헤딩 패턴으로)
python 01_setup_toc.py --auto

# 또는 직접 입력
python 01_setup_toc.py --manual
```

---

## 📅 매일 사용법

```powershell
# 챕터 1 번역 + Discord 전송 (원클릭)
python run_daily.py --chapter 1

# 다음날
python run_daily.py --chapter 2
```

### 단계별 실행
```powershell
python extract_chapter.py --chapter 1      # PDF 텍스트 추출
node 02_gems_translate.js --chapter 1      # Gems 번역
python 03_send_discord.py --chapter 1      # Discord 전송
```

---

## ⚠️ 주의사항

- Google 세션이 만료되면 `node 02_gems_translate.js --auth`로 재로그인
- Gems 입력 한도(약 8000자)를 초과하는 챕터는 자동으로 앞부분만 번역됨
- Discord Webhook URL은 비밀이므로 `.env`를 git에 올리지 마세요
