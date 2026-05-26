---
name: personal-analyze-trade
description: "Use this skill when Codex needs to analyze or inspect the user's investment portfolio Google Sheet: portfolio summary, returns, weights, sector exposure, rebalancing or trade signals, recent trade journal entries, closed positions, strategy review, position retrospectives, price data, or correlation data. Prefer this skill for Google Sheets MCP/Connector read-focused investment analysis and sheet-range selection. For adding a new natural-language or screenshot-based trade entry, use $personal-record-trade instead."
---

# Personal Analyze Trade

## Core Rules

- Use this skill for analysis, review, and Google Sheets range selection. Use `$personal-record-trade` when the primary task is adding a new trade from natural language or a brokerage screenshot.
- Prefer `sheets_values_get` with a precise A1 range. Avoid full-sheet reads.
- Use `sheets_get` only when the sheet structure itself is unknown and metadata is truly needed.
- Include emoji in sheet names exactly as shown in every A1 range, such as `📊 포트폴리오!A4:T32`.
- If Google Sheets tools are not loaded, search for the spreadsheet read/write tools first with a query such as `sheets spreadsheet read values`.
- Do not call Google Sheets write tools unless the user clearly asks to change the sheet.

## Spreadsheet Configuration

- Read this skill folder's local `.env` before calling Google Sheets tools or local scripts.
- Use `GOOGLE_SHEET_ID` as the `spreadsheetId` for both Google Sheets Connector calls and local `gspread` scripts.
- Use `GOOGLE_SHEET_URL` only for human-facing reference when needed.
- Connector-first path: when Google Sheets Connector/MCP tools are available, use `GOOGLE_SHEET_ID` with precise `sheets_values_get` ranges.
- Local fallback path: when Connector tools are unavailable, use the same `.env` with `GOOGLE_SA_*` service-account variables and a local `gspread` helper/script.
- If `.env` is missing or `GOOGLE_SHEET_ID` is empty, stop and ask the user for the sheet ID or URL instead of guessing.
- Never commit `.env`, `service_account.json`, or private key material.
- If local access returns `403 caller does not have permission`, the service account is valid but the spreadsheet has not been shared with `GOOGLE_SA_CLIENT_EMAIL`.

## Sheet Map

### 🏠 대시보드

- Purpose: total market value, returns, and bucket summary.
- Summary range: `🏠 대시보드!B5:H13`
- Columns: 버킷 | 종목수 | 평가금액 | 매입금액 | 평가손익 | 수익률 | 현재비중
- Total assets cell: `🏠 대시보드!C6`

### 📊 포트폴리오

- Purpose: full per-position status, currently about 28 positions.
- Header: `📊 포트폴리오!A4:T4`
- Data: `📊 포트폴리오!A5:T32`
- Header + data: `📊 포트폴리오!A4:T32`
- Asset summary cells on row 3: `📊 포트폴리오!C3,E3,G3,J3,L3` for 원화/달러/헤알/BTC/총자산.
- Exchange rate cell: `📊 포트폴리오!N3`

Column map:

| Column | Meaning |
| --- | --- |
| A | 등급 (S/A+/A/A-/B+/B) |
| B | 통화 (달러/원/헤알/BTC) |
| C | 종목코드 |
| D | 종목명 |
| E | GF티커 |
| F | 섹터 |
| G | 버킷 (성장/코어/인컴/전술) |
| H | 수량 |
| I | 현지가 |
| J | 현재가(원) |
| K | 평균매입가 |
| L | 평가금액 |
| M | 매입금액 |
| N | 평가손익 |
| O | 수익률 |
| P | 현재비중 |
| Q | 목표비중 |
| R | ROIC |
| S | 비고 |
| T | 조정수량 |

### 🎯 비중조절신호

- Purpose: target price, trade signal, and adjustment quantity checks.
- Parameters: `🎯 비중조절신호!B3:H3`
- Header: `🎯 비중조절신호!A4:S4`
- Data: `🎯 비중조절신호!A5:S32`
- Signal-focused read: `🎯 비중조절신호!A5:P32`

### 🏭 섹터현황

- Purpose: sector exposure and concentration review.
- Data: `🏭 섹터현황!A3:J17`

### 📅 특정일잔고

- Purpose: historical holdings snapshot.
- Data: `📅 특정일잔고!A3:T16`

### 📒 매매일지

- Purpose: recent trade journal review. New trade entry automation belongs to `$personal-record-trade`.
- Header: `📒 매매일지!A3:H3`
- Data: `📒 매매일지!A4:H300`
- Current last known data row: 289 as of 2026-05-18.
- Only columns A:H are active after the 2025 cleanup; I:M were removed.

Column map:

| Column | Meaning |
| --- | --- |
| A | 매매일 |
| B | 포지션ID (for example P001, P021) |
| C | 티커 |
| D | 종목명 |
| E | 구분 (매수/매도) |
| F | 수량 |
| G | 금액(원) |
| H | 매매근거 |

Position IDs use `P001` through `P053` to group split buys/sells into one investment idea.

### 👋 청산종목

- Purpose: closed positions.
- Data: `👋 청산종목!A3:N50`

### 🧠 전략·전망

