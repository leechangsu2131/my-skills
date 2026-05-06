"""
5_add_googlefinance.py
──────────────────────
기존 구글시트에 3가지 기능 추가:
  ① GOOGLEFINANCE 현재가 자동화  → '📈 실시간현황' 시트
  ② 상관관계 분석                → '🔗 상관관계' + '📊 가격데이터' 시트
  ③ Apps Script 안내             → 별도 .js 파일 생성

실행: python 5_add_googlefinance.py
"""

import gspread
import os, time

from gsheet_auth import get_client, get_sheet_id  # .env 기반 인증 (service_account.json 폴백)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def rgb(h):
    h = h.lstrip("#")
    return {"red": int(h[:2],16)/255, "green": int(h[2:4],16)/255, "blue": int(h[4:],16)/255}

# ── GF 티커 매핑 ────────────────────────────────────────────────
# 코드 → GOOGLEFINANCE 티커 (달러 종목만. 원화는 KRX: 사용)
GF_TICKERS = {
    "GOOG":   "NASDAQ:GOOGL",
    "NVDA":   "NASDAQ:NVDA",
    "META":   "NASDAQ:META",
    "UNH":    "NYSE:UNH",
    "PLTR":   "NYSE:PLTR",
    "ADBE":   "NASDAQ:ADBE",
    "NFLX":   "NASDAQ:NFLX",
    "ORCL":   "NYSE:ORCL",
    "RDDT":   "NYSE:RDDT",
    "APP":    "NASDAQ:APP",
    "HOOD":   "NASDAQ:HOOD",
    "ARKF":   "NASDAQ:ARKF",
    "QQMM":   "NASDAQ:QQQM",   # 실제 티커
    "SOXX":   "NASDAQ:SOXX",
    "BTC":    "BTC-USD",
    "361580": "KRX:361580",    # GOOGLEFINANCE KRX 현재가는 지원됨
    "461300": "KRX:461300",
    "001450": "KRX:001450",
    "000660": "KRX:000660",
    "105560": "KRX:105560",
    "035420": "KRX:035420",
    "267260": "KRX:267260",
    "360750": "KRX:360750",
    "481180": "KRX:481180",
    "461900": "KRX:461900",
}

# 달러 종목 (환율 곱하기 필요)
USD_CODES = {"GOOG","NVDA","META","UNH","PLTR","ADBE","NFLX",
             "ORCL","RDDT","APP","HOOD","ARKF","QQMM","SOXX"}
BTC_CODES = {"BTC"}
KRW_CODES = {"361580","461300","001450","000660","105560","035420",
             "267260","360750","481180","461900","원화","달러","칵테일펀딩","브라질채권"}

# 실제 보유 종목 (코드, 종목명, 통화, 섹터, 수량, 매입가)
HOLDINGS = [
    ("GOOG",  "Alphabet(GOOGL)", "달러", "빅테크",      167,  235237),
    ("NVDA",  "NVIDIA Corp",     "달러", "AI반도체",    253,  220000),
    ("UNH",   "UnitedHealth",    "달러", "보험",        127,  398841),
    ("461300","아이스크림미디어","원",   "교육콘텐츠", 3587,   15500),
    ("361580","RISE 200 TR",     "원",   "시장지수",   1001,   38030),
    ("META",  "Meta Platforms",  "달러", "빅테크",       48,  991178),
    ("BTC",   "비트코인",         "BTC",  "가상자산",   0.41,122000000),
    ("PLTR",  "Palantir",        "달러", "소프트웨어",  213,  217777),
    ("001450","현대해상",         "원",   "보험",       1425,   29100),
    ("NFLX",  "Netflix",         "달러", "플랫폼",      286,  126957),
    ("SOXX",  "iShares반도체",   "달러", "AI반도체",     53,  330000),
    ("ADBE",  "Adobe",           "달러", "소프트웨어",  100,  494631),
    ("481180","SOL AI소프트웨어","달러", "소프트웨어", 2351,   14445),
    ("461900","PLUS테크TOP10",   "달러", "빅테크",     1166,   18971),
    ("360750","TIGER S&P500",    "원",   "시장지수",    977,   25505),
    ("035420","NAVER",           "원",   "플랫폼",      110,  258888),
    ("QQMM",  "Invesco QQMM",   "달러", "시장지수",     49,  329633),
    ("267260","현대일렉트릭",    "원",   "유틸리티",     10,  780000),
    ("RDDT",  "Reddit",          "달러", "소프트웨어",   48,  291426),
    ("000660","SK하이닉스",      "원",   "AI반도체",      7,  870000),
    ("ORCL",  "Oracle",          "달러", "소프트웨어",   32,  402000),
    ("ARKF",  "ARK Fintech",     "달러", "핀테크",       69,   83431),
    ("HOOD",  "Robinhood",       "달러", "핀테크",       26,  197140),
    ("APP",   "Applovin",        "달러", "소프트웨어",    4,  894756),
]

