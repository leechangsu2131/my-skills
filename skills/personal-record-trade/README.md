# 📈 투자 포트폴리오 자동화 시스템 — 최종 병합본

## 두 버전의 장점을 통합한 이유

| 항목 | portfolio_gsheet_v2 (다른 LLM) | 투자관리시스템 (Claude) | 병합 결과 |
|------|------|------|------|
| Google Sheets 연동 | ✅ gspread 완성 | ❌ 미지원 | ✅ 유지 |
| 실제 보유 28종목 데이터 | ✅ 완비 | 샘플만 | ✅ 적용 |
| GOOGLEFINANCE 자동가격 | ✅ 완성 | ❌ | ✅ 유지 |
| 오프라인 분석 (KRX 포함) | ❌ | ✅ yfinance+seaborn | ✅ 추가 |
| Apps Script 알림 | 4가지 기능 | 3가지 기능 | ✅ 6가지로 확장 |
| 섹터현황 자동 집계 | ❌ | 수식 기반 | ✅ Apps Script로 추가 |
| 주간 복기 알림 | ❌ | 템플릿만 | ✅ 이메일 자동화 |
| Claude Desktop 프롬프트 | ✅ | ❌ | ✅ 유지 |

---

## 파일 구성

| 파일 | 출처 | 역할 |
|------|------|------|
| `gsheet_auth.py` | **신규** | 공통 인증 헬퍼 (.env → service_account.json → OAuth 폴백) |
| `.env.example` | **신규** | 인증 설정 템플릿 (복사해서 .env로 사용) |
| `1_setup_gsheet.py` | v2 | Google Sheets 초기 생성 + 28종목 데이터 이전 |
| `2_add_trade.py` | v2 | 매매 추가 / 현재가 업데이트 / 스냅샷 |
| `3_claude_desktop_prompts.md` | v2 | Claude Desktop 프롬프트 모음 |
| `4_apps_script.js` | **병합** | 6가지 자동화 (알림+스냅샷+복원+섹터+주간복기) |
| `5_add_googlefinance.py` | v2 | GOOGLEFINANCE 실시간현황+상관관계 시트 추가 |
| `6_offline_analysis.py` | **Claude 신규** | yfinance 기반 28종목 오프라인 분석 (KRX 포함) |
| `README.md` | **병합** | 이 파일 |

---

## 빠른 시작

### 1단계: 패키지 설치
```bash
pip install gspread google-auth python-dotenv yfinance pandas seaborn matplotlib openpyxl
```

### 2단계: Google 인증 설정 (최초 1회)
```
console.cloud.google.com → 새 프로젝트
→ Google Sheets API + Drive API 활성화
→ 서비스 계정 → JSON 키 다운로드
```

다운로드한 JSON의 값을 `.env` 파일에 입력합니다:
```bash
cp .env.example .env
# .env 파일을 열고 GOOGLE_SA_* 값을 채워넣기
```

> ⚠️ `.env`는 `.gitignore`에 포함되어 있어 자동으로 커밋에서 제외됩니다.
> 기존 `service_account.json` 방식도 하위호환으로 계속 동작합니다.

### 3단계: Google Sheets 초기 생성
```bash
python 1_setup_gsheet.py
# → 7개 시트 자동 생성 + 28종목 데이터 이전
# → sheet_id.txt 저장됨
```

### 4단계: GOOGLEFINANCE 시트 추가
```bash
python 5_add_googlefinance.py
# → 📈 실시간현황 / 📊 가격데이터 / 🔗 상관관계 시트 추가
```

### 5단계: Apps Script 설정
```
Google Sheets → 확장 프로그램 → Apps Script
→ 4_apps_script.js 전체 붙여넣기 → 저장
→ MY_EMAIL 변수를 본인 이메일로 수정
→ ⏰ 트리거 설정 (아래 참조)
```

### 6단계: 오프라인 분석 (선택)
```bash
python 6_offline_analysis.py              # 기본 1년
python 6_offline_analysis.py --years 2   # 2년
python 6_offline_analysis.py --out ./리포트
# → KRX 종목 포함 28개 전체 히트맵 + 엑셀 리포트
```

---

## 매매 루틴

```
체결 스크린샷
    ↓ Claude Desktop에 붙여넣기
    ↓ "이 체결화면 매매일지에 추가해줘" 입력
    ↓ Claude가 파싱 + 2_add_trade.py 실행
    ↓ Google Sheets 자동 기입
```

