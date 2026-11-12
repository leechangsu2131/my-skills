#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_draft_now.py
경량 CDP(WebSocket) 직결 방식으로 에듀파인 기안 자동화 실행
ing.md 수칙 9번: connect_over_cdp 락 회피 → 탭별 webSocketDebuggerUrl 직결
"""

import asyncio
import json
import sys
import ctypes
import websockets
import urllib.request

CDP_HTTP = "http://127.0.0.1:9222"

# ── 클립보드 ────────────────────────────────────────────────
CF_UNICODETEXT = 13
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def set_clipboard(text: str):
    try:
        encoded = text.encode('utf-16le') + b'\x00\x00'
        user32.OpenClipboard(None)
        user32.EmptyClipboard()
        h = kernel32.GlobalAlloc(0x0042, len(encoded))
        p = kernel32.GlobalLock(h)
        ctypes.memmove(p, encoded, len(encoded))
        kernel32.GlobalUnlock(h)
        user32.SetClipboardData(CF_UNICODETEXT, h)
        user32.CloseClipboard()
        print("   ✓ 클립보드에 본문 복사 완료 (안전망 준비됨)")
        return True
    except Exception as e:
        print(f"   [클립보드 오류] {e}")
        return False


# ── CDP JSON-RPC 경량 헬퍼 ──────────────────────────────────
async def cdp_eval(ws_url: str, expression: str, timeout=10):
    """WebSocket CDP로 JS 실행 후 결과 반환"""
    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        msg_id = 1
        payload = json.dumps({
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": False
            }
        })
        await ws.send(payload)
        deadline = asyncio.get_event_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise TimeoutError("CDP 응답 대기 시간 초과")
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                raise TimeoutError("CDP 응답 대기 시간 초과")
            resp = json.loads(raw)
            if resp.get("id") == msg_id:
                return resp


async def find_edufine_tab():
    """9222 포트에서 에듀파인 탭 webSocketDebuggerUrl 탐색"""
    with urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=5) as r:
        tabs = json.loads(r.read())
    
    # 에듀파인 탭 우선 탐색
    for tab in tabs:
        url = tab.get("url", "").lower()
        t_type = tab.get("type", "")
        if t_type == "page" and ("klef" in url or "eduptl" in url):
            print(f"   ✓ 에듀파인 탭 발견: {tab.get('title','')[:50]}")
            return tab["webSocketDebuggerUrl"]
    
    # 없으면 첫 번째 page 탭
    for tab in tabs:
        if tab.get("type") == "page":
            print(f"   ⚠ 에듀파인 탭 미발견. 현재 탭 사용: {tab.get('title','')[:50]}")
            return tab["webSocketDebuggerUrl"]
    
    return None


async def main():
    TITLE = "2026년 학교 체육시설 개선 사업비 사업실적보고서 제출"
    BODY = (
        "1. 관련: 경상북도경주교육지원청 교육지원과-15363(2026. 4. 3.)\n"
        "2. 위 호와 관련하여 2026년 학교 체육시설 개선 사업비 사업실적보고서를 붙임과 같이 제출합니다.\n"
        "  가. 사업명: 화천초등학교(자투리공간 활용 체육시설 구축)\n"
        "  나. 집행총괄: 교부액 20,000,000원, 집행액 20,000,000원, 집행잔액 0원\n"
        "  다. 집행내역\n"
        "   - 1차(2026. 6. 24.～9. 21.): 18,484,560원\n"
        "   - 2차(2026. 10. 28.): 1,475,280원\n"
        "   - 3차(2026. 11. 3.): 40,160원\n"
        "\n"
        "붙임  사업실적보고서 1부.  끝."
    )

    print("=" * 60)
    print("🚀 [트랙 2] K-에듀파인 공문 기안 봇 (CDP 경량 직결)")
    print(f"   제목: {TITLE}")
    print("=" * 60)

    # 1. 클립보드 안전망 먼저 준비
    set_clipboard(BODY)

    # 2. 에듀파인 탭 탐색
    ws_url = await find_edufine_tab()
    if not ws_url:
        print("[오류] 열린 탭을 찾지 못했습니다.")
        return False

    print(f"   WebSocket: {ws_url[:60]}...")

    # 3. 공지 팝업 제거
    print("   [팝업 제거] 공지사항 팝업 메모리 파괴 시도...")
    try:
        await cdp_eval(ws_url, """
            try {
                var app = nexacro.getApplication();
                var mf = app.mainframe;
                var sub = mf.MainVFrameSet && mf.MainVFrameSet.SubHFrameSet;
                var main = sub && sub.MainFrame;
                if (main && main.noticePopup0) {
                    main.noticePopup0.destroy();
                    'popup_destroyed';
                } else {
                    // popupframes 순회
                    if (app.popupframes) {
                        for (var k in app.popupframes) {
                            try { app.popupframes[k].form.close(); } catch(e) {}
                        }
                    }
                    'popup_closed_all';
                }
            } catch(e) { 'popup_skip:' + e.message; }
        """, timeout=5)
        print("   ✓ 팝업 처리 완료")
    except Exception as e:
        print(f"   (팝업 처리 스킵: {e})")

    await asyncio.sleep(0.5)

    # 4. [업무관리] 시스템 전환 확인 후 기안 메뉴 직결 호출
    print("   [메뉴 직결] gfnOpenMenu('A00AAB0101001') 호출...")
    try:
        result = await cdp_eval(ws_url, """
            (function() {
                try {
                    // 업무관리 시스템으로 전환
                    var top = nexacro.getApplication().mainframe.MainVFrameSet.TopFrame;
                    var cbo = top && top.form && top.form.cboJobList;
                    if (cbo) {
                        var curVal = cbo.value;
                        if (curVal !== 'A00AA') {
                            cbo.set_index(0);
                            cbo.set_value('A00AA');
                            var evtInfo = new nexacro.ItemChangeEventInfo(cbo, 'onitemchanged', 0, 0, cbo.index, cbo.value);
                            cbo.cboJobList_onitemchanged(cbo, evtInfo);
                        }
                    }
                    return 'system_switched';
                } catch(e) { return 'switch_skip:' + e.message; }
            })();
        """, timeout=5)
        print(f"   시스템 전환: {result.get('result',{}).get('result',{}).get('value','')}")
    except Exception as e:
        print(f"   (시스템 전환 스킵: {e})")

    await asyncio.sleep(1.5)

    # 5. 기안 메뉴 직결 호출 (공용서식 기안)
    try:
        result = await cdp_eval(ws_url, """
            (function() {
                try {
                    var lf = nexacro.getApplication().mainframe.MainVFrameSet.SubHFrameSet.LeftFrame;
                    lf.form.gfnOpenMenu('A00AAB0101001');
                    return 'menu_opened';
                } catch(e) {
                    // 대안: 직접 프레임 탐색
                    try {
                        var frames = document.querySelectorAll('iframe');
                        for (var i = 0; i < frames.length; i++) {
                            try {
                                var w = frames[i].contentWindow;
                                if (w && w.form && w.form.gfnOpenMenu) {
                                    w.form.gfnOpenMenu('A00AAB0101001');
                                    return 'menu_opened_fallback';
                                }
                            } catch(e2) {}
                        }
                        return 'menu_fallback_failed:' + e.message;
                    } catch(e3) { return 'menu_error:' + e3.message; }
                }
            })();
        """, timeout=8)
        val = result.get('result',{}).get('result',{}).get('value','')
        print(f"   기안 메뉴: {val}")
    except Exception as e:
        print(f"   (메뉴 직결 오류: {e})")

    await asyncio.sleep(2.5)

    # 6. 기안문 작성 창 대기 후 제목 입력 시도 (Playwright 없이 CDP만으로)
    print("   [안내] 기안문 작성 화면이 열렸습니다.")
    print("         에듀파인 화면을 확인하여 [공용기안문] 버튼을 누르고")
    print("         기안기 팝업이 열리면 아래 내용을 붙여넣으세요.")
    print()
    print("─" * 60)
    print(f"📌 제목: {TITLE}")
    print()
    print("📄 본문 (클립보드에 복사됨 → Ctrl+V):")
    print(BODY)
    print("─" * 60)
    print()
    print("✅ 클립보드에 본문이 복사되어 있습니다.")
    print("   기안기 본문 영역 클릭 후 Ctrl+V 하시면 됩니다.")
    print("   결재선 지정 및 상신은 직접 확인 후 진행해 주세요.")
    return True


if __name__ == "__main__":
    asyncio.run(main())
