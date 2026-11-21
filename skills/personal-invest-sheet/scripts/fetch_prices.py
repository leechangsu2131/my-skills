#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_prices.py  (portfolio 2단계: 가격 수집·환산)

하는 일
  1) universe.csv 를 읽는다 (보유 종목 + 벤치마크 + 환율).
  2) 야후 파이낸스에서 일간 조정종가(배당 반영)를 받는다.
  3) 거래일 달력을 맞추고, 원화/달러 기준 가격·수익률을 만든다.
  4) data/portfolio_out/ 에 CSV로 저장하고, 종목별 점검표를 출력한다.

달력 규칙
  - 주식·ETF·지수가 하나라도 거래한 평일만 쓴다.
  - 휴장일은 직전 값을 최대 5일 이어 붙인다 (그날 수익률 0).
  - BTC·환율은 그 달력의 평일 값만 쓴다. 월요일 수익률에는 주말 변동이 들어간다.

환산 규칙
  - 원화 기준: 달러 표시 자산 x USDKRW
  - 달러 기준: 원화 표시 자산 / USDKRW
  - 환율 티커(...KRW=X)와 파생 환율은 원화 표시 가격으로 취급한다.
  - 파생 티커 "A/B" 는 A 를 B 로 나눈 계열이다.
    헤알 표시 자산(예: 해외 채권)은 KRW=X/BRL=X (원달러 / 달러헤알 = 1헤알당 원)를 대용 계열로 쓴다.
    (야후 BRLKRW=X 는 하루치만 돌려주어 쓰지 않는다.)
    따라서 이자수익과 채권가격 변동은 반영되지 않는다.

사용
  pip install yfinance pandas numpy
  python fetch_prices.py                       # 3년, 원화+달러 둘 다
  python fetch_prices.py --years 5 --base KRW
  python fetch_prices.py --groups main,proxy   # 초소형 제외
  python fetch_prices.py --selftest            # 네트워크 없이 로직 점검

출력 (기본 위치: 공용 .env 의 OUTPUT_DIR/portfolio_out/)
  prices_local.csv   종목별 거래일 그대로, 표시 통화 그대로
  fx_usdkrw.csv      달력에 맞춘 원달러 환율
  prices_krw.csv     원화 기준 가격 (달력 정렬)
  returns_krw.csv    원화 기준 일간 수익률
  prices_usd.csv     달러 기준 가격
  returns_usd.csv    달러 기준 일간 수익률
  fetch_report.csv   종목별 점검표 (성공/실패, 첫 거래일, 결측률, 최대 변동일 등)
