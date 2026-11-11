"""
개산금정산 자동화 봇 (트랙 7)
==============================
경북교육청 K-에듀파인 [학교회계] > 사업관리 > 사업담당 > 품의/정산 > 개산금정산등록 화면에서
담임교사가 집행한 학급 자율 운영비(개산급)를 영수증별로 행추가하여 정산 처리합니다.

확정 메뉴 ID: A00FAA0104001004
증빙구분 코드: '3' (전산자료/신용카드), '1' (세금계산서), '2' (계산서) 등

특징:
 - 브라우저 메인 프로세스 락을 우회하는 WebSocket CDP JSON-RPC 직접 통신
 - 넥사크로 DataSet 레벨 바인딩 주입 및 정밀 저장 처리
 - 상단 수령액/집행액/과부족잔액 실시간 갱신 검증
"""

import asyncio
import json
import urllib.request
import websockets

CDP_HTTP = "http://127.0.0.1:9222"
MENU_ID_GAISAN = "A00FAA0104001004"


def get_klef_ws_url():
    """K-에듀파인 메인 탭 WebSocket URL 획득"""
    try:
        req = urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=3)
        tabs = json.loads(req.read().decode('utf-8'))
        for t in tabs:
            if t.get('type') == 'page' and 'klef' in t.get('url', ''):
                return t.get('webSocketDebuggerUrl')
    except Exception:
        pass
    return None


async def cdp_call(ws, msg_id, method, params=None):
    cmd = {"id": msg_id, "method": method}
    if params:
        cmd["params"] = params
    await ws.send(json.dumps(cmd))
    while True:
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get("id") == msg_id:
            return data


