import sys
import json
from pathlib import Path
import datetime

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(ROOT / ".."))  # for gsheet_auth
import pipeline.layer1_store as L

def fix_dongsung_3rows():
    ticker = "033500"

    # ── 신한투자증권 (2026.06.05) ──
    # Page 5: ROIC (%) 23.4 32.3 44.4 51.1 56.3 (2024~2028)
    # Page 5: 영업이익률(%) 9.0 9.8 11.3 13.4 15.2
    # Page 5: EPS 1,312 1,863 2,638 3,662 4,734
    # Page 5: PER 11.4 13.6 8.2 5.9 4.6
    # Page 5: ROE 21.1 24.2 27.1 29.3 29.0
    # Page 2: Target PER 12.5, 목표주가 33,000원
    shinhan = {
        "roic": 44.4,       # 2026F
        "op_margin": 11.3,  # 2026F
        "fwd_pe_fy": 8.2,   # 2026F PER
        "fair_value": 33000, # 목표주가
    }
    L.save_row(ticker, "analyst_신한투자증권", shinhan)
    print("✅ 신한투자증권: ROIC 44.4%, OPM 11.3%, PER 8.2x, 목표가 33,000원")

    # ── 미래에셋증권 (2026.03.27) ──
    # Page 15: ROIC (%) 4.8 16.2 22.5 30.8 (2023~2026F)
    # Page 4: 영업이익률 (%) 7.0 9.0 9.8 (분기별 추이, 2025 연간 9.8%)
    # Not Rated - 목표주가/PER 미제시
    mirae = {
        "roic": 30.8,       # 2026F (미래에셋 자체 추정)
        "op_margin": 9.8,   # 2025 실적 기준 (2026F 미제시, 두자릿수 OPM 언급)
    }
    L.save_row(ticker, "analyst_미래에셋증권", mirae)
    print("✅ 미래에셋증권: ROIC 30.8%, OPM 9.8% (Not Rated, 목표가 미제시)")

    # ── DS투자증권 (2026.05.19) ──
    # 웹 기사 기반 - ROIC 수치 미기재
    # 목표주가 38,000원, 투자의견 매수
    ds = {
        "fair_value": 38000, # 목표주가
        # ROIC, OPM은 웹 텍스트에 구체적 수치 없으므로 비워둠
    }
    L.save_row(ticker, "analyst_DS투자증권", ds)
    print("✅ DS투자증권: 목표가 38,000원 (ROIC/OPM 웹기사에 미기재, 빈칸 처리)")

    # ── 기업분석 탭용 종합 JSON ──
    # ROIC: 신한 44.4 + 미래 30.8 = 평균 37.6
    # OPM: 신한 11.3 + 미래 9.8 = 평균 10.55
    # 목표가: 신한 33,000 + DS 38,000 = 평균 35,500
    synthesized = {
        "ticker": ticker,
        "investment_opinion": "Buy",
        "target_price": 35500,
        "consensus_metrics": {
            "op": 10.55,
            "eps": 2638,
            "roe": 27.1,
            "f_per": 8.2,
            "roic": 37.6,
            "revenue": ""
        }
    }

    out_dir = ROOT / "data" / "report_context"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{ticker}_1.json", "w", encoding="utf-8") as f:
        json.dump(synthesized, f, indent=2, ensure_ascii=False)
    print(f"\n✅ 기업분석 탭용 종합: ROIC 37.6%(평균), OPM 10.55%, 목표가 35,500원")

if __name__ == "__main__":
    fix_dongsung_3rows()
