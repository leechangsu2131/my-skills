"""
2026학년도 에듀파인(K-에듀파인) 품의 문서 지출결의서 PDF 일괄 무인 다운로드 및 세부 품목 정밀 대조 모듈
- 1품의 N결의(다중 분할 결의) 전수 순회 및 무인 자동 다운로드
- start_OZUtil.createViewer 런타임 후킹으로 파일 저장 대화상자 100% 무인 우회
- 다운로드된 PDF 2페이지 「물품명세서」 PyMuPDF 파싱 & 개별 품목 1:1 정밀 대조표 자동 생성
"""
import asyncio
import csv
import json
import os
import re
import urllib.request
import fitz
import websockets

CDP_HTTP = "http://127.0.0.1:9222"
DOWNLOAD_DIR = r"C:\Users\user\Downloads\지출결의"
SUMMARY_CSV = os.path.join(DOWNLOAD_DIR, "2026학년도_지출결의_총괄대조표.csv")
DETAIL_CSV = os.path.join(DOWNLOAD_DIR, "2026학년도_품목별_실제지출결의_정밀대조표.csv")
PLAN_JSON = os.path.join(DOWNLOAD_DIR, "all_decis_plan.json")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def clean_filename(s):
    s = re.sub(r'[\\/*?:"<>|]', "", str(s))
    return s.strip().replace(" ", "_")

def get_klef_ws():
    tabs = json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=3).read())
    for t in tabs:
        if t.get('type') == 'page' and 'klef' in t.get('url', ''):
            return t.get('webSocketDebuggerUrl')
    return None

async def cdp_call(ws, mid, method, params=None):
    cmd = {"id": mid, "method": method}
    if params:
        cmd["params"] = params
    await ws.send(json.dumps(cmd))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=30)
        data = json.loads(raw)
        if data.get("id") == mid:
            return data

async def eval_js(ws, mid, expr):
    r = await cdp_call(ws, mid, "Runtime.evaluate", {"expression": expr, "returnByValue": True})
    return r.get("result", {}).get("result", {}).get("value")

async def close_all_popups(ws, mid):
    await eval_js(ws, mid, """
    (function(){
        try{
            var popups = nexacro.getPopupFrames();
            for(var k in popups){
                if(k !== '_idArray' && k !== '_idxMap' && k !== 'length'){
                    try{ popups[k].form.close(); }catch(e){}
                }
            }
        }catch(e){}
    })()
    """)

