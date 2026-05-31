"""
sheet_updater.py
────────────────
구글 시트 자동 업데이트 모듈

로컬 data/valuation/ 폴더의 분석 데이터를 구글 스프레드시트의
"🔬 기업분석" 탭(H~V열)과 "📐 밸류계산" 탭에 자동 기록합니다.

사용법:
    python sheet_updater.py                  # 전체 포트폴리오 업데이트
    python sheet_updater.py --ticker 009150  # 특정 종목만 업데이트
    python sheet_updater.py --ticker NVDA    # 미국 주식 업데이트
"""

from __future__ import annotations

import sys
import os
import time
import argparse
from datetime import date
from pathlib import Path

# Windows cp949 인코딩 오류 방지
if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from gsheet_auth import get_client, get_sheet_id
from valuation_app.audit import run_audit
from valuation_app.repository import load_market_data, load_metric_observations

DATA_ROOT = ROOT / "data" / "valuation"

# 시트 GID 상수
GID_ANALYSIS = 1127641143   # 🔬 기업분석
GID_VALUATION = 1931209348  # 📐 밸류계산

# ETF/비분석 대상 티커 (자동 스킵)
SKIP_TICKERS = {
    "SOXX", "QQQM", "ARKF", "BTC", "브라질채권",
    "361580", "360750", "481180", "461900", "461300",
}

# 억 원 변환 상수
OEK = 100_000_000  # 1억


def _sanitize_text(text: str) -> str:
    """시트 기록 전 텍스트 안전 처리: & 기호 제거 등"""
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    return text.replace("&", "and")


def _to_eok(value, currency: str = "KRW") -> float | str:
    """값을 억 원 단위로 변환. 변환 불가능하면 빈 문자열 반환."""
    if value is None:
        return ""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if currency in ("USD", "달러"):
        # USD 종목은 달러 그대로 억 달러 단위로 변환
        return round(v / 100_000_000, 1)  # 1억 달러 단위
    return round(v / OEK, 1)


def _safe_ratio(numerator, denominator, pct: bool = False) -> float | str:
    """안전한 나눗셈. pct=True이면 백분율로 반환."""
    if numerator is None or denominator is None:
        return ""
    try:
        n, d = float(numerator), float(denominator)
    except (TypeError, ValueError):
        return ""
    if d == 0:
        return ""
    result = n / d
    if pct:
        result *= 100
    return round(result, 2)


def _yoy_growth(observations: list, metric_key: str) -> float | str:
    """최근 2개년 YoY 성장률(%) 계산."""
    yearly = []
    for obs in observations:
        mk = getattr(obs, 'metric_key', None) or (obs.get('metric_key') if isinstance(obs, dict) else None)
        period = getattr(obs, 'period', None) or (obs.get('period') if isinstance(obs, dict) else None)
        val = getattr(obs, 'value', None)
        if val is None and isinstance(obs, dict):
            val = obs.get('value')
        
        if mk == metric_key and period and period.endswith("A") and val is not None:
            try:
                year = int(period[:-1])
                yearly.append((year, float(val)))
            except (ValueError, TypeError):
                continue
    
    if len(yearly) < 2:
        return ""
    
    yearly.sort(key=lambda x: x[0], reverse=True)
    latest, prev = yearly[0][1], yearly[1][1]
    if prev == 0:
        return ""
    return round((latest - prev) / abs(prev) * 100, 1)


