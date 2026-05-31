"""
add_ticker_row.py
──────────────────
구글 스프레드시트 "🔬 기업분석" 탭에 신규 관심종목(한미반도체, 042700) 행을 추가합니다.
구글 파이낸스 수식 및 관련 밸류에이션 계산 셀을 알맞게 설정합니다.
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
from sheet_updater import GID_ANALYSIS, _find_ticker_row

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
        
    # 이미 등록되어 있는지 확인
    row = _find_ticker_row(ws, "042700")
    if row is not None:
        print(f"ℹ️ 한미반도체(042700)는 이미 Row {row}에 등록되어 있습니다.")
        return
        
    # 새로운 행의 번호 (기존 티커 열 다음 행)
    b_col = ws.col_values(2)
    next_row = len(b_col) + 1
    
    print(f"📊 한미반도체(042700)를 Row {next_row}에 신규 관심종목으로 등록합니다...")
    
    # 35.0는 한미반도체의 섹터 평균 PER
    peer_per = 35.0
    
    # 22개 컬럼 구조 정의 (A~V)
    row_data = [
        "-",                                       # A: 포지션ID
        "'042700",                                 # B: 티커 (앞에 ' 접두사 붙여서 문자열 포맷 유지)
        "한미반도체",                              # C: 종목명
        "관심",                                    # D: 상태
        f"=IFERROR(IF(ISNUMBER(VALUE(B{next_row})),GOOGLEFINANCE(CONCAT(Y1,B{next_row}),X1),GOOGLEFINANCE(B{next_row},X1)),0)",  # E: 현재가
        f"=IFERROR(IF(ISNUMBER(VALUE(B{next_row})),GOOGLEFINANCE(CONCAT(Y1,B{next_row}),X2),GOOGLEFINANCE(B{next_row},X2))/100000000,0)", # F: 시총(억)
        f"=IFERROR(IF(ISNUMBER(VALUE(B{next_row})),GOOGLEFINANCE(CONCAT(Y1,B{next_row}),X3),GOOGLEFINANCE(B{next_row},X3)),0)", # G: PER
        "",                                        # H: EV/FCF (Python 업데이트)
        "",                                        # I: PBR (Python 업데이트)
        f"=IF(G{next_row},ROUND(G{next_row}/C2,1),0)", # J: Implied성장률%
        f"=IF(G{next_row},ROUND(G{next_row}/{peer_per}*100,1),0)", # K: 섹터PER대비% (수식형)
        "",                                        # L: PER변화1Y (Python 업데이트)
        "",                                        # M: 매출성장률% (Python 업데이트)
        "",                                        # N: 영업마진% (Python 업데이트)
        "",                                        # O: ROIC% (Python 업데이트)
        "",                                        # P: FCF성장률% (Python 업데이트)
        f"=IF(J{next_row}*M{next_row},ROUND(J{next_row}-M{next_row},1),0)", # Q: 성장괴리%p
        "분석 필요",                                # R: 한줄판단
        "일부",                                    # S: 기대현실적
        "유지",                                    # T: 비중판단
        "",                                        # U: 매도트리거
        ""                                         # V: 업데이트일 (Python 업데이트)
    ]
    
    # 시트에 행 추가
    ws.append_row(row_data, value_input_option="USER_ENTERED")
    print(f"✅ 한미반도체(042700) Row {next_row} 추가 완료!")

if __name__ == "__main__":
    main()