```bash
# 단건 매매 추가
python 2_add_trade.py --json '{"date":"2025-05-02","ticker":"NVDA","name":"NVIDIA","type":"매수","qty":10,"price":294130,"amount":2941300}'

# 현재가 일괄 업데이트
python 2_add_trade.py --prices '{"NVDA":294130,"GOOGL":562910,"META":901845}'

# 특정일 스냅샷 추가
python 2_add_trade.py  # → CLI 도움말 확인
```

---

## Apps Script 트리거 설정

| 함수 | 트리거 | 시간 |
|------|--------|------|
| `checkTargetPrice` | 하루 타이머 | 오전 8~9시 |
| `saveMonthlySnapshot` | 월 타이머 | 매월 1일 |
| `weeklyReviewReminder` | 주 타이머 | 매주 월요일 |
| `syncSectorSummary` | 하루 타이머 | 오전 9~10시 (선택) |

---

## 전체 시스템 구조

```
증권사 앱
    │ 체결 스크린샷
    ▼
Claude Desktop (Vision 파싱)
    │ 2_add_trade.py 실행
    ▼
Google Sheets 📊
    ├── 📊 포트폴리오        ← 수동 현재가 (기본)
    ├── 📈 실시간현황        ← GOOGLEFINANCE 자동가격
    ├── 🔗 상관관계          ← CORREL 자동계산
    ├── 🏭 섹터현황          ← Apps Script 자동집계
    ├── 📒 매매일지          ← 자동 추가
    ├── 📅 특정일잔고        ← SUMIF 날짜 복원
    ├── 👋 청산종목
    └── 🧠 전략·전망

    │ (오프라인 / KRX 포함 심화 분석)
    ▼
6_offline_analysis.py
    ├── offline_heatmap.png
    └── offline_analysis_report.xlsx

    │ 복기 · 전략 기록
    ▼
Obsidian (PARA 구조)
    └── Resources/투자/종목복기/
```

---

## ⚠️ 주의사항

- `.env`, `service_account.json`, `sheet_id.txt` → **절대 공유/커밋 금지** (`.gitignore`에 추가 완료)
- 공유 시에는 `.env.example`만 포함되며, 수신자가 자기 크레덴셜을 `.env`에 채워넣으면 됩니다.
- GOOGLEFINANCE KRX historical → 일부 종목 지원 제한 → `6_offline_analysis.py` 사용
- 비트코인(BTC) 거래일 365일 vs 주식 252일 불일치 → `5_add_googlefinance.py`에서 FILTER로 처리됨
- Google Sheets API 할당량: 분당 60회 → `5_add_googlefinance.py`에 `time.sleep()` 포함

---

## 삼성전기 가치분석 대시보드

삼성전기 `009150`을 한 종목씩 깊게 분석하기 위한 시장내포 가치분석 도구입니다. 첫 화면은 가치평가 결론이 아니라 데이터 무결성 확인입니다.

### 설치

```bash
pip install -r requirements-valuation.txt
```

### 테스트

```bash
python -m pytest tests/test_valuation_models.py tests/test_valuation_calculations.py tests/test_valuation_repository.py tests/test_valuation_audit.py tests/test_valuation_formatting.py tests/test_reverse_dcf.py tests/test_value_attribution.py tests/test_margin_scenario.py tests/test_roic_reinvestment.py tests/test_relative_valuation.py -v
```

### 실행

```bash
python -m streamlit run valuation_app/dashboard.py --server.port 8501
```

### 현재 구현 범위

- 2025년 연간 seed data
- 2026년 1분기 seed data
- 주가, 주식수, 시가총액, EV 계산 입력
- FCF, 순부채, NOPAT, 투하자본, ROIC 검산
- 입력값별 출처 상세 패널
- Reverse DCF: 현재 EV가 요구하는 FCF와 WACC/영구성장률 민감도
- Value Attribution: 현재 수익력 가치와 미래 기대 가치 분해
- 매출·마진 시나리오: 필요 FCF를 설명하는 매출 성장률과 영업이익률 조합
- ROIC·재투자 품질: 현재 ROIC, 주가 내포 미래 ROIC, 경제적 이익, EV/NOPAT, 목표 성장률별 필요 재투자율
- 상대가치: P/B 내포 ROE, EV/Sales 필요 마진, EV/NOPAT 가격 부담

이 화면에서 검산을 통과한 공통 입력값을 Reverse DCF, Value Attribution, 매출·마진 시나리오, ROIC, 상대가치 렌즈와 다음 단계의 CAP 렌즈가 사용합니다.