def _per_change_1y(ticker: str, market: dict, all_observations: list) -> float | str:
    """1년 전 PER과 현재 PER의 변화량을 계산합니다."""
    # 1. 1년 전 주가 조회 (yfinance 활용, .KS/.KQ 둘 다 대응)
    import yfinance as yf
    from datetime import datetime, timedelta
    
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)
    
    try:
        hist = None
        if ticker.isdigit() and len(ticker) == 6:
            # 먼저 .KS 시도
            yf_ticker = yf.Ticker(f"{ticker}.KS")
            hist = yf_ticker.history(
                start=(one_year_ago - timedelta(days=7)).strftime("%Y-%m-%d"),
                end=one_year_ago.strftime("%Y-%m-%d")
            )
            if hist.empty:
                # 실패 시 .KQ 시도
                yf_ticker = yf.Ticker(f"{ticker}.KQ")
                hist = yf_ticker.history(
                    start=(one_year_ago - timedelta(days=7)).strftime("%Y-%m-%d"),
                    end=one_year_ago.strftime("%Y-%m-%d")
                )
        else:
            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(
                start=(one_year_ago - timedelta(days=7)).strftime("%Y-%m-%d"),
                end=one_year_ago.strftime("%Y-%m-%d")
            )
            
        if hist is None or hist.empty:
            return ""
            
        price_1y = float(hist.iloc[-1]['Close'])
        
        # 2. 연도별 EPS 추출
        eps_by_year = {}
        for obs in all_observations:
            mk = getattr(obs, 'metric_key', None) or (obs.get('metric_key') if isinstance(obs, dict) else None)
            period = getattr(obs, 'period', None) or (obs.get('period') if isinstance(obs, dict) else None)
            val = getattr(obs, 'value', None)
            if val is None and isinstance(obs, dict):
                val = obs.get('value')
                
            if mk == "eps" and period and period.endswith("A") and val is not None:
                try:
                    year = int(period[:-1])
                    eps_by_year[year] = float(val)
                except (ValueError, TypeError):
                    continue
                    
        if not eps_by_year:
            return ""
            
        years = sorted(eps_by_year.keys(), reverse=True)
        if len(years) < 2:
            return ""
            
        latest_year = years[0]
        prev_year = years[1]
        
        eps_latest = eps_by_year[latest_year]
        eps_prev = eps_by_year[prev_year]
        
        if eps_latest <= 0 or eps_prev <= 0:
            return ""
            
        per_1y = price_1y / eps_prev
        current_price = float(market.get("price", 0))
        if current_price <= 0:
            return ""
            
        per_current = current_price / eps_latest
        diff = per_current - per_1y
        if abs(diff) > 100:
            print(f"  ℹ️ {ticker}: 최근 1년 PER 변화량이 극단적입니다 ({diff:+.2f}배)")
            print(f"    - 1년 전 PER: {price_1y:,.2f} / {eps_prev} = {per_1y:,.2f}배")
            print(f"    - 현재 PER: {current_price:,.2f} / {eps_latest} = {per_current:,.2f}배")
            print(f"    - 원인 분석: EPS가 {eps_prev}에서 {eps_latest}로 변화하며 멀티플의 급격한 팽창/압축 발생 (정상 계산 결과)")
        return round(diff, 2)
        
    except Exception as e:
        print(f"  ⚠️ {ticker}: PER변화1Y 계산 중 에러 — {e}")
        return ""


def _discover_local_tickers() -> list[str]:
    """data/valuation/ 폴더에서 분석 가능한 종목 ID 목록을 반환."""
    tickers = []
    if not DATA_ROOT.exists():
        return tickers
    for d in sorted(DATA_ROOT.iterdir()):
        if d.is_dir() and (d / "normalized" / "metrics.json").exists():
            tickers.append(d.name)
    return tickers


def _find_ticker_row(ws, ticker: str) -> int | None:
    """기업분석 탭의 B열에서 해당 티커의 행 번호를 찾음."""
    b_col = ws.col_values(2)  # B열 전체
    
    # 한국 주식 6자리 vs 시트 내 0 제거된 표기 대응
    ticker_variants = {ticker}
    if ticker.isdigit():
        ticker_variants.add(ticker.lstrip("0"))  # 009150 → 9150
        ticker_variants.add(str(int(ticker)))     # 009150 → 9150
    
    for idx, cell_val in enumerate(b_col):
        cell_str = str(cell_val).strip()
        if cell_str in ticker_variants:
            return idx + 1  # 1-indexed
    
    return None


