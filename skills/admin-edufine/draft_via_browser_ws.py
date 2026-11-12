#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
draft_via_browser_ws.py
브라우저 레벨 WebSocket (Target.activateTarget + Target.attachToTarget)으로
탭 프로세스 락 우회 후 JS 주입
"""

import asyncio
import json
import urllib.request
import websockets

CDP_HTTP = "http://127.0.0.1:9222"


async def main():
    # 1. 브라우저 레벨 WS URL 획득
    with urllib.request.urlopen(f"{CDP_HTTP}/json/version", timeout=5) as r:
        ver = json.loads(r.read())
    browser_ws = ver.get("webSocketDebuggerUrl", "")
    print(f"브라우저 WS: {browser_ws[:70]}")

    # 2. 탭 목록
    with urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=5) as r:
        tabs = json.loads(r.read())

    # 에듀파인/업무포털 탭 ID 찾기
    target_id = None
    for t in tabs:
        url = t.get("url", "").lower()
        if t.get("type") == "page" and ("klef" in url or "eduptl" in url):
            target_id = t.get("id")
            print(f"타겟: {t['title'][:40]} | {t['url'][:60]}")
            break

    if not target_id:
        print("에듀파인 탭 없음")
        return

    async with websockets.connect(browser_ws, max_size=10*1024*1024, open_timeout=10) as ws:

        # 3. 타겟 활성화 (탭을 포그라운드로)
        print(f"\n[1] Target.activateTarget({target_id})...")
        await ws.send(json.dumps({
            "id": 1,
            "method": "Target.activateTarget",
            "params": {"targetId": target_id}
        }))
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        print(f"  활성화: {resp}")

        await asyncio.sleep(1)

        # 4. 타겟에 붙기 (flattenSession=True로 같은 WS에서 직접 메시지 전달)
        print(f"\n[2] Target.attachToTarget({target_id}, flatten=True)...")
        await ws.send(json.dumps({
            "id": 2,
            "method": "Target.attachToTarget",
            "params": {"targetId": target_id, "flatten": True}
        }))

        session_id = None
        deadline = asyncio.get_event_loop().time() + 10
        while asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            msg = json.loads(raw)
            if msg.get("id") == 2:
                session_id = msg.get("result", {}).get("sessionId")
                print(f"  세션 ID: {session_id}")
                break

        if not session_id:
            print("  세션 획득 실패")
            return

        # 5. 세션을 통해 JS 실행
        def send_session(msg_id, expression):
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
            return json.dumps(payload)

        # nexacro 확인
        print("\n[3] nexacro 확인...")
        await ws.send(send_session(10, "typeof nexacro"))
        resp3 = json.loads(await asyncio.wait_for(ws.recv(), timeout=12))
        val = resp3.get("result", {}).get("result", {}).get("value", "?")
        print(f"  nexacro: {val}")

        if "undefined" in str(val):
            # iframe 접근 시도
            print("\n[4] iframe에서 nexacro 탐색...")
            await ws.send(send_session(11, """
                (function(){
                    var frames = document.querySelectorAll('iframe');
                    var info = [];
                    for(var i=0;i<frames.length;i++){
                        try{
                            var w=frames[i].contentWindow;
                            var hasNex = typeof w.nexacro !== 'undefined';
                            info.push(i+':src='+frames[i].src.substring(0,50)+':nexacro='+hasNex);
                        }catch(e){
                            info.push(i+':cross-origin');
                        }
                    }
                    return 'frames('+frames.length+'):['+info.join('|')+']';
                })()
            """))
            resp4 = json.loads(await asyncio.wait_for(ws.recv(), timeout=12))
            val4 = resp4.get("result", {}).get("result", {}).get("value", "")
            print(f"  {val4[:200]}")

        else:
            # nexacro 직결 기안 메뉴 호출
            print("\n[4] 기안 메뉴 직결...")
            js_full = """(function(){
                try{
                    try{
                        var app=nexacro.getApplication();
                        var main=app.mainframe.MainVFrameSet.SubHFrameSet.MainFrame;
                        if(main.noticePopup0) main.noticePopup0.destroy();
                    }catch(pe){}
                    try{
                        var top=nexacro.getApplication().mainframe.MainVFrameSet.TopFrame;
                        var cbo=top.form.cboJobList;
                        if(cbo && cbo.value!='A00AA'){
                            cbo.set_value('A00AA');
                            var ei=new nexacro.ItemChangeEventInfo(
                                cbo,'onitemchanged',0,0,0,'A00AA');
                            top.form.cboJobList_onitemchanged(cbo,ei);
                        }
                    }catch(se){}
                    var lf=nexacro.getApplication()
                        .mainframe.MainVFrameSet.SubHFrameSet.LeftFrame;
                    lf.form.gfnOpenMenu('A00AAB0101001');
                    return 'menu_opened_ok';
                }catch(e){return 'ERROR:'+e.message;}
            })()"""
            await ws.send(send_session(99, js_full))
            resp5 = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            val5 = resp5.get("result", {}).get("result", {}).get("value", "")
            print(f"  결과: {val5}")

    print("\n" + "="*60)
    print("📌 제목: 2026년 학교 체육시설 개선 사업비 사업실적보고서 제출")
    print("📄 본문: Ctrl+V")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
