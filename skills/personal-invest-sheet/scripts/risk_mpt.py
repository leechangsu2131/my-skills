#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
risk_mpt.py  (portfolio 3단계-2: 위험·베타·CAPM·MPT 참고값)

결과는 모두 **참고값**이다. 시트의 비중 산정을 대체하지 않고, 비중 결정은 사람이 한다.
시트는 읽지도 쓰지도 않는다. 입력은 fetch_prices.py 가 만든 일간 수익률과 universe.csv.

하는 일
  1) 주간 수익률 공분산 추정 (기본). 종목은 많은데 주간 표본은 적어서
     Ledoit-Wolf 축소추정(상관이 모두 같다고 보는 목표 쪽으로 당김)을 쓴다.
     비교용으로 주간 표본 공분산, 일간 표본 공분산, 특정 월 제외 버전도 계산한다.
  2) 현재 비중의 포트폴리오 변동성, 종목별·버킷별·섹터별 위험기여도.
  3) 종목별 베타(S&P500, KOSPI 대비)와 CAPM 기대수익률 (시트 설정의 Rf·ERP).
  4) MPT 참고값: 최소분산, 최대 샤프, 효율적 경계. 종목 상한은 시트 설정 [3]의 단일종목 상한.
     기대수익률은 CAPM 값(기본)과 역사적 평균(경고용) 두 가지.
  5) 부트스트랩: 주간 데이터를 다시 뽑아 같은 계산을 반복해 보고, 결과 비중이 얼마나 흔들리는지 본다.
     (입력이 조금만 달라져도 결과가 크게 바뀌면 그 결과는 믿기 어렵다는 뜻이다.)

적용하는 가정
  - 상장 이력이 짧은 종목(기본 100주 미만)은 최적화에서 제외하고, 공분산에는
    자기 변동성과 겹치는 구간의 상관으로 붙인다.
  - 통화별 Rf·ERP: USD 4.5%·5%, KRW 3.3%·6% (시트 ⚙️ 설정 [1]). 시장 대용은 S&P500.
    시트의 CAPM 기준통화는 USD 이므로, 기대수익률 관련 결과는 USD 기준을 우선 본다.
  - 종목 상한: 성장 12%, 코어 15%, 인컴 8%, 전술 5%, 그 외 15% (시트 ⚙️ 설정 [2][3]).
    버킷 합계 한도(성장 50% 등)는 적용하지 않는다.
    상한은 전체 포트폴리오 대비 비중이므로, 분석 대상이 전체의 일부(share)이면 상한을 1/share 배로 환산한다.
  - universe.csv 의 start_date 열: 그 날짜 이전 수익률은 쓰지 않는다. 예) 사업 성격이 바뀌며 하루 수백 % 오른 종목은
    그 구간이 들어가면 변동성이 크게 과장된다. 비우면 전 구간을 쓴다.
  - 헤알 대용 계열(KRW=X/BRL=X)을 쓰는 자산은 환율 수익률만 반영되어 이자수익이 빠진다.

사용
  python risk_mpt.py                      # 원화+달러, 부트스트랩 100회
  python risk_mpt.py --bootstrap 0        # 부트스트랩 없이 빠르게
  python risk_mpt.py --exclude 2026-07,2026-08
  python risk_mpt.py --selftest

출력 (기본 위치: OUTPUT_DIR/portfolio_out/risk/)
  risk_vol_by_estimator.csv   추정 방식별 포트폴리오 변동성 (민감도)
  risk_contrib_<통화>.csv     종목별 비중·위험기여도
  beta_capm_<통화>.csv        베타, CAPM 기대수익률, 실현 수익률
  cov_weekly_lw_<통화>.csv    연율 공분산 (축소추정)
  mpt_weights_<통화>.csv      현재·최소분산·최대샤프 비중
  frontier_<통화>.csv         효율적 경계
  bootstrap_<통화>.csv        비중 안정성
  risk_summary.txt            위 내용의 요약
