"""raw data 탭의 yahoo 행을 최신화하는 스크립트 (사용자 PC에서 실행)
사용: pip install yfinance pandas  →  python fetch_rawdata_yahoo.py
출력: rawdata_yahoo.csv  (raw data 탭 A:Z 열 순서와 동일, 헤더 없음 아님: 헤더 포함)
시트에는 각 티커의 'yahoo' 행(첫 행)에 값으로 붙여넣는다.
"""
import csv, datetime as dt
import yfinance as yf

from invest_common import out_dir, stocks  # noqa: E402  (종목은 universe.csv, 공용 .env 도 여기서 읽음)

# 미국: 시트 티커 그대로 (야후용 변환은 아래에서 함). 한국: 코드 -> 야후 티커(KS=코스피, KQ=코스닥)
US = [s["code"] for s in stocks("USD")]
KR = {s["code"]: s["yahoo"] for s in stocks("KRW")}

COLS = ["ticker", "source", "as_of", "pe_ratio", "ps_ratio", "pb_ratio", "ev_ebitda",
        "fwd_pe_ntm", "fwd_pe_fy", "pe_avg_3y", "pe_vs_3y", "fair_value", "mos",
        "fin_strength", "profit_rank", "piotroski", "altman_z", "roic", "fcf_margin",
        "op_margin", "ev_fcf", "roiic_3y", "rev_cagr_1y", "rev_cagr_2y", "rev_cagr_3y",
        "downside_price(하방가격)"]


def r(x, n=4):
    try:
        if x is None or x != x:
            return ""
        return round(float(x), n)
    except Exception:
        return ""


def rev_series(t):
    """연간 매출(최신→과거). 실패 시 빈 리스트."""
    try:
        inc = t.financials
        if inc is None or inc.empty:
            return []
        for k in ("Total Revenue", "Operating Revenue"):
            if k in inc.index:
                return [float(v) for v in inc.loc[k].dropna().tolist()]
    except Exception:
        pass
    return []


def cagr(series, years):
    # series: 최신→과거. years년 CAGR = (최신/years년 전)^(1/years)-1
    if len(series) <= years or series[years] <= 0:
        return ""
    return r((series[0] / series[years]) ** (1.0 / years) - 1, 10)


def row_for(code, ysym, is_kr):
    t = yf.Ticker(ysym)
    info = {}
    try:
        info = t.info or {}
    except Exception:
        pass
    rs = rev_series(t)
    today = dt.date.today().isoformat()
    op_m = info.get("operatingMargins")
    row = {c: "" for c in COLS}
    row.update({
        "ticker": code, "source": "yahoo", "as_of": today,
        "pe_ratio": r(info.get("trailingPE")),
        "ps_ratio": r(info.get("priceToSalesTrailing12Months")),
        "pb_ratio": r(info.get("priceToBook")),
        "ev_ebitda": r(info.get("enterpriseToEbitda"), 3),
        "fwd_pe_ntm": r(info.get("forwardPE")),
        # 애널리스트 평균 목표가 / 최저 목표가
        "fair_value": r(info.get("targetMeanPrice"), 4),
        "op_margin": r(op_m * 100, 3) if op_m not in (None, "") else "",
        "rev_cagr_1y": cagr(rs, 1), "rev_cagr_2y": cagr(rs, 2), "rev_cagr_3y": cagr(rs, 3),
        "downside_price(하방가격)": r(info.get("targetLowPrice"), 3),
    })
    warn = []
    if not rs:
        warn.append("매출 이력 없음")
    if not info.get("forwardPE"):
        warn.append("선행PER 없음")
    if not info.get("targetLowPrice"):
        warn.append("목표가 없음")
    return row, warn


def main():
    out = []
    for code in US:
        try:
            row, w = row_for(code, code.replace(".", "-"), False)
            out.append(row)
            print(code, "OK", ";".join(w))
        except Exception as e:
            print(code, "실패", e)
    for code, ysym in KR.items():
        try:
            row, w = row_for(code, ysym, True)
            out.append(row)
            print(code, "OK(KR)", ";".join(w))
        except Exception as e:
            print(code, "실패", e)
    with open(out_dir("finance") / "rawdata_yahoo.csv", "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.DictWriter(f, fieldnames=COLS)
        wr.writeheader()
        wr.writerows(out)
    print(out_dir("finance") / "rawdata_yahoo.csv", "저장 (", len(out), "행 )")


if __name__ == "__main__":
    main()
