#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import urllib.request
from pathlib import Path

import websockets

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CDP_HTTP = "http://127.0.0.1:9222"
OUT = Path(__file__).resolve().parent / "edufine_doc_inspect.json"


def tabs():
    return json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=5).read().decode())


async def ev(ws, mid, expr, timeout=25):
    await ws.send(json.dumps({
        "id": mid,
        "method": "Runtime.evaluate",
        "params": {"expression": expr, "returnByValue": True},
    }))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        data = json.loads(raw)
        if data.get("id") == mid:
            if "exceptionDetails" in data.get("result", {}):
                return {"error": data["result"]["exceptionDetails"]}
            return data.get("result", {}).get("result", {}).get("value")


JS = r"""
(() => {
  const iframes = [...document.querySelectorAll('iframe')];
  let win = null, idx = -1;
  iframes.forEach((f, i) => {
    try {
      const href = f.contentWindow.location.href || '';
      if (href.includes('retrieveSanctnWaitDocList')) { win = f.contentWindow; idx = i; }
    } catch (e) {}
  });
  if (!win) return {error: 'no sanctn iframe'};
  const d = win.document;
  const keys = [];
  for (const k in win) {
    try {
      if (typeof win[k] === 'function' && /att|file|down|pdf|hwp|view|call|doc|appr|cnrs|sanctn|public|client/i.test(k))
        keys.push(k);
    } catch (e) {}
  }
  const as = [...d.querySelectorAll('a')].map(a => ({
    text: (a.innerText||'').trim().slice(0,80),
    onclick: (a.getAttribute('onclick')||'').slice(0,250),
    href: (a.getAttribute('href')||'').slice(0,120),
    id: a.id
  })).filter(x => x.text || x.onclick || x.id).slice(0, 80);
  const imgs = [...d.querySelectorAll('img, area, [onclick]')].slice(0, 40).map(el => ({
    tag: el.tagName, id: el.id, src: (el.getAttribute('src')||'').slice(0,80),
    onclick: (el.getAttribute('onclick')||'').slice(0,250),
    title: (el.getAttribute('title')||'').slice(0,80)
  }));
  const chk = d.querySelector('input[name=docinfo]');
  const detailHtml = (d.getElementById('docDetail') && d.getElementById('docDetail').innerHTML
    || d.getElementById('apprInfo') && d.getElementById('apprInfo').innerHTML
    || '').slice(0, 1500);
  return {
    idx, href: win.location.href,
    keys: keys.sort(),
    as, imgs,
    chk: chk ? chk.value : null,
    userId: win.userId || win.UID || win.g_userId || null,
    uidEls: [...d.querySelectorAll('input[type=hidden]')].slice(0,40).map(el => ({name: el.name, id: el.id, value: (el.value||'').slice(0,80)})),
    scripts: [...d.scripts].slice(0,8).map(s => (s.src||'').slice(0,120)),
    detailHtml,
    bodyIds: [...d.querySelectorAll('[id]')].slice(0,80).map(el => el.id)
  };
})()
"""

JS_CLICK_ROW = r"""
(() => {
  const iframes = [...document.querySelectorAll('iframe')];
  let win = null;
  iframes.forEach(f => {
    try {
      if ((f.contentWindow.location.href||'').includes('retrieveSanctnWaitDocList')) win = f.contentWindow;
    } catch (e) {}
  });
  if (!win) return 'no';
  const d = win.document;
  const tr = d.querySelector('input[name=docinfo]');
  if (!tr) return 'no chk';
  const row = tr.closest('tr');
  const clickables = [...row.querySelectorAll('a, img, td')];
  const logs = [];
  for (const el of clickables) {
    const oc = el.getAttribute && el.getAttribute('onclick');
    if (oc && /fn|doCall|view|info|select/i.test(oc)) {
      try { win.eval(oc); logs.push('eval '+oc.slice(0,120)); } catch (e) { logs.push('evalerr '+e); }
    }
  }
  try {
    const td = row.querySelector('td.LtextLeft, td a, img');
    if (td) { td.click(); logs.push('clicked td'); }
  } catch (e) { logs.push('click '+e); }
  return logs;
})()
"""


async def main():
    klef = next(t for t in tabs() if t.get("type")=="page" and "klef.gbe.kr/keris_ui" in (t.get("url") or ""))
    async with websockets.connect(klef["webSocketDebuggerUrl"]) as ws:
        info = await ev(ws, 1, JS)
        print(json.dumps({k: info.get(k) if k!='as' else info.get('as')[:15] for k in (info or {})}, ensure_ascii=False, indent=2)[:8000])
        clicked = await ev(ws, 2, JS_CLICK_ROW)
        print("CLICK", clicked)
        await asyncio.sleep(2)
        info2 = await ev(ws, 3, JS)
        print("AFTER CLICK keys", (info2 or {}).get("keys"))
        print("AFTER detail", ((info2 or {}).get("detailHtml") or "")[:1500])
        print("AFTER as extra", json.dumps((info2 or {}).get("as") or [], ensure_ascii=False)[:3000])
        OUT.write_text(json.dumps({"before": info, "click": clicked, "after": info2}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print("SAVED", OUT)


if __name__ == "__main__":
    asyncio.run(main())