# 상관관계 분석 대상 (달러/BTC 종목만 — GOOGLEFINANCE historical 지원)
CORREL_TICKERS = [
    ("GOOG",  "NASDAQ:GOOGL", "구글"),
    ("NVDA",  "NASDAQ:NVDA",  "엔비디아"),
    ("META",  "NASDAQ:META",  "메타"),
    ("PLTR",  "NYSE:PLTR",    "팔란티어"),
    ("NFLX",  "NASDAQ:NFLX",  "넷플릭스"),
    ("ADBE",  "NASDAQ:ADBE",  "어도비"),
    ("UNH",   "NYSE:UNH",     "UNH"),
    ("ORCL",  "NYSE:ORCL",    "오라클"),
    ("RDDT",  "NYSE:RDDT",    "레딧"),
    ("BTC",   "BTC-USD",      "비트코인"),
    ("SPY",   "NYSEARCA:SPY", "S&P500"),
]
N = len(CORREL_TICKERS)  # 11

# ════════════════════════════════════════════════════════════════
# ① 실시간현황 시트 (GOOGLEFINANCE)
# ════════════════════════════════════════════════════════════════
def build_realtime_sheet(ss):
    print("  📈 '📈 실시간현황' 시트 생성 중...")
    try:
        ws = ss.worksheet("📈 실시간현황")
        ss.del_worksheet(ws)
    except:
        pass
    ws = ss.add_worksheet("📈 실시간현황", rows=80, cols=20)

    # ─ 데이터 준비 ─
    # Row1: 타이틀
    # Row2: 환율 / 총평가금액
    # Row3: 헤더
    # Row4~: 종목 데이터

    USD_KRW_CELL = "B2"   # 환율이 들어갈 셀
    TOTAL_CELL   = "E2"

    headers = ["등급","코드","종목명","통화","섹터","수량",
               "현재가(현지통화)","현재가(원화)","매입가(원화)",
               "평가금액(원)","매입금액(원)","평가손익(원)","수익률(%)",
               "현재비중(%)","목표비중(%)","목표가(원)","매매신호"]

    rows_to_write = []
    # Row1
    rows_to_write.append(["📈 실시간 현황 — GOOGLEFINANCE 자동 갱신"] + [""]*16)
    # Row2 (환율/합계 — 나중에 개별 셀 업데이트)
    rows_to_write.append(["▶ USD/KRW", f'=IFERROR(GOOGLEFINANCE("CURRENCY:USDKRW"),"수동입력")',
                           "", "▶ 총 평가금액(원)", f"=SUM(J4:J{3+len(HOLDINGS)})",
                           "","","","","","","","","","","",""])
    # Row3 헤더
    rows_to_write.append(headers)

    grade_map = {
        "GOOG":"S","NVDA":"S","UNH":"S","461300":"S","361580":"S","META":"S",
        "BTC":"A-","PLTR":"A-","001450":"A","NFLX":"A","SOXX":"A","ADBE":"A-",
        "481180":"A+","461900":"A-","360750":"A","035420":"A-","QQMM":"A-",
        "267260":"A+","RDDT":"A","000660":"A-","ORCL":"B+","ARKF":"B","HOOD":"B+","APP":"A"
    }
    target_map = {
        "GOOG":840000,"NVDA":535000,"UNH":730000,"META":1185000,"PLTR":385000,
        "NFLX":193000,"ADBE":887000,"ORCL":825000,"RDDT":385000,"APP":1033000,
        "HOOD":236000,"001450":70000,"035420":300000,"000660":1600000,"267260":1200000,
    }
    weight_map = {
        "GOOG":0.10,"NVDA":0.09,"UNH":0.08,"461300":0.08,"361580":0.07,
        "META":0.05,"BTC":0.05,"PLTR":0.05,"001450":0.05,"NFLX":0.05,
        "SOXX":0.04,"ADBE":0.04,"481180":0.03,"461900":0.03,"360750":0.03,
        "035420":0.03,"QQMM":0.02,"267260":0.01,"RDDT":0.01,"000660":0.01,
        "ORCL":0.01,"ARKF":0.01,"HOOD":0.01,"APP":0.01,
    }

    data_rows = []
    for r_idx, (code, name, cur, sector, qty, avg_krw) in enumerate(HOLDINGS):
        row_num = r_idx + 4  # 실제 시트 행 번호
        gf      = GF_TICKERS.get(code, "")
        total_cells = f"J4:J{3+len(HOLDINGS)}"

        # 현재가 수식
        if code in USD_CODES and gf:
            price_local = f'=IFERROR(GOOGLEFINANCE("{gf}","price"),"수동입력")'
            price_krw   = f"=G{row_num}*$B$2"
        elif code in BTC_CODES:
            price_local = f'=IFERROR(GOOGLEFINANCE("{gf}","price")*$B$2,"수동입력")'
            price_krw   = f"=G{row_num}"   # 이미 원화
        elif gf:  # KRX
            price_local = f'=IFERROR(GOOGLEFINANCE("{gf}","price"),"수동입력")'
            price_krw   = f"=G{row_num}"
        else:
            price_local = "수동입력"
            price_krw   = "수동입력"

        eval_amt  = f"=IFERROR(F{row_num}*H{row_num},\"\")"
        buy_amt   = avg_krw * qty
        pnl       = f"=IFERROR(J{row_num}-K{row_num},\"\")"
        ret       = f"=IFERROR(L{row_num}/K{row_num},\"\")"
        weight    = f"=IFERROR(J{row_num}/SUM({total_cells}),\"\")"
        tgt_w     = weight_map.get(code, 0)
        tgt_p     = target_map.get(code, "")
        # 매매신호: 목표가 90% 이상이면 매도 검토, 비중초과면 리밸런싱
        signal    = (f'=IFERROR(IF(AND(P{row_num}<>"",G{row_num}>=P{row_num}*0.9),"🎯목표근접",'
                     f'IF(N{row_num}>O{row_num},"⚖️비중초과",'
                     f'IF(N{row_num}<O{row_num}*0.7,"📉비중부족","-"))),"-")')

        data_rows.append([
            grade_map.get(code,""), code, name, cur, sector, qty,
            price_local, price_krw, avg_krw,
            eval_amt, buy_amt, pnl, ret,
            weight, tgt_w, tgt_p, signal
        ])

    rows_to_write.extend(data_rows)
    ws.update(rows_to_write, value_input_option="USER_ENTERED")
    time.sleep(1)

    # 서식 요청
    sid = ws.id
    requests = [
        # 타이틀 행
        {"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex":0,"endRowIndex":1,
                      "startColumnIndex":0,"endColumnIndex":17},
            "cell": {"userEnteredFormat": {
                "backgroundColor": rgb("0D1B2A"),
                "textFormat": {"foregroundColor":rgb("FFFFFF"),"bold":True,"fontSize":13},
                "horizontalAlignment":"LEFT","verticalAlignment":"MIDDLE"}},
            "fields":"userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"}},
        # 헤더 행 (row3)
        {"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex":2,"endRowIndex":3,
                      "startColumnIndex":0,"endColumnIndex":17},
            "cell": {"userEnteredFormat": {
                "backgroundColor": rgb("1B3A5C"),
                "textFormat": {"foregroundColor":rgb("FFFFFF"),"bold":True,"fontSize":9},
                "horizontalAlignment":"CENTER","verticalAlignment":"MIDDLE"}},
            "fields":"userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"}},
        # 환율/합계 행 (row2)
        {"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex":1,"endRowIndex":2,
                      "startColumnIndex":0,"endColumnIndex":6},
            "cell": {"userEnteredFormat": {
                "backgroundColor": rgb("EAF4FF"),
                "textFormat": {"bold":True,"fontSize":10,"foregroundColor":rgb("0D1B2A")}}},
            "fields":"userEnteredFormat(backgroundColor,textFormat)"}},
        # 줄무늬
        {"addBanding": {
            "bandedRange": {
                "bandedRangeId": (sid % 100000000) * 10,
                "range": {"sheetId":sid,"startRowIndex":3,"endRowIndex":3+len(HOLDINGS),
                          "startColumnIndex":0,"endColumnIndex":17},
                "rowProperties": {
                    "firstBandColor": rgb("FFFFFF"),
                    "secondBandColor": rgb("E8F0F8")}}}},
        # freeze
        {"updateSheetProperties": {
            "properties": {"sheetId":sid,
                           "gridProperties": {"frozenRowCount":3,"frozenColumnCount":2}},
            "fields":"gridProperties.frozenRowCount,gridProperties.frozenColumnCount"}},
        # 탭 색상
        {"updateSheetProperties": {
            "properties": {"sheetId":sid,"tabColor":rgb("1A7A4A")},
            "fields":"tabColor"}},
    ]
    # 컬럼 너비
    widths = [60,90,160,60,110,70,130,130,120,120,120,120,90,90,90,110,120]
    for i,w in enumerate(widths):
        requests.append({"updateDimensionProperties": {
            "range":{"sheetId":sid,"dimension":"COLUMNS","startIndex":i,"endIndex":i+1},
            "properties":{"pixelSize":w},"fields":"pixelSize"}})
    # 수익률 숫자 포맷
    for col in [12,13,14]:
        requests.append({"repeatCell": {
            "range":{"sheetId":sid,"startRowIndex":3,"endRowIndex":3+len(HOLDINGS),
                     "startColumnIndex":col,"endColumnIndex":col+1},
            "cell":{"userEnteredFormat":{"numberFormat":{"type":"PERCENT","pattern":"0.00%"}}},
            "fields":"userEnteredFormat.numberFormat"}})
    # 금액 숫자 포맷
    for col in [9,10,11]:
        requests.append({"repeatCell": {
            "range":{"sheetId":sid,"startRowIndex":3,"endRowIndex":3+len(HOLDINGS),
                     "startColumnIndex":col,"endColumnIndex":col+1},
            "cell":{"userEnteredFormat":{"numberFormat":{"type":"NUMBER","pattern":"#,##0"}}},
            "fields":"userEnteredFormat.numberFormat"}})
    # 조건부서식 — 수익률 양수=녹색, 음수=빨강
    requests.append({"addConditionalFormatRule": {
        "rule": {
            "ranges": [{"sheetId":sid,"startRowIndex":3,"endRowIndex":3+len(HOLDINGS),
                        "startColumnIndex":12,"endColumnIndex":13}],
            "booleanRule": {
                "condition": {"type":"NUMBER_GREATER","values":[{"userEnteredValue":"0"}]},
                "format": {"backgroundColor":rgb("D4EDDA")}}},
        "index":0}})
    requests.append({"addConditionalFormatRule": {
        "rule": {
            "ranges": [{"sheetId":sid,"startRowIndex":3,"endRowIndex":3+len(HOLDINGS),
                        "startColumnIndex":12,"endColumnIndex":13}],
            "booleanRule": {
                "condition": {"type":"NUMBER_LESS","values":[{"userEnteredValue":"0"}]},
                "format": {"backgroundColor":rgb("FAD7D7")}}},
        "index":1}})
    # 매매신호 조건부서식
    requests.append({"addConditionalFormatRule": {
        "rule": {
            "ranges": [{"sheetId":sid,"startRowIndex":3,"endRowIndex":3+len(HOLDINGS),
                        "startColumnIndex":16,"endColumnIndex":17}],
            "booleanRule": {
                "condition": {"type":"TEXT_CONTAINS","values":[{"userEnteredValue":"목표근접"}]},
                "format": {"backgroundColor":rgb("FFF3CD"),
                           "textFormat":{"bold":True,"foregroundColor":rgb("856404")}}}},
        "index":2}})

    ss.batch_update({"requests": requests})
    print("  ✅ 실시간현황 시트 완료")
    return ws

