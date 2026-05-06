"""
1_setup_gsheet.py
─────────────────
Google Sheets 포트폴리오 초기 세팅 스크립트
실행 전: pip install gspread google-auth python-dotenv

인증 방법:
  - .env 파일의 GOOGLE_SA_* 환경변수 (권장)
  - service_account.json (하위호환)
  - 또는 OAuth (개인 계정, 한 번만 브라우저 인증)

.env에 GOOGLE_SHEET_ID를 설정하면 기존 시트를 사용합니다 (Drive API 불필요).
비워두면 새 스프레드시트를 생성합니다 (Drive API 권한 필요).
"""

import json, datetime, os, time

from gsheet_auth import get_client  # .env 기반 인증 (service_account.json 폴백)

# ── 색상 팔레트 (Sheets API용 RGB 0~1) ────────────────────────
def rgb(hex_str):
    h = hex_str.lstrip("#")
    return {
        "red":   int(h[0:2], 16) / 255,
        "green": int(h[2:4], 16) / 255,
        "blue":  int(h[4:6], 16) / 255,
    }

CN = "0D1B2A"; CM = "1B3A5C"; CL = "2D6A9F"
CW = "FFFFFF"; CS = "E8F0F8"; CY = "FFFDE7"
CPG = "D4EDDA"; CPR = "FAD7D7"; CGB = "EAF4FF"

# ── 시트 헤더 정의 ─────────────────────────────────────────────
SHEETS = {
    "📊 포트폴리오": {
        "headers": ["등급","종목명","통화","구글분류","섹터","피터린치","코드",
                    "수량","현재가(원)","매입가(원)","평가금액","매입금액",
                    "평가손익","수익률(%)","현재비중(%)","목표비중(%)","ROIC","버킷","비고"],
        "col_widths": [60,180,60,160,120,120,90,70,120,120,120,120,120,90,90,90,70,80,200],
        "freeze_col": 2,
    },
    "🎯 비중조절신호": {
        "headers": ["종목명","버킷","확신도","현재가(원)","목표가(원)","하방(원)",
                    "잔여기간(년)","연수익률","손익비","종합점수",
                    "모델비중(%)","현재비중(%)","편차(%)","매매신호","메모"],
        "col_widths": [180,80,70,120,120,120,100,90,80,100,100,100,90,100,200],
        "freeze_col": 1,
    },
    "🏭 섹터현황": {
        "headers": ["섹터","종목수","평가금액(원)","매입금액(원)","평가손익",
                    "수익률(%)","평가비중(%)","목표비중(%)","편차(%)","메모"],
        "col_widths": [140,70,140,140,120,90,100,100,90,180],
        "freeze_col": 1,
    },
    "📒 매매일지": {
        "headers": ["매매일","티커","종목명","구분","수량","단가(원)","금액(원)",
                    "매매이유","타이밍이유","만족도(-10~10)",
                    "사후분석","컨디션","인지오류","해결전략","비고"],
        "col_widths": [110,80,160,70,70,110,120,200,150,100,200,90,180,180,180],
        "freeze_col": 3,
    },
    "📅 특정일잔고": {
        "headers": ["스냅샷날짜","코드","종목명","통화","수량","현재가(원)",
                    "평가금액(원)","총자산비중(%)","메모"],
        "col_widths": [120,90,160,70,80,120,130,120,180],
        "freeze_col": 1,
    },
    "👋 청산종목": {
        "headers": ["종목명","진입가설","진입근거","매수가","목표가","하방",
                    "매도완료일","보유기간(개월)","실현손익","수익률(%)",
                    "사후평가(1-10)","인지오류","해결전략","재매매의향"],
        "col_widths": [160,200,200,110,110,110,110,90,120,90,100,200,200,100],
        "freeze_col": 1,
    },
    "🧠 전략·전망": {
        "headers": ["전략명/전망가설","관련종목","중요도","확인시기",
                    "확률","기대값","대응전략","결과/업데이트"],
        "col_widths": [240,180,80,100,80,90,200,200],
        "freeze_col": 1,
    },
}

