"""연간 FCF 이력(최근 5개 회계연도)을 모아 평균을 구하는 스크립트 (사용자 PC에서 실행)

준비
  pip install yfinance pandas requests
  한국 종목은 fetch_fundamentals_kr.py 와 같은 폴더에서 실행 (DART 키는 거기와 같은 방식:
  환경변수 DART_API_KEY 또는 .env). 키가 없으면 한국 종목은 건너뛰고 미국만 수집한다.

사용: python fetch_fcf_history.py   →  fcf_history.csv

FCF = 영업현금흐름 - CapEx, 단위는 시트와 같은 '억' (미국은 억 달러, 한국은 억 원)
평균은 5년 평균을 우선 쓰고, 5년치가 안 되면 3년 평균, 3년도 안 되면 빈칸.
"""
import csv
import datetime as dt
import os
import sys

import yfinance as yf

from invest_common import out_dir, stocks  # noqa: E402  (종목은 universe.csv, 공용 .env 도 여기서 읽음)

_US, _KR = stocks("USD"), stocks("KRW")
US = [s["code"] for s in _US]
KR = [s["code"] for s in _KR]
FIN = {s["code"] for s in stocks("USD", include_closed=True) + stocks("KRW", include_closed=True) if s["fin"]}  # 금융·지주: FCF 개념이 맞지 않음(참고만)
EOK = 1e8
NYEARS = 5


def pick_row(df, names):
    for n in names:
        if n in df.index:
            return df.loc[n]
    return None


def us_history(code):
    """[(회계연도, FCF억)] 최신 -> 과거"""
    t = yf.Ticker(code.replace(".", "-"))
    cf = t.cashflow  # 연간, 열 = 회계연도 말 날짜(최신 먼저)
    if cf is None or cf.empty:
        return []
    ocf = pick_row(cf, ["Operating Cash Flow", "Total Cash From Operating Activities"])
    capex = pick_row(cf, ["Capital Expenditure", "Capital Expenditures"])
    fcf_row = pick_row(cf, ["Free Cash Flow"])
    out = []
    for col in cf.columns:
        v = None
        if ocf is not None and capex is not None and ocf[col] == ocf[col] and capex[col] == capex[col]:
            c = float(capex[col])
            v = float(ocf[col]) + c if c <= 0 else float(ocf[col]) - c
        elif fcf_row is not None and fcf_row[col] == fcf_row[col]:
            v = float(fcf_row[col])
        if v is not None:
            out.append((col.year, round(v / EOK, 2)))
    return out


def kr_history(key, corp_codes, kr, code, today):
    corp = corp_codes.get(code)
    if not corp:
        return []
    y = today.year
    vals = {}
    # 사업보고서 한 건에 당기·전기·전전기가 들어 있다 -> 2번 호출로 6개년
    for bsns in (y - 1, y - 4):
        fs, rows = kr.fetch_report(key, corp, bsns, "11011")
        if not rows:
            continue
        o = kr.find(rows, "CF", kr.OCF)
        c = kr.find(rows, "CF", kr.CAPEX)
        if o is None or c is None:
            continue
        for k, yr in (("thstrm_amount", bsns), ("frmtrm_amount", bsns - 1), ("bfefrmtrm_amount", bsns - 2)):
            ov, cv = kr.num(o.get(k)), kr.num(c.get(k))
            if ov is not None and cv is not None and yr not in vals:
                vals[yr] = round((ov - abs(cv)) / EOK, 2)
    return sorted(vals.items(), reverse=True)


def row_from(code, hist, note=""):
    hist = hist[:NYEARS]
    fcfs = [v for _, v in hist]
    r = {"ticker": code, "n_years": len(fcfs)}
    for i in range(NYEARS):
        r[f"fy{i}"] = hist[i][0] if i < len(hist) else ""
        r[f"fcf{i}"] = fcfs[i] if i < len(fcfs) else ""
    avg5 = round(sum(fcfs[:5]) / 5, 2) if len(fcfs) >= 5 else ""
    avg3 = round(sum(fcfs[:3]) / 3, 2) if len(fcfs) >= 3 else ""
    r["avg5"], r["avg3"] = avg5, avg3
    r["avg_used"] = avg5 if avg5 != "" else avg3
    r["basis"] = "5년" if avg5 != "" else ("3년" if avg3 != "" else "")
    if code in FIN:
        note = (note + ";금융·지주:FCF 참고불가").strip(";")
    r["note"] = note
    return r


def main():
    today = dt.date.today()
    out = []
    for code in US:
        try:
            h = us_history(code)
            out.append(row_from(code, h, "" if h else "이력없음"))
            print(code, "OK", len(h), "년")
        except Exception as e:  # noqa: BLE001
            print(code, "실패", e)
            out.append(row_from(code, [], f"실패:{type(e).__name__}"))
    try:
        import fetch_fundamentals_kr as kr
        key = kr.get_key()
        corp_codes = kr.load_corp_codes(key)
        for code in KR:
            try:
                h = kr_history(key, corp_codes, kr, code, today)
                out.append(row_from(code, h, "" if h else "이력없음"))
                print(code, "OK(KR)", len(h), "년")
            except SystemExit:
                raise
            except Exception as e:  # noqa: BLE001
                print(code, "실패", e)
                out.append(row_from(code, [], f"실패:{type(e).__name__}"))
    except (ImportError, SystemExit) as e:
        print("한국 종목은 건너뜀:", e)
    cols = ["ticker", "n_years"] + [f"{p}{i}" for i in range(NYEARS) for p in ("fy", "fcf")] + \
           ["avg5", "avg3", "avg_used", "basis", "note"]
    with open(out_dir("finance") / "fcf_history.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print(out_dir("finance") / "fcf_history.csv", "저장 (", len(out), "행 )")


if __name__ == "__main__":
    sys.exit(main())