# ════════════════════════════════════════════════════════════════
# ② 가격데이터 + 상관관계 시트
# ════════════════════════════════════════════════════════════════
def build_price_data_sheet(ss):
    print("  📊 '📊 가격데이터' 시트 생성 중...")
    try:
        ws = ss.worksheet("📊 가격데이터")
        ss.del_worksheet(ws)
    except:
        pass
    ws = ss.add_worksheet("📊 가격데이터", rows=400, cols=15)
    sid = ws.id

    tickers = CORREL_TICKERS  # 11개
    names   = [t[2] for t in tickers]
    gf_tks  = [t[1] for t in tickers]

    # 안내 헤더
    header_data = [
        ["📊 가격데이터 — GOOGLEFINANCE 과거 가격 (상관관계 분석용)"],
        ["※ 이 시트는 건드리지 마세요. 상관관계 시트가 여기서 데이터를 가져옵니다."],
        ["▶ 종목 정의"],
        ["코드","GF 티커","종목명","지원여부","비고"],
    ]
    for i,(code,gf,name) in enumerate(tickers):
        support = "△ KRX historical 제한" if gf.startswith("KRX") else ("BTC(365일)" if "BTC" in gf else "✅")
        header_data.append([code, gf, name, support, ""])
    header_data.append([])
    header_data.append(["▶ 과거 가격 데이터 (최근 1년)"])

    # 날짜 + 종목 헤더 (row: len(header_data)+1)
    data_start_row = len(header_data) + 2  # 1-indexed
    price_header = ["날짜"] + names
    header_data.append(price_header)

    ws.update(header_data, value_input_option="USER_ENTERED")

    # 가격 데이터: GOOGLEFINANCE는 배열로 반환 — 첫 번째 종목으로 날짜 가져오고 나머지는 VLOOKUP
    # 날짜 열: GOOG 기준 (미국 주식 거래일 = 기준)
    # B열 = 날짜 (GOOGLEFINANCE GOOG 배열의 날짜)
    # C~M열 = 각 종목 종가
    #
    # 구글시트에서 배열 수식으로 처리:
    # =IFERROR(GOOGLEFINANCE("NASDAQ:GOOGL","close",TODAY()-365,TODAY(),1),"")
    # → 2열 배열 반환 (날짜, 가격) → index 1=날짜, 2=가격

    # 날짜 + GOOG 같이 (배열 수식)
    goog_formula = (
        f'=IFERROR(GOOGLEFINANCE("{gf_tks[0]}","close",'
        f'TODAY()-365,TODAY(),1),"")'
    )
    ws.update_cell(data_start_row + 1, 1, goog_formula)

    # 나머지 종목: 날짜 기준 VLOOKUP
    for col_i, (code, gf, name) in enumerate(tickers[1:], start=3):  # C열부터
        formula = (
            f'=IFERROR(ARRAYFORMULA(IFERROR(VLOOKUP($A{data_start_row+1}:$A,'
            f'GOOGLEFINANCE("{gf}","close",TODAY()-365,TODAY(),1),2,0),"")),"")'
        )
        ws.update_cell(data_start_row + 1, col_i, formula)
        time.sleep(0.3)

    # 서식
    requests = [
        {"repeatCell": {
            "range": {"sheetId":sid,"startRowIndex":0,"endRowIndex":1,
                      "startColumnIndex":0,"endColumnIndex":1},
            "cell": {"userEnteredFormat": {
                "backgroundColor":rgb("0D1B2A"),
                "textFormat":{"foregroundColor":rgb("FFFFFF"),"bold":True,"fontSize":11}}},
            "fields":"userEnteredFormat(backgroundColor,textFormat)"}},
        {"repeatCell": {
            "range": {"sheetId":sid,"startRowIndex":3,"endRowIndex":4,
                      "startColumnIndex":0,"endColumnIndex":len(tickers)+1},
            "cell": {"userEnteredFormat": {
                "backgroundColor":rgb("1B3A5C"),
                "textFormat":{"foregroundColor":rgb("FFFFFF"),"bold":True,"fontSize":9},
                "horizontalAlignment":"CENTER"}},
            "fields":"userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        {"updateSheetProperties": {
            "properties":{"sheetId":sid,"tabColor":rgb("5B21B6")},
            "fields":"tabColor"}},
    ]
    ss.batch_update({"requests":requests})
    print(f"  ✅ 가격데이터 시트 완료 (데이터 로딩은 구글시트에서 수초 소요)")
    return ws, data_start_row