# ── 실제 보유 데이터 ───────────────────────────────────────────
PORTFOLIO_DATA = [
    ["S","Alphabet(GOOGL)","달러","핵심성장-미국","빅테크","대형우량주","GOOG",167,562910,235237,94006105,39284579,"","","","",30.0,"성장",""],
    ["S","NVIDIA Corp","달러","핵심성장-미국","AI반도체","대형우량주","NVDA",253,294130,220000,74414955,55660000,"","","","",90.0,"성장",""],
    ["S","UnitedHealth(UNH)","달러","코어-미국","보험","대형우량주","UNH",127,546020,398841,69344645,50652807,"","","",0.002,9.0,"코어",""],
    ["S","아이스크림미디어","원","코어-한국","교육콘텐츠","경기순환","461300",3587,18600,15500,66718200,55598500,"","",0.079,100.0,"코어","초등해자"],
    ["S","RISE 200 TR","원","코어-한국","시장지수","경기순환","361580",1001,56895,38030,56951895,38068030,"","","","","코어",""],
    ["S","Meta Platforms","달러","핵심성장-미국","빅테크","고성장","META",48,901845,991178,43288569,47576544,"","",0.035,25.0,"성장","peg 0.61"],
    ["A-","비트코인","BTC","전술-기타","가상자산","경기순환","BTC",0.41,113966772,122000000,46726376,50020000,"","","","","전술","샤프지수향상"],
    ["A-","Palantir(PLTR)","달러","핵심성장-미국","소프트웨어","고성장","PLTR",213,205023,217777,43669920,46386501,"","","","","성장",""],
    ["A","현대해상","원","인컴","보험","자산주","001450",1425,30400,29100,43320000,41467500,"","",0.022,13.0,"인컴","배당 개시 기대"],
    ["B+","브라질채권","헤알","인컴","채권","자산주","브라질채권",140000,296,255,41440000,35700000,"","","","","인컴",""],
    ["A","Netflix(NFLX)","달러","핵심성장-미국","플랫폼","고성장","NFLX",286,137964,126957,39457787,36309702,"","",0.066,20.0,"성장",""],
    ["A","반도체 iShares(SOXX)","달러","핵심성장-미국","AI반도체","고성장","SOXX",53,680079,330000,36044213,17490000,"","","","","성장",""],
    ["A-","Adobe(ADBE)","달러","코어-미국","소프트웨어","고성장","ADBE",100,362707,494631,36270710,49463100,"","","",30.0,"성장","peg 0.59"],
    ["A+","SOL 미국AI소프트웨어","달러","핵심성장-미국","소프트웨어","고성장","481180",2351,12125,14445,28505875,33960195,"","","","","성장",""],
    ["A-","PLUS 미국테크TOP10","달러","핵심성장-미국","빅테크","고성장","461900",1166,23275,18971,27138650,22120186,"","","","","성장",""],
    ["A","TIGER 미국S&P500","원","코어-미국","시장지수","대형우량주","360750",977,26160,25505,25558320,24918385,"","","","","코어",""],
    ["A-","NAVER","원","코어-한국","플랫폼","자산주","035420",110,211000,258888,23210000,28477680,"","",0.036,"","코어","두나무합병기대"],
    ["A-","Invesco QQMM","달러","핵심성장-미국","시장지수","고성장","QQMM",49,405153,329633,19852502,16152017,"","","","","성장",""],
    ["-","칵테일펀딩","원","인컴","채권","자산주","칵테일펀딩","",13000000,12000000,13000000,12000000,"","","","","인컴",""],
    ["A+","현대일렉트릭","원","핵심성장-한국","유틸리티","고성장","267260",10,1252000,780000,12520000,7800000,"","","",0.0,"성장","변압기 이익률최고"],
    ["A","Reddit(RDDT)","달러","핵심성장-미국","소프트웨어","고성장","RDDT",48,216990,291426,10415544,13988448,"","",0.071,60.0,"성장",""],
    ["B","원화 현금","원","전술-현금","현금","자산주","원화",11000000,1,"",11000000,11000000,"","","","","전술",""],
    ["A-","SK하이닉스","원","핵심성장-한국","AI반도체","경기순환","000660",7,1286000,870000,9002000,6090000,"","","",40.0,"성장",""],
    ["B+","Oracle(ORCL)","달러","핵심성장-미국","소프트웨어","고성장","ORCL",32,237859,402000,7611513,12864000,"","",0.280,10.0,"성장","스타게이트"],
    ["B","달러 현금","달러","전술-현금","현금","자산주","달러",4000,1473,"",5895280,5720000,"","","","","전술",""],
    ["B","ARK Fintech(ARKF)","달러","핵심성장-미국","핀테크","고성장","ARKF",69,60721,83431,4189775,5756739,"","","","","성장",""],
    ["B+","Robinhood(HOOD)","달러","핵심성장-미국","핀테크","고성장","HOOD",26,107426,197140,2793095,5125640,"","","",10.0,"성장","peg 0.15"],
    ["A","Applovin(APP)","달러","핵심성장-미국","소프트웨어","고성장","APP",4,657839,894756,2631358,3579024,"","",0.041,"","성장","peg 0.44"],
]