def update_analysis_tab(
    ticker: str,
    input_set,
    market: dict,
    all_observations: list,
    ws=None,
    doc=None,
) -> bool:
    """
    기업분석 탭의 H~V열을 업데이트합니다.
    
    Returns:
        True if updated, False if skipped
    """
    if ws is None:
        if doc is None:
            client = get_client()
            doc = client.open_by_key(get_sheet_id())
        for sheet in doc.worksheets():
            if sheet.id == GID_ANALYSIS:
                ws = sheet
                break
        if ws is None:
            print(f"  ⚠️ 기업분석 탭을 찾을 수 없습니다.")
            return False
    
    row = _find_ticker_row(ws, ticker)
    if row is None:
        print(f"  ⚠️ 티커 {ticker}를 기업분석 탭에서 찾을 수 없습니다.")
        return False
    
    inp = input_set.inputs
    currency = market.get("currency", "원")
    
    # 각 컬럼 값 계산
    ev_fcf = _safe_ratio(inp.get("enterprise_value"), inp.get("fcf"))
    pbr = _safe_ratio(market.get("market_cap"), inp.get("total_equity"))
    rev_growth = _yoy_growth(all_observations, "revenue")
    op_margin = _safe_ratio(inp.get("operating_income"), inp.get("revenue"), pct=True)
    roic_pct = ""
    if inp.get("roic") is not None:
        try:
            roic_pct = round(float(inp["roic"]) * 100, 2)
        except (TypeError, ValueError):
            roic_pct = ""
    fcf_growth = _yoy_growth(all_observations, "fcf")
    update_date = date.today().isoformat()
    
    # H~V 열 업데이트 (J, Q열은 수식이므로 건너뜀, R~U는 사용자 영역)
    # H=8, I=9, J=10(skip), K=11, L=12, M=13, N=14, O=15, P=16, Q=17(skip)
    # R=18, S=19, T=20, U=21, V=22
    
    # 기존 R~U값 읽기 (사용자 입력 보호)
    existing_ru = ws.get_values(f"R{row}:U{row}")
    has_existing_ru = existing_ru and existing_ru[0] and any(str(v).strip() for v in existing_ru[0])
    
    # 리포트 컨텍스트 로드
    report_ctx = {}
    report_path = ROOT / "data" / "report_context" / f"{ticker}.json"
    if report_path.exists():
        import json
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report_ctx = json.load(f)
        except Exception:
            pass
            
    # 산업 맥락 로드하여 글로벌 Peer PER 가져오기
    from valuation_app.industry_researcher import IndustryResearcher
    researcher = IndustryResearcher()
    ctx = researcher.load_context(ticker)
    
    # Layer 1 Unified Metrics 로드 (개념 지도 기반 Fallback 로직 적용)
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from pipeline.unified_metrics import get_unified_metrics
    unified = get_unified_metrics(ticker)
    
    pe_ratio = unified.get("pe_ratio", "")
    ps_ratio = unified.get("ps_ratio", "")
    
    if unified.get("pb_ratio") is not None:
        pbr = unified["pb_ratio"]
        
    if unified.get("roic") is not None:
        roic_pct = unified["roic"]
        
    if unified.get("op_margin") is not None:
        op_margin = unified["op_margin"]
        
    if unified.get("fcf_margin") is not None:
        # FCF 마진이 있으면 어떻게 처리할지 (현재는 O열 ROIC, P열 FCF성장률, H열 EV/FCF 사용)
        pass
    
    # K열 우선순위: 리포트의 peer_target_per > industry_context의 peer_per > market의 peer_average_per
    report_metrics = report_ctx.get("metrics", {})
    peer_per = report_metrics.get("peer_target_per") or ctx.get("peer_per") or market.get("peer_average_per") or ""

    updates = []
    # K4 셀 헤더 이름을 "섹터PER대비%"로 지정
    updates.append({"range": "K4", "values": [["섹터PER대비%"]]})
    
    # E열 (col 5) - 현재가
    updates.append({"range": f"E{row}", "values": [[market.get("price", "")]]})
    # F열 (col 6) - 시총(억)
    updates.append({"range": f"F{row}", "values": [[_to_eok(market.get("market_cap"), market.get("currency", "원"))]]})
    
    # G열 (col 7) - PER
    updates.append({"range": f"G{row}", "values": [[pe_ratio]]})
    # H열 (col 8) - EV/FCF 
    updates.append({"range": f"H{row}", "values": [[ev_fcf]]})
    # I열 (col 9) - PBR
    updates.append({"range": f"I{row}", "values": [[pbr]]})
    # PSR은 시트에 열이 없으므로 쓰지 않음
    # J열 - EV/EBITDA (기존 스킵 유지)
    
    # K열 (col 11) - 섹터PER대비%
    if peer_per:
        try:
            peer_per_val = float(peer_per)
            if peer_per_val > 0:
                sector_per_vs_pct = f"=IF(G{row}, ROUND(G{row}/{peer_per_val}*100, 1), 0)"
            else:
                sector_per_vs_pct = ""
        except (ValueError, TypeError):
            sector_per_vs_pct = ""
    else:
        sector_per_vs_pct = ""
    updates.append({"range": f"K{row}", "values": [[sector_per_vs_pct]]})
    # L열 (col 12) - PER변화1Y
    per_change_1y = _per_change_1y(ticker, market, all_observations)
    updates.append({"range": f"L{row}", "values": [[per_change_1y]]})
    # M열 (col 13) - 매출성장률%
    updates.append({"range": f"M{row}", "values": [[rev_growth]]})
    # N열 (col 14) - 영업마진%
    updates.append({"range": f"N{row}", "values": [[op_margin]]})
    # O열 (col 15) - ROIC%
    updates.append({"range": f"O{row}", "values": [[roic_pct]]})
    # P열 (col 16) - FCF성장률%
    updates.append({"range": f"P{row}", "values": [[fcf_growth]]})
    # V열 (col 22) - 업데이트일
    updates.append({"range": f"V{row}", "values": [[update_date]]})
    
    # W~AK열 (애널리스트, 적정가, 점수 등 Raw Data 성격 지표)은 
    # 기업분석 탭 다이어트를 위해 시트에서 물리적으로 삭제되었으므로 업데이트하지 않습니다.

    
    # 사용자 영역(R~U)이 비어있으면 기본값 입력
    if not has_existing_ru:
        updates.append({"range": f"R{row}", "values": [["분석 필요"]]})
        updates.append({"range": f"S{row}", "values": [["일부"]]})
        updates.append({"range": f"T{row}", "values": [["유지"]]})
    
    ws.batch_update(updates, value_input_option="USER_ENTERED")
    print(f"  ✅ 기업분석 탭 Row {row} 업데이트 완료 ({ticker})")
    return True


