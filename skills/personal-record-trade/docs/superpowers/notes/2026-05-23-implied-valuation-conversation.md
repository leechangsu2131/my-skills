# Implied Valuation Tool Conversation Notes

Date: 2026-05-23

## Product Direction

The tool is intended to help with investment thinking by reverse-engineering what the current market price implies about a company.

The user prefers a web dashboard, not a CLI or spreadsheet-first tool. The first version should analyze one stock at a time in depth. Data should be fetched automatically where possible, while important assumptions remain editable.

## Design Lessons From The Conversation

- The dashboard should not be formula-first. The user found raw formulas difficult to internalize.
- The screen should be organized around investment questions:
  - How much future expectation is embedded in the current price?
  - What operating performance must be true for the price to make sense?
  - Are those expectations reasonable versus history and peers?
  - Which special models apply to this company type?
- Formulas still matter, but they should act as transparent audit trails behind each answer.
- Each result should show:
  - the question being answered
  - the selected model and why it was selected
  - the formula
  - the actual substituted values
  - the data source and timestamp
  - the formula/source reference
  - a beginner-friendly explanation
- The user wants the design process itself preserved because it is part of building the system.

## Current Preferred Interface

Use a beginner-friendly, transparent dashboard:

1. Start with a plain-language investment question.
2. Show the current market-implied answer.
3. Explain why that model was chosen.
4. Show the formula and substituted values.
5. Show source lineage for both data and formula.
6. Compare the implied assumptions against history and peers.

## Model Selection Principle

The initial screen should choose models based on the company and the question, not expose every model at once.

Core models:

- Reverse DCF: market-implied FCF growth.
- Value Attribution: current earnings power versus future growth value.
- Implied ROIC / ROE: required business quality.
- Sensitivity analysis: downside if core assumptions miss.

Conditional models:

- EV/Sales -> margin: useful for loss-making, SaaS, or revenue-first businesses.
- POS: useful for biotech, startups, and binary event companies.
- CAP: useful when the key question is how long excess returns can last.
- Franchise value: useful after P/E intuition is established.
- Credit spread linkage: useful when bond data is available and risk divergence matters.

## Case Study Direction

The user wants to build the system while performing a real valuation case study.

Chosen company:

- Samsung Electro-Mechanics
- Korean name: 삼성전기
- Likely ticker: 009150.KS

The next design iteration should use Samsung Electro-Mechanics instead of NVIDIA and walk through the analysis step by step.

## Samsung Electro-Mechanics Initial Data Snapshot

Date checked: 2026-05-23.

Market data is volatile and should be refreshed during implementation. The first case-study snapshot uses:

- Ticker: 009150.KS
- Last close found: KRW 1,340,000 on 2026-05-22.
- yfinance returned current price KRW 1,340,000, previous close KRW 1,204,000, market cap about KRW 101.2 trillion, total cash about KRW 2.70 trillion, total debt about KRW 2.28 trillion.
- Official Samsung Electro-Mechanics 2025 financial information shows revenue KRW 11.3145 trillion, operating profit KRW 913.3 billion, net income KRW 731.0 billion, and total assets KRW 14.596 trillion.
- yfinance cash flow data shows 2025 operating cash flow about KRW 1.49 trillion, capex about KRW 1.25 trillion, and free cash flow about KRW 244 billion.

Initial product insight:

- A one-stage Reverse DCF using current FCF will likely produce an implied growth rate close to WACC.
- That result should not be shown as a final answer. It should trigger an explanation: the market is probably not valuing the company on 2025 trailing FCF alone.
- For Samsung Electro-Mechanics, the more natural first question is: "What recovery or structural growth in margins, ROIC, and FCF conversion is the current price implying?"
- The dashboard should visibly separate historical facts, analyst estimates, and user assumptions.
- The latest quarter should sit beside annual data. Annual data describes business capacity and through-cycle context; the latest quarter describes current momentum and whether the market narrative is starting to show up in results.
- Official Q1 2026 press release says revenue was KRW 3.2091 trillion and operating profit was KRW 280.6 billion, with revenue +17% YoY/+11% QoQ and operating profit +40% YoY/+17% QoQ. It also notes one-off severance cost of KRW 71.4 billion and continued demand for AI server/data center/automotive high-value products.
- yfinance quarterly financials returned a conflicting Q1 2026 operating income number. The product should detect and display source conflicts. For operating results, official company release should be the primary source, while yfinance can remain a convenience source for market data and initial pulls.
- The user wants the general v3 model set to remain visible while walking through the Samsung Electro-Mechanics case. It should not sit below the fold. Treat it as a persistent "model palette" or right-side reference panel.
- Step 2 should be a scenario map rather than a single answer. Show required FCF under discount-spread scenarios, then compare it with normalized FCF generated from revenue, operating margin, tax rate, and FCF conversion assumptions.
- If the one-stage steady-state model produces an extreme result, the product should explicitly explain that this is a diagnostic signal. It means the market price may require multi-year growth, much higher normalized margins, lower discount spreads, or a long competitive advantage period.

