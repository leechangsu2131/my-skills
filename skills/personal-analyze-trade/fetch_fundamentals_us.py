#!/usr/bin/env python3
"""미국 종목 재무 데이터 수집 (yfinance) -> fundamentals_us.csv

사용법
  pip install yfinance pandas
  python fetch_fundamentals_us.py                 # 아래 DEFAULT_TICKERS 전체
  python fetch_fundamentals_us.py GOOG WDAY       # 일부만 (처음엔 이렇게 시험)

출력: fundamentals_us.csv (같은 폴더)
  - *_usd 열: 달러 원값
  - *_eok 열: 억 달러 (밸류계산 탭 입력 단위. 시총 361.1 같은 값과 같은 단위로 가정)
  - warn 열: 못 가져온 항목 표시 (비어 있으면 정상)

계산식
  FCF         = 영업현금흐름 - CapEx  (최근 4분기 합 = TTM)
  순부채      = 총부채 - 현금및단기투자 (최근 분기말)
  투자자본    = 야후 Invested Capital, 없으면 자기자본 + 순부채
  EBIT        = 영업이익 (TTM)
  NOPAT       = EBIT x (1 - 세율)
  ROIC        = NOPAT / 투자자본

주의: 야후는 비공식 데이터라 항목명이 바뀌거나 빠질 수 있다. warn 열을 꼭 본다.
"""
import sys
import time
import datetime as dt

import pandas as pd
import yfinance as yf

# 보유·관심 개별 종목 (ETF는 재무제표가 없어 제외)
DEFAULT_TICKERS = [
    "GOOG", "NVDA", "META", "PLTR", "NFLX", "ADBE", "UNH", "ORCL",
    "RDDT", "APP", "HOOD", "WDAY", "NTNX", "CRM", "NOW",
]

EOK = 1e8  # 1억


def pick(df, names):
    """df(행=항목, 열=분기)에서 names 중 먼저 있는 항목 행(Series)을 반환. 없으면 None."""
    if df is None or df.empty:
        return None
    for n in names:
        if n in df.index:
            return df.loc[n]
    return None


def ttm(df, names, warn, label):
    """최근 4분기 합. 4분기가 안 모이면 NaN."""
    s = pick(df, names)
    if s is None:
        warn.append(label + "없음")
        return float("nan")
    s = s.dropna()
    if len(s) < 4:
        warn.append(label + "분기부족")
        return float("nan")
    return float(s.iloc[:4].sum())  # 열은 최신 분기가 앞쪽


def latest(df, names, warn, label):
    """가장 최근 분기말 값."""
    s = pick(df, names)
    if s is None:
        warn.append(label + "없음")
        return float("nan")
    s = s.dropna()
    if s.empty:
        warn.append(label + "없음")
        return float("nan")
    return float(s.iloc[0])


