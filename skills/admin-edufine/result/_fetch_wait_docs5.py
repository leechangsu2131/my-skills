#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import urllib.request
from datetime import datetime

import websockets

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CDP_HTTP = "http://127.0.0.1:9222"


def get_json(path):
    return json.loads(urllib.request.urlopen(f"{CDP_HTTP}{path}", timeout=5).read().decode())


async def cdp_call(ws, msg_id, method, params=None, timeout=25):
    cmd = {"id": msg_id, "method": method}
    if params:
        cmd["params"] = params
    await ws.send(json.dumps(cmd))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        data = json.loads(raw)
        if data.get("id") == msg_id:
            return data


def val(data):
    if "exceptionDetails" in data.get("result", {}):
        ed = data["result"]["exceptionDetails"]
        return {"error": ed.get("exception", {}).get("description") or ed.get("text")}
    res = data.get("result", {}).get("result", {})
    if res.get("subtype") == "error":
        return {"error": res.get("description")}
    return res.get("value")


JS_DETAIL = r"""
(() => {
  const as = [...document.querySelectorAll('a')].map(a => ({
    text: (a.innerText||'').trim().slice(0,120),
    title: (a.getAttribute('title')||'').slice(0,120),
    href: (a.getAttribute('href')||'').slice(0,200),
    onclick: (a.getAttribute('onclick')||'').slice(0,300)
  })).filter(x => x.text || x.title || x.onclick);
  const html = (document.body && document.body.innerHTML || '').slice(0, 4000);
  return {href: location.href, title: document.title, text: (document.body.innerText||'').slice(0,1500), as: as.slice(0, 20), html};
})()
"""

JS_SEARCH_IN_IFRAME2 = r"""
(() => {
  const f = document.querySelectorAll('iframe')[2];
  const w = f.contentWindow;
  const d = w.document;
  const logs = [w.location.href, d.title];
  const fns = ['fncSearch','fnSearch','doSearch','searchDoc'];
  for (const n of fns) {
    try { if (typeof w[n] === 'function') { w[n](); logs.push('called '+n); } } catch(e) { logs.push(n+' '+e); }
  }
  const btns = [...d.querySelectorAll('a, button, input')].filter(el => /조회/.test(el.innerText||el.value||''));
  logs.push('btns '+btns.length);
  try { if (btns[0]) btns[0].click(); logs.push('clicked'); } catch(e) { logs.push('click '+e); }
  return logs;
})()
"""


async def eval_on(ws, mid, expr):
    data = await cdp_call(ws, mid, "Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
    return val(data)


async def main():
    tabs = get_json("/json")
    for t in tabs:
        if t.get("type") == "iframe" and "retrieveSanctnWaitDocListNice" in (t.get("url") or ""):
            async with websockets.connect(t["webSocketDebuggerUrl"]) as ws:
                d = await eval_on(ws, 1, JS_DETAIL)
                print("NICE DETAIL", json.dumps(d, ensure_ascii=False)[:4000])
            break

    klef = next(t for t in tabs if t.get("type")=="page" and "keris_ui" in (t.get("url") or ""))
    async with websockets.connect(klef["webSocketDebuggerUrl"]) as ws:
        # temporarily open sanctn, click search, read, restore cnrs
        SANCTN = "https://klef.gbe.kr/bms/cz/cb/viw/retrieveSanctnWaitDocList.do?leftMenu=1"
        CNRS = "https://klef.gbe.kr/bms/cz/cb/viw/retrieveCnrsWaitDocList.do?MENU_ID=A00AAB0103001&FILE_ID=AABCnrsWaitDocList&alimZon=alimZon"
        await eval_on(ws, 1, f"document.querySelectorAll('iframe')[2].src = {json.dumps(SANCTN)}")
        await asyncio.sleep(3)
        logs = await eval_on(ws, 2, JS_SEARCH_IN_IFRAME2)
        print("SEARCH", logs)
        await asyncio.sleep(2)
        text = await eval_on(ws, 3, "document.querySelectorAll('iframe')[2].contentDocument.body.innerText.slice(0,2000)")
        print("AFTER SEARCH TEXT:\n", text)
        await eval_on(ws, 4, f"document.querySelectorAll('iframe')[2].src = {json.dumps(CNRS)}")
        print("restored cnrs")


if __name__ == "__main__":
    asyncio.run(main())