## Damodaran FCFF Template Review

File supplied by user: `D:\Downloads\fcffsimpleginzu.xlsx`.
Video/transcript supplied by user: "Valuation Modeling: Excel as a tool" (`https://www.youtube.com/watch?v=kyKfJ_7-mdg`).

The `.gsheet` shortcut could not be read locally, but the exported `.xlsx` was readable with a Python fallback after the artifact-tool import failed because of comment metadata (`Comment createdAt is required`).

Useful workbook structure:

- `Input sheet`: centralized actuals, assumptions, industry inputs, cost of capital, stable growth overrides, failure probability, and special adjustments.
- `Stories to Numbers`: narrative-facing bridge from assumptions to cash flows and final value. This is highly relevant to the user's concern that formulas are not intuitive.
- `Valuation output`: forecast engine. It forecasts revenue, operating margin, EBIT, tax, EBIT(1-t), reinvestment, FCFF, cost of capital, discount factors, terminal value, equity bridge, and value per share.
- `Diagnostics`: explicit reasonableness checks for revenue growth, margins, reinvestment/sales-to-capital, return on capital, risk metrics, and price-versus-value.

Design implication:

- Our web tool should borrow the template's conceptual architecture, not necessarily its spreadsheet UI:
  - Inputs/Assumptions
  - Story to Numbers
  - Valuation Output
  - Diagnostics
  - Sources/Audit
- Keep the v3 model palette visible, but add a "Damodaran map" showing where each screen belongs in the DCF spine.
- For Samsung Electro-Mechanics, the next screen should show Value Attribution and CAP diagnostics while preserving the story-to-numbers bridge.

Transcript-derived principles to preserve:

- The spreadsheet is a tool; the investor owns the valuation. Avoid language like "the model says." Use "your assumptions imply."
- Keep the model parsimonious: simple enough to understand manually, rigorous enough to avoid hand-waving.
- Avoid black boxes. Macros and opaque functions are not necessary for the first version.
- Before opening the model, choose a company and gather at least one annual report plus the latest quarterly report if the annual report is not fresh.
- For non-financial companies, FCFF is the default valuation spine. Financial service companies need a different model.
- Inputs should be visibly separate from calculated cells. Damodaran uses yellow input cells and green calculated cells; our web UI should use comparable color/label conventions.
- Key first-page data requirements:
  - valuation date and company name
  - country of incorporation
  - industry classification
  - revenue and operating income/EBIT
  - interest expense
  - book equity and book debt
  - cash and marketable securities
  - cross holdings / non-operating assets
  - minority interests
  - shares outstanding and current stock price
  - effective and marginal tax rates
- Key forecast drivers:
  - revenue growth next year
  - operating margin next year
  - revenue growth years 2-5
  - target operating margin
  - year of margin convergence
  - sales-to-capital ratio for reinvestment efficiency
  - risk-free rate / cost of capital
  - terminal cost of capital, terminal ROIC, failure probability, reinvestment lag, tax normalization, NOL, and terminal growth overrides where relevant
- The "Stories to Numbers" sheet is especially important. It forces the investor to explain why revenue growth, margins, sales-to-capital, and cost of capital are what they are.
- The "Diagnostics" sheet should not just produce an answer. It should point to the input levers that drive value when the result looks too high or too low.

## Multi-Lens Valuation Direction

The user clarified that Damodaran's method is ultimately a cash-flow valuation lens. It is useful, but the tool should not be limited to it.

New product direction:

- Analyze one company step by step through multiple lenses.
- Each lens answers a different investment question.
- The dashboard should make the current lens, previous lens, and next lens visible.
- The output should compare whether the conclusions converge or diverge.
- Divergence is important: it may reveal an opportunity, a flawed assumption, or a company where one valuation method is inappropriate.

Proposed lens order for Samsung Electro-Mechanics:

1. Market Snapshot and Source Integrity
   - What are the current market facts?
   - Are annual, quarterly, and market data sources consistent?

2. FCFF / Reverse DCF Lens
   - What FCF growth or normalized FCF does the price require?
   - Uses Damodaran-style cash-flow logic.

3. Value Attribution Lens
   - How much of the current EV is explained by current earnings power versus future expectations?

4. Margin and Revenue Scenario Lens
   - What revenue and operating margin combination would make the story plausible?

5. ROIC / Reinvestment Quality Lens
   - Can the required growth be produced with attractive returns on capital?
   - Uses sales-to-capital, reinvestment rate, and ROIC diagnostics.

6. Relative Valuation Lens
   - How do P/E, P/B, EV/EBIT, EV/Sales, and peer multiples compare?
   - Useful as a market-pricing sanity check, not a standalone truth.

7. CAP / Moat Duration Lens
   - How long must excess returns last?

8. Risk and Downside Lens
   - What happens if growth, margin, WACC, or ROIC assumptions disappoint?

9. Narrative Consistency Lens
   - Does the market story match the numerical assumptions?
   - For Samsung Electro-Mechanics, this includes AI server, high-value MLCC, FC-BGA, silicon capacitor, automotive, and cyclicality questions.