def fetch_one(sym):
    warn = []
    t = yf.Ticker(sym)
    info = {}
    try:
        info = t.info or {}
    except Exception as e:  # noqa: BLE001
        warn.append("info실패:" + type(e).__name__)

    inc = t.quarterly_income_stmt
    cf = t.quarterly_cashflow
    bs = t.quarterly_balance_sheet

    ocf = ttm(cf, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"], warn, "영업CF")
    capex = ttm(cf, ["Capital Expenditure"], warn, "CapEx")  # 야후는 음수로 줌
    fcf_direct = ttm(cf, ["Free Cash Flow"], [], "FCF")
    if pd.notna(ocf) and pd.notna(capex):
        fcf = ocf + capex if capex <= 0 else ocf - capex
    else:
        fcf = fcf_direct
    ebit = ttm(inc, ["EBIT", "Operating Income"], warn, "EBIT")
    revenue = ttm(inc, ["Total Revenue", "Operating Revenue"], warn, "매출")
    pretax = ttm(inc, ["Pretax Income"], [], "")
    tax = ttm(inc, ["Tax Provision"], [], "")

    debt = latest(bs, ["Total Debt"], warn, "총부채")
    cash = latest(
        bs,
        ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"],
        warn,
        "현금",
    )
    equity = latest(bs, ["Stockholders Equity", "Common Stock Equity"], warn, "자기자본")
    net_debt = debt - cash if pd.notna(debt) and pd.notna(cash) else float("nan")

    inv_cap = latest(bs, ["Invested Capital"], [], "")
    inv_src = "야후"
    if pd.isna(inv_cap) and pd.notna(equity) and pd.notna(net_debt):
        inv_cap = equity + net_debt
        inv_src = "자기자본+순부채"
    elif pd.isna(inv_cap):
        inv_src = ""
        warn.append("투자자본없음")

    # 세율: 세금/세전이익이 0~40% 범위면 사용, 아니면 21% 가정
    tax_rate = 0.21
    tax_src = "가정21%"
    if pd.notna(pretax) and pretax > 0 and pd.notna(tax) and 0 <= tax / pretax <= 0.40:
        tax_rate = tax / pretax
        tax_src = "실효세율"

    nopat = ebit * (1 - tax_rate) if pd.notna(ebit) else float("nan")
    roic = nopat / inv_cap if pd.notna(nopat) and pd.notna(inv_cap) and inv_cap > 0 else float("nan")
    op_margin = ebit / revenue if pd.notna(ebit) and pd.notna(revenue) and revenue else float("nan")

    mcap = info.get("marketCap")
    row = {
        "ticker": sym,
        "source": "yfinance",
        "date": dt.date.today().isoformat(),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "market_cap_usd": mcap,
        "total_debt_usd": debt,
        "cash_usd": cash,
        "net_debt_usd": net_debt,
        "ocf_ttm_usd": ocf,
        "capex_ttm_usd": capex,
        "fcf_ttm_usd": fcf,
        "ebit_ttm_usd": ebit,
        "revenue_ttm_usd": revenue,
        "equity_usd": equity,
        "invested_capital_usd": inv_cap,
        "invested_capital_src": inv_src,
        "tax_rate": round(tax_rate, 4),
        "tax_rate_src": tax_src,
        "nopat_ttm_usd": nopat,
        "roic_pct": round(roic * 100, 2) if pd.notna(roic) else float("nan"),
        "op_margin_pct": round(op_margin * 100, 2) if pd.notna(op_margin) else float("nan"),
        "pb": info.get("priceToBook"),
        "pe_trailing": info.get("trailingPE"),
        "warn": ";".join(warn),
    }
    # 억 달러 환산 열 (밸류계산 입력용)
    for k in ["market_cap", "net_debt", "fcf_ttm", "ebit_ttm", "nopat_ttm", "invested_capital", "equity"]:
        v = row.get(k + "_usd")
        row[k + "_eok"] = round(v / EOK, 2) if v is not None and pd.notna(v) else float("nan")
    return row


def main():
    tickers = [a.upper() for a in sys.argv[1:]] or DEFAULT_TICKERS
    rows = []
    for i, sym in enumerate(tickers, 1):
        print(f"[{i}/{len(tickers)}] {sym} ...", flush=True)
        try:
            rows.append(fetch_one(sym))
        except Exception as e:  # noqa: BLE001
            print(f"  실패: {type(e).__name__}: {e}")
            rows.append({"ticker": sym, "source": "yfinance",
                         "date": dt.date.today().isoformat(),
                         "warn": f"실패:{type(e).__name__}"})
        time.sleep(1.0)  # 야후 호출 제한 회피

    df = pd.DataFrame(rows)
    df.to_csv("fundamentals_us.csv", index=False, encoding="utf-8-sig")
    show = [c for c in ["ticker", "market_cap_eok", "net_debt_eok", "fcf_ttm_eok",
                        "ebit_ttm_eok", "invested_capital_eok", "roic_pct", "warn"] if c in df.columns]
    print()
    print(df[show].to_string(index=False))
    print("\n저장: fundamentals_us.csv")


if __name__ == "__main__":
    main()
