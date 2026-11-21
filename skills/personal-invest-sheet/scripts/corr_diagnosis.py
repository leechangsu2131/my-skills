#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
corr_diagnosis.py  (portfolio 3단계-1: 상관 진단)

fetch_prices.py 가 만든 일간 수익률(returns_krw.csv, returns_usd.csv)로
보유 종목들이 실제로 얼마나 같이 움직이는지 진단한다.

만드는 것
  1) 상관행렬: 피어슨(일간·주간)과 스피어만(일간). 종목 쌍마다 겹치는 구간만 쓴다.
  2) 시나리오: 전체 기간(all)과 특정 월을 뺀 기간(기본: 2026-07, 코스피 급등락 달).
  3) 기준통화: 원화(KRW)와 달러(USD)를 나란히.
  4) 롤링 평균 상관(60일·120일)과 상관이 높은 쌍의 롤링 상관.
  5) 상관이 높은 묶음(평균연결 군집, 스피어만 일간·피어슨 주간 두 기준)과 유효 독립 자산 수.
  6) 벤치마크(KOSPI, S&P500)와의 상관.
  7) 환율 영향: 종목별 원화/달러 변동성 차이와 환율과의 상관.
  8) 요약 텍스트 corr_summary.txt

읽는 것은 수익률 CSV와 universe.csv 뿐이고, 시트는 건드리지 않는다.

주의해서 읽을 점
  - 한국장이 닫힌 뒤 미국장이 열리는 시차 때문에, 한국-미국 종목의 일간 상관은
    실제보다 낮게 나오는 경향이 있다. 주간 상관과 비교해서 본다.
  - 피어슨은 극단값 하루에 크게 흔들린다. 스피어만(순위)과 월 제외 시나리오를 같이 본다.
  - 유효 독립 자산 수는 상관행렬만으로 계산한 진단값이다 (비중·변동성 미반영).
    비중과 위험까지 반영한 분석은 다음 단계(risk_mpt.py)에서 한다.

사용
  python corr_diagnosis.py                       # 원화+달러, 2026-07 제외 비교
  python corr_diagnosis.py --exclude 2026-07,2026-08
  python corr_diagnosis.py --exclude none        # 제외 시나리오 없이
  python corr_diagnosis.py --groups main,proxy   # 초소형 제외
  python corr_diagnosis.py --min-weeks 150       # 최근 상장(150주 미만) 종목을 빼고 계산 -> corr_w150 폴더
  python corr_diagnosis.py --selftest            # 가짜 데이터로 로직 점검

출력 (기본 위치: OUTPUT_DIR/portfolio_out/corr/)
  corr_<방법>_<주기>_<통화>_<시나리오>.csv   상관행렬 (보유 종목 + 벤치마크)
  corr_neff.csv                 유효 독립 자산 수·평균 상관 (행렬별)
  corr_clusters.csv             상관이 높은 묶음
  corr_rolling_avg_<통화>.csv   롤링 평균 상관
  corr_rolling_pairs_<통화>.csv 상관이 가장 높은 쌍의 롤링 상관
  corr_vs_benchmarks.csv        종목별 KOSPI·S&P500 상관
  fx_effect.csv                 종목별 환율 영향
  corr_summary.txt              위 내용의 요약
