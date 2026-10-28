#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import ctypes
import json
import sys
import urllib.request
import websockets

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CDP_HTTP = "http://127.0.0.1:9222"
CF_UNICODETEXT = 13
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

TITLE = "「경북형 웍스 AI」 활용 우수 사례 공모전 신청서 제출(에이전트 부문)"
BODY = """1. 관련: 미래교육정보과-15666(2026. 10. 11.)
2. 「경북형 웍스 AI」 활용 우수 사례 공모전 신청서(에이전트 부문)를 붙임과 같이 제출하고자 합니다.

붙임  공모 신청서(에이전트 부문) 1부.  끝."""


def set_clipboard_text(text: str) -> bool:
    if not text:
        return False
    try:
        if not user32.OpenClipboard(None):
            return False
        user32.EmptyClipboard()
        encoded = text.encode("utf-16le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(0x0042, len(encoded))
        if not h_mem:
            user32.CloseClipboard()
            return False
        p_mem = kernel32.GlobalLock(h_mem)
        if not p_mem:
            user32.CloseClipboard()
            return False
        ctypes.memmove(p_mem, encoded, len(encoded))
        kernel32.GlobalUnlock(h_mem)
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        user32.CloseClipboard()
        return True
    except Exception as e:
        print("clipboard fail", e)
        return False


def get_edufine_ws_url():
    tabs = json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=3).read().decode())
    for t in tabs:
        if t.get("type") == "page":
            url = t.get("url", "")
            if "klef" in url and "keris_ui" in url:
                return t.get("webSocketDebuggerUrl")
    for t in tabs:
        if t.get("type") == "page" and "klef" in t.get("url", ""):
            return t.get("webSocketDebuggerUrl")
    return None


async def main():
    print("clipboard:", set_clipboard_text(BODY))
    ws_url = get_edufine_ws_url()
    print("WS:", ws_url)
    async with websockets.connect(ws_url) as ws:
        cmd = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": """(() => {
                    let targetWin = null;
                    let iframes = document.querySelectorAll('iframe');
                    for (let f of iframes) {
                        try {
                            let url = f.contentWindow.location.href || '';
                            if (url.includes('retrieveCmmnFormatList') || url.includes('CmmnFormat')) {
                                targetWin = f.contentWindow;
                                break;
                            }
                        } catch(e) {}
                    }
                    if (!targetWin) return {ok:false, err:'no format iframe'};
                    try {
                        targetWin.eval("fncFormDraft('R10CB193640000146000','일반서식', '표준서식(결재4인,협조4인)');");
                        return {ok:true, href: targetWin.location.href};
                    } catch(e) {
                        return {ok:false, err: String(e)};
                    }
                })()""",
                "returnByValue": True,
                "awaitPromise": True,
            },
        }
        await ws.send(json.dumps(cmd))
        raw = await asyncio.wait_for(ws.recv(), timeout=12)
        print(raw)

    await asyncio.sleep(2)
    tabs = json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=3).read().decode())
    print("TABS AFTER:")
    for t in tabs:
        if t.get("type") in ("page", "iframe"):
            print(" ", t.get("type"), t.get("url"), (t.get("title") or "")[:80])


if __name__ == "__main__":
    asyncio.run(main())