def update_valuation_tab(
    ticker: str,
    input_set,
    market: dict,
    ws=None,
    doc=None,
) -> bool:
    """
    밸류계산 탭의 입력 셀을 업데이트합니다.
    수식 셀(B15, B17 등)은 절대 건드리지 않습니다.
    
    Returns:
        True if updated, False if skipped
    """
    if ws is None:
        if doc is None:
            client = get_client()
            doc = client.open_by_key(get_sheet_id())
        for sheet in doc.worksheets():
            if sheet.id == GID_VALUATION:
                ws = sheet
                break
        if ws is None:
            print(f"  ⚠️ 밸류계산 탭을 찾을 수 없습니다.")
            return False
    
    inp = input_set.inputs
    currency = market.get("currency", "원")
    is_usd = currency in ("USD", "달러")
    
    # 단위 변환 (억 원 기준, USD는 억 달러)
    divider = OEK
    
    company_name = _sanitize_text(market.get("company_name", ticker))
    tax_rate = 21 if is_usd else 22
    
    # 입력 셀만 업데이트 (수식 셀 제외)
    updates = [
        # Row 3: 종목 기본 정보
        {"range": "A3", "values": [[company_name]]},
        {"range": "B3", "values": [[ticker]]},
        {"range": "C3", "values": [[date.today().isoformat()]]},
        # Row 8: 법인세율
        {"range": "B8", "values": [[tax_rate]]},
        # Row 12: 시가총액
        {"range": "B12", "values": [[_to_eok(market.get("market_cap"), currency)]]},
        # Row 13: 순부채
        {"range": "B13", "values": [[_to_eok(inp.get("net_debt"), currency)]]},
        # Row 14: FCF
        {"range": "B14", "values": [[_to_eok(inp.get("fcf"), currency)]]},
        # Row 20: EBIT (영업이익)
        {"range": "B20", "values": [[_to_eok(inp.get("operating_income"), currency)]]},
        # Row 27: PBR
        {"range": "B27", "values": [[_safe_ratio(market.get("market_cap"), inp.get("total_equity"))]]},
        # Row 36: 청산가치 (자본총계)
        {"range": "B36", "values": [[_to_eok(inp.get("total_equity"), currency)]]},
        # Row 37: 투자자본
        {"range": "B37", "values": [[_to_eok(inp.get("invested_capital"), currency)]]},
    ]
    
    ws.batch_update(updates, value_input_option="USER_ENTERED")
    print(f"  ✅ 밸류계산 탭 업데이트 완료 ({company_name} / {ticker})")
    return True


def update_single_ticker(ticker: str, update_valuation: bool = True) -> bool:
    """
    단일 종목의 기업분석 탭과 밸류계산 탭을 업데이트합니다.
    """
    metrics_path = DATA_ROOT / ticker / "normalized" / "metrics.json"
    market_path = DATA_ROOT / ticker / "normalized" / "market.json"
    
    if not metrics_path.exists() or not market_path.exists():
        print(f"  ⚠️ {ticker}: 정규화 데이터(metrics.json / market.json)가 없습니다. 건너뜁니다.")
        return False
    
    try:
        observations = load_metric_observations(metrics_path)
        market = load_market_data(market_path)
        input_set, checks, derived = run_audit(observations, market)
        all_observations = observations + derived
    except Exception as e:
        print(f"  ❌ {ticker}: 데이터 로드 실패 — {e}")
        return False
    
    # 구글 시트 클라이언트 초기화 (재사용)
    client = get_client()
    doc = client.open_by_key(get_sheet_id())
    
    analysis_ws = None
    valuation_ws = None
    for sheet in doc.worksheets():
        if sheet.id == GID_ANALYSIS:
            analysis_ws = sheet
        elif sheet.id == GID_VALUATION:
            valuation_ws = sheet
    
    success = update_analysis_tab(ticker, input_set, market, all_observations, ws=analysis_ws)
    
    if update_valuation and success:
        time.sleep(0.5)  # API 할당량 초과 방지
        update_valuation_tab(ticker, input_set, market, ws=valuation_ws)
    
    return success


