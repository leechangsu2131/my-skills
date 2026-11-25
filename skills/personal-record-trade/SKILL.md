---
name: personal-record-trade
description: "보관된 이전 매매 기록 입력 절차를 설명합니다. 현재 새 매매 기록은 personal-invest-sheet를 사용하며, 이 문서는 기존 2_add_trade.py 기반 Google Sheets 입력 흐름을 참고할 때만 봅니다."
metadata:
  category: 개인·생활
  status: 보관
  summary: 이전 Google Sheets 매매일지 입력 절차와 2_add_trade.py 사용법을 보관한다. 현재 신규 기록에는 사용하지 않는다.
---

# 매매 기록 입력 (보관)

> **보관 (2026-11-20)**: 2026-11-22부터 새 투자시트 작업은 `personal-invest-sheet` 스킬에서 처리한다. 이 문서는 이전 Google Sheets 매매일지 입력 흐름을 참고하기 위한 기록이며, 아래의 시트 구조와 환경 설정은 현재와 다를 수 있다.

## 이전 사용 범위

이전에는 Google Sheet의 `📒 매매일지` 탭에 새 매매 기록을 추가하는 작업에만 사용했다.

포트폴리오 현황, 수익률, 목표 비중, 매매 신호, 업종 비중, 청산 포지션, 전략 검토를 분석하는 작업은 별도 분석 스킬의 범위다. 현재 신규 작업은 `personal-invest-sheet` 안내를 따른다.

## 과거 요청 예시

- `/record-trade 오늘 SCHD 10주를 41,000원에 매수함. 배당락일 전이라 포모 와서 샀음. 만족도는 6점`
- `이 체결 스크린샷을 매매일지에 추가해줘.`
- `방금 산 NVDA 10주를 투자 매매일지에 기록해줘.`

## 이전 환경 설정과 비밀값 관리

- **`.env` File Path:** `C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade\.env`
- 이 파일에는 Google 서비스 계정 인증 정보, 시트 ID, DART API 키, KRX 로그인 정보 등 비밀값이 들어갈 수 있다.
- **중요:** 사용자 스크립트를 작성하거나 환경변수를 확인할 때는 항상 `import sys, pathlib; sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file()))); from skill_env import load_env; load_env()` (중앙 `OneDrive\96. 인증\.env`을 읽음) so you don't falsely assume keys are missing!
- 기존 스크립트와 자료를 보존한다. 사용자가 설정 또는 이전 작업을 분명히 요청하지 않는 한 포트폴리오 스프레드시트를 새로 만들지 않는다.

## 이전 매매 기록 입력 절차

1. Parse the user's natural-language trade entry or brokerage screenshot into structured trade fields.
2. Normalize dates to `YYYY-MM-DD`. Interpret relative dates from the current system date, such as `오늘` as today and `어제` as yesterday.
3. Map missing optional values to an empty string.
4. Run `2_add_trade.py` with a JSON payload.
5. Report the recorded trade back to the user as a concise Markdown table.

## 입력 JSON 필드

Use the fields accepted by `2_add_trade.py`:

| Field | Meaning |
| --- | --- |
| `date` | 매매일, `YYYY-MM-DD` |
| `ticker` | 종목 티커 or 코드 |
| `name` | 종목명 |
| `type` | 매수 or 매도 |
| `qty` | 수량 |
| `price` | 단가, 원화 기준 when possible |
| `amount` | 총 거래금액 |
| `reason` | 매매 이유 |
| `timing` | 타이밍 이유 |
| `score` | 만족도, -10 to 10 |
| `analysis` | 사후분석, usually blank for new entries |
| `condition` | 당시 컨디션 or 심리 상태 |
| `bias` | 인지오류 or 편향 |
| `fix` | 해결전략 or 다음 행동 원칙 |
| `memo` | 기타 메모 |

Example:

```bash
python 2_add_trade.py --json '{"date":"2026-05-22","ticker":"NVDA","name":"NVIDIA","type":"매수","qty":10,"price":294130,"amount":2941300,"reason":"AI 수혜","timing":"조정 구간","score":"6","analysis":"","condition":"중","bias":"포모","fix":"분할매수 유지","memo":""}'
```

## 작업 범위 제한

