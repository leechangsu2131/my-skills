#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
draft_find_app.py
nexacro 객체 구조 탐색 후 올바른 app 접근 경로 찾기 + 기안 메뉴 열기
"""

import asyncio
import json
import urllib.request
import websockets

CDP_HTTP = "http://127.0.0.1:9222"


async def session_eval(ws, session_id, msg_id, expression, timeout=15):
    payload = {
        "id": msg_id,
        "sessionId": session_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": False,
            "timeout": 5000
        }
    }
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


async def get_session(ws, target_id):
    await ws.send(json.dumps({
        "id": 2,
        "method": "Target.attachToTarget",
        "params": {"targetId": target_id, "flatten": True}
    }))
    deadline = asyncio.get_event_loop().time() + 10
    while asyncio.get_event_loop().time() < deadline:
        remaining = deadline - asyncio.get_event_loop().time()
        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        msg = json.loads(raw)
        if msg.get("id") == 2:
            return msg.get("result", {}).get("sessionId")
    return None


async def main():
    with urllib.request.urlopen(f"{CDP_HTTP}/json/version", timeout=5) as r:
        ver = json.loads(r.read())
    browser_ws = ver["webSocketDebuggerUrl"]

    with urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=5) as r:
        tabs = json.loads(r.read())

    # K-에듀파인 타겟
    target_id = None
    for t in tabs:
        url = t.get("url", "").lower()
        if t.get("type") == "page" and "klef" in url:
            target_id = t.get("id")
            print(f"타겟: {t['title'][:40]}")
            break

    if not target_id:
        print("에듀파인 탭 없음"); return

    async with websockets.connect(browser_ws, max_size=10*1024*1024) as ws:
        # 세션 연결
        session_id = await get_session(ws, target_id)
        print(f"세션: {session_id}")

        # nexacro 앱 접근 경로 탐색
        print("\n[1] nexacro 구조 탐색...")
        r1 = await session_eval(ws, session_id, 10, """(function(){
            try{
                var keys = Object.keys(nexacro).slice(0,20);
                return 'nexacro keys: ' + keys.join(',');
            }catch(e){ return 'err:'+e.message; }
        })()""")
        print(f"  {r1.get('value','')[:200]}")

        # _applications 탐색
        print("\n[2] nexacro._applications 탐색...")
        r2 = await session_eval(ws, session_id, 11, """(function(){
            try{
                var apps = nexacro._applications;
                if(!apps) return 'no _applications';
                var keys = Object.keys(apps);
                return 'apps: ' + keys.join(',') + ' count:'+keys.length;
            }catch(e){ return 'err:'+e.message; }
        })()""")
        print(f"  {r2.get('value','')[:200]}")

        # 첫 번째 앱으로 mainframe 접근
        print("\n[3] 첫 번째 앱 mainframe 접근...")
        r3 = await session_eval(ws, session_id, 12, """(function(){
            try{
                var apps = nexacro._applications;
                var keys = Object.keys(apps);
                if(keys.length === 0) return 'no apps';
                var app = apps[keys[0]];
                var mf = app.mainframe;
                if(!mf) return 'no mainframe in app['+keys[0]+']';
                return 'mainframe found: ' + mf.toString().substring(0,50);
            }catch(e){ return 'err:'+e.message; }
        })()""")
        print(f"  {r3.get('value','')[:200]}")

        # 기안 메뉴 직결 (올바른 app 접근)
        print("\n[4] 기안 메뉴 직결 시도...")
        r4 = await session_eval(ws, session_id, 99, """(function(){
            try{
                var apps = nexacro._applications;
                var keys = Object.keys(apps);
                if(keys.length === 0) return 'no_apps';
                var app = apps[keys[0]];
                var mf = app.mainframe;

                // 팝업 제거
                try{
                    var main=mf.MainVFrameSet.SubHFrameSet.MainFrame;
                    if(main && main.noticePopup0) main.noticePopup0.destroy();
                }catch(pe){}

                // 업무관리 전환
                try{
                    var top=mf.MainVFrameSet.TopFrame;
                    var cbo=top.form.cboJobList;
                    if(cbo && cbo.value!='A00AA'){
                        cbo.set_value('A00AA');
                        var ei=new nexacro.ItemChangeEventInfo(
                            cbo,'onitemchanged',0,0,0,'A00AA');
                        top.form.cboJobList_onitemchanged(cbo,ei);
                    }
                }catch(se){}

                // 기안 메뉴 직결 (공용서식 기안)
                var lf=mf.MainVFrameSet.SubHFrameSet.LeftFrame;
                lf.form.gfnOpenMenu('A00AAB0101001');
                return 'SUCCESS_menu_opened';
            }catch(e){
                // 대안: app.popupframes 등 다른 경로
                try{
                    var app2 = window.application || window.app;
                    if(app2){
                        var lf2=app2.mainframe.MainVFrameSet.SubHFrameSet.LeftFrame;
                        lf2.form.gfnOpenMenu('A00AAB0101001');
                        return 'SUCCESS_via_window_app';
                    }
                }catch(e2){}
                return 'ERROR:'+e.message;
            }
        })()""", timeout=20)
        val4 = r4.get("value", "")
        print(f"  결과: {val4}")

        if "SUCCESS" in str(val4):
            print("\n🎉 기안 메뉴가 열렸습니다!")
            print("   에듀파인에서 [공용기안문] 버튼을 눌러주세요.")
        else:
            # 대안: window 레벨 탐색
            print("\n[5] window 레벨 app 탐색 (대안)...")
            r5 = await session_eval(ws, session_id, 100, """(function(){
                try{
                    var candidates = ['application','App','nexacroApp','mainApp','_app'];
                    for(var i=0;i<candidates.length;i++){
                        if(window[candidates[i]]){
                            return 'found: window.'+candidates[i];
                        }
                    }
                    // 가능한 글로벌 중 mainframe이 있는 것
                    var globals = Object.keys(window).filter(function(k){
                        try{ return window[k] && window[k].mainframe; }catch(e){ return false; }
                    });
                    return 'globals_with_mainframe: '+globals.join(',');
                }catch(e){ return 'err:'+e.message; }
            })()""")
            print(f"  {r5.get('value','')[:200]}")

    print("\n" + "="*60)
    print("📌 제목: 2026년 학교 체육시설 개선 사업비 사업실적보고서 제출")
    print("📄 본문: Ctrl+V (클립보드에 복사됨)")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