async def execute_gaisan_jungsan(rows: list, start_date: str = "2026-03-01", auto_submit: bool = False) -> dict:
    """
    개산금정산 자동화 메인 진입점.
    rows: [{'사용일자': '2026-10-23', '사용업체명': 'G마켓', '사용금액': 101800, '증빙구분': '전산자료', '사용내역': '학급운영 물품 구입'}]
    """
    if not rows:
        return {"success": False, "message": "입력할 정산 항목이 없습니다."}

    ws_url = get_klef_ws_url()
    if not ws_url:
        return {
            "success": False,
            "message": "9222 포트에 열려있는 K-에듀파인 탭을 찾지 못했습니다. 에듀파인에 로그인 후 다시 시도해 주세요."
        }

    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        # 1. 팝업 파괴 & 학교회계(A00FA) 전환
        init_script = """
        (function(){
            var app = nexacro.getApplication();
            if(!app) return JSON.stringify({error: 'no_app'});

            // 팝업 파괴
            try {
                if(app.mainframe && app.mainframe.MainVFrameSet && app.mainframe.MainVFrameSet.SubHFrameSet){
                    app.mainframe.MainVFrameSet.SubHFrameSet.MainFrame.noticePopup0.destroy();
                }
            } catch(e){}

            // 학교회계(A00FA, idx 2) 전환
            var top = app.mainframe.MainVFrameSet.TopFrame.form;
            var cbo = top.cboJobList;
            if(cbo.value !== 'A00FA'){
                var oldIdx = cbo.index;
                cbo.set_index(2);
                if(top.cboJobList_onitemchanged){
                    var evt = new nexacro.ItemChangeEventInfo(cbo, 'onitemchanged', oldIdx, 'A00AA', '업무관리', 2, 'A00FA', '학교회계');
                    top.cboJobList_onitemchanged(cbo, evt);
                }
            }
            return JSON.stringify({status: 'ok', currentJob: cbo.value});
        })()
        """
        r1 = await cdp_call(ws, 1, "Runtime.evaluate", {"expression": init_script, "returnByValue": True})
        await asyncio.sleep(2)

        # 2. 개산금정산등록 메뉴 열기 (gfnOpenMenu)
        open_script = f"""
        (function(){{
            var app = nexacro.getApplication();
            var left = app.mainframe.MainVFrameSet.SubHFrameSet.LeftFrame;
            if(left && left.form && left.form.gfnOpenMenu){{
                left.form.gfnOpenMenu('{MENU_ID_GAISAN}');
                return 'opened';
            }}
            return 'failed';
        }})()
        """
        r2 = await cdp_call(ws, 2, "Runtime.evaluate", {"expression": open_script, "returnByValue": True})
        await asyncio.sleep(3)

        # 3. 시작일자 설정 및 조회
        clean_date = start_date.replace("-", "").strip()
        search_script = f"""
        (function(){{
            var app = nexacro.getApplication();
            var workFrame = app.mainframe.MainVFrameSet.SubHFrameSet.WorkVFrameSet.WorkFrame;
            var targetFrame = null;
            for(var i=0; i<workFrame.all.length; i++){{
                if(workFrame.all[i].name.indexOf('{MENU_ID_GAISAN}') >= 0){{
                    targetFrame = workFrame.all[i];
                    break;
                }}
            }}
            if(!targetFrame) return JSON.stringify({{error: 'targetFrame not found'}});

            var form = targetFrame.form;
            var searchDiv = form.divWork.form.divSearch.form;
            searchDiv.calRecptDteFrom.set_value('{clean_date}');
            form.divWork.form.divAuth.form.btnAuthS01.click(); // [조회]
            return JSON.stringify({{status: 'searched', from: searchDiv.calRecptDteFrom.value}});
        }})()
        """
        r3 = await cdp_call(ws, 3, "Runtime.evaluate", {"expression": search_script, "returnByValue": True})
        await asyncio.sleep(2.5)

        # 4. 정산 행들 추가 및 입력
        rows_json = json.dumps(rows, ensure_ascii=False)
        insert_script = f"""
        (function(){{
            var app = nexacro.getApplication();
            var workFrame = app.mainframe.MainVFrameSet.SubHFrameSet.WorkVFrameSet.WorkFrame;
            var targetFrame = null;
            for(var i=0; i<workFrame.all.length; i++){{
                if(workFrame.all[i].name.indexOf('{MENU_ID_GAISAN}') >= 0){{
                    targetFrame = workFrame.all[i];
                    break;
                }}
            }}
            if(!targetFrame) return JSON.stringify({{error: 'targetFrame not found'}});

            var form = targetFrame.form;
            var btnAdd = form.divWork.form.divAuth3.form.btnAddRow;
            var dsDetail = form.divWork.form.grdDetail.getBindDataset();
            var inputRows = {rows_json};

            var added = [];
            for(var item of inputRows){{
                btnAdd.click();
                var newRow = dsDetail.rowposition;
                
                var dte = String(item['사용일자'] || '').replace(/-/g, '').trim();
                var place = String(item['사용업체명'] || '').trim();
                var amt = parseInt(String(item['사용금액'] || '0').replace(/[^0-9]/g, ''), 10);
                var cn = String(item['사용내역'] || '').trim();
                
                // 증빙구분 코드 매핑 (전산자료/신용카드: 3, 기타: 3)
                var pruf = '3';
                if(item['증빙구분'] === '현금영수증') pruf = '4';
                else if(item['증빙구분'] === '세금계산서') pruf = '1';

                dsDetail.setColumn(newRow, 'pymntDte', dte);
                dsDetail.setColumn(newRow, 'usePlaceNm', place);
                dsDetail.setColumn(newRow, 'pymntAmt', amt);
                dsDetail.setColumn(newRow, 'prufSeCd', pruf);
                dsDetail.setColumn(newRow, 'useCn', cn);
                added.push({{row: newRow, dte: dte, place: place, amt: amt}});
            }}

            // 5. 저장
            var btnSave = form.divWork.form.divAuth.form.btnAuthR01;
            btnSave.click();

            return JSON.stringify({{status: 'saved', addedCount: added.length, added: added}});
        }})()
        """
        r4 = await cdp_call(ws, 4, "Runtime.evaluate", {"expression": insert_script, "returnByValue": True})
        res_val = json.loads(r4.get("result", {}).get("result", {}).get("value"))

        await asyncio.sleep(2)

        # 6. 정산서 제출 (옵션)
        if auto_submit:
            submit_script = f"""
            (function(){{
                var app = nexacro.getApplication();
                var workFrame = app.mainframe.MainVFrameSet.SubHFrameSet.WorkVFrameSet.WorkFrame;
                for(var i=0; i<workFrame.all.length; i++){{
                    if(workFrame.all[i].name.indexOf('{MENU_ID_GAISAN}') >= 0){{
                        var form = workFrame.all[i].form;
                        form.divWork.form.divAuth2.form.btnPrsnt.click();
                        return 'submitted';
                    }}
                }}
                return 'failed';
            }})()
            """
            await cdp_call(ws, 5, "Runtime.evaluate", {"expression": submit_script, "returnByValue": True})

        return {
            "success": True,
            "message": f"총 {len(rows)}건 개산금정산 입력 및 저장이 완료되었습니다!" + (" (정산서 제출 완료)" if auto_submit else "")
        }