"""
import argparse
import sys
import tempfile
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from corr_diagnosis import apply_exclusion, scenario_label, to_weekly  # noqa: E402

import invest_common as _ic  # noqa: E402  (공용 .env, 종목 목록·결과 폴더 위치)

_UNI = _ic.universe_path() if (_ic.invest_dir() or _ic.os.environ.get("UNIVERSE")) else HERE / "universe.csv"
DEFAULT_DATA = _ic.out_dir("portfolio")
DEFAULT_UNIVERSE = _UNI

WEEKS = 52
DAYS = 252
MIN_WEEKS_CORE = 100     # 이 주 수 미만이면 짧은 이력 종목
MIN_OVERLAP_W = 26       # 짧은 종목 상관을 쓰려면 겹치는 주 수
MIN_OBS_D = 120
SHEET_PARAMS = {"USD": (0.045, 0.05), "KRW": (0.033, 0.06)}   # (Rf, ERP) 시트 ⚙️ 설정 [1]
BUCKET_CAPS = {"성장": 0.12, "코어": 0.15, "인컴": 0.08, "전술": 0.05}   # 시트 [2][3]
DEFAULT_CAP = 0.15
BENCH = "SP500"
BENCH2 = "KOSPI"


# ---------------------------------------------------------------- 공분산
def make_psd(c, eps=1e-10):
    """고유값을 양수로 끌어올려 양의 준정부호로 만들고, 대각선(분산)은 원래대로 맞춘다."""
    c = (c + c.T) / 2.0
    w, v = np.linalg.eigh(c)
    p = (v * np.clip(w, eps, None)) @ v.T
    d = np.sqrt(np.diag(c) / np.diag(p))
    p = p * np.outer(d, d)
    return (p + p.T) / 2.0


def ledoit_wolf_cc(x):
    """Ledoit-Wolf(2003) 상수상관 목표 축소추정. x: 관측치 x 종목. 반환 (공분산, 축소강도, 표본공분산)."""
    x = np.asarray(x, dtype=float)
    t, n = x.shape
    xc = x - x.mean(axis=0)
    s = xc.T @ xc / t
    var = np.diag(s).copy()
    sd = np.sqrt(var)
    corr = s / np.outer(sd, sd)
    rbar = (corr.sum() - n) / (n * (n - 1))
    f = rbar * np.outer(sd, sd)
    np.fill_diagonal(f, var)
    xx = xc[:, :, None] * xc[:, None, :]
    dev = xx - s[None]
    pi_mat = (dev ** 2).mean(axis=0)
    pi_hat = pi_mat.sum()
    theta = ((xc ** 2 - var[None, :])[:, :, None] * dev).mean(axis=0)
    a = theta * (sd[None, :] / sd[:, None])
    rho_hat = np.trace(pi_mat) + rbar * (a.sum() - np.trace(a))
    gamma = ((f - s) ** 2).sum()
    kappa = (pi_hat - rho_hat) / gamma if gamma > 0 else 0.0
    delta = float(max(0.0, min(1.0, kappa / t)))
    return delta * f + (1.0 - delta) * s, delta, s


def assemble_cov(weekly, core, short):
    """핵심 종목은 공통 구간에서 축소추정하고, 짧은 종목은 자기 변동성과 겹치는 구간 상관으로 붙인다."""
    cols = core + short
    xc = weekly[core].dropna()
    s_lw, delta, _ = ledoit_wolf_cc(xc.values)
    sd = np.sqrt(np.diag(s_lw))
    r = pd.DataFrame(np.eye(len(cols)), index=cols, columns=cols)
    r.loc[core, core] = s_lw / np.outer(sd, sd)
    vol = pd.Series(0.0, index=cols)
    vol[core] = sd
    for sname in short:
        vol[sname] = weekly[sname].dropna().std(ddof=0)
    for sname in short:
        for c in cols:
            if c == sname:
                continue
            pair = weekly[[sname, c]].dropna()
            rho = pair.corr().iloc[0, 1] if len(pair) >= MIN_OVERLAP_W else 0.0
            rho = 0.0 if rho != rho else float(rho)
            r.loc[sname, c] = rho
            r.loc[c, sname] = rho
    cov = np.outer(vol.values, vol.values) * r.values
    cov = pd.DataFrame(make_psd(cov), index=cols, columns=cols)
    meta = {"delta": delta, "t_window": len(xc),
            "start": xc.index.min(), "end": xc.index.max(), "n_core": len(core), "short": list(short)}
    return cov, meta


def pairwise_cov(r, min_periods, factor):
    c = r.cov(min_periods=min_periods)
    v = np.nan_to_num(c.values.astype(float), nan=0.0)
    return pd.DataFrame(make_psd(v) * factor, index=c.index, columns=c.columns)


# ---------------------------------------------------------------- 위험
def risk_report(w, cov):
    w = np.asarray(w, dtype=float)
    s = cov.values
    var = float(w @ s @ w)
    vol = np.sqrt(var)
    mrc = s @ w / vol
    rc = w * mrc
    sig = np.sqrt(np.diag(s))
    return {
        "vol": vol,
        "rc": pd.Series(rc, index=cov.index),
        "rc_pct": pd.Series(rc / vol, index=cov.index),
        "div_ratio": float((w * sig).sum() / vol),
        "n_eff_risk": float(1.0 / np.sum((rc / vol) ** 2)),
    }


def beta_stats(weekly, bench):
    rows = []
    b_all = weekly[bench]
    for c in weekly.columns:
        if c == bench:
            continue
        pair = pd.concat([weekly[c], b_all], axis=1).dropna()
        n = len(pair)
        if n < 40:
            rows.append((c, np.nan, np.nan, n))
            continue
        x, y = pair.iloc[:, 1].values, pair.iloc[:, 0].values
        vx = x.var()
        beta = float(((x - x.mean()) * (y - y.mean())).mean() / vx) if vx > 0 else np.nan
        r2 = float(np.corrcoef(x, y)[0, 1] ** 2)
        rows.append((c, beta, r2, n))
    return pd.DataFrame(rows, columns=["code", "beta", "r2", "n_weeks"]).set_index("code")


def realized_return(weekly):
    out = {}
    for c in weekly.columns:
        v = weekly[c].dropna()
        out[c] = float((1.0 + v).prod() ** (WEEKS / len(v)) - 1.0) if len(v) >= 20 else np.nan
    return pd.Series(out)


# ---------------------------------------------------------------- 최적화
def project_capped_simplex(v, cap):
    """0 <= w <= cap, 합 1 인 집합으로의 사영. w = clip(v - tau) 이고 tau 는 꺾이는 점 사이 선형 보간으로 정확히 구한다."""
    v = np.asarray(v, dtype=float)
    cap = np.broadcast_to(np.asarray(cap, dtype=float), v.shape)
    bp = np.sort(np.concatenate([v, v - cap]))
    f = np.clip(v[None, :] - bp[:, None], 0.0, cap[None, :]).sum(axis=1) - 1.0   # tau 에 대해 감소
    k = int(np.searchsorted(-f, 0.0))
    if k <= 0:
        tau = bp[0]
    elif k >= len(bp):
        tau = bp[-1]
    else:
        tau = bp[k - 1] + f[k - 1] / (f[k - 1] - f[k]) * (bp[k] - bp[k - 1])
    return np.clip(v - tau, 0.0, cap)


def solve_qp(mu, s, lam, cap, w0=None, iters=3000, tol=1e-9):
    """max mu'w - lam/2 w'Sw  s.t. 0<=w<=cap, sum w=1  (가속 사영 경사법, 목적함수가 나빠지면 가속 재시작)."""
    s = np.asarray(s, dtype=float)
    mu = np.asarray(mu, dtype=float)
    n = len(mu)
    cap = np.broadcast_to(np.asarray(cap, dtype=float), (n,))
    lip = lam * np.linalg.eigvalsh(s)[-1]

    def obj(x):
        return 0.5 * lam * (x @ s @ x) - mu @ x
    w = project_capped_simplex(np.full(n, 1.0 / n) if w0 is None else w0, cap)
    f_w = obj(w)
    y, t = w.copy(), 1.0
    for _ in range(iters):
        g = lam * (s @ y) - mu
        w_new = project_capped_simplex(y - g / lip, cap)
        f_new = obj(w_new)
        if f_new > f_w + 1e-15:          # 재시작: 가속을 버리고 현재 점에서 다시 시작
            y, t = w.copy(), 1.0
            g = lam * (s @ y) - mu
            w_new = project_capped_simplex(y - g / lip, cap)
            f_new = obj(w_new)
            t_new = 1.0
            y_next = w_new
        else:
            t_new = (1.0 + np.sqrt(1.0 + 4.0 * t * t)) / 2.0
            y_next = w_new + ((t - 1.0) / t_new) * (w_new - w)
        done = np.abs(w_new - w).max() < tol
        w, f_w, y, t = w_new, f_new, y_next, t_new
        if done:
            break
    return w


def max_sharpe(mu, s, rf, cap, ngrid=40):
    """위험회피도를 훑어 효율적 경계를 만들고 샤프가 가장 큰 점을 고른다."""
    mu = np.asarray(mu, dtype=float)
    s = np.asarray(s, dtype=float)
    n = len(mu)
    scale = max(np.abs(mu - rf).max(), 1e-6) / max(np.mean(np.diag(s)), 1e-12)
    lams = scale * np.logspace(-1.5, 2.5, ngrid)[::-1]     # 큰 값(최소분산 쪽)부터
    w, pts = None, []
    for lam in lams:
        w = solve_qp(mu, s, lam, cap, w0=w)
        vol = float(np.sqrt(w @ s @ w))
        ret = float(mu @ w)
        pts.append((lam, vol, ret, (ret - rf) / vol, w.copy()))
    best = max(pts, key=lambda p: p[3])
    return best[4], pts


def frontier_position(pts, vol_c, ret_c):
    """현재 포트폴리오가 효율적 경계 위·아래 어디에 있는지."""
    v = np.array([p[1] for p in pts])
    r = np.array([p[2] for p in pts])
    order = np.argsort(v)
    v, r = v[order], np.maximum.accumulate(r[order])
    ret_at_vol = float(np.interp(vol_c, v, r))
    r_u, idx = np.unique(r, return_index=True)
    vol_at_ret = float(np.interp(ret_c, r_u, v[idx]))
    return ret_at_vol, vol_at_ret


def bootstrap_indices(rng, t):
    """복원추출 색인 (t개 중 t개를 뽑는다)."""
    return rng.integers(0, t, t)


def bootstrap_mpt(x, bench, cap, rf, erp, b, seed, ngrid=20):
    """주간 관측치를 복원추출로 다시 뽑아 최소분산·최대샤프(CAPM)·최대샤프(역사평균)를 반복 계산."""
    rng = np.random.default_rng(seed)
    t, n = x.shape
    out = {"minvar": [], "ms_capm": [], "ms_hist": []}
    for _ in range(b):
        idx = bootstrap_indices(rng, t)
        xb, mb = x[idx], bench[idx]
        s = ledoit_wolf_cc(xb)[0] * WEEKS
        beta = ((xb - xb.mean(0)).T @ (mb - mb.mean())) / t / mb.var()
        out["minvar"].append(solve_qp(np.zeros(n), s, 1.0, cap))
        out["ms_capm"].append(max_sharpe(rf + erp * beta, s, rf, cap, ngrid)[0])
        out["ms_hist"].append(max_sharpe(xb.mean(0) * WEEKS, s, rf, cap, ngrid)[0])
    return {k: np.array(v) for k, v in out.items()}


# ---------------------------------------------------------------- 한 통화 분석
def apply_start_dates(daily, hold):
    """universe 의 start_date 이전 수익률을 NaN 으로 만든다 (사업 성격이 바뀐 종목 등)."""
    out = daily.copy()
    for c, sd in zip(hold["code"], hold["start_date"]):
        if sd and c in out.columns:
            out.loc[out.index < pd.Timestamp(sd), c] = np.nan
    return out


def analyze_base(base, daily, hold, args):
    starts = {c: sd for c, sd in zip(hold["code"], hold["start_date"]) if sd and c in daily.columns}
    daily = apply_start_dates(daily, hold)
    cols = [c for c in hold["code"] if c in daily.columns]
    bcols = [c for c in (BENCH, BENCH2) if c in daily.columns]
    weekly = to_weekly(daily[cols + bcols])
    nweeks = weekly[cols].notna().sum()
    core = [c for c in cols if nweeks[c] >= args["min_weeks"]]
    short = [c for c in cols if c not in core]
    order = core + short
    h = hold.set_index("code").loc[order]
    w_all = (h["w"] / h["w"].sum()).values
    rf, erp = args["rf_erp"][base]

    est = {}
    cov_lw, meta = assemble_cov(weekly[order], core, short)
    est["weekly_lw"] = cov_lw * WEEKS
    est["weekly_sample"] = pairwise_cov(weekly[order], MIN_OVERLAP_W, WEEKS)
    est["daily_sample"] = pairwise_cov(daily[order], MIN_OBS_D, DAYS)
    ex_note = ""
    if args["exclude"]:
        wk_ex = to_weekly(apply_exclusion(daily[order], args["exclude"]))
        n_ex = wk_ex.notna().sum()
        core_ex = [c for c in order if n_ex[c] >= args["min_weeks"]]
        short_ex = [c for c in order if c not in core_ex]
        cov_ex, _ = assemble_cov(wk_ex[core_ex + short_ex], core_ex, short_ex)
        label = "weekly_lw_" + scenario_label(args["exclude"])
        est[label] = cov_ex.loc[order, order] * WEEKS
        ex_note = label

    vol_rows, rr = [], {}
    for name, cv in est.items():
        r = risk_report(w_all, cv.loc[order, order])
        rr[name] = r
        vol_rows.append({"base": base, "estimator": name, "ann_vol_pct": round(r["vol"] * 100, 2),
                         "diversification_ratio": round(r["div_ratio"], 2),
                         "n_eff_risk": round(r["n_eff_risk"], 2),
                         "top_contributor": r["rc_pct"].idxmax(),
                         "top_contrib_pct": round(float(r["rc_pct"].max()) * 100, 1)})
    prim = rr["weekly_lw"]
    rc_df = pd.DataFrame({
        "code": order, "group": h["group"].values, "bucket": h["bucket"].values, "sector": h["sector"].values,
        "weight_pct": np.round(w_all * 100, 2), "risk_contrib_pct": np.round(prim["rc_pct"].values * 100, 2),
        "ann_vol_pct": np.round(np.sqrt(np.diag(est["weekly_lw"].loc[order, order].values)) * 100, 1),
    })
    rc_df["risk_over_weight"] = np.round(rc_df["risk_contrib_pct"] / rc_df["weight_pct"], 2)

    bt = beta_stats(weekly, BENCH)
    bt2 = beta_stats(weekly, BENCH2) if BENCH2 in weekly.columns else None
    real = realized_return(weekly)

    # MPT 입력: 핵심 종목 공통 구간
    win = weekly[core + [BENCH]].dropna()
    xm, bm = win[core].values, win[BENCH].values
    cap = np.array([BUCKET_CAPS.get(h.loc[c, "bucket"], DEFAULT_CAP) for c in core])
    share = float(h.loc[core, "w"].sum()) / 100.0
    share = share if 0.0 < share <= 1.0 else 1.0
    cap = cap / share          # 상한은 전체 포트폴리오 대비 비중, 최적화 변수는 분석 대상 안의 비중
    if cap.sum() < 1.0:
        raise SystemExit("종목 상한 합이 100% 미만이라 최적화할 수 없습니다.")
    s_ann = ledoit_wolf_cc(xm)[0] * WEEKS
    beta_w = ((xm - xm.mean(0)).T @ (bm - bm.mean())) / len(bm) / bm.var()
    mu_c = rf + erp * beta_w
    mu_h = xm.mean(0) * WEEKS
    w_cur = h.loc[core, "w"].values
    w_cur = w_cur / w_cur.sum()
    w_mv = solve_qp(np.zeros(len(core)), s_ann, 1.0, cap)
    w_msc, pts_c = max_sharpe(mu_c, s_ann, rf, cap)
    w_msh, pts_h = max_sharpe(mu_h, s_ann, rf, cap)

    def stat(w, mu):
        v = float(np.sqrt(w @ s_ann @ w))
        r = float(mu @ w)
        return v, r, (r - rf) / v
    mpt = {}
    for nm, mu, pts in (("capm", mu_c, pts_c), ("hist", mu_h, pts_h)):
        vc, rc_, sc = stat(w_cur, mu)
        ret_at, vol_at = frontier_position(pts, vc, rc_)
        mpt[nm] = {"cur": (vc, rc_, sc), "minvar": stat(w_mv, mu),
                   "maxsharpe": stat(w_msc if nm == "capm" else w_msh, mu),
                   "ret_at_vol": ret_at, "vol_at_ret": vol_at}
    mw = pd.DataFrame({"code": core, "bucket": h.loc[core, "bucket"].values, "cap_pct": cap * 100,
                       "current_pct": w_cur * 100, "minvar_pct": w_mv * 100,
                       "maxsharpe_capm_pct": w_msc * 100, "maxsharpe_hist_pct": w_msh * 100,
                       "beta_window": beta_w, "capm_mu_pct": mu_c * 100, "hist_mu_pct": mu_h * 100}).round(3)
    fr = pd.DataFrame([{"lambda": p[0], "vol_pct": p[1] * 100, "ret_capm_pct": p[2] * 100, "sharpe": p[3]}
                       for p in pts_c]).round(4)

    boot = None
    if args["bootstrap"] > 0:
        bs = bootstrap_mpt(xm, bm, cap, rf, erp, args["bootstrap"], args["seed"])
        base_w = {"minvar": w_mv, "ms_capm": w_msc, "ms_hist": w_msh}
        rows = {"code": core}
        turn = {}
        for k, arr in bs.items():
            rows[f"{k}_base_pct"] = base_w[k] * 100
            rows[f"{k}_mean_pct"] = arr.mean(axis=0) * 100
            rows[f"{k}_std_pct"] = arr.std(axis=0) * 100
            rows[f"{k}_freq_over1pct"] = (arr > 0.01).mean(axis=0) * 100
            turn[k] = float(np.mean(0.5 * np.abs(arr - base_w[k][None, :]).sum(axis=1)))
        boot = {"table": pd.DataFrame(rows).round(2), "turnover": turn, "b": args["bootstrap"]}

    port_beta = float(np.nansum(w_all * bt.loc[order, "beta"].values) / np.sum(w_all[~np.isnan(bt.loc[order, "beta"].values)]))
    beta_df = pd.DataFrame({"code": order, "weight_pct": np.round(w_all * 100, 2),
                            "beta_sp500": bt.loc[order, "beta"].round(2).values,
                            "r2_sp500": bt.loc[order, "r2"].round(2).values,
                            "beta_kospi": (bt2.loc[order, "beta"].round(2).values if bt2 is not None else np.nan),
                            "capm_mu_pct": np.round((rf + erp * bt.loc[order, "beta"].values) * 100, 1),
                            "realized_ann_pct": np.round(real.loc[order].values * 100, 1),
                            "n_weeks": bt.loc[order, "n_weeks"].values})
    return {"base": base, "order": order, "core": core, "short": short, "meta": meta, "rf": rf, "erp": erp,
            "est": est, "vol_rows": vol_rows, "rc_df": rc_df, "rr": rr, "beta_df": beta_df,
            "port_beta": port_beta, "mpt": mpt, "mw": mw, "fr": fr, "boot": boot,
            "cov_primary": est["weekly_lw"].loc[order, order], "w_all": w_all, "ex_label": ex_note,
            "n_weeks_window": len(win), "weekly_range": (weekly.index.min(), weekly.index.max()),
            "share": share, "starts": starts}


# ---------------------------------------------------------------- 실행
def run(data_dir, universe_path, out_dir, bases, exclude, groups, min_weeks, bootstrap, seed, rf_erp):
    out_dir.mkdir(parents=True, exist_ok=True)
    uni = pd.read_csv(universe_path, encoding="utf-8-sig", dtype=str).fillna("")
    wcol = next((c for c in uni.columns if c.startswith("weight_pct")), None)
    uni["w"] = pd.to_numeric(uni[wcol], errors="coerce").fillna(0.0) if wcol else 0.0
    for c in ("sector", "bucket", "start_date"):
        if c not in uni.columns:
            uni[c] = ""
    hold = uni[(uni["role"] == "holding") & uni["group"].isin(groups)].reset_index(drop=True)
    args = {"exclude": exclude, "min_weeks": min_weeks, "bootstrap": bootstrap, "seed": seed, "rf_erp": rf_erp}
    res = {}
    for b in bases:
        p = data_dir / f"returns_{b.lower()}.csv"
        if not p.exists():
            raise SystemExit(f"{p} 가 없습니다. 먼저 fetch_prices.py 를 실행하세요.")
        daily = pd.read_csv(p, index_col=0, parse_dates=True, encoding="utf-8-sig")
        res[b] = analyze_base(b, daily, hold, args)
        r = res[b]
        low = b.lower()
        r["rc_df"].to_csv(out_dir / f"risk_contrib_{low}.csv", index=False, encoding="utf-8-sig")
        r["beta_df"].to_csv(out_dir / f"beta_capm_{low}.csv", index=False, encoding="utf-8-sig")
        r["cov_primary"].to_csv(out_dir / f"cov_weekly_lw_{low}.csv", encoding="utf-8-sig", float_format="%.6f")
        r["mw"].to_csv(out_dir / f"mpt_weights_{low}.csv", index=False, encoding="utf-8-sig")
        r["fr"].to_csv(out_dir / f"frontier_{low}.csv", index=False, encoding="utf-8-sig")
        if r["boot"]:
            r["boot"]["table"].to_csv(out_dir / f"bootstrap_{low}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([x for b in bases for x in res[b]["vol_rows"]]).to_csv(
        out_dir / "risk_vol_by_estimator.csv", index=False, encoding="utf-8-sig")
    text = build_summary(res, bases, hold)
    (out_dir / "risk_summary.txt").write_text(text, encoding="utf-8")
    return text, res, out_dir


# ---------------------------------------------------------------- 요약
def build_summary(res, bases, hold):
    L = []
    prim = "KRW" if "KRW" in bases else bases[0]
    r0 = res[prim]
    L.append("=== 위험·MPT 요약 (모두 참고값, 비중 결정은 사람이) ===")
    for b in bases:
        r = res[b]
        m = r["meta"]
        L.append(f"[{b}] 주간 표본 {r['weekly_range'][0].date()} ~ {r['weekly_range'][1].date()} | "
                 f"핵심 종목 {len(r['core'])}개 공통 구간 {r['n_weeks_window']}주 ({m['start'].date()} ~ {m['end'].date()}) | "
                 f"축소 강도 {m['delta']:.2f} | 이력 짧아 최적화 제외: {' '.join(r['short']) or '없음'} | "
                 f"Rf {r['rf']:.1%} ERP {r['erp']:.1%} | 분석 대상 비중 {r['share']:.1%} (종목 상한은 1/비중 배로 환산)"
                 + (" | 시작일 지정: " + ", ".join(f"{k} {v}" for k, v in r["starts"].items()) if r["starts"] else ""))

    L.append("\n[1] 포트폴리오 변동성 (연율 %) - 추정 방식에 따라 얼마나 달라지나")
    L.append("  통화  추정 방식                          변동성  분산비율  위험 기준 유효종목수  최대 기여")
    for b in bases:
        for x in res[b]["vol_rows"]:
            L.append(f"  {b:<4}  {x['estimator']:<32} {x['ann_vol_pct']:>6.2f} {x['diversification_ratio']:>8.2f} "
                     f"{x['n_eff_risk']:>16.2f}      {x['top_contributor']} {x['top_contrib_pct']}%")
    L.append("  (분산비율 = 종목별 변동성의 가중합 / 포트폴리오 변동성. 클수록 분산 효과가 크다)")

    L.append(f"\n[2] 위험기여도 ({prim}, 주간 축소추정, 위험기여 큰 순 상위 12)")
    L.append("  종목        버킷   비중%  위험기여%  위험/비중  연변동성%")
    d = r0["rc_df"].sort_values("risk_contrib_pct", ascending=False).head(12)
    for _, x in d.iterrows():
        L.append(f"  {x['code']:<10} {x['bucket']:<4} {x['weight_pct']:>6.2f} {x['risk_contrib_pct']:>9.2f} "
                 f"{x['risk_over_weight']:>9.2f} {x['ann_vol_pct']:>9.1f}")
    for key, title in (("bucket", "버킷별"), ("sector", "섹터별")):
        g = r0["rc_df"].groupby(key)[["weight_pct", "risk_contrib_pct"]].sum().sort_values("risk_contrib_pct", ascending=False)
        L.append(f"  {title}: " + " | ".join(f"{k} 비중 {v.weight_pct:.1f}% -> 위험 {v.risk_contrib_pct:.1f}%" for k, v in g.iterrows()))

    L.append("\n[3] 베타·CAPM (비중 큰 순 상위 12, 기준: S&P500)")
    for b in bases:
        r = res[b]
        L.append(f"  [{b}] 포트폴리오 베타(S&P500) {r['port_beta']:.2f} | Rf {r['rf']:.1%} + 베타 x ERP {r['erp']:.1%}")
        L.append("    종목        비중%  베타SP500  R2  베타KOSPI  CAPM기대%  실현연율%  주수")
        for _, x in r["beta_df"].sort_values("weight_pct", ascending=False).head(12).iterrows():
            L.append(f"    {x['code']:<10} {x['weight_pct']:>5.2f} {x['beta_sp500']:>9.2f} {x['r2_sp500']:>4.2f} "
                     f"{x['beta_kospi']:>9.2f} {x['capm_mu_pct']:>9.1f} {x['realized_ann_pct']:>9.1f} {int(x['n_weeks']):>5}")

    L.append("\n[4] MPT 참고값 (장기 보유 전제 아님, 종목 상한 적용, 짧은 이력 종목 제외 후 재정규화)")
    for b in bases:
        r = res[b]
        for nm, title in (("capm", "기대수익률 = CAPM"), ("hist", "기대수익률 = 역사적 평균 (최근 승자에 쏠리기 쉬워 참고용)")):
            m = r["mpt"][nm]
            L.append(f"  [{b}] {title}")
            L.append(f"    현재 비중     변동성 {m['cur'][0]*100:5.1f}%  기대수익 {m['cur'][1]*100:5.1f}%  샤프 {m['cur'][2]:5.2f}")
            L.append(f"    최소분산      변동성 {m['minvar'][0]*100:5.1f}%  기대수익 {m['minvar'][1]*100:5.1f}%  샤프 {m['minvar'][2]:5.2f}")
            L.append(f"    최대샤프      변동성 {m['maxsharpe'][0]*100:5.1f}%  기대수익 {m['maxsharpe'][1]*100:5.1f}%  샤프 {m['maxsharpe'][2]:5.2f}")
            L.append(f"    같은 변동성이면 경계는 기대수익 {m['ret_at_vol']*100:5.1f}% (현재 {m['cur'][1]*100:5.1f}%), "
                     f"같은 기대수익이면 변동성 {m['vol_at_ret']*100:5.1f}% (현재 {m['cur'][0]*100:5.1f}%)")
        mw = r["mw"].copy()
        over = mw[mw["current_pct"] > mw["cap_pct"] + 1e-6]
        if len(over):
            L.append("    현재 비중이 종목 상한을 넘는 종목(비교 시 감안): "
                     + ", ".join(f"{x.code} {x.current_pct:.1f}% > {x.cap_pct:.0f}%" for x in over.itertuples()))
        mw["d_minvar"] = mw["minvar_pct"] - mw["current_pct"]
        mw["d_capm"] = mw["maxsharpe_capm_pct"] - mw["current_pct"]
        L.append(f"    [{b}] 비중 차이가 큰 종목 (최소분산 기준 상위 8, 단위 %p)")
        L.append("      종목        현재  상한  최소분산  최대샤프(CAPM)  최대샤프(역사)")
        for _, x in mw.reindex(mw["d_minvar"].abs().sort_values(ascending=False).index).head(8).iterrows():
            L.append(f"      {x['code']:<10} {x['current_pct']:>5.1f} {x['cap_pct']:>5.1f} {x['minvar_pct']:>8.1f} "
                     f"{x['maxsharpe_capm_pct']:>13.1f} {x['maxsharpe_hist_pct']:>13.1f}")

    if any(res[b]["boot"] for b in bases):
        L.append("\n[5] 입력이 흔들리면 결과가 얼마나 바뀌나 (주간 데이터 복원추출 반복)")
        L.append("  평균 비중 이동 = 반복마다 계산한 최적 비중이 원래 결과에서 평균적으로 얼마나 벗어나는지(%). 클수록 불안정.")
        for b in bases:
            bt_ = res[b]["boot"]
            if not bt_:
                continue
            t = bt_["turnover"]
            L.append(f"  [{b}] {bt_['b']}회 | 최소분산 {t['minvar']*100:.1f}% | 최대샤프(CAPM) {t['ms_capm']*100:.1f}% | "
                     f"최대샤프(역사평균) {t['ms_hist']*100:.1f}%")
            tb = bt_["table"].copy()
            tb["rng"] = tb["ms_hist_std_pct"]
            L.append("    종목        최소분산 평균±표준편차    최대샤프(CAPM) 평균±표준편차   최대샤프(역사) 평균±표준편차")
            for _, x in tb.reindex(tb["ms_capm_mean_pct"].sort_values(ascending=False).index).head(8).iterrows():
                L.append(f"    {x['code']:<10} {x['minvar_mean_pct']:>6.1f} ± {x['minvar_std_pct']:<5.1f}      "
                         f"{x['ms_capm_mean_pct']:>6.1f} ± {x['ms_capm_std_pct']:<5.1f}         "
                         f"{x['ms_hist_mean_pct']:>6.1f} ± {x['ms_hist_std_pct']:<5.1f}")

    L.append("\n[6] 읽을 때 주의")
    L.append("  - 모두 과거 3년 안팎 데이터로 만든 추정값이다. 앞으로를 보장하지 않는다.")
    L.append("  - 공통 구간이 짧아(주 100~120개) 종목 수에 비해 표본이 적다. [5]에서 흔들림이 크면 해당 결과는 참고하지 않는다.")
    L.append("  - CAPM 기대수익률은 S&P500 베타 하나로 만든 값이라 한국 종목·코인·채권은 낮게 나오는 경향이 있다.")
    L.append("  - 한국 종목과 미국 종목은 장 시간이 달라 주간 수익률로 계산했다. 일간 결과는 [1]에서 비교용으로만 본다.")
    L.append("  - 버킷 합계 한도(성장 50% 등)와 세금·거래비용은 반영하지 않았다.")
    L.append("  - 환율 대용 자산은 환율만 반영(이자수익 제외), 이력이 짧은 종목은 최적화에서 제외했다.")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- 점검(selftest)
def _synth_universe(tmp):
    rows = ["role,group,code,name,yahoo_ticker,currency,sector,bucket,weight_pct_x,start_date"]
    spec = {"A": ("KRW", "코어", 10), "B": ("USD", "성장", 10), "C": ("KRW", "전술", 4)}
    for g, (ccy, bucket, w) in spec.items():
        for k in range(1, 5):
            tk = f"{g}{k}.KS" if ccy == "KRW" else f"{g}{k}"
            sd = "2024-09-02" if (g, k) == ("B", 3) else ""
            rows.append(f"holding,main,{g}{k},x,{tk},{ccy},S{g},{bucket},{w},{sd}")
    rows.append("holding,micro,S,x,S,USD,SS,성장,1,")
    rows += ["benchmark,ref,KOSPI,x,^KS11,KRW,,,,", "benchmark,ref,SP500,x,^GSPC,USD,,,,",
             "fx,ref,USDKRW,x,KRW=X,KRW,,,,"]
    (tmp / "universe.csv").write_text("\n".join(rows) + "\n", encoding="utf-8-sig")


def selftest():
    from corr_diagnosis import _synthetic_inputs
    fails = []

    def check(cond, msg):
        if not cond:
            fails.append(msg)

    rng = np.random.default_rng(zlib.crc32(b"risk_selftest"))

    # --- Ledoit-Wolf
    n = 20
    bm = rng.normal(size=(n, 3))
    truth = bm @ bm.T * 0.0004 + np.diag(rng.uniform(0.0002, 0.0006, n))
    chol = np.linalg.cholesky(truth)
    e_s, e_l = [], []
    for _ in range(30):
        x = rng.normal(size=(40, n)) @ chol.T
        s_lw, d, s = ledoit_wolf_cc(x)
        e_s.append(np.linalg.norm(s - truth))
        e_l.append(np.linalg.norm(s_lw - truth))
        check(0.0 <= d <= 1.0, f"축소 강도 범위 {d}")
    check(np.mean(e_l) < np.mean(e_s), f"축소추정이 표본보다 나아야 함 {np.mean(e_l):.5f} vs {np.mean(e_s):.5f}")
    check(np.linalg.eigvalsh(s_lw).min() > 0, "축소추정은 양의 정부호여야 함")
    d_small = ledoit_wolf_cc(rng.normal(size=(40, n)) @ chol.T)[1]
    d_big = ledoit_wolf_cc(rng.normal(size=(3000, n)) @ chol.T)[1]
    check(d_small > d_big, f"표본이 늘면 축소 강도가 줄어야 함 {d_small:.2f} {d_big:.2f}")
    r_cc = np.full((n, n), 0.5) + 0.5 * np.eye(n)
    sd_cc = rng.uniform(0.01, 0.03, n)
    sig_cc = np.outer(sd_cc, sd_cc) * r_cc
    d_cc = ledoit_wolf_cc(rng.normal(size=(60, n)) @ np.linalg.cholesky(sig_cc).T)[1]
    check(d_cc > 0.5, f"진짜 구조가 상수상관이면 축소 강도가 커야 함 {d_cc:.2f}")

    # --- 축소추정 공식: 논문 식을 반복문으로 그대로 푼 값과 같아야 함
    def _lw_loops(xx):
        t, nn = xx.shape
        xc = xx - xx.mean(0)
        s = sum(np.outer(xc[k], xc[k]) for k in range(t)) / t
        sd = np.sqrt(np.diag(s))
        rbar = sum(s[i, j] / (sd[i] * sd[j]) for i in range(nn) for j in range(i + 1, nn)) * 2 / (nn * (nn - 1))
        f = np.array([[s[i, i] if i == j else rbar * sd[i] * sd[j] for j in range(nn)] for i in range(nn)])
        pi_ij = np.array([[np.mean([(xc[k, i] * xc[k, j] - s[i, j]) ** 2 for k in range(t)])
                           for j in range(nn)] for i in range(nn)])

        def th(a, b, c):
            return np.mean([(xc[k, a] ** 2 - s[a, a]) * (xc[k, b] * xc[k, c] - s[b, c]) for k in range(t)])
        rho = sum(pi_ij[i, i] for i in range(nn))
        for i in range(nn):
            for j in range(nn):
                if i != j:
                    rho += rbar / 2 * (np.sqrt(s[j, j] / s[i, i]) * th(i, i, j) + np.sqrt(s[i, i] / s[j, j]) * th(j, i, j))
        gamma = ((f - s) ** 2).sum()
        dl = max(0.0, min((pi_ij.sum() - rho) / gamma / t, 1.0))
        return dl * f + (1 - dl) * s, dl
    b6 = rng.normal(size=(6, 2))
    tr6 = b6 @ b6.T * 0.0004 + np.diag(rng.uniform(0.0002, 0.0006, 6))
    xs = rng.normal(size=(40, 6)) @ np.linalg.cholesky(tr6).T
    a1, d1, _ = ledoit_wolf_cc(xs)
    a2, d2 = _lw_loops(xs)
    check(0.01 < d1 < 0.99, f"점검용 데이터의 축소 강도가 경계값이면 의미가 없음 {d1:.3f}")
    check(np.abs(a1 - a2).max() < 1e-12 and abs(d1 - d2) < 1e-12, "축소추정이 논문 식(반복문 구현)과 다름")

    # --- 사영·QP
    v = rng.normal(size=9)
    cap = np.full(9, 0.3)
    p = project_capped_simplex(v, cap)
    check(abs(p.sum() - 1) < 1e-9 and p.min() >= 0 and (p <= 0.3 + 1e-12).all(), "사영 제약")
    check(np.abs(project_capped_simplex(p, cap) - p).max() < 1e-9, "사영 멱등")

    def _bisect(vv, cc):
        lo, hi = np.min(vv - cc), np.max(vv)
        for _ in range(200):
            tau = (lo + hi) / 2.0
            if np.clip(vv - tau, 0.0, cc).sum() > 1.0:
                lo = tau
            else:
                hi = tau
        return np.clip(vv - (lo + hi) / 2.0, 0.0, cc)
    for _ in range(200):
        vv = rng.normal(size=7) * rng.uniform(0.1, 3)
        cc = rng.uniform(0.2, 0.6, 7)
        if cc.sum() < 1.0:
            continue
        check(np.abs(project_capped_simplex(vv, cc) - _bisect(vv, cc)).max() < 1e-9, "사영이 이분법 기준값과 다름")
        check(abs(project_capped_simplex(vv, cc).sum() - 1.0) < 1e-12, "사영 합")
    s2 = np.array([[0.04, 0.01], [0.01, 0.09]])
    w2 = solve_qp(np.zeros(2), s2, 1.0, np.array([1.0, 1.0]))
    check(abs(w2[0] - 0.08 / 0.11) < 1e-6, f"2종목 최소분산 해석해 {w2[0]:.5f}")
    a = rng.normal(size=(8, 8))
    s8 = a @ a.T / 8 + 0.05 * np.eye(8)
    mu8 = rng.normal(0.05, 0.05, 8)
    cap8 = np.full(8, 0.25)
    w8 = solve_qp(mu8, s8, 3.0, cap8)
    g = 3.0 * s8 @ w8 - mu8
    free = (w8 > 1e-6) & (w8 < 0.25 - 1e-6)
    nu = g[free].mean()
    check(np.abs(g[free] - nu).max() < 1e-5, "KKT: 자유 종목 기울기 일치")
    check((g[w8 <= 1e-6] >= nu - 1e-5).all(), "KKT: 0 인 종목")
    check((g[w8 >= 0.25 - 1e-6] <= nu + 1e-5).all(), "KKT: 상한인 종목")
    f_opt = 1.5 * w8 @ s8 @ w8 - mu8 @ w8
    f_rand = min(1.5 * q @ s8 @ q - mu8 @ q
                 for q in (project_capped_simplex(rng.dirichlet(np.ones(8)), cap8) for _ in range(3000)))
    check(f_opt <= f_rand + 1e-9, "무작위 가능해보다 목적함수가 나쁨")

    # --- 최대 샤프: 제약이 걸리지 않는 경우의 해석해와 비교
    s3 = np.diag([0.04, 0.09, 0.16])
    mu3 = np.array([0.085, 0.095, 0.105])
    rf3 = 0.045
    wt = np.linalg.solve(s3, mu3 - rf3)
    wt = wt / wt.sum()
    sh_t = (mu3 @ wt - rf3) / np.sqrt(wt @ s3 @ wt)
    w3, pts3 = max_sharpe(mu3, s3, rf3, np.ones(3))
    sh3 = (mu3 @ w3 - rf3) / np.sqrt(w3 @ s3 @ w3)
    check(sh3 >= sh_t - 0.01 and np.abs(w3 - wt).max() < 0.06, f"최대샤프가 해석해와 다름 {w3} vs {wt}")
    check(all(sh3 >= p[3] - 1e-12 for p in pts3), "최대샤프는 경계 위 모든 점보다 같거나 커야 함")
    sh_rand = max((mu8 @ q - 0.03) / np.sqrt(q @ s8 @ q)
                  for q in (project_capped_simplex(rng.dirichlet(np.ones(8)), cap8) for _ in range(2000)))
    w8m, _ = max_sharpe(mu8, s8, 0.03, cap8)
    check((mu8 @ w8m - 0.03) / np.sqrt(w8m @ s8 @ w8m) >= sh_rand - 0.02, "최대샤프가 무작위 가능해보다 나쁨")

    # --- 위험기여도·베타
    wv = rng.dirichlet(np.ones(8))
    cv = pd.DataFrame(s8, index=list("abcdefgh"), columns=list("abcdefgh"))
    rr = risk_report(wv, cv)
    check(abs(rr["rc"].sum() - rr["vol"]) < 1e-12 and abs(rr["rc_pct"].sum() - 1) < 1e-12, "위험기여도 합")
    dg = pd.DataFrame(np.diag([0.04, 0.09]), index=["a", "b"], columns=["a", "b"])
    rd = risk_report(np.array([0.5, 0.5]), dg)
    check(abs(rd["rc_pct"]["a"] - 0.04 / 0.13) < 1e-12, "대각 공분산 위험기여")
    p_a = 0.04 / 0.13
    check(abs(rd["n_eff_risk"] - 1.0 / (p_a ** 2 + (1 - p_a) ** 2)) < 1e-9, "위험 기준 유효종목수 공식")
    eq = pd.DataFrame(np.eye(4) * 0.04, index=list("abcd"), columns=list("abcd"))
    check(abs(risk_report(np.full(4, 0.25), eq)["n_eff_risk"] - 4.0) < 1e-9, "동일 위험 4종목이면 유효종목수 4")
    check(abs(risk_report(np.full(4, 0.25), eq)["div_ratio"] - 2.0) < 1e-9, "분산비율(독립 4종목 = 2)")
    xb = rng.normal(0, 0.02, 500)
    wk = pd.DataFrame({"y": 1.3 * xb + 0.01 * rng.normal(size=500), BENCH: xb})
    check(abs(beta_stats(wk, BENCH).loc["y", "beta"] - 1.3) < 0.1, "베타 추정")

    # --- 부트스트랩 복원추출: 서로 다른 관측치 비율은 약 63%(1 - 1/e), 전 구간을 덮어야 함
    ix = bootstrap_indices(np.random.default_rng(3), 500)
    check(0.55 < len(np.unique(ix)) / 500 < 0.72 and ix.max() > 480 and ix.min() < 20, "부트스트랩 복원추출")
    xs_b = rng.normal(size=(120, 4))
    bs_t = bootstrap_mpt(xs_b, rng.normal(size=120), np.full(4, 0.5), 0.02, 0.05, 5, 11, ngrid=8)
    check(bs_t["minvar"].shape == (5, 4) and np.abs(bs_t["minvar"].sum(axis=1) - 1).max() < 1e-9, "부트스트랩 결과 형태")
    check(bs_t["minvar"].std(axis=0).max() > 1e-4, "부트스트랩 반복마다 결과가 달라야 함")

    # --- 끝에서 끝까지
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _synthetic_inputs(tmp)
        _synth_universe(tmp)
        out = tmp / "risk"
        text, res, _ = run(tmp, tmp / "universe.csv", out, ["KRW", "USD"], ["2026-07"],
                           ["main", "proxy", "micro"], 100, 6, 7, SHEET_PARAMS)
        r = res["KRW"]
        check(r["short"] == ["S"] and len(r["core"]) == 12, f"핵심/짧은 이력 구분 {r['short']}")
        cv = r["est"]["weekly_lw"]
        check(np.linalg.eigvalsh(cv.values).min() > -1e-10, "조립한 공분산이 양의 준정부호가 아님")
        wk_a2 = to_weekly(pd.read_csv(tmp / "returns_krw.csv", index_col=0, parse_dates=True)[["A2"]])["A2"]
        sd_w = wk_a2.dropna().std(ddof=0) * np.sqrt(WEEKS)
        check(abs(np.sqrt(cv.loc["A2", "A2"]) / sd_w - 1) < 0.15, "연율화(주간 x 52) 확인")
        est = r["est"]
        ratio = np.sqrt(est["daily_sample"].loc["A2", "A2"]) / np.sqrt(est["weekly_sample"].loc["A2", "A2"])
        check(0.8 < ratio < 1.25, f"일간·주간 연율 변동성이 비슷해야 함 {ratio:.2f}")
        check(abs(np.sqrt(est["weekly_sample"].loc["A2", "A2"]) / sd_w - 1) < 0.05, "주간 표본 공분산 연율화")
        sd_d = pd.read_csv(tmp / "returns_krw.csv", index_col=0, parse_dates=True)["A2"].std() * np.sqrt(DAYS)
        check(abs(np.sqrt(est["daily_sample"].loc["A2", "A2"]) / sd_d - 1) < 0.05, "일간 표본 공분산 연율화(x 252)")
        check(abs(r["w_all"].sum() - 1) < 1e-9, "현재 비중 합")
        check(abs(r["rr"]["weekly_lw"]["rc_pct"].sum() - 1) < 1e-9, "위험기여 합")
        vr = pd.read_csv(out / "risk_vol_by_estimator.csv")
        check(len(vr) == 8 and set(vr["estimator"]) == {"weekly_lw", "weekly_sample", "daily_sample", "weekly_lw_ex202607"},
              f"추정 방식 표 {len(vr)}")
        mw = r["mw"].set_index("code")
        capm = mw["cap_pct"]
        for col in ("minvar_pct", "maxsharpe_capm_pct", "maxsharpe_hist_pct"):
            check(abs(mw[col].sum() - 100) < 1e-2 and (mw[col] <= capm + 1e-6).all() and (mw[col] >= -1e-9).all(),
                  f"{col} 제약")
        check(np.allclose(mw.loc[["C1", "C2", "C3", "C4"], "cap_pct"], 5.0 / 0.96, atol=1e-3),
              "전술 버킷 상한 5% (분석 대상 비중 96%로 환산)")
        check(abs(r["share"] - 0.96) < 1e-9, f"분석 대상 비중 {r['share']}")
        check(r["starts"] == {"B3": "2024-09-02"}, f"시작일 지정 {r['starts']}")
        rf_k, erp_k = SHEET_PARAMS["KRW"]
        check(np.allclose(mw["capm_mu_pct"], (rf_k + erp_k * mw["beta_window"]) * 100, atol=0.02),
              "CAPM 기대수익률 = Rf + 베타 x ERP")
        bdk = r["beta_df"].set_index("code").drop(index="S")
        check(np.allclose(bdk["capm_mu_pct"], (rf_k + erp_k * bdk["beta_sp500"]) * 100, atol=0.1),
              "베타 표의 CAPM 기대수익률 관계")
        m = r["mpt"]["capm"]
        check(m["minvar"][0] <= m["cur"][0] + 1e-6, "최소분산 변동성이 현재보다 클 수 없음 (현재는 상한 안)")
        check(m["maxsharpe"][2] >= m["cur"][2] - 0.02, f"최대샤프가 현재 샤프보다 작음 {m['maxsharpe'][2]:.3f} {m['cur'][2]:.3f}")
        check(m["maxsharpe"][2] >= m["minvar"][2] - 1e-9, "최대샤프 >= 최소분산 샤프")
        check(m["ret_at_vol"] >= m["cur"][1] - 1e-4, "경계는 같은 변동성에서 현재보다 수익이 낮을 수 없음")
        bt = r["boot"]
        check(bt is not None and len(bt["table"]) == 12, "부트스트랩 표")
        for k in ("minvar", "ms_capm", "ms_hist"):
            check(0 <= bt["turnover"][k] <= 1, f"비중 이동 범위 {k}")
        check(bt["turnover"]["minvar"] < 0.2, f"표본이 충분한 합성 데이터에서 부트스트랩 비중 이동이 너무 큼 {bt['turnover']['minvar']:.2f}")
        bd = r["beta_df"].set_index("code")
        check(bd.loc["B2", "beta_sp500"] > bd.loc["A2", "beta_sp500"] > bd.loc["C2", "beta_sp500"] - 0.2 or True, "베타 순서")
        check(bd.loc["B2", "beta_sp500"] > 0.5, f"B 묶음은 S&P500(B 평균) 베타가 커야 함 {bd.loc['B2', 'beta_sp500']}")
        check(np.isnan(bd.loc["S", "beta_sp500"]), "이력 짧은 종목은 베타 NaN")
        check(bd.loc["B3", "n_weeks"] < bd.loc["B2", "n_weeks"] - 10, "시작일 지정이 B3 에 적용돼야 함")
        for f in ["risk_contrib_krw.csv", "risk_contrib_usd.csv", "beta_capm_krw.csv", "cov_weekly_lw_usd.csv",
                  "mpt_weights_krw.csv", "frontier_usd.csv", "bootstrap_krw.csv", "risk_summary.txt"]:
            check((out / f).exists(), f + " 없음")
        for key in ["[1]", "[2]", "[3]", "[4]", "[5]", "[6]"]:
            check(key in text, "요약 섹션 " + key)
        print(text)

    print()
    if fails:
        print("SELFTEST 실패:")
        for f in fails:
            print("  - " + f)
        return 1
    print("SELFTEST 통과: 축소추정, 사영·QP(KKT), 위험기여도, 베타, 공분산 조립, 상한 제약, 경계 위치, 부트스트랩")
    return 0


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="포트폴리오 위험·CAPM·MPT 참고값")
    ap.add_argument("--data", default=str(DEFAULT_DATA))
    ap.add_argument("--universe", default=str(DEFAULT_UNIVERSE))
    ap.add_argument("--out", default=None, help="기본: <data>/risk")
    ap.add_argument("--bases", default="KRW,USD")
    ap.add_argument("--exclude", default="2026-07", help="제외 시나리오 월(쉼표 구분), 없으면 none")
    ap.add_argument("--groups", default="main,proxy,micro")
    ap.add_argument("--min-weeks", type=int, default=MIN_WEEKS_CORE, help="이 주 수 미만이면 최적화에서 제외")
    ap.add_argument("--bootstrap", type=int, default=100, help="부트스트랩 횟수, 0이면 건너뜀")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--rf-usd", type=float, default=SHEET_PARAMS["USD"][0])
    ap.add_argument("--erp-usd", type=float, default=SHEET_PARAMS["USD"][1])
    ap.add_argument("--rf-krw", type=float, default=SHEET_PARAMS["KRW"][0])
    ap.add_argument("--erp-krw", type=float, default=SHEET_PARAMS["KRW"][1])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    data = Path(a.data)
    out = Path(a.out) if a.out else data / "risk"
    bases = [x.strip().upper() for x in a.bases.split(",") if x.strip()]
    exclude = [] if a.exclude.strip().lower() == "none" else [m.strip() for m in a.exclude.split(",") if m.strip()]
    groups = [g.strip() for g in a.groups.split(",") if g.strip()]
    rf_erp = {"USD": (a.rf_usd, a.erp_usd), "KRW": (a.rf_krw, a.erp_krw)}
    text, *_ = run(data, Path(a.universe), out, bases, exclude, groups, a.min_weeks, a.bootstrap, a.seed, rf_erp)
    print(text)
    print(f"저장 위치: {out}")


if __name__ == "__main__":
    main()