async def collect_pumui_and_decis(ws, next_id):
    """품의목록 조회 후 이창수(lee2131)의 모든 지출결의(다중 결의 포함) 수집"""
    print("▶ [1단계] 품의목록 조회 기간(20260301~20261231) 설정 및 검색...")
    await eval_js(ws, next_id(), """
    (function(){
        try{
            var app = nexacro.getApplication();
            var wf = app.mainframe.MainVFrameSet.SubHFrameSet.WorkVFrameSet.WorkFrame;
            var frame = null;
            for(var i=0; i<wf.all.length; i++){
                if(wf.all[i].name.indexOf('A00FAA0104001002') >= 0){ frame = wf.all[i]; break; }
            }
            if(!frame) return 'no_pumui_frame';
            var form = frame.form;
            var btn = form.divWork.form.divAuth01.form.btnExpdCnsulOutpt;
            var targetForm = btn.onclick._user_handlers[0].target;
            
            var sf = targetForm.divSearch.form || targetForm.divSearch;
            sf.calCnsulBeginDte.set_value('20260301');
            sf.calCnsulEndDte.set_value('20261231');
            targetForm.fnSearch();
            return 'search_triggered';
        }catch(e){ return 'err:'+e.message; }
    })()
    """)
    await asyncio.sleep(3.5)

    items_raw = await eval_js(ws, next_id(), """
    (function(){
        var app = nexacro.getApplication();
        var wf = app.mainframe.MainVFrameSet.SubHFrameSet.WorkVFrameSet.WorkFrame;
        var frame = null;
        for(var i=0; i<wf.all.length; i++){
            if(wf.all[i].name.indexOf('A00FAA0104001002') >= 0){ frame = wf.all[i]; break; }
        }
        var form = frame.form;
        var btn = form.divWork.form.divAuth01.form.btnExpdCnsulOutpt;
        var targetForm = btn.onclick._user_handlers[0].target;
        var ds = targetForm.dsMain;
        
        var items = [];
        for(var i=0; i<ds.rowcount; i++){
            if(ds.getColumn(i, 'cnsulManId') === 'lee2131'){
                var sts = ds.getColumn(i, 'sclExpdStsSeNm');
                var cAmt = ds.getColumn(i, 'cnsulAmt');
                var caatAmt = ds.getColumn(i, 'sclCaatAmt');
                items.push({
                    rowIdx: i,
                    seq: ds.getColumn(i, 'sclCnsulSeq'),
                    no: ds.getColumn(i, 'sclCnsulNo'),
                    caatNo: ds.getColumn(i, 'sclCaatNo') || '',
                    dte: ds.getColumn(i, 'cnsulDte'),
                    sj: ds.getColumn(i, 'sj'),
                    sts: sts,
                    cnsulAmt: typeof cAmt === 'object' ? (cAmt.hi || 0) : cAmt,
                    caatAmt: typeof caatAmt === 'object' ? (caatAmt.hi || 0) : caatAmt,
                    confmDocSn: ds.getColumn(i, 'confmDocSn')
                });
            }
        }
        return JSON.stringify(items);
    })()
    """)
    all_items = json.loads(items_raw)
    target_items = [it for it in all_items if it['sts'] == '원인행위' and it['caatNo']]
    print(f"  → 원인행위/결의 대상 품의 총 {len(target_items)}건 수집 완료")

    print("\n▶ [2단계] 각 품의별 지출결의(다중 분할결의) 전수 스캔...")
    decis_plan = []
    for it in target_items:
        await close_all_popups(ws, next_id())
        await asyncio.sleep(0.3)

        # 지출진행상태 팝업 열기
        await eval_js(ws, next_id(), f"""
        (function(){{
            try{{
                var app = nexacro.getApplication();
                var wf = app.mainframe.MainVFrameSet.SubHFrameSet.WorkVFrameSet.WorkFrame;
                var frame = null;
                for(var i=0; i<wf.all.length; i++){{
                    if(wf.all[i].name.indexOf('A00FAA0104001002') >= 0){{ frame = wf.all[i]; break; }}
                }}
                var form = frame.form;
                var btn = form.divWork.form.divAuth01.form.btnExpdCnsulOutpt;
                var targetForm = btn.onclick._user_handlers[0].target;
                
                targetForm.dsPopParam.setColumn(0,"cddcSeCd","R10");
                targetForm.dsPopParam.setColumn(0,"accnutSeCd","2");
                targetForm.dsPopParam.setColumn(0,"accnutYr","2026");
                targetForm.dsPopParam.setColumn(0,"instCd","R100006630");
                targetForm.dsPopParam.setColumn(0,"searchSe","cnsul");
                targetForm.dsPopParam.setColumn(0,"searchSe2","pacmOut");
                targetForm.dsPopParam.setColumn(0,"searchNo",{json.dumps(it['no'])});
                targetForm.dsPopParam.setColumn(0,"sclCaatNo",{json.dumps(it['caatNo'])});
                targetForm.dsPopParam.setColumn(0,"sclPacmNo","");
                targetForm.dsPopParam.setColumn(0,"confmDocSn",{json.dumps(str(it['confmDocSn']))});
                
                var oArg = {{paramDataset: targetForm.dsPopParam}};
                var oOption = {{title: "지출진행상태", popuptype: "modal"}};
                targetForm.gfnOpenPopup("FADMANGECLI003P01", "fadmangecli::FADMANGECLI003P01.xfdl", oArg, "fnPopupCallback", oOption);
                return 'ok';
            }}catch(e){{ return 'err:'+e.message; }}
        }})()
        """)
        await asyncio.sleep(1.8)

        p_data_raw = await eval_js(ws, next_id(), """
        (function(){
            try{
                var pf = nexacro.getPopupFrames()["FADMANGECLI003P01"];
                if(!pf || !pf.form) return JSON.stringify({count: 0, rows: []});
                var pForm = pf.form;
                var dsD = pForm.dsDecis;
                if(!dsD || dsD.rowcount === 0) return JSON.stringify({count: 0, rows: []});
                
                var rows = [];
                for(var i=0; i<dsD.rowcount; i++){
                    var amt = dsD.getColumn(i, 'decisAmt');
                    rows.push({
                        rowIdx: i,
                        sclExresNo: dsD.getColumn(i, 'sclExresNo'),
                        sclExresSeq: dsD.getColumn(i, 'sclExresSeq'),
                        decisDte: dsD.getColumn(i, 'decisDte'),
                        decisAmt: typeof amt === 'object' ? amt.hi : amt,
                        sclExpdStsSeNm: dsD.getColumn(i, 'sclExpdStsSeNm'),
                        sclCaatNo: dsD.getColumn(i, 'sclCaatNo'),
                        chgSn: dsD.getColumn(i, 'chgSn'),
                        confmDocSn: dsD.getColumn(i, 'confmDocSn'),
                        cddcSeCd: dsD.getColumn(i, 'cddcSeCd'),
                        accnutSeCd: dsD.getColumn(i, 'accnutSeCd'),
                        accnutYr: dsD.getColumn(i, 'accnutYr'),
                        instCd: dsD.getColumn(i, 'instCd')
                    });
                }
                return JSON.stringify({count: dsD.rowcount, rows: rows});
            }catch(e){ return JSON.stringify({error: e.message}); }
        })()
        """)
        p_data = json.loads(p_data_raw)
        decis_rows = p_data.get('rows', [])
        tot_decis = sum(r['decisAmt'] for r in decis_rows)
        print(f"  [{it['seq']}] {it['sj'][:28]} | 품의:{it['cnsulAmt']:,}원 | 결의:{tot_decis:,}원 ({len(decis_rows)}건)")
        for dr in decis_rows:
            decis_plan.append({"pumui": it, "decis": dr})

    with open(PLAN_JSON, "w", encoding="utf-8") as f:
        json.dump(decis_plan, f, ensure_ascii=False, indent=2)
    print(f"  → 총 {len(decis_plan)}건의 전체 지출결의 플랜 생성 완료\n")
    return decis_plan

