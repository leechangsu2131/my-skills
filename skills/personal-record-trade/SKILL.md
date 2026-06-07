---
name: personal-record-trade
description: "Use this skill when Codex needs to record a new trade entry in the user's Google Sheets trade journal from natural language, brokerage screenshots, or parsed execution details. This skill is for trade-entry capture and append workflows using the existing 2_add_trade.py script. For portfolio analysis, return checks, rebalancing signals, trade-signal review, journal review, or Google Sheets range-based inspection, use $personal-analyze-trade instead."
---

# Personal Record Trade

## Scope

Use this skill only when the main task is to add a new trade record to the Google Sheet `📒 매매일지` tab.

Use `$personal-analyze-trade` instead when the task is to inspect or analyze the investment sheet, including portfolio status, returns, target weights, trade signals, sector exposure, closed positions, strategy review, or position retrospectives.

## Trigger Examples

- `/record-trade 오늘 SCHD 10주를 41,000원에 매수함. 배당락일 전이라 포모 와서 샀음. 만족도는 6점`
- `이 체결 스크린샷을 매매일지에 추가해줘.`
- `방금 산 NVDA 10주를 투자 매매일지에 기록해줘.`

## Setup & Secrets (Don't Forget!)

- **`.env` File Path:** `C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade\.env`
- This file contains all critical secrets: `GOOGLE_SA_*` credentials, `GOOGLE_SHEET_ID`, `DART_API_KEY`, and `KRX` login info.
- **CRITICAL REMINDER:** When writing custom python scripts or checking environment variables, ALWAYS use `from dotenv import load_dotenv; load_dotenv(r'C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade\.env')` so you don't falsely assume keys are missing!
- Keep the existing scripts and resources in this folder. Do not recreate the portfolio spreadsheet unless the user explicitly asks for setup or migration work.

## Trade Entry Workflow

1. Parse the user's natural-language trade entry or brokerage screenshot into structured trade fields.
2. Normalize dates to `YYYY-MM-DD`. Interpret relative dates from the current system date, such as `오늘` as today and `어제` as yesterday.
3. Map missing optional values to an empty string.
4. Run `2_add_trade.py` with a JSON payload.
5. Report the recorded trade back to the user as a concise Markdown table.

## JSON Fields

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

## Boundaries

- Do not use this skill for read-only portfolio review. Use `$personal-analyze-trade`.
- Do not perform broad Google Sheets analysis here. This skill may confirm the append result, but deeper review belongs to `$personal-analyze-trade`.
- Do not change formulas, dashboard ranges, or portfolio structure unless the user explicitly requests maintenance work.

## Core Directories & Data Flow

This skill contains several sub-modules for data ingestion and deep investment analysis:

- **`pipeline/`**: The data ingestion and mapping engine. 
  - Fetches DART (Korean financial statements), YFinance, and GuruFocus data.
  - **Rule:** DART is the core truth for KR stocks. Do NOT use external APIs (Naver, yfinance) to search for KR stock tickers; use `corpCode.xml` or existing DART modules.
- **`valuation_app/`**: The Streamlit-based valuation dashboard and modeling toolkit.
  - Generates insights using `dashboard.py`. Use `test_dashboard_robust.py` or `run_audit()` to test UI metrics (ROIC, EV) safely without triggering Streamlit `AppTest` selectbox errors.
- **`data/valuation/{ticker}/normalized/`**: The core data storage.
  - `market.json`: Contains price, market cap, shares outstanding.
  - `metrics.json`: Contains structured historical and forward financial metrics.
  - **Rule:** If historical ROIC/NOPAT is missing, you MUST run a script to calculate and append them (NOPAT = OP*(1-tax), IC = Equity+NetDebt, ROIC = NOPAT/IC) after fetching raw DART data.

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

## Strict Verification Checklist (MUST READ)

To prevent breaking the pipeline or Google Sheet, rigidly follow these steps:

1. **Environment Initialization:** ALWAYS run `from dotenv import load_dotenv; load_dotenv(r'C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade\.env')` in EVERY script. Never assume an API key is missing just because the environment is empty.
2. **Local Data First:** Do not rely on external web APIs for basic lookups (like ticker codes) when DART API and `.env` are already established as the project standard.
3. **Google Sheets Safeties:**
   - **Emoji Ban:** Never use emojis (like ✅) in `print()` statements when running Python in the Windows console (cp949 encoding errors will crash the script mid-execution).
   - **No Blind Appends:** When adding a company to the "기업분석" (Company Analysis) tab, always read existing rows first to prevent duplicate lines.
   - **Position ID & Status:** For initial research/analysis, set the Position ID (Column A) to `""` (blank) and Status (Column D) to `"관심종목"`. Do NOT auto-generate a Position ID until an actual trade occurs.
   - **Ticker Preservation:** To prevent Google Sheets from stripping leading zeros (e.g. `009540` -> `9540`), always prepend an apostrophe (`'009540`) or use `value_input_option='RAW'`.
4. **Final Verification:** After any Google Sheet update or Data Pipeline run, ALWAYS fetch the last updated rows or read the generated JSON to prove to the user that the data was inserted cleanly and correctly.
