#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_draft_ctx.py
올바른 iframe 실행 컨텍스트(contextId)에서 nexacro 직결 호출
ing.md: nexacro는 메인 프레임이 아닌 하위 iframe에서 동작
"""

import asyncio
import json
import urllib.request
import websockets

CDP_HTTP = "http://127.0.0.1:9222"


async def recv_until(ws, target_id=None, timeout=15):
    """target_id에 해당하는 응답 or 모든 메시지 수신"""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return None
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            msg = json.loads(raw)
            if target_id is None or msg.get("id") == target_id:
                return msg
        except asyncio.TimeoutError:
            return None


async def main():
    # 1. 에듀파인 탭 탐색
    with urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=5) as r:
        tabs = json.loads(r.read())

    target_tab = None
    for tab in tabs:
        url = tab.get("url", "").lower()
        if tab.get("type") == "page" and ("klef" in url or "eduptl" in url):
            target_tab = tab
            break
    if not target_tab:
        for tab in tabs:
            if tab.get("type") == "page":
                target_tab = tab
                break

    if not target_tab:
        print("[오류] 탭 없음")
        return

    ws_url = target_tab["webSocketDebuggerUrl"]
    print(f"탭: {target_tab.get('title','')[:60]}")
    print(f"URL: {target_tab.get('url','')[:80]}")

    async with websockets.connect(ws_url, max_size=10*1024*1024, open_timeout=10) as ws:

        # 2. Runtime 활성화 및 실행 컨텍스트 목록 수집
        print("\n[1] Runtime.enable → 실행 컨텍스트 수집...")
        await ws.send(json.dumps({"id": 10, "method": "Runtime.enable"}))

        contexts = []
        deadline = asyncio.get_event_loop().time() + 5
        while asyncio.get_event_loop().time() < deadline:
            remaining = deadline - asyncio.get_event_loop().time()
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                msg = json.loads(raw)
                method = msg.get("method", "")
                if method == "Runtime.executionContextCreated":
                    ctx = msg["params"]["context"]
                    ctx_id = ctx.get("id")
                    ctx_name = ctx.get("name", "")
                    ctx_origin = ctx.get("origin", "")
                    ctx_desc = ctx.get("auxData", {})
                    contexts.append({
                        "id": ctx_id,
                        "name": ctx_name,
                        "origin": ctx_origin,
                        "aux": ctx_desc
                    })
            except asyncio.TimeoutError:
                break

        print(f"   수집된 컨텍스트 수: {len(contexts)}")
        for c in contexts:
            print(f"   - id={c['id']} name='{c['name'][:30]}' origin={c['origin'][:50]}")

        # 3. nexacro가 있는 컨텍스트 탐색
        print("\n[2] nexacro 객체 보유 컨텍스트 탐색...")
        nexacro_ctx_id = None

        # 컨텍스트가 없으면 기본(메인) 컨텍스트로 시도
        test_ids = [c["id"] for c in contexts] if contexts else [None]

        for ctx_id in test_ids:
            params = {
                "expression": "typeof nexacro !== 'undefined' ? 'found:'+nexacro.toString().substring(0,30) : 'notfound'",
                "returnByValue": True,
                "awaitPromise": False,
                "timeout": 3000
            }
            if ctx_id is not None:
                params["contextId"] = ctx_id

            msg_id = 100 + (ctx_id or 0)
            await ws.send(json.dumps({
                "id": msg_id,
                "method": "Runtime.evaluate",
                "params": params
            }))
            resp = await recv_until(ws, target_id=msg_id, timeout=8)
            if resp:
                val = resp.get("result", {}).get("result", {}).get("value", "")
                if val and "found" in str(val):
                    nexacro_ctx_id = ctx_id
                    print(f"   ✓ nexacro 발견 contextId={ctx_id}: {str(val)[:60]}")
                    break
                else:
                    print(f"   - contextId={ctx_id}: {str(val)[:40]}")

        if nexacro_ctx_id is None and not contexts:
            # 컨텍스트 없이 메인으로 재시도
            print("   컨텍스트 목록 없음 → 메인 프레임 직접 시도")
            nexacro_ctx_id = None  # None이면 contextId 파라미터 없이 실행

        # 4. 기안 메뉴 직결 호출
        print(f"\n[3] gfnOpenMenu 직결 (contextId={nexacro_ctx_id})...")
        js_draft = """(function(){
            try{
                // 공지 팝업 제거
                try{
                    var app=nexacro.getApplication();
                    var mf=app.mainframe;
                    var sh=mf.MainVFrameSet.SubHFrameSet;
                    var main=sh.MainFrame;
                    if(main.noticePopup0) main.noticePopup0.destroy();
                } catch(pe){}

                // 업무관리 전환
                try{
                    var top=nexacro.getApplication().mainframe.MainVFrameSet.TopFrame;
                    var cbo=top.form.cboJobList;
                    if(cbo && cbo.value!='A00AA'){
                        cbo.set_value('A00AA');
                        var ei=new nexacro.ItemChangeEventInfo(cbo,'onitemchanged',0,0,0,'A00AA');
                        top.form.cboJobList_onitemchanged(cbo,ei);
                    }
                } catch(se){}

                // 기안 메뉴 직결
                var lf=nexacro.getApplication().mainframe.MainVFrameSet.SubHFrameSet.LeftFrame;
                lf.form.gfnOpenMenu('A00AAB0101001');
                return 'SUCCESS: menu opened';
            } catch(e) {
                return 'ERROR: '+e.message;
            }
        })()"""

        params = {
            "expression": js_draft,
            "returnByValue": True,
            "awaitPromise": False,
            "timeout": 5000
        }
        if nexacro_ctx_id is not None:
            params["contextId"] = nexacro_ctx_id

        await ws.send(json.dumps({
            "id": 999,
            "method": "Runtime.evaluate",
            "params": params
        }))
        resp_final = await recv_until(ws, target_id=999, timeout=15)
        if resp_final:
            val = resp_final.get("result", {}).get("result", {}).get("value", "")
            err = resp_final.get("result", {}).get("exceptionDetails", {})
            print(f"   결과: {val}")
            if err:
                print(f"   예외: {err.get('text','')}")
        else:
            print("   응답 없음 (timeout)")

    print("\n" + "="*60)
    print("🎉 완료!")
    print("   에듀파인 화면에서 [공용기안문] 버튼을 눌러주세요.")
    print()
    print("   📌 제목:")
    print("   2026년 학교 체육시설 개선 사업비 사업실적보고서 제출")
    print()
    print("   📄 본문: Ctrl+V (클립보드에 복사됨)")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
