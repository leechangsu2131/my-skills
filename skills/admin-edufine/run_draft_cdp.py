#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_draft_cdp.py
CDP 경량 직결로 에듀파인 기안 메뉴 열기
(타임아웃 15초, 개별 recv 대기)
"""

import asyncio
import json
import urllib.request
import websockets

CDP_HTTP = "http://127.0.0.1:9222"

async def cdp_call(ws, msg_id, expression, recv_timeout=15):
    """CDP Runtime.evaluate 호출 후 해당 id 응답만 수신"""
    payload = {
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": False,
            "timeout": 5000
        }
    }
    await ws.send(json.dumps(payload))
    # id가 맞는 응답이 올 때까지 최대 recv_timeout초 대기
    deadline = asyncio.get_event_loop().time() + recv_timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return {"error": "timeout"}
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            resp = json.loads(raw)
            if resp.get("id") == msg_id:
                result = resp.get("result", {}).get("result", {})
                return result
        except asyncio.TimeoutError:
            return {"error": "timeout"}


async def main():
    # 에듀파인 탭 탐색
    with urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=5) as r:
        tabs = json.loads(r.read())

    ws_url = None
    tab_title = ""
    for tab in tabs:
        url = tab.get("url", "").lower()
        if tab.get("type") == "page" and ("klef" in url or "eduptl" in url):
            ws_url = tab["webSocketDebuggerUrl"]
            tab_title = tab.get("title", "")
            break
    if not ws_url:
        for tab in tabs:
            if tab.get("type") == "page":
                ws_url = tab["webSocketDebuggerUrl"]
                tab_title = tab.get("title", "")
                break

    if not ws_url:
        print("[오류] 열린 탭 없음")
        return

    print(f"탭 감지: {tab_title[:60]}")
    print(f"WebSocket: {ws_url[:70]}...")

    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:

        # ① 공지 팝업 제거
        print("\n[1] 공지 팝업 메모리 파괴...")
        r1 = await cdp_call(ws, 1,
            "try{"
            "nexacro.getApplication().mainframe.MainVFrameSet.SubHFrameSet.MainFrame.noticePopup0.destroy();"
            "'popup_ok'"
            "}catch(e){'skip:'+e.message}")
        print(f"    -> {r1.get('value', r1)}")

        await asyncio.sleep(0.8)

        # ② [업무관리] 시스템 전환
        print("\n[2] 업무관리 시스템 전환...")
        js_switch = """(function(){
            try{
                var app=nexacro.getApplication();
                var top=app.mainframe.MainVFrameSet.TopFrame;
                var cbo=top.form.cboJobList;
                if(cbo.value!='A00AA'){
                    cbo.set_value('A00AA');
                    var ei=new nexacro.ItemChangeEventInfo(
                        cbo,'onitemchanged',0,0,0,'A00AA');
                    top.form.cboJobList_onitemchanged(cbo,ei);
                    return 'switched_to_workMgmt';
                } else {
                    return 'already_workMgmt';
                }
            }catch(e){return 'sw_err:'+e.message;}
        })()"""
        r2 = await cdp_call(ws, 2, js_switch)
        print(f"    -> {r2.get('value', r2)}")

        await asyncio.sleep(2.0)

        # ③ 기안 메뉴 직결 호출 (공용서식 기안)
        print("\n[3] gfnOpenMenu('A00AAB0101001') 기안 메뉴 직결...")
        js_menu = """(function(){
            try{
                var lf=nexacro.getApplication()
                    .mainframe.MainVFrameSet.SubHFrameSet.LeftFrame;
                lf.form.gfnOpenMenu('A00AAB0101001');
                return 'menu_opened_ok';
            }catch(e){return 'menu_err:'+e.message;}
        })()"""
        r3 = await cdp_call(ws, 3, js_menu)
        print(f"    -> {r3.get('value', r3)}")

        await asyncio.sleep(3.0)

        # ④ 현재 화면 확인 (디버그용)
        print("\n[4] 현재 넥사크로 화면 확인...")
        js_check = """(function(){
            try{
                var app=nexacro.getApplication();
                var mf=app.mainframe;
                // 활성 MDI 탭 타이틀 확인
                var tabbar=mf.MainVFrameSet.SubHFrameSet.MainFrame;
                return tabbar ? tabbar.toString() : 'unknown';
            }catch(e){return 'check_err:'+e.message;}
        })()"""
        r4 = await cdp_call(ws, 4, js_check)
        print(f"    -> {r4.get('value', r4)}")

    print("\n" + "="*60)
    print("🎉 CDP 메뉴 직결 완료!")
    print("   에듀파인 화면에서 [공용기안문] 버튼을 눌러주세요.")
    print("   기안기 팝업이 열리면:")
    print()
    print("   📌 제목 입력:")
    print("   2026년 학교 체육시설 개선 사업비 사업실적보고서 제출")
    print()
    print("   📄 본문: Ctrl+V (클립보드에 복사됨)")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