TRADE_LOG = [
    ["2025-01-09","QQQM","Invesco QQMM","매도",3,295334,886002,"리밸런싱","","0","","중","","",""],
    ["2025-01-25","MAGS","Magnificent7ETF","매수",145,84038,12185510,"최고와함께","방학","0","","상","","",""],
    ["2025-02-11","NVDA","NVIDIA","매수",49,213633,10467917,"최고의기업과함께","과매도구간","5","","하","보상심리","","새벽 뇌동매수"],
    ["2025-02-18","NVDA","NVIDIA","매수",110,178795,19667450,"최고의기업과함께","과매도구간","0","","중","","",""],
    ["2025-02-19","PLTR","Palantir","매도","","","","고평가판단","방학","-10","팔고 오르니 배아팠음","상/중","추세추종","처음원칙유지","나중에 재매수 후 하락"],
    ["2025-02-19","001450","현대해상","매수/매도","",24000,"","시가배당률높음","방학","-10","산업모름 배당만 봄","하","주가분석실패·손실회피","투자근거명확화",""],
    ["2025-02-22","PGY","파가야","매수","","","","이스라엘재건기대","전문가추천","-10","포모진입","하","포모·군중심리","기대값 정확히계산",""],
    ["2025-03-01","PLTR","Palantir","매수",308,151057,46525556,"최고의문제해결기업","방학","-10","","하","","",""],
    ["2025-03-02","PLTR","Palantir","매도",454,132217,60026518,"리밸런싱","","","","","","",""],
]

CLOSED = [
    ["한국금융지주우","저평가 배당주","배당재개기대",172100,65000,55000,"2024-04-01","","","","만족10","","",""],
    ["삼성전자","파운드리협력기대","부진연속",220500,73000,55000,"2024-04-01","","","","","","",""],
    ["Palantir(1차)","최고와함께","PER고평가",139.11,140,80,"",26,"","","후회10","추세추종무시","처음원칙유지",""],
    ["두산밥캣","행동주의기대","가치의심",72000,"","","",22,"","","좋은종목빨리팜","주가분석실패·손실회피","투자근거명확화",""],
    ["파가야(PGY)","이스라엘재건기대","포모진입",13.89,30,7,"",2,-2200000,"","후회10남말만","포모·군중심리","기대값계산정확히",""],
    ["한국전력","저PBR고ROE","전기요금인하",43550,72000,50000,"2025-01-24","","","","만족10","","",""],
    ["한화에어로스페이스","방산저가매수","전쟁축소리스크",1417000,1400000,900000,"","","","","","","",""],
]

STRATEGY = [
    ["저평가된 배당주는 배신하지 않는다","","7","2","4","2","",""],
    ["위대한 기업의 일시적 악재","","4","3","1","0","",""],
    ["과매도 구간 매수","","6","3","0","3","",""],
    ["저 PBR 고 ROE","","6","0","3","3","",""],
    ["최고와 함께 하라","","3","1","1","0","",""],
    ["","","","","","","",""],
    ["미·중 냉전 장기화 – 대만 리스크","TSMC, 삼성전자","12","6개월","70%","1.40","분산 유지",""],
    ["부채주도 유동성 확장 → 위험자산 상승","BTC, 빅테크","11","","90%","9.90","비중확대",""],
    ["AI 투자 → 실적 검증 필요","엔비디아, PLTR, ORCL","11.5","12개월","40%","0.38","실적 확인 후 판단",""],
    ["소프트웨어 해자 유지","META, GOOGL, RDDT","8","","90%","7.20","보유",""],
    ["비트코인 디지털 금 지위 확립","BTC","10","","90%","9.00","비중 유지",""],
    ["한국 소액주주 가치제고","저PBR주","9.5","","80%","7.60","이익실현 후 비중조절",""],
]

