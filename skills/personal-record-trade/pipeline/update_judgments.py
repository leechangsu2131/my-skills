"""
update_judgments.py
───────────────────
클로드의 밸류에이션 분석 결과(저평가/고평가/왜곡 시그널 등)를 기반으로
구글 스프레드시트의 R열(한줄판단)과 T열(비중판단)을 직접 업데이트합니다.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

# Windows cp949 인코딩 오류 방지
if hasattr(sys.stdout, 'reconfigure'):
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

from gsheet_auth import get_client, get_sheet_id
from sheet_updater import _find_ticker_row, GID_ANALYSIS

# 종목별 업데이트할 판단 내용
JUDGMENTS_TO_UPDATE = {
    "NVDA": {
        "judgment": "실제 성장이 시장 기대(Implied 10.2%)를 크게 초과 중. 가장 강력한 저평가 시그널",
        "action": "확대"
    },
    "APP": {
        "judgment": "AI 광고 엔진 성장세가 시장 기대를 크게 상회. 괴리율 -43%p로 저평가 시그널",
        "action": "확대"
    },
    "RDDT": {
        "judgment": "UGC 커뮤니티 및 데이터 라이선스 고성장. 시장 기대 대비 저평가 매력적",
        "action": "확대"
    },
    "PLTR": {
        "judgment": "PER 226배로 내포 기대 성장률(88%)이 실제(56%)보다 크게 높아 고평가 부담",
        "action": "축소"
    },
    "ADBE": {
        "judgment": "AI 위협 우려로 과도한 저평가(PER 15배). 높은 자본효율성(ROIC 55%) 대비 매력적",
        "action": "확대"
    },
    "ORCL": {
        "judgment": "AI 인프라(OCI) 확장을 위한 CAPEX 급증으로 일시적 FCF 음수 기록하나 실질 고성장",
        "action": "유지"
    },
    "001450": {
        "judgment": "보험사 회계 특성상 마진/ROIC 왜곡되나 예상 PER 4배 수준으로 극심한 저평가 매력",
        "action": "유지"
    }
}

def main():
    client = get_client()
    doc = client.open_by_key(get_sheet_id())
    
    ws = None
    for sheet in doc.worksheets():
        if sheet.id == GID_ANALYSIS:
            ws = sheet
            break
            
    if ws is None:
        print("❌ 기업분석 탭을 찾을 수 없습니다.")
        return
        
    print("📊 한줄판단(R열) 및 비중판단(T열) 업데이트 시작...")
    print("=" * 60)
    
    # 리포트 컨텍스트 동적 로드
    report_dir = ROOT / "data" / "report_context"
    if report_dir.exists():
        import json
        for file in report_dir.glob("*.json"):
            ticker = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                    summary = report_data.get("summary")
                    opinion = report_data.get("investment_opinion", "유지")
                    
                    if summary:
                        action = "확대" if opinion.lower() in ["buy", "outperform", "매수"] else ("축소" if opinion.lower() in ["sell", "underperform", "매도"] else "유지")
                        JUDGMENTS_TO_UPDATE[ticker] = {
                            "judgment": f"[리포트 반영] {summary}",
                            "action": action
                        }
            except Exception as e:
                print(f"  ⚠️ {ticker} 리포트 로드 실패: {e}")

    # GuruFocus 컨텍스트 동적 로드 및 판단 보강
    guru_dir = ROOT / "data" / "gurufocus_context"
    if guru_dir.exists():
        import json
        for file in guru_dir.glob("*.json"):
            ticker = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    guru_data = json.load(f)
                    
                if ticker in JUDGMENTS_TO_UPDATE:
                    base_judgment = JUDGMENTS_TO_UPDATE[ticker]["judgment"]
                    base_action = JUDGMENTS_TO_UPDATE[ticker]["action"]
                else:
                    base_judgment = "추가 분석 필요"
                    base_action = "유지"
                    
                fs = guru_data.get("financial_strength", "?")
                pr = guru_data.get("profitability_rank", "?")
                zscore = guru_data.get("altman_z_score", "?")
                
                guru_addon = f" (GuruFocus 퀄리티: 건전성 {fs}/10, 수익성 {pr}/10, Z스코어 {zscore})"
                
                JUDGMENTS_TO_UPDATE[ticker] = {
                    "judgment": base_judgment + guru_addon,
                    "action": base_action
                }
            except Exception as e:
                print(f"  ⚠️ {ticker} GuruFocus 로드 실패: {e}")

    updates = []
    for ticker, data in JUDGMENTS_TO_UPDATE.items():
        row = _find_ticker_row(ws, ticker)
        if row is None:
            print(f"  ⚠️ 티커 {ticker}를 시트에서 찾을 수 없습니다. 건너뜁니다.")
            continue
            
        # R열 (col 18) - 한줄판단
        updates.append({"range": f"R{row}", "values": [[data["judgment"]]]})
        # T열 (col 20) - 비중판단
        updates.append({"range": f"T{row}", "values": [[data["action"]]]})
        print(f"  📝 {ticker} (Row {row}) 예약: 한줄판단='{data['judgment'][:20]}...', 비중판단='{data['action']}'")
        
    if updates:
        ws.batch_update(updates, value_input_option="USER_ENTERED")
        print("=" * 60)
        print(f"🎉 성공적으로 {len(updates)//2}개 종목의 판단 열(R, T)이 시트에 업데이트되었습니다!")
    else:
        print("❌ 업데이트할 내역이 없습니다.")

if __name__ == "__main__":
    main()