10. Synthesis
   - Where do methods agree?
   - Where do they disagree?
   - Which assumptions matter most?
   - What should the investor watch next?

## Open Product Question

For Samsung Electro-Mechanics, the tool should begin by deciding which valuation question is most natural:

- Is the current stock price pricing in an MLCC/camera module cycle recovery?
- How much normalized operating margin or ROIC recovery is embedded?
- Is the market valuing current trough earnings or future cycle recovery?
- Which assumptions are historical facts, analyst estimates, or user inputs?

## DART to LLM to Sheet Pipeline Review

The user supplied a proposed automation pipeline with these files:

- `dart_collector.py`
- `llm_extractor.py`
- `main.py`
- `pipeline-design.jsx`
- `requirements.txt`
- `sheet_updater.py`

Conclusion: this is useful, but primarily as the data ingestion and normalization layer, not as the valuation model itself.

Useful ideas to preserve:

- DART can provide official annual and quarterly financial statement rows.
- An LLM can help map Korean account names that vary by company and report, such as different labels for capex, cash flow, debt, or equity.
- A preprocessing layer that groups accounts by statement type before extraction is the right direction.
- Automatic validation such as `FCF = operating cash flow - capex` and `net debt = short debt + long debt - cash` should be preserved.
- Google Sheets can remain an export target, especially for compatibility with Damodaran-style templates.

Required changes before using it in this product:

- Keep a local normalized data store before updating any sheet. Suggested layers:
  - raw DART response
  - normalized metric table
  - source/audit table
  - valuation model inputs
- Every extracted number must carry source lineage:
  - report year and report code
  - annual or quarter flag
  - statement name
  - original account name
  - original amount and normalized unit
  - extraction confidence
  - whether the number came directly from DART, deterministic calculation, market data, or user override
- The LLM should not return only final metrics. It should return metric plus evidence. This is central to the user's desire for transparent formulas and beginner-friendly explanations.
- Use deterministic rules first for common line items, then ask the LLM to resolve ambiguous or company-specific account mappings.
- Use structured validation, preferably a schema such as Pydantic, instead of permissive JSON parsing.
- Avoid hardcoded sheet IDs, worksheet names, credentials paths, and model names. These should come from configuration.
- Support both annual and latest quarter data. DART report codes:
  - annual report: `11011`
  - first quarter: `11013`
  - half-year: `11012`
  - third quarter: `11014`
- The dashboard should show DART/market data freshness before showing valuation conclusions.

Design implication:

- Add a "Source Integrity" or "Data Pipeline" screen before the valuation lenses.
- The screen should answer:
  - Where did this number come from?
  - Was it extracted, calculated, estimated, or manually overridden?
  - Which formula used it?
  - Which values failed or passed reconciliation checks?
- For Samsung Electro-Mechanics, this data layer should collect:
  - latest annual financials
  - latest quarterly financials
  - current price, shares, market cap, EV
  - debt, cash, equity, invested capital, operating profit, operating cash flow, capex, FCF
  - source links and timestamps

## Implementation Progress Notes - ROIC Lens

The user asked to continue the multi-lens analysis after Reverse DCF, Value Attribution, and revenue/margin scenarios. The next implemented lens is ROIC / Reinvestment Quality.

Design intent:

- Show why ROIC matters before using it as a formula input.
- Make 25% ROIC a user-adjustable comparison point, not a hidden ceiling or claim.
- Explain current ROIC versus WACC through economic profit.
- Show `Reinvestment Rate = g / ROIC` so the user can see how growth quality changes with business quality.
- Show the McKinsey value-driver formula transparently, but warn when the one-stage formula breaks under current EV/NOPAT because that means the price likely requires multi-stage margin recovery, revenue growth, or long competitive advantage duration.

Next likely lens:

- Relative valuation, using P/E, P/B, EV/NOPAT or EV/EBIT, and EV/Sales only after the user can see how each multiple maps back to growth, margin, ROIC, or book-return assumptions.

## Implementation Progress Notes - ROIC Diagnostic Correction

The user noticed that tab 6 did not calculate the future expected ROIC embedded in the current price.

Root cause:

- The first implementation only used the current NOPAT based formula:
  `EV/NOPAT = (1 - g/ROIC) / (WACC - g)`.
- Samsung Electro-Mechanics' current EV/NOPAT is about `135.1x`.
- At WACC `9%` and perpetual growth `3%`, that one-stage formula can explain at most `1 / (9% - 3%) = 16.7x`, even if ROIC tends toward infinity.
- Therefore the displayed `None` was mathematically valid but product-wise confusing.

Correction:

- Keep the current NOPAT diagnostic and explicitly show `해 없음` when the formula cannot solve.
- Add the invested-capital based implied future ROIC:
  `EV = Invested Capital × (Future ROIC - g) / (WACC - g)`
  so `Future ROIC = g + EV × (WACC - g) / Invested Capital`.
- This better answers the user's intended question: what future normalized business quality is the current price asking for?