def build_correlation_sheet(ss, price_data_start_row):
    print("  🔗 '🔗 상관관계' 시트 생성 중...")
    try:
        ws = ss.worksheet("🔗 상관관계")
        ss.del_worksheet(ws)
    except:
        pass
    ws = ss.add_worksheet("🔗 상관관계", rows=60, cols=20)
    sid = ws.id

    tickers = CORREL_TICKERS
    names   = [t[2] for t in tickers]
    n = len(tickers)
    pd_sheet = "📊 가격데이터"
    dr = price_data_start_row + 1  # 실제 데이터 시작행 (1-indexed, 가격데이터 시트)

    intro = [
        ["🔗 상관관계 분석 — 포트폴리오 분산 진단"],
        ["▶ 분석기간: 최근 1년 (365일)  |  데이터: GOOGLEFINANCE 자동 갱신"],
        [],
        ["📖 해석 가이드"],
        ["범위", "의미", "투자 시사점"],
        ["0.8 이상", "강한 양의 상관", "두 종목이 같이 움직임 → 분산 효과 낮음"],
        ["0.5 ~ 0.8", "보통 양의 상관", "같은 방향이지만 완전 연동은 아님"],
        ["-0.2 ~ 0.5", "약하거나 무상관", "좋은 분산 조합"],
        ["-0.5 ~ -0.2","약한 음의 상관", "헤징 효과 있음"],
        ["-0.8 이하", "강한 음의 상관", "완벽한 헤징 → 변동성 크게 감소"],
        [],
        ["▶ 상관계수 행렬"],
        [],
    ]
    ws.update(intro, value_input_option="USER_ENTERED")

    # 헤더 행 (row 14 = index 13)
    header_row_idx = len(intro) + 1  # 1-indexed
    header = ["종목↓ / →"] + names
    ws.update_cell(header_row_idx, 1, "종목↓ / →")
    for j, name in enumerate(names, start=2):
        ws.update_cell(header_row_idx, j, name)

    # 상관계수 행렬 수식
    # 가격데이터 컬럼: A=날짜, B=GOOG, C=NVDA, ... (col = j+2 in 가격데이터)
    import string
    price_cols = string.ascii_uppercase

    matrix_rows = []
    for i in range(n):
        col_i = price_cols[i+1]  # B부터 시작
        row_data = [names[i]]
        for j in range(n):
            col_j = price_cols[j+1]
            if i == j:
                row_data.append(1.0)
            else:
                # FILTER로 빈값 제거 후 CORREL
                formula = (
                    f"=IFERROR(CORREL("
                    f"FILTER('{pd_sheet}'!{col_i}{dr}:{col_i}500,"
                    f"'{pd_sheet}'!{col_i}{dr}:{col_i}500<>\"\","
                    f"'{pd_sheet}'!{col_j}{dr}:{col_j}500<>\"\"),"
                    f"FILTER('{pd_sheet}'!{col_j}{dr}:{col_j}500,"
                    f"'{pd_sheet}'!{col_i}{dr}:{col_i}500<>\"\","
                    f"'{pd_sheet}'!{col_j}{dr}:{col_j}500<>\"\")"
                    f"),\"N/A\")"
                )
                row_data.append(formula)
        matrix_rows.append(row_data)

    start_r = header_row_idx + 1
    ws.update(f"A{start_r}", matrix_rows, value_input_option="USER_ENTERED")
    time.sleep(1)

    # 서식 요청
    requests = [
        # 타이틀
        {"repeatCell": {
            "range": {"sheetId":sid,"startRowIndex":0,"endRowIndex":1,"startColumnIndex":0,"endColumnIndex":20},
            "cell": {"userEnteredFormat": {
                "backgroundColor":rgb("0D1B2A"),
                "textFormat":{"foregroundColor":rgb("FFFFFF"),"bold":True,"fontSize":12}}},
            "fields":"userEnteredFormat(backgroundColor,textFormat)"}},
        # 안내 헤더 (row5)
        {"repeatCell": {
            "range": {"sheetId":sid,"startRowIndex":4,"endRowIndex":5,"startColumnIndex":0,"endColumnIndex":3},
            "cell": {"userEnteredFormat": {
                "backgroundColor":rgb("1B3A5C"),
                "textFormat":{"foregroundColor":rgb("FFFFFF"),"bold":True,"fontSize":9},
                "horizontalAlignment":"CENTER"}},
            "fields":"userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        # 행렬 헤더
        {"repeatCell": {
            "range": {"sheetId":sid,"startRowIndex":header_row_idx-1,"endRowIndex":header_row_idx,
                      "startColumnIndex":0,"endColumnIndex":n+1},
            "cell": {"userEnteredFormat": {
                "backgroundColor":rgb("1B3A5C"),
                "textFormat":{"foregroundColor":rgb("FFFFFF"),"bold":True,"fontSize":9},
                "horizontalAlignment":"CENTER"}},
            "fields":"userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        # 행렬 왼쪽 종목명 열
        {"repeatCell": {
            "range": {"sheetId":sid,"startRowIndex":start_r-1,"endRowIndex":start_r-1+n,
                      "startColumnIndex":0,"endColumnIndex":1},
            "cell": {"userEnteredFormat": {
                "backgroundColor":rgb("1B3A5C"),
                "textFormat":{"foregroundColor":rgb("FFFFFF"),"bold":True,"fontSize":9},
                "horizontalAlignment":"CENTER"}},
            "fields":"userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        # 숫자 포맷 (행렬 값)
        {"repeatCell": {
            "range": {"sheetId":sid,"startRowIndex":start_r-1,"endRowIndex":start_r-1+n,
                      "startColumnIndex":1,"endColumnIndex":n+1},
            "cell": {"userEnteredFormat": {"numberFormat":{"type":"NUMBER","pattern":"0.00"}}},
            "fields":"userEnteredFormat.numberFormat"}},
        # 탭 색상
        {"updateSheetProperties": {
            "properties":{"sheetId":sid,"tabColor":rgb("2D6A9F")},
            "fields":"tabColor"}},
        # 컬럼 너비
        {"updateDimensionProperties": {
            "range":{"sheetId":sid,"dimension":"COLUMNS","startIndex":0,"endIndex":1},
            "properties":{"pixelSize":120},"fields":"pixelSize"}},
    ]
    for ci in range(1, n+1):
        requests.append({"updateDimensionProperties": {
            "range":{"sheetId":sid,"dimension":"COLUMNS","startIndex":ci,"endIndex":ci+1},
            "properties":{"pixelSize":80},"fields":"pixelSize"}})

    # 조건부서식 — 상관계수 색상 스케일 (적색=1, 흰색=0, 청색=-1)
    requests.append({"addConditionalFormatRule": {
        "rule": {
            "ranges": [{"sheetId":sid,
                        "startRowIndex":start_r-1,"endRowIndex":start_r-1+n,
                        "startColumnIndex":1,"endColumnIndex":n+1}],
            "gradientRule": {
                "minpoint": {"color":rgb("4472C4"),"type":"NUMBER","value":"-1"},
                "midpoint": {"color":rgb("FFFFFF"),"type":"NUMBER","value":"0"},
                "maxpoint": {"color":rgb("C0392B"),"type":"NUMBER","value":"1"}}},
        "index":0}})

    # 높은 상관 강조 (0.8 이상 — 경고)
    requests.append({"addConditionalFormatRule": {
        "rule": {
            "ranges": [{"sheetId":sid,
                        "startRowIndex":start_r-1,"endRowIndex":start_r-1+n,
                        "startColumnIndex":1,"endColumnIndex":n+1}],
            "booleanRule": {
                "condition":{"type":"NUMBER_GREATER_THAN_EQ","values":[{"userEnteredValue":"0.8"}]},
                "format":{"textFormat":{"bold":True,"foregroundColor":rgb("7B0000")}}}},
        "index":1}})

    ss.batch_update({"requests":requests})
    print("  ✅ 상관관계 시트 완료")

# ════════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════════
def main():
    print("🔐 인증 중...")
    gc = get_client()
    sid = get_sheet_id()
    ss  = gc.open_by_key(sid)
    print(f"📄 스프레드시트 열기: {ss.title}")

    print("\n① GOOGLEFINANCE 실시간현황 시트...")
    build_realtime_sheet(ss)
    time.sleep(2)

    print("\n② 가격데이터 시트...")
    _, price_start = build_price_data_sheet(ss)
    time.sleep(2)

    print("\n③ 상관관계 시트...")
    build_correlation_sheet(ss, price_start)

    print(f"\n✅ 모든 시트 추가 완료!")
    print(f"🔗 {ss.url}")
    print("\n⚠️  GOOGLEFINANCE 데이터 로딩에 수십 초 걸릴 수 있습니다.")
    print("    시트를 열고 잠시 기다리면 자동으로 채워집니다.")
    print("\n📌 Apps Script 알림은 4_apps_script.js 파일을 참고하세요.")

if __name__ == "__main__":
    main()
