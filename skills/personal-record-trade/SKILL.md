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

## Setup

- `.env` must contain the Google credentials expected by `gsheet_auth.py`, including `GOOGLE_SA_*` values and `GOOGLE_SHEET_ID`.
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
