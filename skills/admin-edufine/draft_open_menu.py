#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
draft_open_menu.py
_pApplication / _application 으로 기안 메뉴 직결
"""

import asyncio, json, urllib.request, websockets

CDP_HTTP = "http://127.0.0.1:9222"


async def session_eval(ws, session_id, msg_id, expression, timeout=20):
    payload = {"id": msg_id, "sessionId": session_id,
                "method": "Runtime.evaluate",
                "params": {"expression": expression,
                           "returnByValue": True, "awaitPromise": False, "timeout": 6000}}
    await ws.send(json.dumps(payload))
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        remaining = deadline - asyncio.get_event_loop().time()
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            msg = json.loads(raw)
            if msg.get("id") == msg_id:
                return msg.get("result", {}).get("result", {})
        except asyncio.TimeoutError:
            break
    return {"value": "TIMEOUT"}


async def main():
    with urllib.request.urlopen(f"{CDP_HTTP}/json/version", timeout=5) as r:
        browser_ws = json.loads(r.read())["webSocketDebuggerUrl"]
    with urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=5) as r:
        tabs = json.loads(r.read())

    target_id = None
    for t in tabs:
        if t.get("type") == "page" and "klef" in t.get("url","").lower():
            target_id = t["id"]
            print(f"타겟: {t['title'][:50]}")
            break

    if not target_id:
        print("에듀파인 탭 없음"); return

    async with websockets.connect(browser_ws, max_size=10*1024*1024) as ws:
        # 세션
        await ws.send(json.dumps({"id":2,"method":"Target.attachToTarget",
                                  "params":{"targetId":target_id,"flatten":True}}))
        session_id = None
        deadline = asyncio.get_event_loop().time() + 10
        while asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            msg = json.loads(raw)
            if msg.get("id") == 2:
                session_id = msg.get("result", {}).get("sessionId")
                break
        print(f"세션: {session_id}")

        # _pApplication 구조 확인
        print("\n[1] _pApplication.mainframe 확인...")
        r1 = await session_eval(ws, session_id, 10, """(function(){
            try{
                var app = _pApplication || _application;
                if(!app) return 'no_app';
                var mf = app.mainframe;
                if(!mf) return 'no_mainframe';
                return 'mainframe:'+mf.id+' children:'+Object.keys(mf).slice(0,10).join(',');
            }catch(e){return 'err:'+e.message;}
        })()""")
        print(f"  {r1.get('value','')[:200]}")

        # 업무관리 시스템 현재 값 확인
        print("\n[2] 현재 시스템 콤보 값 확인...")
        r2 = await session_eval(ws, session_id, 11, """(function(){
            try{
                var app = _pApplication || _application;
                var top = app.mainframe.MainVFrameSet.TopFrame;
                var cbo = top.form.cboJobList;
                return 'cbo_value:'+cbo.value+' index:'+cbo.index;
            }catch(e){return 'err:'+e.message;}
        })()""")
        print(f"  {r2.get('value','')[:200]}")

        # 팝업 제거 + 업무관리 전환 + 기안 메뉴 직결
        print("\n[3] 팝업제거 + 시스템전환 + 기안 메뉴 직결...")
        r3 = await session_eval(ws, session_id, 99, """(function(){
            var app = _pApplication || _application;
            var mf = app.mainframe;

            // 공지 팝업 제거
            try{
                var main = mf.MainVFrameSet.SubHFrameSet.MainFrame;
                if(main && main.noticePopup0) main.noticePopup0.destroy();
            }catch(pe){}

            // 업무관리 전환
            var switched = false;
            try{
                var top = mf.MainVFrameSet.TopFrame;
                var cbo = top.form.cboJobList;
                if(cbo && cbo.value !== 'A00AA'){
                    cbo.set_value('A00AA');
                    var ei = new nexacro.ItemChangeEventInfo(
                        cbo,'onitemchanged',0,0,0,'A00AA');
                    top.form.cboJobList_onitemchanged(cbo, ei);
                    switched = true;
                }
            }catch(se){ return 'switch_err:'+se.message; }

            // 기안 메뉴 직결
            try{
                var lf = mf.MainVFrameSet.SubHFrameSet.LeftFrame;
                lf.form.gfnOpenMenu('A00AAB0101001');
                return 'SUCCESS switched='+switched;
            }catch(me){
                return 'menu_err:'+me.message+' switched='+switched;
            }
        })()""", timeout=25)
        val3 = r3.get("value", "")
        print(f"  결과: {val3}")

        if "SUCCESS" in str(val3):
            # 2초 대기 후 화면 확인
            await asyncio.sleep(2.0)
            print("\n[4] 현재 MDI 탭 확인...")
            r4 = await session_eval(ws, session_id, 50, """(function(){
                try{
                    var app=_pApplication||_application;
                    var main=app.mainframe.MainVFrameSet.SubHFrameSet.MainFrame;
                    var tabs=main.tabpages || {};
                    var info=[];
                    Object.keys(tabs).forEach(function(k){
                        try{info.push(k);}catch(e){}
                    });
                    return 'MDI tabs:'+info.slice(0,10).join(',');
                }catch(e){return 'check_err:'+e.message;}
            })()""")
            print(f"  {r4.get('value','')[:200]}")

    print("\n" + "="*60)
    if "SUCCESS" in str(val3):
        print("🎉 기안 메뉴가 열렸습니다!")
        print("   에듀파인 화면에서 [공용기안문] 버튼을 클릭하세요.")
    else:
        print("⚠ 메뉴 직결 실패. 아래 절차로 수동 진행:")
        print("   에듀파인 → 문서관리 → 기안 → 공용기안문")
    print()
    print("📌 제목: 2026년 학교 체육시설 개선 사업비 사업실적보고서 제출")
    print("📄 본문: Ctrl+V (클립보드에 복사됨)")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
