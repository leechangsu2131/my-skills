#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import urllib.request
import websockets

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CDP_HTTP = "http://127.0.0.1:9222"


def get_json(path):
    return json.loads(urllib.request.urlopen(f"{CDP_HTTP}{path}", timeout=5).read().decode())


async def cdp_call(ws, msg_id, method, params=None, timeout=15):
    cmd = {"id": msg_id, "method": method}
    if params:
        cmd["params"] = params
    await ws.send(json.dumps(cmd))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        data = json.loads(raw)
        if data.get("id") == msg_id:
            return data


async def main():
    tabs = get_json("/json")
    print("BEFORE TABS:")
    for t in tabs:
        if t.get("type") in ("page", "iframe"):
            print(" ", t.get("type"), t.get("url"), (t.get("title") or "")[:50])

    version = get_json("/json/version")
    browser_ws = version["webSocketDebuggerUrl"]
    print("BROWSER WS:", browser_ws)

    async with websockets.connect(browser_ws) as ws:
        res = await cdp_call(
            ws,
            1,
            "Target.createTarget",
            {"url": "https://klef.gbe.kr/keris_ui/main.do"},
        )
        print("createTarget:", json.dumps(res, ensure_ascii=False))

    await asyncio.sleep(4)
    tabs = get_json("/json")
    print("AFTER TABS:")
    for t in tabs:
        if t.get("type") in ("page", "iframe"):
            print(" ", t.get("type"), t.get("url"), (t.get("title") or "")[:50])


if __name__ == "__main__":
    asyncio.run(main())