- Purpose: strategy success rate, market outlook, monthly notes, and position retrospectives.
- Strategy success rates: `🧠 전략·전망!A3:G10`
- Market outlook: `🧠 전략·전망!A13:B27`
- Monthly mood notes: `🧠 전략·전망!A28:B37`
- Position retrospective header: `🧠 전략·전망!A40:J40`
- Position retrospective data: `🧠 전략·전망!A41:J65`

### 📊 가격데이터

- Purpose: historical price data.
- Full data: `📊 가격데이터!A1:AG1530`
- This is a large sheet. Read only the needed ticker/date columns whenever possible.

### 🔗 상관관계

- Purpose: correlation review.
- Data: `🔗 상관관계!A1:AE60`

## Common Read Patterns

Use these ranges first unless the user asks for something more specific:

```text
Dashboard summary:              🏠 대시보드!B5:H13
Portfolio header + positions:   📊 포트폴리오!A4:T32
Trade signals:                  🎯 비중조절신호!A5:P32
Recent trade journal sample:    📒 매매일지!A4:H14
Position retrospectives:        🧠 전략·전망!A40:J65
Sector exposure:                🏭 섹터현황!A3:J17
Closed positions:               👋 청산종목!A3:N50
```

For formatted values, rely on the default formatted rendering or request `valueRenderOption: "FORMATTED_VALUE"` when the tool supports it. For formulas, request `valueRenderOption: "FORMULA"`.

## Local gspread Fallback

Use this path when Google Sheets Connector/MCP tools are unavailable.

- Install dependencies if needed: `gspread`, `google-auth`, and `python-dotenv`.
- Load `skills/personal-analyze-trade/.env`.
- Build service-account credentials from the `GOOGLE_SA_*` variables.
- Open the spreadsheet by `GOOGLE_SHEET_ID`.
- Read only the required worksheet/range pairs listed in this skill.

Important Windows/PowerShell lesson from live verification:

- Do not pass emoji sheet names inside a PowerShell-embedded Python A1 range such as `📊 포트폴리오!A4:T32`; they may be encoded as `??` and Google Sheets will return `Unable to parse range`.
- Instead, open the spreadsheet, select the worksheet object from `ss.worksheets()` by its live title or known index, then call `ws.get("A4:T32")` without the sheet name.
- Do not put Korean trade reasons or labels directly inside an inline PowerShell Python script. They may be written to the sheet as `??`.
- For Korean write payloads, create/read a UTF-8 JSON file, or use ASCII-only escaped JSON, then pass the parsed values to `gspread`.
- The verified worksheet order is:

| Index | Worksheet |
| --- | --- |
| 0 | 🏠 대시보드 |
| 1 | 📊 포트폴리오 |
| 2 | 🎯 비중조절신호 |
| 3 | 🏭 섹터현황 |
| 4 | 📅 특정일잔고 |
| 5 | 📒 매매일지 |
| 6 | 👋 청산종목 |
| 7 | 🧠 전략·전망 |
| 8 | 📊 가격데이터 |
| 9 | 🔗 상관관계 |
| 10 | ⚙️ Apps Script |

Minimal local read pattern:

```python
worksheets = ss.worksheets()
portfolio = worksheets[1]
rows = portfolio.get("A4:T32")
```

Use worksheet indexes only after confirming the live worksheet list. If the order changes, match by the title returned from the API rather than typing emoji titles into the shell command.

Minimal local write pattern for Korean text:

```python
rows = json.loads(Path("payload.json").read_text(encoding="utf-8"))
trade_journal = ss.worksheets()[5]
trade_journal.update("A292:H295", rows, value_input_option="USER_ENTERED")
```

## Write Guidance

Only write when the user explicitly requests a sheet change.

For normal trade-entry work, prefer `$personal-record-trade`, which maps natural language or screenshot trades and uses the existing `2_add_trade.py` workflow.

If a direct Google Sheets append is explicitly required for the current sheet:

```javascript
spreadsheetId: "<GOOGLE_SHEET_ID from .env>"
range: "📒 매매일지!A:H"
valueInputOption: "USER_ENTERED"
values: [["2026-05-21", "P001", "NVDA", "NVIDIA", "매수", 10, 3000000, "추가매수"]]
```

## Large Write Safety

- Keep batch writes small. For Korean-heavy rows, update at most five rows per call.
- Split long text fields from numeric fields when needed. Write A:G first, then update H separately.
- Avoid problematic `&` strings in tool JSON if the MCP parser fails. For example, prefer `SP500` over `S&P500`.
- Provide a wider row range than the number of rows being written to avoid `tried writing to row N`.
- If a Korean text argument causes `unexpected argument`, shorten or remove spaces in the text and retry with a smaller payload.
- After writing, verify with `sheets_values_get` against the last few relevant rows.

## Response Style

- Summarize portfolio analysis in Korean unless the user asks otherwise.
- Mention the exact ranges read when reporting results.
- Separate observed sheet data from interpretation. Make it clear when a conclusion is an inference from the sheet values.
- Do not provide investment advice as certainty. Frame analysis as portfolio review, risk/weight observation, or trade-signal interpretation based on the sheet.