"""
import argparse
import sys
import tempfile
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
import invest_common as _ic  # noqa: E402  (공용 .env, 종목 목록·결과 폴더 위치)

_UNI = _ic.universe_path() if (_ic.invest_dir() or _ic.os.environ.get("UNIVERSE")) else HERE / "universe.csv"
DEFAULT_DATA = _ic.out_dir("portfolio")
DEFAULT_UNIVERSE = _UNI

MIN_OBS_D = 120      # 일간 상관을 내려면 쌍마다 겹치는 관측치가 이만큼 필요
MIN_OBS_W = 26       # 주간 상관의 최소 관측 주 수
ROLL_STEP = 5        # 롤링 평균 상관은 5거래일마다 계산
ANN = 252
METHODS = [("pearson", "daily"), ("spearman", "daily"), ("pearson", "weekly")]


# ---------------------------------------------------------------- 기본 도구
def quote_ccy(ticker, currency):
    t = ticker.upper()
    if t.endswith("KRW=X") or t.startswith("KRW=X/"):
        return "KRW"
    return currency.upper()


def scenario_label(months):
    return "ex" + "_".join(m.replace("-", "") for m in months)


def apply_exclusion(r, months):
    """제외할 달의 수익률을 NaN 으로 만든다 (행은 그대로 둔다)."""
    if not months:
        return r
    mask = np.asarray(r.index.to_period("M").astype(str).isin(months))
    out = r.copy()
    out.loc[mask, :] = np.nan
    return out


def to_weekly(r):
    """일간 수익률을 금요일 기준 주간 수익률로 복리 합성한다. 결측이 낀 주는 NaN."""
    keys = r.index.to_period("W-FRI")
    codes, uniques = pd.factorize(keys)
    vals = r.values.astype(float)
    out = np.empty((len(uniques), vals.shape[1]))
    for k in range(len(uniques)):
        block = vals[codes == k]
        out[k] = np.where(np.isnan(block).any(axis=0), np.nan, np.prod(1.0 + block, axis=0) - 1.0)
    return pd.DataFrame(out, index=uniques.to_timestamp(how="end").normalize(), columns=r.columns)


def corr_matrices(r, cols):
    d = r[cols]
    w = to_weekly(d)
    return {
        ("pearson", "daily"): d.corr(method="pearson", min_periods=MIN_OBS_D),
        ("spearman", "daily"): d.corr(method="spearman", min_periods=MIN_OBS_D),
        ("pearson", "weekly"): w.corr(method="pearson", min_periods=MIN_OBS_W),
    }


def avg_offdiag(c, w=None):
    """대각선을 뺀 평균 상관. w 를 주면 비중곱 가중평균."""
    v = np.asarray(c.values, dtype=float)
    iu = np.triu_indices(v.shape[0], 1)
    x = v[iu]
    ok = ~np.isnan(x)
    if not ok.any():
        return float("nan")
    if w is None:
        return float(x[ok].mean())
    ww = (np.asarray(w)[:, None] * np.asarray(w)[None, :])[iu]
    s = ww[ok].sum()
    return float((x[ok] * ww[ok]).sum() / s) if s > 0 else float("nan")


def usable_cols(c):
    """상관이 비어 있는 쌍이 없을 때까지, 결측이 가장 많은 종목부터 하나씩 뺀다."""
    cols = list(c.columns)
    v = np.asarray(c.values, dtype=float).copy()
    np.fill_diagonal(v, 1.0)
    keep = list(range(len(cols)))
    while keep:
        nn = np.isnan(v[np.ix_(keep, keep)]).sum(axis=0)
        if nn.max() == 0:
            break
        keep.pop(int(nn.argmax()))
    ok = [cols[i] for i in keep]
    return ok, [x for x in cols if x not in ok]


def eff_bets(c):
    """상관행렬 고유값 기준 유효 독립 자산 수(참여비율), 1번 요인 비중, 80% 설명 요인 수."""
    ok, bad = usable_cols(c)
    sub = c.loc[ok, ok].values.astype(float)
    lam = np.clip(np.linalg.eigvalsh(sub), 0.0, None)[::-1]
    n_eff = float(lam.sum() ** 2 / (lam ** 2).sum())
    pc1 = float(lam[0] / lam.sum())
    n80 = int(np.searchsorted(np.cumsum(lam) / lam.sum(), 0.8) + 1)
    return n_eff, pc1, n80, len(ok), bad


def cluster_assign(c, rho_cut):
    """평균연결 군집. 묶음 안 평균 거리가 rho_cut 에 해당하는 거리 이하일 때만 합친다."""
    ok, bad = usable_cols(c)
    sub = np.clip(c.loc[ok, ok].values.astype(float), -1.0, 1.0)
    dist = np.sqrt(0.5 * (1.0 - sub))
    cut = np.sqrt(0.5 * (1.0 - rho_cut))
    cl = [[i] for i in range(len(ok))]
    while len(cl) > 1:
        best = None
        for a in range(len(cl)):
            for b in range(a + 1, len(cl)):
                dd = dist[np.ix_(cl[a], cl[b])].mean()
                if best is None or dd < best[0]:
                    best = (dd, a, b)
        if best[0] > cut:
            break
        _, a, b = best
        cl[a] = cl[a] + cl[b]
        del cl[b]
    groups = [[ok[i] for i in g] for g in cl] + [[x] for x in bad]
    groups.sort(key=lambda g: (-len(g), g[0]))
    return groups


def cluster_table(groups, c, hold, scen, base, rho_cut, basis="spearman_daily"):
    wmap = dict(zip(hold["code"], hold["w"]))
    smap = dict(zip(hold["code"], hold["sector"]))
    rows = []
    for k, g in enumerate(groups, 1):
        if len(g) > 1:
            sub = c.loc[g, g].values.astype(float)
            iu = np.triu_indices(len(g), 1)
            intra = float(np.nanmean(sub[iu]))
        else:
            intra = float("nan")
        rows.append({
            "base": base, "scenario": scen, "basis": basis, "rho_cut": rho_cut, "cluster": k, "n": len(g),
            "members": " ".join(sorted(g, key=lambda x: -wmap.get(x, 0))),
            "weight_pct": round(sum(wmap.get(x, 0) for x in g), 2),
            "avg_intra_corr": round(intra, 3) if intra == intra else "",
            "sectors": " / ".join(sorted({smap.get(x, "") for x in g if smap.get(x, "")})),
        })
    return pd.DataFrame(rows)


def rolling_avg_corr(r, cols, wvec, window, step=ROLL_STEP, method="spearman"):
    d = r[cols]
    n = len(d)
    minp = int(window * 0.8)
    ends = list(range(window, n + 1, step))
    if not ends or ends[-1] != n:
        ends.append(n)
    rows = []
    for e in ends:
        c = d.iloc[e - window:e].corr(method=method, min_periods=minp)
        rows.append((d.index[e - 1], avg_offdiag(c), avg_offdiag(c, wvec)))
    out = pd.DataFrame(rows, columns=["date", f"avg_corr_{window}", f"wavg_corr_{window}"])
    return out.set_index("date")


def top_pairs(c, cols, k):
    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            v = c.loc[cols[i], cols[j]]
            if v == v:
                pairs.append((cols[i], cols[j], float(v)))
    pairs.sort(key=lambda x: -x[2])
    return pairs[:k]


def fx_effect(rets, fx_ret, hold, ann=ANN):
    rows = []
    for h in hold.itertuples(index=False):
        c = h.code
        if c not in rets["KRW"].columns or c not in rets["USD"].columns:
            continue
        rk, ru = rets["KRW"][c], rets["USD"][c]
        local = ru if h.qccy == "USD" else rk
        vk, vu = rk.std() * np.sqrt(ann) * 100, ru.std() * np.sqrt(ann) * 100
        rows.append({
            "code": c, "local_ccy": h.qccy, "weight_pct": h.w,
            "vol_krw_pct": round(float(vk), 1), "vol_usd_pct": round(float(vu), 1),
            "vol_diff_pct": round(float(vk - vu), 1),
            "corr_local_vs_usdkrw": round(float(local.corr(fx_ret)), 3),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 실행
def run(data_dir, universe_path, out_dir, bases, exclude, cluster_rho, groups, min_weeks=0):
    out_dir.mkdir(parents=True, exist_ok=True)
    uni = pd.read_csv(universe_path, encoding="utf-8-sig", dtype=str).fillna("")
    wcol = next((c for c in uni.columns if c.startswith("weight_pct")), None)
    uni["w"] = pd.to_numeric(uni[wcol], errors="coerce").fillna(0.0) if wcol else 0.0
    if "sector" not in uni.columns:
        uni["sector"] = ""
    hold = uni[(uni["role"] == "holding") & uni["group"].isin(groups)].reset_index(drop=True)
    hold["qccy"] = [quote_ccy(t, c) for t, c in zip(hold["yahoo_ticker"], hold["currency"])]
    bench_codes = list(uni.loc[uni["role"] == "benchmark", "code"])

    rets = {}
    for b in bases:
        p = data_dir / f"returns_{b.lower()}.csv"
        if not p.exists():
            raise SystemExit(f"{p} 가 없습니다. 먼저 fetch_prices.py 를 실행하세요.")
        rets[b] = pd.read_csv(p, index_col=0, parse_dates=True, encoding="utf-8-sig")

    dropped = {}
    if min_weeks > 0:        # 최근 상장 등으로 주 수가 모자라는 종목은 아예 뺀다
        for b in bases:
            nw = to_weekly(rets[b]).notna().sum()
            for c in hold["code"]:
                if c in nw.index and nw[c] < min_weeks:
                    dropped[c] = int(nw[c])
        hold = hold[~hold["code"].isin(dropped)].reset_index(drop=True)

    scen = {"all": []}
    if exclude:
        scen[scenario_label(exclude)] = exclude
    ex_label = scenario_label(exclude) if exclude else None
    primary = "KRW" if "KRW" in bases else bases[0]

    mats, neff_rows, cl_tables = {}, [], []
    for base in bases:
        cols_h = [c for c in hold["code"] if c in rets[base].columns]
        cols_b = [c for c in bench_codes if c in rets[base].columns]
        wvec = np.array([float(hold.loc[hold["code"] == c, "w"].iloc[0]) for c in cols_h])
        for sname, months in scen.items():
            r = apply_exclusion(rets[base], months)
            m = corr_matrices(r, cols_h + cols_b)
            mats[(base, sname)] = m
            for (meth, freq), c in m.items():
                c.to_csv(out_dir / f"corr_{meth}_{freq}_{base.lower()}_{sname}.csv",
                         encoding="utf-8-sig", float_format="%.4f")
                ch = c.loc[cols_h, cols_h]
                n_eff, pc1, n80, n_ok, bad = eff_bets(ch)
                neff_rows.append({
                    "base": base, "scenario": sname, "method": meth, "freq": freq,
                    "n_assets": len(cols_h), "n_used": n_ok,
                    "n_eff": round(n_eff, 2), "pc1_share_pct": round(pc1 * 100, 1), "n_pc_80pct": n80,
                    "avg_corr": round(avg_offdiag(ch), 3), "wavg_corr": round(avg_offdiag(ch, wvec), 3),
                    "excluded": " ".join(bad),
                })
            for key, lab in ((("spearman", "daily"), "spearman_daily"), (("pearson", "weekly"), "pearson_weekly")):
                cc = m[key].loc[cols_h, cols_h]
                cl_tables.append(cluster_table(cluster_assign(cc, cluster_rho), cc, hold, sname, base, cluster_rho, lab))
        # 롤링 (전체 기간)
        r_all = rets[base]
        roll = pd.concat([rolling_avg_corr(r_all, cols_h, wvec, 60),
                          rolling_avg_corr(r_all, cols_h, wvec, 120)], axis=1).sort_index()
        roll.to_csv(out_dir / f"corr_rolling_avg_{base.lower()}.csv", encoding="utf-8-sig", float_format="%.4f")
        nonmicro = [c for c in cols_h if hold.loc[hold["code"] == c, "group"].iloc[0] != "micro"]
        tp = top_pairs(mats[(base, "all")][("spearman", "daily")], nonmicro, 8)
        pr = {}
        for a, b_, _ in tp:
            for w in (60, 120):
                pr[f"{a}|{b_}_{w}"] = r_all[a].rolling(w, min_periods=int(w * 0.8)).corr(r_all[b_])
        pd.DataFrame(pr).to_csv(out_dir / f"corr_rolling_pairs_{base.lower()}.csv",
                                encoding="utf-8-sig", float_format="%.4f", index_label="date")

    neff = pd.DataFrame(neff_rows)
    neff.to_csv(out_dir / "corr_neff.csv", index=False, encoding="utf-8-sig")
    cl = pd.concat(cl_tables, ignore_index=True)
    cl.to_csv(out_dir / "corr_clusters.csv", index=False, encoding="utf-8-sig")

    # 벤치마크 상관 (주 통화, 전체 기간)
    cs = mats[(primary, "all")][("spearman", "daily")]
    cp = mats[(primary, "all")][("pearson", "weekly")]
    bench_rows = []
    for c in hold["code"]:
        if c not in cs.columns:
            continue
        row = {"code": c}
        for bcode in bench_codes:
            if bcode in cs.columns:
                row[f"{bcode}_spearman_daily"] = round(float(cs.loc[c, bcode]), 3)
                row[f"{bcode}_pearson_weekly"] = round(float(cp.loc[c, bcode]), 3)
        bench_rows.append(row)
    bench_df = pd.DataFrame(bench_rows)
    bench_df.to_csv(out_dir / "corr_vs_benchmarks.csv", index=False, encoding="utf-8-sig")

    # 환율 영향
    fx_df = None
    fxp = data_dir / "fx_usdkrw.csv"
    if "KRW" in rets and "USD" in rets and fxp.exists():
        fx = pd.read_csv(fxp, index_col=0, parse_dates=True, encoding="utf-8-sig")["USDKRW"]
        fx_ret = fx.pct_change().reindex(rets["KRW"].index)
        fx_df = fx_effect(rets, fx_ret, hold)
        fx_df.to_csv(out_dir / "fx_effect.csv", index=False, encoding="utf-8-sig")

    text = build_summary(mats, neff, cl, bench_df, fx_df, hold, rets[primary], primary,
                         ex_label, bases, cluster_rho, dropped, min_weeks)
    (out_dir / "corr_summary.txt").write_text(text, encoding="utf-8")
    return text, mats, neff, cl, fx_df, out_dir


# ---------------------------------------------------------------- 요약
def build_summary(mats, neff, cl, bench_df, fx_df, hold, r, primary, ex_label, bases, rho_cut, dropped=None, min_weeks=0):
    L = []
    cols_h = [c for c in hold["code"] if c in r.columns]
    wmap = dict(zip(hold["code"], hold["w"]))
    L.append("=== 상관 진단 요약 ===")
    if dropped:
        L.append(f"최근 상장·이력 부족으로 제외(주 수 < {min_weeks}): "
                 + ", ".join(f"{c}({n}주)" for c, n in dropped.items()))
    L.append(f"기간 {r.index.min().date()} ~ {r.index.max().date()} ({len(r)}거래일) | "
             f"종목 {len(cols_h)}개 | 주 통화 {primary} | 비교 시나리오 {ex_label or '없음'}")

    L.append("\n[1] 유효 독립 자산 수 (상관행렬 기준, 비중 미반영)")
    t = neff[neff["base"] == primary].copy()
    for _, x in t.iterrows():
        L.append(f"  {x['scenario']:<9} {x['method']:<8} {x['freq']:<6} 독립 자산 수 {x['n_eff']:>5} / {x['n_used']} | "
                 f"1번 요인 {x['pc1_share_pct']:>5}% | 80% 설명 요인 {x['n_pc_80pct']}개 | "
                 f"평균 상관 {x['avg_corr']:+.2f} (비중가중 {x['wavg_corr']:+.2f})")
    ex = t[t["excluded"] != ""]
    if len(ex):
        L.append("  (겹치는 기간이 짧아 제외된 종목: " + ", ".join(sorted(set(" ".join(ex["excluded"]).split()))) + ")")

    c_all = mats[(primary, "all")]
    cs, cpd, cpw = c_all[("spearman", "daily")], c_all[("pearson", "daily")], c_all[("pearson", "weekly")]
    nonmicro = [c for c in cols_h if hold.loc[hold["code"] == c, "group"].iloc[0] != "micro"]

    L.append("\n[2] 가장 높게 같이 움직이는 쌍 (초소형 제외, 스피어만 일간 기준)")
    cx = mats.get((primary, ex_label)) if ex_label else None
    head = "  쌍                     스피어만  피어슨일간  피어슨주간" + (f"  스피어만({ex_label})" if cx else "")
    if ("USD" in bases) and primary != "USD":
        head += "  스피어만(USD)"
    L.append(head)
    cu = mats.get(("USD", "all")) if primary != "USD" else None
    for a, b, v in top_pairs(cs, nonmicro, 15):
        s = f"  {a + ' - ' + b:<22} {v:>+7.2f} {cpd.loc[a, b]:>+10.2f} {cpw.loc[a, b]:>+10.2f}"
        if cx:
            s += f" {cx[('spearman', 'daily')].loc[a, b]:>+14.2f}"
        if cu is not None:
            s += f" {cu[('spearman', 'daily')].loc[a, b]:>+13.2f}"
        L.append(s)

    if cx:
        L.append(f"\n[3] {ex_label[2:]} 을(를) 빼면 피어슨 일간 상관이 가장 크게 달라지는 쌍 (초소형 제외, 차이 = 전체 - 제외)")
        diffs = []
        for i in range(len(nonmicro)):
            for j in range(i + 1, len(nonmicro)):
                a, b = nonmicro[i], nonmicro[j]
                v1, v2 = cpd.loc[a, b], cx[("pearson", "daily")].loc[a, b]
                if v1 == v1 and v2 == v2:
                    diffs.append((a, b, v1, v2, v1 - v2))
        diffs.sort(key=lambda x: -abs(x[4]))
        for a, b, v1, v2, d in diffs[:10]:
            L.append(f"  {a + ' - ' + b:<22} 전체 {v1:+.2f} -> 제외 {v2:+.2f} (차이 {d:+.2f})")
        L.append(f"  전체 쌍 평균 차이(전체 - 제외): {np.mean([x[4] for x in diffs]):+.3f}")

    kr = [c for c in cols_h if hold.loc[hold["code"] == c, "qccy"].iloc[0] == "KRW"
          and hold.loc[hold["code"] == c, "group"].iloc[0] != "proxy"]
    us = [c for c in cols_h if hold.loc[hold["code"] == c, "qccy"].iloc[0] == "USD"
          and not hold.loc[hold["code"] == c, "yahoo_ticker"].iloc[0].upper().endswith("-USD")]

    def cross(c):
        v = c.loc[kr, us].values.astype(float)
        return float(np.nanmean(v)) if v.size else float("nan")
    L.append(f"\n[4] 한국 종목 {len(kr)}개 ↔ 미국 종목 {len(us)}개 평균 상관 (시차 효과 점검, {primary} 전체 기간)")
    L.append(f"  피어슨 일간 {cross(cpd):+.2f} | 스피어만 일간 {cross(cs):+.2f} | 피어슨 주간 {cross(cpw):+.2f}")
    L.append("  (주간이 일간보다 크게 높으면, 일간 수치는 시차 때문에 한미 동조를 낮게 보여준다는 뜻)")

    L.append(f"\n[5] 상관이 높은 묶음 (평균 상관 {rho_cut:.2f} 이상, {primary}, 전체 기간)")
    for basis, title in (("spearman_daily", "스피어만 일간"), ("pearson_weekly", "피어슨 주간 (한미 시차 보정)")):
        k = cl[(cl["base"] == primary) & (cl["scenario"] == "all") & (cl["basis"] == basis)]
        L.append(f"  <{title}>")
        for _, x in k.iterrows():
            if x["n"] > 1:
                L.append(f"    묶음 {x['cluster']}: {x['members']} | 비중 {x['weight_pct']}% | 평균 상관 {x['avg_intra_corr']}")
        singles = k[k["n"] == 1]["members"].tolist()
        if singles:
            L.append("    단독: " + " ".join(singles))

    L.append(f"\n[6] 벤치마크 상관 ({primary}, 스피어만 일간 / 피어슨 주간)")
    bcols = [c for c in bench_df.columns if c != "code"]
    names = sorted({c.rsplit("_", 2)[0] for c in bcols})
    L.append("  종목        " + "  ".join(f"{n:>8}일간 {n:>8}주간" for n in names))
    for _, x in bench_df.iterrows():
        L.append(f"  {x['code']:<10}  " + "  ".join(
            f"{x[n + '_spearman_daily']:>+11.2f} {x[n + '_pearson_weekly']:>+11.2f}" for n in names))

    if fx_df is not None:
        L.append("\n[7] 환율 영향 (연율화 변동성 %, 비중 큰 순)")
        L.append("  종목        통화  비중%   원화변동성  달러변동성  차이   로컬수익률-환율 상관")
        for _, x in fx_df.sort_values("weight_pct", ascending=False).iterrows():
            L.append(f"  {x['code']:<10} {x['local_ccy']:<4} {x['weight_pct']:>5.2f} {x['vol_krw_pct']:>10.1f} "
                     f"{x['vol_usd_pct']:>10.1f} {x['vol_diff_pct']:>+6.1f} {x['corr_local_vs_usdkrw']:>+16.2f}")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- 점검(selftest)
def _synthetic_inputs(tmp):
    """3개 묶음(묶음 안 상관 0.8, 묶음 사이 0.1) + 짧은 이력 종목 + 극단값 하루."""
    rng = np.random.default_rng(zlib.crc32(b"corr_selftest"))
    idx = pd.bdate_range("2024-05-01", "2026-11-13")[1:]
    n = len(idx)
    m = rng.normal(size=n)
    f = {g: rng.normal(size=n) for g in "ABC"}
    cols = {}
    for g in "ABC":
        for k in range(1, 5):
            e = rng.normal(size=n)
            cols[f"{g}{k}"] = 0.01 * (np.sqrt(0.1) * m + np.sqrt(0.7) * f[g] + np.sqrt(0.2) * e)
    r = pd.DataFrame(cols, index=idx)
    spike = pd.Timestamp("2026-07-15")
    r.loc[spike, "A1"] = 7.0                                   # 하루 +700%
    r["S"] = np.nan
    r.loc[r.index[-100:], "S"] = 0.01 * rng.normal(size=100)  # 이력 100일
    lagged = np.roll(f["A"], 1)                                # A 묶음을 하루 늦게 따라가는 종목 L (시차)
    lagged[0] = 0.0
    r["L"] = 0.01 * (np.sqrt(0.95) * lagged
                     + np.sqrt(0.05) * np.random.default_rng(zlib.crc32(b"lag")).normal(size=n))
    r["KOSPI"] = r[["A1", "A2", "A3", "A4"]].mean(axis=1) * 0.8 + 0.003 * rng.normal(size=n)
    r["SP500"] = r[["B1", "B2", "B3", "B4"]].mean(axis=1) * 0.8 + 0.003 * rng.normal(size=n)
    fx_ret = pd.Series(0.004 * rng.normal(size=n), index=idx)
    rk = r
    ru = (1.0 + r) / (1.0 + fx_ret.values[:, None]) - 1.0
    rk.to_csv(tmp / "returns_krw.csv", encoding="utf-8-sig", index_label="date")
    ru.to_csv(tmp / "returns_usd.csv", encoding="utf-8-sig", index_label="date")
    fx = pd.Series(1400.0 * np.cumprod(1.0 + fx_ret.values), index=idx, name="USDKRW")
    fx.to_csv(tmp / "fx_usdkrw.csv", encoding="utf-8-sig", index_label="date")
    rows = ["role,group,code,name,yahoo_ticker,currency,sector,bucket,weight_pct_x"]
    ccy = {"A": "KRW", "B": "USD", "C": "KRW"}
    for g in "ABC":
        for k in range(1, 5):
            c = ccy[g] if not (g == "C" and k > 2) else "USD"
            tk = f"{g}{k}.KS" if c == "KRW" else f"{g}{k}"
            rows.append(f"holding,main,{g}{k},x,{tk},{c},S{g},core,8")
    rows.append("holding,main,L,x,L.KS,KRW,SL,core,8")
    rows.append("holding,micro,S,x,S,USD,SS,core,1")
    rows += ["benchmark,ref,KOSPI,x,^KS11,KRW,,,", "benchmark,ref,SP500,x,^GSPC,USD,,,",
             "fx,ref,USDKRW,x,KRW=X,KRW,,,"]
    (tmp / "universe.csv").write_text("\n".join(rows) + "\n", encoding="utf-8-sig")
    return idx


def selftest():
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        idx = _synthetic_inputs(tmp)
        out = tmp / "corr"
        text, mats, neff, cl, fx_df, out_dir = run(
            tmp, tmp / "universe.csv", out, ["KRW", "USD"], ["2026-07"], 0.5, ["main", "proxy", "micro"])
        ex = scenario_label(["2026-07"])
        check(ex == "ex202607", "시나리오 이름")

        kall, kex = mats[("KRW", "all")], mats[("KRW", "ex202607")]
        sp, pe, pw = kall[("spearman", "daily")], kall[("pearson", "daily")], kall[("pearson", "weekly")]
        # 구조 복원
        check(0.70 < sp.loc["A2", "A3"] < 0.90, f"묶음 안 스피어만 {sp.loc['A2', 'A3']:.2f}")
        check(0.70 < pe.loc["B1", "B2"] < 0.90, f"묶음 안 피어슨 {pe.loc['B1', 'B2']:.2f}")
        check(0.00 < sp.loc["A2", "B2"] < 0.25, f"묶음 사이 스피어만 {sp.loc['A2', 'B2']:.2f}")
        check(0.55 < pw.loc["A2", "A3"] < 0.95, f"주간 피어슨 {pw.loc['A2', 'A3']:.2f}")
        # 극단값: 피어슨은 무너지고 스피어만은 유지, 월 제외하면 회복
        check(pe.loc["A1", "A2"] < 0.30, f"극단값 하루가 피어슨을 못 무너뜨림 {pe.loc['A1', 'A2']:.2f}")
        check(sp.loc["A1", "A2"] > 0.70, f"스피어만은 유지돼야 함 {sp.loc['A1', 'A2']:.2f}")
        check(kex[("pearson", "daily")].loc["A1", "A2"] > 0.70, "월 제외 시나리오가 피어슨을 회복시켜야 함")
        # 짧은 이력: 쌍 상관 NaN, 요약에서 제외 표시
        check(np.isnan(sp.loc["S", "A1"]), "이력 100일 종목은 상관이 NaN 이어야 함")
        t0 = neff[(neff["base"] == "KRW") & (neff["scenario"] == "all") & (neff["method"] == "spearman")].iloc[0]
        check(t0["excluded"] == "S" and t0["n_used"] == 13, f"제외 종목 처리 {t0['excluded']!r} {t0['n_used']}")
        # 군집: 12개가 정확히 3묶음 + S 단독
        k = cl[(cl["base"] == "KRW") & (cl["scenario"] == "all") & (cl["basis"] == "spearman_daily")]
        sets = sorted(sorted(s.split()) for s in k["members"])
        want = sorted([["A1", "A2", "A3", "A4"], ["B1", "B2", "B3", "B4"], ["C1", "C2", "C3", "C4"], ["S"], ["L"]])
        check(sets == want, f"일간 군집 복원 실패 {sets}")
        kw = cl[(cl["base"] == "KRW") & (cl["scenario"] == "ex202607") & (cl["basis"] == "pearson_weekly")]
        sets_w = sorted(sorted(s.split()) for s in kw["members"])
        want_w = sorted([["A1", "A2", "A3", "A4", "L"], ["B1", "B2", "B3", "B4"], ["C1", "C2", "C3", "C4"], ["S"]])
        check(sets_w == want_w, f"주간 군집 복원 실패(시차 종목 L 이 A 묶음에 들어가야 함) {sets_w}")
        # 유효 독립 자산 수: 3묶음이면 3~6 사이
        te = neff[(neff["base"] == "KRW") & (neff["scenario"] == "ex202607") & (neff["method"] == "pearson")
                  & (neff["freq"] == "daily")].iloc[0]
        check(3.0 < te["n_eff"] < 6.0, f"유효 독립 자산 수 {te['n_eff']}")
        # 주간 합성: 한 주의 일간 수익률 복리와 같아야 함
        r0 = pd.read_csv(tmp / "returns_krw.csv", index_col=0, parse_dates=True)[["A2"]]
        wk = to_weekly(r0)
        w_end = pd.Timestamp("2025-03-14")
        days = r0.loc["2025-03-10":"2025-03-14", "A2"].values
        check(len(days) == 5 and abs(wk.loc[w_end, "A2"] - (np.prod(1 + days) - 1)) < 1e-12, "주간 복리 합성")
        # 롤링
        ra = pd.read_csv(out / "corr_rolling_avg_krw.csv", index_col=0, parse_dates=True)
        check(len(ra) > 100 and ra["avg_corr_60"].dropna().between(-1, 1).all(), "롤링 평균 상관 범위")
        check(ra.index.max() == idx[-1], "롤링 마지막 날짜")
        check((out / "corr_rolling_pairs_krw.csv").exists(), "롤링 쌍 파일")
        # 환율 영향
        x = fx_df.set_index("code").loc["A2"]
        check(abs(x["vol_usd_pct"] - np.sqrt(x["vol_krw_pct"] ** 2 + (0.004 * np.sqrt(ANN) * 100) ** 2)) < 0.12 * x["vol_usd_pct"],
              f"환율 영향 변동성 관계 {x['vol_krw_pct']} {x['vol_usd_pct']}")
        check(-1 <= x["corr_local_vs_usdkrw"] <= 1, "환율 상관 범위")
        # 파일·요약
        for f in ["corr_neff.csv", "corr_clusters.csv", "corr_vs_benchmarks.csv", "fx_effect.csv", "corr_summary.txt",
                  "corr_pearson_daily_krw_all.csv", "corr_spearman_daily_usd_ex202607.csv", "corr_pearson_weekly_usd_all.csv"]:
            check((out / f).exists(), f + " 없음")
        check(len(list(out.glob("corr_*_*_*_*.csv"))) == 12, "상관행렬 파일 12개")
        for key in ["[1]", "[2]", "[3]", "[4]", "[5]", "[6]", "[7]"]:
            check(key in text, "요약 섹션 " + key)
        sec3 = text.split("[3]")[1].split("[4]")[0]
        check("A1 - A" in sec3, "극단값 쌍(A1)이 [3]에 나와야 함 (방향 무관)")
        bk = pd.read_csv(out / "corr_vs_benchmarks.csv").set_index("code")
        check(bk.loc["A2", "KOSPI_spearman_daily"] > bk.loc["A2", "SP500_spearman_daily"], "벤치마크 상관 방향")
        # 최근 상장 제외 옵션: 주 수가 모자라는 S(약 20주)만 빠져야 함
        text2, mats2, neff2, cl2, _, _ = run(tmp, tmp / "universe.csv", tmp / "corr30", ["KRW"], ["2026-07"], 0.5,
                                              ["main", "proxy", "micro"], min_weeks=30)
        sp2 = mats2[("KRW", "all")][("spearman", "daily")]
        check("S" not in sp2.columns and "A1" in sp2.columns and "L" in sp2.columns, "min_weeks 로 S 만 빠져야 함")
        check("주 수 < 30" in text2 and "S(" in text2, "요약 머리에 제외 종목이 표시돼야 함")
        n2 = neff2[(neff2["scenario"] == "all") & (neff2["method"] == "spearman")].iloc[0]
        check(n2["excluded"] == "" and n2["n_used"] == 13, f"제외 후 사용 종목 {n2['n_used']}")
        print(text)

    print()
    if fails:
        print("SELFTEST 실패:")
        for f in fails:
            print("  - " + f)
        return 1
    print("SELFTEST 통과: 상관 복원, 극단값·월 제외, 짧은 이력, 군집, 유효 독립 자산 수, 주간 합성, 롤링, 환율 영향")
    return 0


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="포트폴리오 상관 진단")
    ap.add_argument("--data", default=str(DEFAULT_DATA), help="fetch_prices.py 출력 폴더")
    ap.add_argument("--universe", default=str(DEFAULT_UNIVERSE))
    ap.add_argument("--out", default=None, help="기본: <data>/corr")
    ap.add_argument("--bases", default="KRW,USD")
    ap.add_argument("--exclude", default="2026-07", help="제외 시나리오 월(쉼표 구분), 없으면 none")
    ap.add_argument("--groups", default="main,proxy,micro")
    ap.add_argument("--cluster-corr", type=float, default=0.5, help="묶음 기준 평균 상관 (기본 0.5)")
    ap.add_argument("--min-weeks", type=int, default=0, help="이 주 수 미만인 종목(최근 상장)을 계산에서 뺀다, 0이면 끔")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    data = Path(a.data)
    out = Path(a.out) if a.out else data / (f"corr_w{a.min_weeks}" if a.min_weeks > 0 else "corr")
    bases = [b.strip().upper() for b in a.bases.split(",") if b.strip()]
    exclude = [] if a.exclude.strip().lower() == "none" else [m.strip() for m in a.exclude.split(",") if m.strip()]
    groups = [g.strip() for g in a.groups.split(",") if g.strip()]
    text, *_ = run(data, Path(a.universe), out, bases, exclude, a.cluster_corr, groups, a.min_weeks)
    print(text)
    print(f"저장 위치: {out}")


if __name__ == "__main__":
    main()
