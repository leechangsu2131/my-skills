"""연간 매출·영업이익 이력(최근 5개 회계연도) -> 영업마진 평균/최저/최고, 매출성장률 (사용자 PC에서 실행)

준비
  pip install yfinance pandas requests
  한국 종목은 fetch_fundamentals_kr.py 와 같은 폴더에서 실행 (DART 키: 환경변수 DART_API_KEY 또는 .env).
  키가 없으면 한국 종목은 건너뛰고 미국만 수집한다.

사용: python fetch_margin_history.py   ->  margin_history.csv
  이 CSV를 narrative_dcf.html 의 'CSV 불러오기'에 올리면 입력 시드가 종목 자체 이력으로 바뀐다.

단위: 억 (미국은 억 달러, 한국은 억 원).  마진 = 영업이익 / 매출 (%)
yfinance 연간 손익은 보통 최근 4~5개년만 준다. 4년 미만이면 n_years 로 알려 주고 시드는 있는 만큼만 쓴다.
"""
import csv
import datetime as dt
import sys

import yfinance as yf

from invest_common import out_dir, stocks  # noqa: E402  (종목은 universe.csv, 공용 .env 도 여기서 읽음)

_US, _KR = stocks("USD"), stocks("KRW")
US = [s["code"] for s in _US]
KR = [s["code"] for s in _KR]
FIN = {s["code"] for s in stocks("USD", include_closed=True) + stocks("KRW", include_closed=True) if s["fin"]}
EOK = 1e8
NY = 5


def us_hist(code):
    t = yf.Ticker(code.replace(".", "-"))
    st = t.income_stmt
    if st is None or st.empty:
        return []
    rev = next((st.loc[n] for n in ("Total Revenue", "Operating Revenue") if n in st.index), None)
    op = next((st.loc[n] for n in ("Operating Income", "Total Operating Income As Reported", "EBIT") if n in st.index), None)
    if rev is None or op is None:
        return []
    out = []
    for c in st.columns:
        r, o = rev[c], op[c]
        if r == r and o == o and float(r) > 0:
            out.append((c.year, round(float(r) / EOK, 2), round(float(o) / EOK, 2)))
    return out


def kr_hist(key, corp_codes, kr, code, today):
    corp = corp_codes.get(code)
    if not corp:
        return []
    y = today.year
    vals = {}
    for bsns in (y - 1, y - 4):
        fs, rows = kr.fetch_report(key, corp, bsns, "11011")
        if not rows:
            continue
        r = kr.find(rows, "IS", kr.REV)
        o = kr.find(rows, "IS", kr.OPINC)
        if r is None or o is None:
            continue
        for k, yr in (("thstrm_amount", bsns), ("frmtrm_amount", bsns - 1), ("bfefrmtrm_amount", bsns - 2)):
            rv, ov = kr.num(r.get(k)), kr.num(o.get(k))
            if rv and ov is not None and yr not in vals:
                vals[yr] = (round(rv / EOK, 2), round(ov / EOK, 2))
    return [(yr, a, b) for yr, (a, b) in sorted(vals.items(), reverse=True)]


def row(code, hist, note=""):
    hist = hist[:NY]
    r = {"ticker": code, "n_years": len(hist)}
    ms = []
    for i in range(NY):
        if i < len(hist):
            fy, rv, op = hist[i]
            m = round(op / rv * 100, 2)
            ms.append(m)
            r.update({f"fy{i}": fy, f"rev{i}": rv, f"op{i}": op, f"m{i}": m})
        else:
            r.update({f"fy{i}": "", f"rev{i}": "", f"op{i}": "", f"m{i}": ""})
    r["m_avg"] = round(sum(ms) / len(ms), 2) if ms else ""
    r["m_min"] = min(ms) if ms else ""
    r["m_max"] = max(ms) if ms else ""
    # 연평균 매출성장률 (가장 오래된 해 -> 최신 해)
    if len(hist) >= 3 and hist[-1][1] > 0 and hist[0][1] > 0:
        n = len(hist) - 1
        r["rev_cagr"] = round(((hist[0][1] / hist[-1][1]) ** (1 / n) - 1) * 100, 2)
    else:
        r["rev_cagr"] = ""
    if code in FIN:
        note = (note + ";금융·지주:영업마진 참고불가").strip(";")
    r["note"] = note
    return r


def main():
    today = dt.date.today()
    out = []
    for code in US:
        try:
            h = us_hist(code)
            out.append(row(code, h, "" if h else "이력없음"))
            print(code, "OK", len(h), "년")
        except Exception as e:  # noqa: BLE001
            print(code, "실패", e)
            out.append(row(code, [], f"실패:{type(e).__name__}"))
    try:
        import fetch_fundamentals_kr as kr
        key = kr.get_key()
        cc = kr.load_corp_codes(key)
        for code in KR:
            try:
                h = kr_hist(key, cc, kr, code, today)
                out.append(row(code, h, "" if h else "이력없음"))
                print(code, "OK(KR)", len(h), "년")
            except SystemExit:
                raise
            except Exception as e:  # noqa: BLE001
                print(code, "실패", e)
                out.append(row(code, [], f"실패:{type(e).__name__}"))
    except (ImportError, SystemExit) as e:
        print("한국 종목은 건너뜀:", e)
    cols = ["ticker", "n_years"] + [f"{p}{i}" for i in range(NY) for p in ("fy", "rev", "op", "m")] + \
           ["m_avg", "m_min", "m_max", "rev_cagr", "note"]
    with open(out_dir("finance") / "margin_history.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print(out_dir("finance") / "margin_history.csv", "저장 (", len(out), "행 )")


if __name__ == "__main__":
    sys.exit(main())