async def download_all_decis(ws, next_id, decis_plan):
    """모든 지출결의서 PDF 일괄 무인 다운로드 (OZ Viewer Hook)"""
    print("="*75)
    print(f"🚀 [3단계] 지출결의서 PDF {len(decis_plan)}건 무인 다운로드 진행...")
    print("="*75)

    by_pumui = {}
    for item in decis_plan:
        p_seq = item['pumui']['seq']
        if p_seq not in by_pumui:
            by_pumui[p_seq] = {"pumui": item['pumui'], "decisList": []}
        by_pumui[p_seq]["decisList"].append(item['decis'])

    total_downloaded = 0
    for p_seq, p_group in by_pumui.items():
        pumui = p_group['pumui']
        decis_list = p_group['decisList']

        needed = []
        for d in decis_list:
            clean_sj = clean_filename(pumui['sj'][:16])
            clean_exres = clean_filename(d['sclExresSeq'])
            target_filename = f"{d['decisDte']}_{pumui['seq']}_{clean_exres}_{clean_sj}_{d['decisAmt']}원.pdf"
            full_path = os.path.join(DOWNLOAD_DIR, target_filename)

            if os.path.exists(full_path) and os.path.getsize(full_path) > 10000:
                total_downloaded += 1
                d['target_file'] = target_filename
            else:
                d['target_file'] = target_filename
                needed.append(d)

        if not needed:
            continue

        await close_all_popups(ws, next_id())
        await asyncio.sleep(0.4)

        # 지출진행상태 팝업 열기
        await eval_js(ws, next_id(), f"""
        (function(){{
            try{{
                var app = nexacro.getApplication();
                var wf = app.mainframe.MainVFrameSet.SubHFrameSet.WorkVFrameSet.WorkFrame;
                var frame = null;
                for(var i=0; i<wf.all.length; i++){{
                    if(wf.all[i].name.indexOf('A00FAA0104001002') >= 0){{ frame = wf.all[i]; break; }}
                }}
                var form = frame.form;
                var btn = form.divWork.form.divAuth01.form.btnExpdCnsulOutpt;
                var targetForm = btn.onclick._user_handlers[0].target;
                
                targetForm.dsPopParam.setColumn(0,"cddcSeCd","R10");
                targetForm.dsPopParam.setColumn(0,"accnutSeCd","2");
                targetForm.dsPopParam.setColumn(0,"accnutYr","2026");
                targetForm.dsPopParam.setColumn(0,"instCd","R100006630");
                targetForm.dsPopParam.setColumn(0,"searchSe","cnsul");
                targetForm.dsPopParam.setColumn(0,"searchSe2","pacmOut");
                targetForm.dsPopParam.setColumn(0,"searchNo",{json.dumps(pumui['no'])});
                targetForm.dsPopParam.setColumn(0,"sclCaatNo",{json.dumps(pumui['caatNo'] or '')});
                targetForm.dsPopParam.setColumn(0,"sclPacmNo","");
                targetForm.dsPopParam.setColumn(0,"confmDocSn",{json.dumps(str(pumui['confmDocSn']))});
                
                var oArg = {{paramDataset: targetForm.dsPopParam}};
                var oOption = {{title: "지출진행상태", popuptype: "modal"}};
                targetForm.gfnOpenPopup("FADMANGECLI003P01", "fadmangecli::FADMANGECLI003P01.xfdl", oArg, "fnPopupCallback", oOption);
                return 'ok';
            }}catch(e){{ return 'err:'+e.message; }}
        }})()
        """)
        await asyncio.sleep(2.2)

        for d in needed:
            row_idx = d['rowIdx']
            target_filename = d['target_file']
            full_file_path = os.path.join(DOWNLOAD_DIR, target_filename)

            # 리포트 팝업 모달 열기
            await eval_js(ws, next_id(), f"""
            (function(){{
                try{{
                    var pf = nexacro.getPopupFrames()["FADMANGECLI003P01"];
                    if(!pf || !pf.form) return 'no_popup';
                    var pForm = pf.form;
                    var nRow = {row_idx};
                    var displayname = "지출결의서 출력";
                    var exportFilename = "지출결의서 출력";
                    var reportFilePath = "/f/fad/mang/exre";
                    var reportFileName = "FADMANGEXRE008R01";
                    var odiFileName = "FADMANGEXRE008R01";
                    
                    pForm.dsOzParam.setColumn(0, "selngChitYn", "N");
                    pForm.dsOzParam.setColumn(0, "cddcSeCd", pForm.dsDecis.getColumn(nRow, "cddcSeCd"));
                    pForm.dsOzParam.setColumn(0, "accnutSeCd", pForm.dsDecis.getColumn(nRow, "accnutSeCd"));
                    pForm.dsOzParam.setColumn(0, "accnutYr", pForm.dsDecis.getColumn(nRow, "accnutYr"));
                    pForm.dsOzParam.setColumn(0, "instCd", pForm.dsDecis.getColumn(nRow, "instCd"));
                    pForm.dsOzParam.setColumn(0, "sclCaatNo", pForm.dsDecis.getColumn(nRow, "sclCaatNo"));
                    pForm.dsOzParam.setColumn(0, "sclExresNo", pForm.dsDecis.getColumn(nRow, "sclExresNo"));
                    pForm.dsOzParam.setColumn(0, "chgSn", pForm.dsDecis.getColumn(nRow, "chgSn"));
                    pForm.dsOzParam.setColumn(0, "confmDocSn", pForm.dsDecis.getColumn(nRow, "confmDocSn"));
                    pForm.dsOzParam.setColumn(0, "printerNm", pForm.gfnGetUserInfo("userNm"));
                    pForm.dsOzParam.setColumn(0, "sanctnRequstYn", "N");
                    
                    var arrParam = pForm.gfnMakeReportParam(pForm.dsOzParam);
                    var reportListInfo = {{
                        concatPageYn: "N",
                        showSubReportYn: "N",
                        barcodePrintYn: "Y",
                        barcodeInfo: {{barcodePaperOrientation: "V"}},
                        reportList: [{{
                            displayname: displayname,
                            exportFilename: exportFilename,
                            reportFilePath: reportFilePath,
                            reportFileName: reportFileName,
                            dataInfo: [{{odiFileName: odiFileName, csvParamName: "", csvData: ""}}],
                            param: arrParam
                        }}]
                    }};
                    
                    var oArg = {{reportListInfo: reportListInfo}};
                    var oOption = {{popuptype: "modal", title: displayname, width: 1000, height: 700, resize: true}};
                    pForm.gfnOpenPopup("reportPopupModal", "common::commonReport.xfdl", oArg, "fnPopupCallback", oOption);
                    return 'ok';
                }}catch(e){{ return 'err:'+e.message; }}
            }})()
            """)

            # 렌더링 대기
            for wait_i in range(12):
                await asyncio.sleep(1)
                v_pg = await eval_js(ws, next_id(), """
                (function(){
                    try{
                        var iframe = document.querySelector('iframe[src*="ozhviewer.jsp"]');
                        if(!iframe) return 'no';
                        var win = iframe.contentWindow;
                        if(!win.OZViewer) return 'no';
                        var p = win.OZViewer.GetInformation("TOTAL_PAGE");
                        return (p && p != '0') ? ('yes:' + p) : 'no';
                    }catch(e){ return 'no'; }
                })()
                """)
                if 'yes:' in str(v_pg):
                    break

            # 후킹 주입 및 _callSavePdf 호출
            await eval_js(ws, next_id(), f"""
            (function(){{
                try{{
                    var iframe = document.querySelector('iframe[src*="ozhviewer.jsp"]');
                    var win = iframe.contentWindow;
                    var util = win.start_OZUtil;
                    if(!util) return 'no_util';
                    
                    var targetPath = {json.dumps(DOWNLOAD_DIR)};
                    var targetFile = {json.dumps(target_filename)};
                    
                    var origCreate = util.createViewer;
                    util.createViewer = function(id, cb){{
                        try{{
                            util.setParameter("export.confirmsave", "false");
                            util.setParameter("export.mode", "silent");
                            util.setParameter("export.path", targetPath);
                            util.setParameter("export.filename", targetFile);
                        }}catch(e){{}}
                        return origCreate.apply(this, arguments);
                    }};
                    
                    win._callSavePdf();
                    return 'called';
                }}catch(e){{ return 'err:'+e.message; }}
            }})()
            """)

            # 파일 생성 대기
            saved = False
            for wf in range(8):
                await asyncio.sleep(1)
                if os.path.exists(full_file_path) and os.path.getsize(full_file_path) > 10000:
                    saved = True
                    sz = os.path.getsize(full_file_path) / 1024
                    print(f"  ✅ 결의 {d['sclExresSeq']} 저장 성공: {target_filename} ({sz:.1f} KB)")
                    total_downloaded += 1
                    break

            if not saved:
                print(f"  ⚠️ 결의 {d['sclExresSeq']} 저장 실패: {target_filename}")

            # reportPopupModal 닫기
            await eval_js(ws, next_id(), """
            (function(){
                try{
                    var popups = nexacro.getPopupFrames();
                    if(popups["reportPopupModal"]){
                        popups["reportPopupModal"].form.close();
                    }
                }catch(e){}
            })()
            """)
            await asyncio.sleep(1.0)

        await close_all_popups(ws, next_id())

    print(f"\n🎉 전체 {len(decis_plan)}건 중 {total_downloaded}건 PDF 저장 완료!\n")