- Do not use this skill for read-only portfolio review. Use `$personal-analyze-trade`.
- Do not perform broad Google Sheets analysis here. This skill may confirm the append result, but deeper review belongs to `$personal-analyze-trade`.
- Do not change formulas, dashboard ranges, or portfolio structure unless the user explicitly requests maintenance work.

## 이전 폴더 구조와 데이터 흐름

This skill contains several sub-modules for data ingestion and deep investment analysis:

- **`pipeline/`**: 데이터 수집 및 매핑 엔진. 
  - DART(국내 재무제표), YFinance, GuruFocus 자료를 가져온다.
  - **규칙:** 국내 종목의 기준 자료는 DART다. 국내 종목 코드를 찾을 때 Naver·yfinance 등 외부 API를 사용하지 말고 `corpCode.xml` 또는 기존 DART 모듈을 사용한다.
- **`valuation_app/`**: Streamlit 기반 가치평가 대시보드와 모델링 도구.
  - `dashboard.py`로 분석 결과를 만든다. Streamlit `AppTest` 선택 상자 오류를 피하면서 화면 지표(ROIC, EV)를 확인할 때는 `test_dashboard_robust.py` 또는 `run_audit()`를 사용한다.
- **`data/valuation/{ticker}/normalized/`**: 핵심 정규화 데이터 저장 위치.
  - `market.json`: 주가, 시가총액, 발행 주식 수를 담는다.
  - `metrics.json`: 과거 및 예상 재무 지표를 구조화해 담는다.
  - **규칙:** 과거 ROIC/NOPAT가 없으면 원본 DART 자료를 받은 뒤 계산식(NOPAT = OP*(1-tax), IC = Equity+NetDebt, ROIC = NOPAT/IC)에 따라 계산해 추가한다.

## ⚠️ 실수 방지 규칙집 (반드시 먼저 읽을 것)

**작업 시작 전에 반드시 아래 파일을 읽고 시작한다:**
- [`docs/pipeline_rules.md`](file:///C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/docs/pipeline_rules.md)

이 파일에는 이전 대화에서 발생한 모든 실수를 9개 카테고리로 분류하여 기록해 두었다.
핵심 원칙:
1. **작업 후 반드시 검증** — 코드 실행, 시트 값 확인, 대시보드 실행까지 완료해야 "됐다"고 말할 수 있다
2. **데이터 복붙/추정 금지** — 각 소스마다 직접 읽은 실제 값만 넣는다
3. **이전 합의사항 존중** — 기존 로직을 임의로 변경하지 않는다
4. **리서치 검색은 투트랙** — 검색 → 선별 → 다운로드 (filetype:pdf 직접 검색 금지)
5. **raw data는 소스별 개별 행, 기업분석은 종합 1행**

## 과거 검증 확인 목록

To prevent breaking the pipeline or Google Sheet, rigidly follow these steps:

1. **환경 초기화:** 항상 `import sys, pathlib; sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file()))); from skill_env import load_env; load_env()` (중앙 `OneDrive\96. 인증\.env`을 읽음) in EVERY script. Never assume an API key is missing just because the environment is empty.
2. **로컬 데이터 우선:** DART API와 `.env`가 프로젝트 표준으로 정해져 있으면 종목 코드처럼 기본 정보를 찾을 때 외부 웹 API에 의존하지 않는다.
3. **Google Sheets 안전 규칙:**
   - **Emoji Ban:** Never use emojis (like ✅) in `print()` statements when running Python in the Windows console (cp949 encoding errors will crash the script mid-execution).
   - **No Blind Appends:** When adding a company to the "기업분석" (Company Analysis) tab, always read existing rows first to prevent duplicate lines.
   - **Position ID & Status:** For initial research/analysis, set the Position ID (Column A) to `""` (blank) and Status (Column D) to `"관심종목"`. Do NOT auto-generate a Position ID until an actual trade occurs.
   - **Ticker Preservation:** To prevent Google Sheets from stripping leading zeros (e.g. `009540` -> `9540`), always prepend an apostrophe (`'009540`) or use `value_input_option='RAW'`.
4. **최종 검증:** Google Sheet를 업데이트하거나 데이터 파이프라인을 실행한 뒤에는 마지막으로 갱신된 행을 다시 읽거나 생성된 JSON을 확인해 데이터가 정확히 들어갔는지 증명한다.
