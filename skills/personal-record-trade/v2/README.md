# 📈 투자 포트폴리오 자동화 시스템

## 전체 흐름

```
증권사 앱 체결 화면
        │  스크린샷
        ▼
Claude Desktop (Vision 파싱)
  "이 체결화면 매매일지에 추가해줘"
        │  JSON 추출 + 스크립트 실행
        ▼
2_add_trade.py (gspread)
        │  Sheets API
        ▼
Google Sheets 📊
  ├── 📊 포트폴리오
  ├── 🎯 비중조절신호
  ├── 🏭 섹터현황
  ├── 📒 매매일지  ← 자동 추가
  ├── 📅 특정일잔고
  ├── 👋 청산종목
  └── 🧠 전략·전망

        │  깊은 분석·리서치
        ▼
Obsidian Vault (PARA)
  └── Resources/투자/종목복기/
```

## 시작하기

```bash
# 1. 패키지 설치
pip install gspread google-auth

# 2. service_account.json 발급 후 이 폴더에 저장

# 3. Google Sheets 초기 생성 (최초 1회)
python 1_setup_gsheet.py

# 4. 이후 매매 추가
python 2_add_trade.py --json '{"date":"2025-05-02","ticker":"NVDA",...}'

# 5. 현재가 일괄 업데이트
python 2_add_trade.py --prices '{"NVDA":294130,"GOOG":562910}'
```

## 파일 구성
| 파일 | 역할 |
|------|------|
| `1_setup_gsheet.py` | Google Sheets 초기 생성 + 기존 데이터 이전 |
| `2_add_trade.py` | 매매 추가 / 현재가 업데이트 / 스냅샷 추가 |
| `3_claude_desktop_prompts.md` | Claude Desktop에서 쓸 프롬프트 모음 |
| `service_account.json` | ⚠️ Google 서비스 계정 키 (절대 공유 금지) |
| `sheet_id.txt` | 스프레드시트 ID (자동 생성) |