SNAPSHOT = [
    ["24.11.21","UNH","UnitedHealth","달러",171,459879,78639440,"10.1%",""],
    ["24.11.21","NVDA","NVIDIA","달러",270,266651,71995968,"9.3%",""],
    ["24.11.21","GOOG","Alphabet","달러",167,428053,71485014,"9.2%",""],
    ["24.11.21","BTC","비트코인","BTC",0.256,121335751,31061952,"4.0%",""],
    ["25.01.29","GOOG","Alphabet","달러",167,479922,80146974,"9.3%",""],
    ["25.01.29","NVDA","NVIDIA","달러",270,273327,73798497,"8.6%",""],
    ["25.01.29","461300","아이스크림미디어","원",2756,16910,46603960,"5.4%",""],
    ["25.04.28","GOOG","Alphabet","달러",167,514777,85967922,"9.6%",""],
    ["25.04.28","NVDA","NVIDIA","달러",253,319941,80945233,"9.0%",""],
    ["25.04.28","461300","아이스크림미디어","원",3587,18190,65247530,"7.3%",""],
    ["25.04.28","BTC","비트코인","BTC",0.41,112562892,46150785,"5.2%",""],
]

SHEET_DATA = {
    "📊 포트폴리오": PORTFOLIO_DATA,
    "📒 매매일지": TRADE_LOG,
    "👋 청산종목": CLOSED,
    "📅 특정일잔고": SNAPSHOT,
    "🧠 전략·전망": STRATEGY,
}

# ── 배치 업데이트 헬퍼 ─────────────────────────────────────────
def batch_format(sheet_id, requests):
    """여러 포맷 요청을 한 번에 전송"""
    return requests  # spreadsheet.batch_update()에서 처리

def header_format_req(sheet_id, num_cols, bg=CN, fg=CW):
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0, "endRowIndex": 1,
                "startColumnIndex": 0, "endColumnIndex": num_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": rgb(bg),
                    "textFormat": {"foregroundColor": rgb(fg), "bold": True, "fontSize": 10,
                                   "fontFamily": "Malgun Gothic"},
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
        }
    }

def freeze_req(sheet_id, rows=1, cols=0):
    return {
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id,
                           "gridProperties": {"frozenRowCount": rows, "frozenColumnCount": cols}},
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }
    }

def col_width_req(sheet_id, col_idx, width_px):
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                      "startIndex": col_idx, "endIndex": col_idx + 1},
            "properties": {"pixelSize": width_px},
            "fields": "pixelSize",
        }
    }

def banded_rows_req(sheet_id, start_row, end_row, num_cols,
                    odd=CW, even=CS):
    # bandedRangeId가 INT32를 초과하지 않도록 보정
    safe_id = (int(sheet_id) % 100000000) * 10 + start_row
    return {
        "addBanding": {
            "bandedRange": {
                "bandedRangeId": safe_id,
                "range": {"sheetId": sheet_id,
                          "startRowIndex": start_row, "endRowIndex": end_row,
                          "startColumnIndex": 0, "endColumnIndex": num_cols},
                "rowProperties": {
                    "headerColor": rgb(CN),
                    "firstBandColor": rgb(odd),
                    "secondBandColor": rgb(even),
                },
            }
        }
    }

def tab_color_req(sheet_id, hex_color):
    return {
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "tabColor": rgb(hex_color)},
            "fields": "tabColor",
        }
    }