def parse_all_pdfs_and_build_csv():
    """다운로드된 모든 지출결의서 PDF 2페이지 물품명세서를 파싱하여 정밀 대조표 생성"""
    print("="*75)
    print("📊 [4단계] PDF 물품명세서 정밀 파싱 및 2개 대조표 CSV 생성...")
    print("="*75)

    if not os.path.exists(PLAN_JSON):
        print(f"오류: {PLAN_JSON} 파일이 없습니다.")
        return

    with open(PLAN_JSON, "r", encoding="utf-8") as f:
        decis_plan = json.load(f)

    all_pdfs = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.pdf')]

    def parse_pdf(pdf_path):
        try:
            doc = fitz.open(pdf_path)
        except Exception:
            return {}

        text_p1 = doc[0].get_text() if len(doc) > 0 else ""
        creditor_match = re.search(r"채권자명\s*\(실거래처\)\s*([\s\S]*?)(?:부가세액|조달/기타수수료|사업자번호)", text_p1)
        creditor = creditor_match.group(1).strip().replace("\n", " ") if creditor_match else ""
        creditor = re.sub(r"\(화천초등학교\)", "", creditor).strip()

        title_match = re.search(r"건\s*명\s*([\s\S]*?)(?:적\s*요|채\s*권\s*자)", text_p1)
        subject = title_match.group(1).strip().replace("\n", " ") if title_match else ""

        items = []
        if len(doc) > 1:
            blocks = doc[1].get_text("blocks")
            blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
            start_y, end_y = None, None
            for b in blocks:
                if "물 품 명 세 서" in b[4]:
                    start_y = b[3]
                elif "합  계" in b[4] and start_y is not None:
                    end_y = b[1]
                    break

            if start_y is not None:
                table_blocks = [b for b in blocks if b[1] >= start_y and (end_y is None or b[3] <= end_y + 10)]
                tokens = []
                for b in table_blocks:
                    for line in b[4].split('\n'):
                        l = line.strip()
                        if l and l != "물 품 명 세 서" and "합  계" not in l and "품명" not in l and "규격" not in l:
                            tokens.append(l)

                idx = 0
                while idx < len(tokens):
                    p_name = tokens[idx]
                    idx += 1
                    if idx >= len(tokens): break
                    spec = ""
                    if not re.match(r'^\d+$', tokens[idx]):
                        spec = tokens[idx]
                        idx += 1
                    if idx >= len(tokens): break
                    qty = 1
                    if re.match(r'^\d+$', tokens[idx]):
                        qty = int(tokens[idx])
                        idx += 1
                    if idx >= len(tokens): break
                    unit = tokens[idx]
                    idx += 1
                    if idx >= len(tokens): break
                    untprc = 0
                    if re.match(r'^\d{1,3}(,\d{3})*$', tokens[idx]):
                        untprc = int(tokens[idx].replace(',', ''))
                        idx += 1
                    if idx >= len(tokens): break
                    amt = 0
                    if re.match(r'^\d{1,3}(,\d{3})*$', tokens[idx]):
                        amt = int(tokens[idx].replace(',', ''))
                        idx += 1

                    if p_name and amt > 0:
                        items.append({
                            "prdlstNm": p_name,
                            "stndNm": spec,
                            "qty": qty,
                            "unitNm": unit,
                            "untprc": untprc if untprc > 0 else amt,
                            "amt": amt
                        })

        return {"creditor": creditor, "subject": subject, "items": items}

    summary_rows = []
    detail_rows = []

    for plan in decis_plan:
        p = plan['pumui']
        d = plan['decis']

        clean_seq = p['seq']
        clean_exres = d['sclExresSeq']
        amt_str = str(d['decisAmt'])

        matched_file = None
        for f in all_pdfs:
            if clean_seq in f and clean_exres in f and amt_str in f:
                matched_file = f
                break
        if not matched_file:
            for f in all_pdfs:
                if clean_seq in f and amt_str in f and d['decisDte'] in f:
                    matched_file = f
                    break

        parsed = {}
        if matched_file:
            pdf_path = os.path.join(DOWNLOAD_DIR, matched_file)
            parsed = parse_pdf(pdf_path)

        creditor = parsed.get("creditor", "")
        items = parsed.get("items", [])

        summary_rows.append({
            "순번": p['seq'],
            "품의일자": p['dte'],
            "품의제목": p['sj'],
            "품의금액": p['cnsulAmt'],
            "결의일자": d['decisDte'],
            "결의번호": d['sclExresSeq'],
            "거래처": creditor,
            "지출결의금액": d['decisAmt'],
            "품목수": len(items),
            "PDF파일명": matched_file or "미저장"
        })

        if items:
            for itm in items:
                detail_rows.append({
                    "품의일자": p['dte'],
                    "품의번호": p['seq'],
                    "품의제목": p['sj'],
                    "물품명": itm['prdlstNm'],
                    "규격": itm['stndNm'],
                    "결의수량": itm['qty'],
                    "단위": itm['unitNm'],
                    "결의단가": itm['untprc'],
                    "실제_지출결의금액": itm['amt'],
                    "결의일자": d['decisDte'],
                    "결의번호": d['sclExresSeq'],
                    "채권자(거래처)": creditor,
                    "결의서PDF": matched_file or ""
                })
        else:
            detail_rows.append({
                "품의일자": p['dte'],
                "품의번호": p['seq'],
                "품의제목": p['sj'],
                "물품명": parsed.get("subject", p['sj']),
                "규격": "",
                "결의수량": 1,
                "단위": "식",
                "결의단가": d['decisAmt'],
                "실제_지출결의금액": d['decisAmt'],
                "결의일자": d['decisDte'],
                "결의번호": d['sclExresSeq'],
                "채권자(거래처)": creditor,
                "결의서PDF": matched_file or ""
            })

    with open(SUMMARY_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["순번", "품의일자", "품의제목", "품의금액", "결의일자", "결의번호", "거래처", "지출결의금액", "품목수", "PDF파일명"])
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"  ✅ 총괄 대조표 저장 완료: {SUMMARY_CSV} (총 {len(summary_rows)}건 결의)")

    with open(DETAIL_CSV, "w", encoding="utf-8-sig", newline="") as f:
        if detail_rows:
            writer = csv.DictWriter(f, fieldnames=list(detail_rows[0].keys()))
            writer.writeheader()
            writer.writerows(detail_rows)
    print(f"  ✅ 품목별 정밀 대조표 저장 완료: {DETAIL_CSV} (총 {len(detail_rows)}개 품목)")

async def main():
    ws_url = get_klef_ws()
    if not ws_url:
        print("오류: 9222 포트에서 K-에듀파인 탭을 찾을 수 없습니다.")
        return

    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        msg_id = 5000
        def next_id():
            nonlocal msg_id
            msg_id += 1
            return msg_id

        # 1~2단계: 품의 및 다중 지출결의 스캔
        decis_plan = await collect_pumui_and_decis(ws, next_id)

        # 3단계: 전체 PDF 일괄 무인 다운로드
        await download_all_decis(ws, next_id, decis_plan)

        # 4단계: PDF 물품명세서 파싱 및 최종 CSV 생성
        parse_all_pdfs_and_build_csv()

if __name__ == '__main__':
    asyncio.run(main())