def update_all_portfolio() -> dict:
    """
    data/valuation/ 폴더의 모든 종목을 순회하여 기업분석 탭을 일괄 업데이트합니다.
    밸류계산 탭은 마지막 종목의 데이터로 덮어씁니다.
    
    Returns:
        {"success": [...], "skipped": [...], "failed": [...]}
    """
    tickers = _discover_local_tickers()
    if not tickers:
        print("❌ data/valuation/ 폴더에 분석 가능한 종목이 없습니다.")
        return {"success": [], "skipped": [], "failed": []}
    
    # 구글 시트 클라이언트 초기화 (전체에서 재사용)
    client = get_client()
    doc = client.open_by_key(get_sheet_id())
    
    analysis_ws = None
    valuation_ws = None
    for sheet in doc.worksheets():
        if sheet.id == GID_ANALYSIS:
            analysis_ws = sheet
        elif sheet.id == GID_VALUATION:
            valuation_ws = sheet
    
    results = {"success": [], "skipped": [], "failed": []}
    last_successful_data = None
    
    print(f"\n📊 전체 포트폴리오 시트 업데이트 시작 ({len(tickers)}개 종목)")
    print("=" * 60)
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] {ticker}")
        
        # ETF/비분석 대상 스킵
        if ticker in SKIP_TICKERS:
            print(f"  ⏭️ 스킵 (ETF/비분석 대상)")
            results["skipped"].append(ticker)
            continue
        
        metrics_path = DATA_ROOT / ticker / "normalized" / "metrics.json"
        market_path = DATA_ROOT / ticker / "normalized" / "market.json"
        
        if not metrics_path.exists() or not market_path.exists():
            print(f"  ⏭️ 스킵 (데이터 없음)")
            results["skipped"].append(ticker)
            continue
        
        try:
            observations = load_metric_observations(metrics_path)
            market = load_market_data(market_path)
            input_set, checks, derived = run_audit(observations, market)
            all_observations = observations + derived
            
            success = update_analysis_tab(
                ticker, input_set, market, all_observations, ws=analysis_ws
            )
            
            if success:
                results["success"].append(ticker)
                last_successful_data = (ticker, input_set, market)
            else:
                results["failed"].append(ticker)
            
        except Exception as e:
            print(f"  ❌ 실패: {e}")
            results["failed"].append(ticker)
        
        # API 할당량 초과 방지: 1초 대기
        time.sleep(1)
    
    # 밸류계산 탭: 마지막 성공 종목으로 업데이트
    if last_successful_data and valuation_ws:
        t, inp_set, mkt = last_successful_data
        print(f"\n📐 밸류계산 탭 업데이트: {t}")
        update_valuation_tab(t, inp_set, mkt, ws=valuation_ws)
    
    # 결과 요약
    print("\n" + "=" * 60)
    print(f"📊 업데이트 완료!")
    print(f"  ✅ 성공: {len(results['success'])}건 — {results['success']}")
    print(f"  ⏭️ 스킵: {len(results['skipped'])}건 — {results['skipped']}")
    print(f"  ❌ 실패: {len(results['failed'])}건 — {results['failed']}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="구글 시트 자동 업데이트")
    parser.add_argument("--ticker", type=str, help="특정 종목만 업데이트 (예: 009150, NVDA)")
    parser.add_argument("--all", action="store_true", help="전체 포트폴리오 일괄 업데이트")
    parser.add_argument("--no-valuation", action="store_true", help="밸류계산 탭 업데이트 생략")
    args = parser.parse_args()
    
    if args.ticker:
        print(f"🎯 단일 종목 업데이트: {args.ticker}")
        update_single_ticker(args.ticker, update_valuation=not args.no_valuation)
    elif args.all:
        update_all_portfolio()
    else:
        # 기본: 전체 포트폴리오 업데이트
        update_all_portfolio()


if __name__ == "__main__":
    main()