# ── 메인 실행 ─────────────────────────────────────────────────
def main():
    print("🔐 Google API 인증 중...")
    gc = get_client()

    # .env의 GOOGLE_SHEET_ID가 있으면 기존 시트 사용, 없으면 신규 생성
    from gsheet_auth import _load_dotenv
    _load_dotenv()
    existing_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()

    if existing_id:
        print(f"📄 기존 스프레드시트 열기 (ID: {existing_id[:12]}...)")
        ss = gc.open_by_key(existing_id)

        # 겹치는 탭은 삭제 대신 이름 변경으로 보존 (예: "📊 포트폴리오 (1)")
        target_names = set(SHEETS.keys())
        existing_titles = {w.title for w in ss.worksheets()}
        for w in ss.worksheets():
            if w.title in target_names:
                time.sleep(1) # API Rate Limit 회피
                n = 1
                new_title = f"{w.title} ({n})"
                while new_title in existing_titles:
                    n += 1
                    new_title = f"{w.title} ({n})"
                print(f"  📝 기존 '{w.title}' → '{new_title}' 으로 이름 변경")
                w.update_title(new_title)
                existing_titles.discard(w.title)
                existing_titles.add(new_title)

        default_sheet = None   # 기존 시트 사용 시 기본 탭 삭제 불필요
    else:
        title = f"📈 투자 포트폴리오 {datetime.date.today()}"
        print(f"📄 '{title}' 스프레드시트 생성 중...")
        ss = gc.create(title)
        default_sheet = ss.sheet1   # 신규 생성 시 기본 Sheet1은 나중에 삭제

    tab_colors = {
        "📊 포트폴리오": "1B3A5C",
        "🎯 비중조절신호": "B02020",
        "🏭 섹터현황": "1A7A4A",
        "📒 매매일지": "CA8A04",
        "📅 특정일잔고": "5B21B6",
        "👋 청산종목": "374151",
        "🧠 전략·전망": "1E40AF",
    }

    all_requests = []
    created_sheets = {}

    for name, config in SHEETS.items():
        print(f"  📋 '{name}' 시트 생성 중...")
        time.sleep(2) # API Rate Limit 회피
        ws = ss.add_worksheet(title=name, rows=200, cols=len(config["headers"]))
        sid = ws.id
        created_sheets[name] = ws

        # 헤더 작성
        time.sleep(1) # API Rate Limit 회피
        ws.append_row(config["headers"], value_input_option="USER_ENTERED")

        # 데이터 작성
        data = SHEET_DATA.get(name, [])
        if data:
            time.sleep(1) # API Rate Limit 회피
            ws.append_rows(data, value_input_option="USER_ENTERED")

        # 포맷 요청 수집
        all_requests.append(header_format_req(sid, len(config["headers"])))
        all_requests.append(freeze_req(sid, rows=1, cols=config.get("freeze_col", 0)))
        all_requests.append(tab_color_req(sid, tab_colors.get(name, "1B3A5C")))

        # 컬럼 너비
        for ci, w in enumerate(config["col_widths"]):
            all_requests.append(col_width_req(sid, ci, w))

        # 줄무늬 행
        end_row = max(len(data) + 5, 100)
        all_requests.append(banded_rows_req(sid, 1, end_row, len(config["headers"])))

    # 비중조절신호 시트 — 수동 입력 안내 행 추가
    sig_ws = created_sheets["🎯 비중조절신호"]
    sig_ws.append_row(["★ 아래에 종목별 신호 데이터를 입력하세요"], value_input_option="USER_ENTERED")

    # 섹터현황 — 섹터 목록 추가
    sec_ws = created_sheets["🏭 섹터현황"]
    sectors = ["빅테크","AI반도체","소프트웨어","플랫폼","시장지수",
               "보험","교육콘텐츠","유틸리티","핀테크","채권","가상자산","현금"]
    for s in sectors:
        sec_ws.append_row([s,"","","","","","","","",""], value_input_option="USER_ENTERED")

    # 기본 Sheet1 삭제
    if default_sheet:
        all_requests.append({
            "deleteSheet": {"sheetId": default_sheet.id}
        })

    print("🎨 서식 일괄 적용 중...")
    ss.batch_update({"requests": all_requests})

    # 공유 설정 (링크 있으면 누구나 볼 수 있게)
    ss.share(None, perm_type="anyone", role="reader")
    print(f"\n✅ 완료!")
    print(f"🔗 스프레드시트 URL: https://docs.google.com/spreadsheets/d/{ss.id}")
    print(f"📋 스프레드시트 ID: {ss.id}")
    print(f"\n⚠️  add_trade.py 에서 사용할 SHEET_ID를 저장해두세요:")
    print(f"   SHEET_ID = '{ss.id}'")

    # ID를 파일로 저장
    with open(os.path.join(os.path.dirname(__file__), "sheet_id.txt"), "w") as f:
        f.write(ss.id)
    print(f"\n📁 sheet_id.txt 에도 저장됨")

if __name__ == "__main__":
    main()