"""
import argparse
import contextlib
import io
import sys
import tempfile
import time
import zlib
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
import invest_common as _ic  # noqa: E402  (공용 .env, 종목 목록·결과 폴더 위치)

_UNI = _ic.universe_path() if (_ic.invest_dir() or _ic.os.environ.get("UNIVERSE")) else HERE / "universe.csv"
DEFAULT_UNIVERSE = _UNI
DEFAULT_OUT = _ic.out_dir("portfolio")

FFILL_LIMIT = 5      # 휴장일 이어붙이기 한도 (달력 평일 기준)
SHORT_OBS = 250      # 관측치가 이보다 적으면 SHORT 표시
STALE_DAYS = 7       # 마지막 거래일이 이보다 오래되면 STALE 표시
SUSPECT_RET = 0.40   # 하루 변동이 이보다 크면 SUSPECT 표시 (분할·데이터 오류 의심)
FX_CODE = "USDKRW"


# ---------------------------------------------------------------- 기본 도구
def is_continuous(ticker):
    """365일 거래되는 코인과 환율은 거래일 달력을 만들 때 쓰지 않는다."""
    t = ticker.upper()
    return t.endswith("-USD") or t.endswith("=X")


def quote_ccy(ticker, currency):
    """가격이 어느 통화로 표시되는지. 환율·파생 환율(KRW=X/...)은 원화 표시 가격이다."""
    t = ticker.upper()
    if t.endswith("KRW=X") or t.startswith("KRW=X/"):
        return "KRW"
    return currency.upper()


def load_universe(path, groups):
    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
    need = {"role", "group", "code", "yahoo_ticker", "currency"}
    miss = need - set(df.columns)
    if miss:
        raise SystemExit("universe.csv 에 열이 없습니다: " + ", ".join(sorted(miss)))
    df = df[~df["role"].isin(["watch", "closed"])]  # 관심·정리 종목은 재무 수집용이라 가격 분석에서 뺀다
    df = df[(df["role"] != "holding") | (df["group"].isin(groups))].copy()
    if df["code"].duplicated().any():
        dup = df.loc[df["code"].duplicated(), "code"].tolist()
        raise SystemExit("code 가 중복됩니다: " + ", ".join(dup))
    if FX_CODE not in set(df["code"]):
        raise SystemExit(FX_CODE + " 행이 universe.csv 에 필요합니다.")
    df["quote_ccy"] = [quote_ccy(t, c) for t, c in zip(df["yahoo_ticker"], df["currency"])]
    bad = df[~df["quote_ccy"].isin(["KRW", "USD"])]
    if len(bad):
        raise SystemExit("지원하지 않는 표시통화: " + ", ".join(
            f"{c}({q})" for c, q in zip(bad["code"], bad["quote_ccy"])))
    return df.reset_index(drop=True)


# ---------------------------------------------------------------- 수집
def _to_date_index(s):
    idx = pd.DatetimeIndex(s.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    out = pd.Series(np.asarray(s.values, dtype=float), index=idx.normalize())
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out.dropna()


def fetch_yahoo(ticker, start, end, retries=2):
    try:
        import yfinance as yf
    except ImportError:
        raise SystemExit("yfinance 가 없습니다. 먼저 실행: pip install yfinance")
    err = ""
    for _ in range(retries + 1):
        try:
            h = yf.Ticker(ticker).history(start=start, end=end,
                                          auto_adjust=True, actions=False)
            if h is not None and len(h) > 0 and "Close" in h:
                return _to_date_index(h["Close"]), ""
            err = "빈 결과"
        except Exception as e:  # 네트워크·티커 오류 모두 한 종목 실패로 처리
            err = f"{type(e).__name__}: {e}"
        time.sleep(1.5)
    return None, err


def fetch_all(uni, start, end, fetcher=fetch_yahoo):
    raw, errs, cache = {}, {}, {}

    def get(t):
        """티커 하나의 (시리즈, 오류). "A/B" 는 A 를 B 로 나눈 파생 계열."""
        if t not in cache:
            if "/" in t:
                a, b = t.split("/", 1)
                sa, ea = get(a)
                sb, eb = get(b)
                if sa is None or sb is None:
                    cache[t] = (None, f"구성 티커 실패 {a}:{ea or 'ok'} {b}:{eb or 'ok'}")
                else:
                    d = (sa / sb).dropna()
                    cache[t] = (d, "") if len(d) else (None, "구성 티커 날짜가 겹치지 않음")
            else:
                cache[t] = fetcher(t, start, end)
        return cache[t]

    n = len(uni)
    for i, row in enumerate(uni.itertuples(index=False), 1):
        t = row.yahoo_ticker
        s, err = get(t)
        if s is None or len(s) == 0:
            errs[row.code] = err or "데이터 없음"
            print(f"[{i:2d}/{n}] {row.code:<10} {t:<12} FAIL  {errs[row.code]}")
        else:
            raw[row.code] = s
            print(f"[{i:2d}/{n}] {row.code:<10} {t:<12} OK    "
                  f"{s.index.min().date()} ~ {s.index.max().date()}  n={len(s)}")
    return raw, errs


# ---------------------------------------------------------------- 정렬·환산
def build_calendar(uni, raw):
    sets = [raw[r.code].index for r in uni.itertuples(index=False)
            if r.code in raw and not is_continuous(r.yahoo_ticker)]
    if sets:
        cal = sets[0]
        for ix in sets[1:]:
            cal = cal.union(ix)
    else:
        cal = raw[FX_CODE].index
    cal = cal[cal.dayofweek < 5]
    return cal.sort_values()


def align(raw, cal):
    cols = {}
    for code, s in raw.items():
        full = s.reindex(s.index.union(cal)).ffill(limit=FFILL_LIMIT)
        cols[code] = full.reindex(cal)
    return pd.DataFrame(cols, index=cal)


def convert(aligned, uni, base):
    fx = aligned[FX_CODE]
    q = dict(zip(uni["code"], uni["quote_ccy"]))
    role = dict(zip(uni["code"], uni["role"]))
    out = {}
    for code in aligned.columns:
        if role[code] == "fx":
            continue
        s = aligned[code]
        if q[code] == base:
            out[code] = s
        elif base == "KRW":      # 달러 -> 원
            out[code] = s * fx
        else:                    # 원 -> 달러
            out[code] = s / fx
    return pd.DataFrame(out, index=aligned.index)


def _save(df, path):
    df.to_csv(path, encoding="utf-8-sig", index_label="date", float_format="%.10g")


# ---------------------------------------------------------------- 처리·점검표
def process(uni, raw, errs, bases, out_dir, end):
    out_dir.mkdir(parents=True, exist_ok=True)
    if FX_CODE not in raw:
        raise SystemExit("USDKRW 환율을 받지 못해 환산할 수 없습니다. "
                         "인터넷 연결과 yfinance 설치를 확인하세요. " + errs.get(FX_CODE, ""))
    cal = build_calendar(uni, raw)
    order = [c for c in uni["code"] if c in raw]
    aligned = align(raw, cal)[order]

    _save(pd.concat(raw, axis=1, sort=True)[order], out_dir / "prices_local.csv")
    _save(aligned[[FX_CODE]], out_dir / "fx_usdkrw.csv")
    for base in bases:
        px = convert(aligned, uni, base)
        ret = px.pct_change(fill_method=None).iloc[1:]
        _save(px, out_dir / f"prices_{base.lower()}.csv")
        _save(ret, out_dir / f"returns_{base.lower()}.csv")

    rows = []
    for row in uni.itertuples(index=False):
        c = row.code
        rec = {"code": c, "yahoo_ticker": row.yahoo_ticker,
               "group": row.group, "quote_ccy": row.quote_ccy}
        if c not in raw:
            rec.update(status="FAIL", flags=errs.get(c, "데이터 없음"))
        else:
            s, al = raw[c], aligned[c]
            first, last = s.index.min(), s.index.max()
            seg = al[al.index >= first]
            r = al.pct_change(fill_method=None).abs()
            mx = float(r.max()) if r.notna().any() else 0.0
            mxd = r.idxmax().date().isoformat() if r.notna().any() else ""
            flags = []
            if len(s) < SHORT_OBS:
                flags.append("SHORT")
            if (end - last.date()).days > STALE_DAYS:
                flags.append("STALE")
            if mx > SUSPECT_RET:
                flags.append("SUSPECT")
            rec.update(
                status="OK",
                first_date=first.date().isoformat(),
                last_date=last.date().isoformat(),
                n_obs=len(s),
                miss_pct=round(float(seg.isna().mean() * 100), 2) if len(seg) else 100.0,
                max_abs_ret_pct=round(mx * 100, 1),
                max_ret_date=mxd,
                flags=" ".join(flags),
            )
        rows.append(rec)
    rep = pd.DataFrame(rows)
    rep["n_obs"] = rep["n_obs"].astype("Int64")
    rep.to_csv(out_dir / "fetch_report.csv", index=False, encoding="utf-8-sig")
    return rep, cal


def print_summary(rep, cal, uni, out_dir):
    cols = ["code", "yahoo_ticker", "status", "first_date", "last_date",
            "n_obs", "miss_pct", "max_abs_ret_pct", "max_ret_date", "flags"]
    print("\n=== 종목별 점검표 ===")
    view = rep.reindex(columns=cols).astype(object)
    print(view.where(view.notna(), "").to_string(index=False))
    ok = int((rep["status"] == "OK").sum())
    print(f"\n성공 {ok} / 실패 {len(rep) - ok} / 전체 {len(rep)}")
    print(f"공통 달력: {cal.min().date()} ~ {cal.max().date()}  ({len(cal)}거래일)")
    flagged = rep[(rep["status"] == "OK") & (rep["flags"].fillna("") != "")]
    if len(flagged):
        print("확인 필요: " + ", ".join(f"{c}({f})" for c, f in zip(flagged["code"], flagged["flags"])))
    wcol = next((c for c in uni.columns if c.startswith("weight_pct")), None)
    if wcol:
        failed = set(rep.loc[rep["status"] == "FAIL", "code"])
        w = pd.to_numeric(uni[wcol], errors="coerce").fillna(0)
        mask = (uni["role"] == "holding") & uni["code"].isin(failed)
        if mask.any():
            print(f"수집 실패 보유종목 비중 합(스냅샷): {w[mask].sum():.2f}%")
    print(f"저장 위치: {out_dir}")
    print("다음: 실패/확인 필요 종목의 티커를 universe.csv 에서 고친 뒤 다시 실행하세요.")


# ---------------------------------------------------------------- 점검(selftest)
def _synthetic(ticker, start, end):
    if ticker == "FAIL1.KS":
        return None, "synthetic fail"
    days = pd.date_range(start, end, freq="D")
    wk = days[days.dayofweek < 5]
    us_hol = set(wk[3::37])
    kr_hol = set(wk[11::41])
    both = set(wk[20::97])
    t = ticker.upper()
    if t.endswith("-USD"):
        idx = days
    elif t.endswith("=X"):
        idx = wk
    elif t.endswith(".KS") or t.endswith(".KQ") or t == "^KS11":
        idx = wk[~wk.isin(list(kr_hol | both))]
    else:
        idx = wk[~wk.isin(list(us_hol | both))]
    if t == "NEW":
        idx = idx[len(idx) * 6 // 10:]
    base = {"KRW=X": 1400.0, "BRL=X": 5.5, "BTC-USD": 90000.0,
            "^KS11": 2500.0, "^GSPC": 6000.0}.get(t, 20000.0 if t[-3:] in (".KS", ".KQ") else 100.0)
    vol = 0.03 if t == "BTC-USD" else (0.004 if t.endswith("=X") else 0.012)
    rng = np.random.default_rng(zlib.crc32(t.encode()))
    vals = base * np.exp(np.cumsum(rng.normal(0, vol, len(idx))))
    return pd.Series(vals, index=idx), ""


def selftest():
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    mini = (
        "role,group,code,name,yahoo_ticker,currency,weight_pct_x\n"
        "holding,main,AAA,a,AAA,USD,10\n"
        "holding,main,BBB,b,BBB,USD,10\n"
        "holding,main,KR1,k,111111.KS,KRW,10\n"
        "holding,main,KQ1,q,222222.KQ,KRW,10\n"
        "holding,main,BTC,c,BTC-USD,USD,10\n"
        "holding,proxy,BRLPROXY,p,KRW=X/BRL=X,BRL,10\n"
        "holding,micro,NEW,n,NEW,USD,1\n"
        "holding,main,FAIL1,f,FAIL1.KS,KRW,3\n"
        "benchmark,ref,KOSPI,i,^KS11,KRW,\n"
        "benchmark,ref,SP500,i,^GSPC,USD,\n"
        "fx,ref,USDKRW,x,KRW=X,KRW,\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        up = tmp / "u.csv"
        up.write_text(mini, encoding="utf-8-sig")
        uni = load_universe(up, ["main", "proxy", "micro"])
        check(len(uni) == 11, "universe 행 수")
        check(uni.loc[uni.code == "BRLPROXY", "quote_ccy"].iloc[0] == "KRW",
              "BRLKRW 는 원화 표시 가격으로 취급해야 함")

        end = date(2026, 11, 13)
        start = end - timedelta(days=900)
        raw, errs = fetch_all(uni, start, end, fetcher=_synthetic)
        check("FAIL1" in errs and "FAIL1" not in raw, "실패 종목이 errs 에만 있어야 함")
        # 파생 티커: 1헤알당 원 = 원달러 / 달러헤알
        brl = _synthetic("BRL=X", start, end)[0]
        dd = raw["BRLPROXY"].index[50]
        check(abs(raw["BRLPROXY"][dd] - raw["USDKRW"][dd] / brl[dd]) < 1e-9 * raw["BRLPROXY"][dd],
              "파생 티커 계산(KRW=X/BRL=X)")

        def _no_brl(t, s_, e_):
            return (None, "x") if t == "BRL=X" else _synthetic(t, s_, e_)
        with contextlib.redirect_stdout(io.StringIO()):
            _, errs2 = fetch_all(uni, start, end, fetcher=_no_brl)
        check("BRLPROXY" in errs2, "구성 티커가 실패하면 파생 종목도 실패해야 함")
        # BBB 에 10거래일짜리 데이터 공백을 만든다 (이어붙이기 한도 시험)
        bidx = raw["BBB"].index
        raw["BBB"] = raw["BBB"].drop(bidx[300:310])

        out = tmp / "out"
        rep, cal = process(uni, raw, errs, ["KRW", "USD"], out, end)
        for f in ["prices_local", "fx_usdkrw", "prices_krw", "returns_krw",
                  "prices_usd", "returns_usd", "fetch_report"]:
            check((out / f"{f}.csv").exists(), f + ".csv 없음")

        pk = pd.read_csv(out / "prices_krw.csv", index_col=0, parse_dates=True, encoding="utf-8-sig")
        pu = pd.read_csv(out / "prices_usd.csv", index_col=0, parse_dates=True, encoding="utf-8-sig")
        rk = pd.read_csv(out / "returns_krw.csv", index_col=0, parse_dates=True, encoding="utf-8-sig")
        ru = pd.read_csv(out / "returns_usd.csv", index_col=0, parse_dates=True, encoding="utf-8-sig")
        fx = pd.read_csv(out / "fx_usdkrw.csv", index_col=0, parse_dates=True, encoding="utf-8-sig")["USDKRW"]

        check((pk.index.dayofweek < 5).all(), "달력에 주말이 있음")
        eq_dates = raw["AAA"].index.union(raw["KR1"].index).union(raw["BBB"].index)\
            .union(raw["KQ1"].index).union(raw["KOSPI"].index).union(raw["SP500"].index).union(raw["NEW"].index)
        eq_dates = eq_dates[eq_dates.dayofweek < 5]
        check(pk.index.equals(eq_dates.sort_values()), "달력 = 주식류 거래일 합집합(평일)이어야 함")
        check("FAIL1" not in pk.columns and "USDKRW" not in pk.columns, "표에 실패 종목·환율이 들어감")
        check(len(rk) == len(pk) - 1 and len(ru) == len(pu) - 1, "수익률 행 수")

        # 달러 자산 -> 원화
        d = [x for x in raw["AAA"].index if x in pk.index][50]
        check(abs(pk.loc[d, "AAA"] - raw["AAA"][d] * fx[d]) < 1e-6 * pk.loc[d, "AAA"], "AAA 원화 환산 틀림")
        check(abs(pu.loc[d, "AAA"] - raw["AAA"][d]) < 1e-9 * pu.loc[d, "AAA"], "AAA 달러 기준은 원본이어야 함")
        # 원화 자산 -> 달러
        d2 = [x for x in raw["KR1"].index if x in pk.index][50]
        check(abs(pk.loc[d2, "KR1"] - raw["KR1"][d2]) < 1e-6 * pk.loc[d2, "KR1"], "KR1 원화 기준은 원본이어야 함")
        check(abs(pu.loc[d2, "KR1"] * fx[d2] - pk.loc[d2, "KR1"]) < 1e-6 * pk.loc[d2, "KR1"], "KR1 달러 환산 틀림")
        # BRLPROXY 대용
        d3 = [x for x in raw["BRLPROXY"].index if x in pk.index][50]
        check(abs(pk.loc[d3, "BRLPROXY"] - raw["BRLPROXY"][d3]) < 1e-6 * pk.loc[d3, "BRLPROXY"], "BRLPROXY 원화")
        check(abs(pu.loc[d3, "BRLPROXY"] - raw["BRLPROXY"][d3] / fx[d3]) < 1e-6 * pu.loc[d3, "BRLPROXY"], "BRLPROXY 달러")
        # 휴장일 이어붙이기: 주식 시장 휴장일에도 값이 있어야 함(구멍 없음)
        a = pk["AAA"]
        seg = a[a.first_valid_index():]
        check(not seg.isna().any(), "AAA 중간에 결측 구멍")
        # 긴 공백: 앞 5일만 이어붙이고 나머지는 비워둔다
        rows_gap = pk.index[(pk.index > bidx[299]) & (pk.index < bidx[310])]
        check(len(rows_gap) >= 10, "공백 구간 행 수")
        check(pk.loc[rows_gap[:5], "BBB"].notna().all(), "공백 앞 5일은 이어붙여야 함")
        check(pk.loc[rows_gap[5:], "BBB"].isna().all(), "공백 5일 초과분은 비워야 함")
        # 짧은 이력
        check(pk["NEW"].first_valid_index() > pk.index[0], "NEW 는 앞부분이 비어 있어야 함")
        check(pd.isna(rk["NEW"].iloc[0]), "NEW 초기 수익률은 NaN 이어야 함")
        # BTC 월요일 수익률에 주말 변동 포함
        btc = raw["BTC"]
        n_chk = 0
        for i in range(1, len(pk.index)):
            m, p = pk.index[i], pk.index[i - 1]
            if m.dayofweek == 0 and m in btc.index and p in btc.index:
                exp = btc[m] / btc[p] - 1
                check(abs(ru.loc[m, "BTC"] - exp) < 1e-9, "BTC 월요일 수익률")
                n_chk += 1
        check(n_chk > 10, "BTC 월요일 검증 표본 부족")
        # 점검표
        r = rep.set_index("code")
        check(r.loc["FAIL1", "status"] == "FAIL", "FAIL1 상태")
        check("SHORT" not in r.loc["AAA", "flags"], "AAA 는 SHORT 아님")
        check(r.loc["AAA", "status"] == "OK", "AAA 상태")
        check(r.loc["AAA", "max_ret_date"] == ru["AAA"].abs().idxmax().date().isoformat(),
              "최대 변동일")
        print_summary(rep, cal, uni, out)

    print()
    if fails:
        print("SELFTEST 실패:")
        for f in fails:
            print("  - " + f)
        return 1
    print("SELFTEST 통과: 달력 정렬, 원화/달러 환산, BRLPROXY 대용, BTC 주말 처리, 실패 종목 처리")
    return 0


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="포트폴리오 가격 수집·환산")
    ap.add_argument("--universe", default=str(DEFAULT_UNIVERSE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--years", type=float, default=3.0, help="수집 기간(년), 기본 3")
    ap.add_argument("--groups", default="main,proxy,micro",
                    help="포함할 보유 그룹, 쉼표 구분 (기본: main,proxy,micro)")
    ap.add_argument("--base", choices=["KRW", "USD", "both"], default="both")
    ap.add_argument("--selftest", action="store_true", help="네트워크 없이 로직 점검")
    args = ap.parse_args()

    if args.selftest:
        sys.exit(selftest())

    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    uni = load_universe(Path(args.universe), groups)
    end = date.today()
    start = end - timedelta(days=int(365.25 * args.years))
    bases = ["KRW", "USD"] if args.base == "both" else [args.base]

    print(f"종목 {len(uni)}개, 기간 {start} ~ {end}, 기준통화 {'+'.join(bases)}")
    raw, errs = fetch_all(uni, start, end + timedelta(days=1))
    out_dir = Path(args.out)
    rep, cal = process(uni, raw, errs, bases, out_dir, end)
    print_summary(rep, cal, uni, out_dir)


if __name__ == "__main__":
    main()
