"""
estimate_aggregator.py - Layer 2 Aggregation Engine
소스별 추정치를 통계적으로 집계하여 대표값과 신뢰도를 산출합니다.
(API 불필요 - CV 기반 자동 판별만 수행)
"""
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DISCREPANCY_THRESHOLD = 0.15  # CV 15% 초과 시 낮은 신뢰도


def aggregate_estimates(ticker: str, metric: str) -> dict:
    """
    Layer 1에서 소스별 최신 추정치를 가져와 통계 집계.
    Returns: {value, confidence, cv, n_sources, ...}
    """
    from pipeline.layer1_store import get_all_estimates
    records = get_all_estimates(ticker)

    # metric이 포함된 record만 필터 (fwd_pe의 경우 fwd_pe_ntm, fwd_pe_fy 모두 포함)
    subset = []
    for r in records:
        if metric == "forward_pe":
            # NTM과 FY를 모두 수집
            val = r.get("fwd_pe_ntm") or r.get("fwd_pe_fy")
            if val is not None:
                subset.append({"source": r["source"], "as_of": r["as_of"], "value": val})
        else:
            if r.get(metric) is not None:
                subset.append({"source": r["source"], "as_of": r["as_of"], "value": r[metric]})

    # 소스별 최신 데이터만 사용
    latest_by_source = {}
    for r in subset:
        src = r["source"]
        if src not in latest_by_source or r["as_of"] >= latest_by_source[src]["as_of"]:
            latest_by_source[src] = r

    values = []
    for src, r in latest_by_source.items():
        if r.get("value") is not None:
            values.append(r["value"])

    if not values:
        return {"value": "", "confidence": "", "cv": 0.0, "n_sources": 0}

    arr = np.array(values)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr))
    cv = std_val / mean_val if mean_val != 0 else 0

    # 대표값: 3개 이상이면 이상치 제거 후 중앙값, 아니면 단순 중앙값
    if len(arr) >= 3:
        p25, p75 = np.percentile(arr, [25, 75])
        iqr = p75 - p25
        clean = arr[(arr >= p25 - 1.5 * iqr) & (arr <= p75 + 1.5 * iqr)]
        rep_val = float(np.median(clean)) if len(clean) > 0 else float(np.median(arr))
    else:
        rep_val = float(np.median(arr))

    # 신뢰도 판별
    if len(values) == 1:
        confidence = ""  # 소스가 1개면 비교 불가, 빈칸
    elif cv < 0.08:
        confidence = "높음"
    elif cv < DISCREPANCY_THRESHOLD:
        confidence = "보통"
    else:
        confidence = "낮음"

    return {
        "value": round(rep_val, 2),
        "confidence": confidence,
        "cv": round(cv, 3),
        "n_sources": len(values),
    }
