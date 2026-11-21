#!/usr/bin/env python3
"""미국 종목 재무 데이터 수집 (yfinance) -> fundamentals_us.csv

사용법
  pip install yfinance pandas
  python fetch_fundamentals_us.py                 # universe.csv 의 미국 개별주(보유·관심) 전체
  python fetch_fundamentals_us.py MSFT AAPL       # 일부만 (처음엔 이렇게 시험)

출력: fundamentals_us.csv (같은 폴더)
  - *_usd 열: 달러 원값
  - *_eok 열: 억 달러 (밸류계산 탭 입력 단위. 시총 361.1 같은 값과 같은 단위로 가정)
  - warn 열: 못 가져온 항목 표시 (비어 있으면 정상)

계산식
  FCF         = 영업현금흐름 - CapEx  (최근 4분기 합 = TTM)
  순부채      = 총부채 - 현금및단기투자 (최근 분기말)
  투자자본    = 야후 Invested Capital, 없으면 자기자본 + 총부채(야후 정의와 비슷)
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

# 종목은 universe.csv(비공개, 드라이브)에서 읽는다: 개별 주식(asset=stock) 중 보유·관심
from invest_common import out_dir, role_label, stocks  # noqa: E402

_US = stocks("USD")
HOLDINGS = [s["code"] for s in _US]
GROUP = {s["code"]: role_label(s["role"]) for s in _US}
# 금융업은 순부채·FCF·ROIC 개념이 맞지 않아 경고만 붙인다 (universe fin=Y)
FINANCIALS = {s["code"] for s in stocks("USD", include_closed=True) if s["fin"]}

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


def annual_growth(df, names):
    """최근 회계연도 vs 직전 회계연도 증감률(%). 직전 값이 0 이하면 NaN."""
    s = pick(df, names)
    if s is None:
        return float("nan")
    s = s.dropna()
    if len(s) < 2 or s.iloc[1] <= 0:
        return float("nan")
    return round((float(s.iloc[0]) / float(s.iloc[1]) - 1) * 100, 1)


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
    try:  # 시트 기업분석의 매출성장률·FCF성장률은 최근 회계연도 기준
        rev_g = annual_growth(t.income_stmt, ["Total Revenue", "Operating Revenue"])
        fcf_g = annual_growth(t.cashflow, ["Free Cash Flow"])
    except Exception:  # noqa: BLE001
        rev_g = fcf_g = float("nan")

    ocf = ttm(cf, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"], warn, "영업CF")
    capex = ttm(cf, ["Capital Expenditure"], warn, "CapEx")  # 야후는 음수로 줌
    fcf_direct = ttm(cf, ["Free Cash Flow"], [], "FCF")
    if pd.notna(ocf) and pd.notna(capex):
        fcf = ocf + capex if capex <= 0 else ocf - capex
    else:
        fcf = fcf_direct
    # 야후 "EBIT"는 이자·투자수익이 섞여 영업마진이 부풀려지므로 영업이익을 먼저 쓴다
    ebit = ttm(inc, ["Operating Income", "EBIT"], warn, "영업이익")
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
    if pd.isna(inv_cap) and pd.notna(equity) and pd.notna(debt):
        inv_cap = equity + debt
        inv_src = "자기자본+총부채"
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
    # 밸류계산 탭(B8)과 같은 21% 세율로 계산한 ROIC (종목 간 비교용)
    nopat21 = ebit * (1 - 0.21) if pd.notna(ebit) else float("nan")
    roic21 = nopat21 / inv_cap if pd.notna(nopat21) and pd.notna(inv_cap) and inv_cap > 0 else float("nan")
    if sym in FINANCIALS:
        warn.append("금융업:순부채·FCF·ROIC 참고불가")

    mcap = info.get("marketCap")
    row = {
        "ticker": sym,
        "group": GROUP.get(sym, ""),
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
        "roic_pct_21": round(roic21 * 100, 2) if pd.notna(roic21) else float("nan"),
        "op_margin_pct": round(op_margin * 100, 2) if pd.notna(op_margin) else float("nan"),
        "rev_growth_fy_pct": rev_g,
        "fcf_growth_fy_pct": fcf_g,
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
    tickers = [a.upper() for a in sys.argv[1:]] or HOLDINGS
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
    df.to_csv(out_dir("finance") / "fundamentals_us.csv", index=False, encoding="utf-8-sig")

    def col(c):
        return df[c] if c in df.columns else float("nan")

    def r2(c):
        return pd.to_numeric(col(c), errors="coerce").round(2)

    # 시트 '📥 재무수집' 탭 A:Q 열 순서 그대로 (붙여넣기용)
    paste = pd.DataFrame({
        "티커": col("ticker"), "구분": col("group"), "수집일": col("date"),
        "종가": col("price"), "시총": col("market_cap_eok"), "순부채": col("net_debt_eok"),
        "FCF": col("fcf_ttm_eok"), "영업이익": col("ebit_ttm_eok"), "자기자본": col("equity_eok"),
        "투자자본": col("invested_capital_eok"), "영업마진": col("op_margin_pct"),
        "ROIC": col("roic_pct_21"), "PBR": r2("pb"), "PER": r2("pe_trailing"), "경고": col("warn"),
        "매출성장률": col("rev_growth_fy_pct"), "FCF성장률": col("fcf_growth_fy_pct"),
    })
    paste.to_csv(out_dir("finance") / "sheet_paste_us.csv", index=False, encoding="utf-8-sig")
    show = [c for c in ["ticker", "market_cap_eok", "net_debt_eok", "fcf_ttm_eok",
                        "ebit_ttm_eok", "invested_capital_eok", "op_margin_pct", "roic_pct_21", "group", "warn"] if c in df.columns]
    print()
    print(df[show].to_string(index=False))
    print(f"\n저장: {out_dir('finance')} 의 fundamentals_us.csv, sheet_paste_us.csv (단위: 억 달러)")


if __name__ == "__main__":
    main()
