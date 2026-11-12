#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_nexacro.py
9222 포트에서 nexacro 객체가 있는 탭/컨텍스트를 찾고
기안 메뉴 직결 호출
"""

import asyncio
import json
import urllib.request
import websockets

CDP_HTTP = "http://127.0.0.1:9222"


async def try_tab(tab):
    ws_url = tab.get("webSocketDebuggerUrl", "")
    if not ws_url:
        print(f"  WS없음: {tab['url'][:60]}")
        return None

    title = tab.get("title", "")
    url = tab.get("url", "")
    print(f"\n=== 탭: {title[:40]} ===")
    print(f"  URL: {url[:70]}")

    try:
        async with websockets.connect(ws_url, max_size=5*1024*1024, open_timeout=5) as ws:
            # nexacro 타입 확인
            await ws.send(json.dumps({
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": "typeof nexacro",
                    "returnByValue": True,
                    "awaitPromise": False,
                    "timeout": 3000
                }
            }))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            val = resp.get("result", {}).get("result", {}).get("value", "?")
            print(f"  nexacro 타입: {val}")

            if val != "undefined" and val != "?":
                # nexacro 발견! 기안 메뉴 직결
                print("  ✓ nexacro 발견! 기안 메뉴 직결 시도...")

                js_full = """(function(){
                    try{
                        // 팝업 제거
                        try{
                            var app=nexacro.getApplication();
                            var main=app.mainframe.MainVFrameSet.SubHFrameSet.MainFrame;
                            if(main.noticePopup0) main.noticePopup0.destroy();
                        }catch(pe){}

                        // 업무관리 전환
                        try{
                            var top=nexacro.getApplication().mainframe.MainVFrameSet.TopFrame;
                            var cbo=top.form.cboJobList;
                            if(cbo && cbo.value!='A00AA'){
                                cbo.set_value('A00AA');
                                var ei=new nexacro.ItemChangeEventInfo(
                                    cbo,'onitemchanged',0,0,0,'A00AA');
                                top.form.cboJobList_onitemchanged(cbo,ei);
                                return 'switched_then_menu';
                            }
                        }catch(se){}

                        // 기안 메뉴 직결
                        var lf=nexacro.getApplication()
                            .mainframe.MainVFrameSet.SubHFrameSet.LeftFrame;
                        lf.form.gfnOpenMenu('A00AAB0101001');
                        return 'menu_opened';
                    }catch(e){
                        return 'ERROR:'+e.message;
                    }
                })()"""

                await ws.send(json.dumps({
                    "id": 99,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": js_full,
                        "returnByValue": True,
                        "awaitPromise": False,
                        "timeout": 5000
                    }
                }))
                resp2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=12))
                result = resp2.get("result", {}).get("result", {}).get("value", "")
                print(f"  메뉴 직결 결과: {result}")
                return result
            else:
                print("  nexacro 없음")
                return None

    except asyncio.TimeoutError:
        print("  타임아웃")
        return None
    except Exception as e:
        print(f"  오류: {e}")
        return None


async def main():
    with urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=5) as r:
        tabs = json.loads(r.read())

    print(f"전체 탭 수: {len(tabs)}")

    # 에듀파인/업무포털 관련 탭 먼저
    priority_tabs = []
    other_tabs = []
    for t in tabs:
        url = t.get("url", "").lower()
        t_type = t.get("type", "")
        if t_type == "page" and ("klef" in url or "eduptl" in url):
            priority_tabs.append(t)
        elif t_type == "page":
            other_tabs.append(t)

    print(f"우선 탭(에듀파인/업무포털): {len(priority_tabs)}개")

    found = None
    for tab in priority_tabs:
        result = await try_tab(tab)
        if result and "ERROR" not in str(result):
            found = result
            break

    if not found:
        print("\n우선 탭에서 미발견 → 나머지 탭 검색...")
        for tab in other_tabs[:5]:  # 처음 5개만
            result = await try_tab(tab)
            if result and "ERROR" not in str(result):
                found = result
                break

    print("\n" + "="*60)
    if found:
        print(f"🎉 성공: {found}")
        print("   에듀파인에서 [공용기안문] 버튼을 눌러주세요!")
    else:
        print("⚠ 자동 메뉴 열기 실패 → 수동 진행 안내:")
        print("  에듀파인 → 문서관리 → 기안 → 공용기안문")
    print()
    print("📌 제목: 2026년 학교 체육시설 개선 사업비 사업실적보고서 제출")
    print("📄 본문: Ctrl+V (클립보드에 복사됨)")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
