#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import websockets

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CDP_HTTP = "http://127.0.0.1:9222"
RESULT_DIR = Path(__file__).parent


def get_json(path):
    return json.loads(urllib.request.urlopen(f"{CDP_HTTP}{path}", timeout=5).read().decode())


async def cdp_call(ws, msg_id, method, params=None, timeout=30):
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


JS_RESTORE_AND_PROBE = r"""
(async () => {
  const CNRS = 'https://klef.gbe.kr/bms/cz/cb/viw/retrieveCnrsWaitDocList.do?MENU_ID=A00AAB0103001&FILE_ID=AABCnrsWaitDocList&alimZon=alimZon';
  const candidates = [
    'https://klef.gbe.kr/bms/cz/cb/viw/retrieveSanctnWaitDocList.do?MENU_ID=A00AAB0102001&FILE_ID=AABSanctnWaitDocList&alimZon=alimZon',
    'https://klef.gbe.kr/bms/cz/cb/viw/retrieveSanctnWaitDocList.do?leftMenu=1',
    'https://klef.gbe.kr/bms/cz/cb/wrt/retrieveSanctnWaitDocList.do?leftMenu=1',
    'https://klef.gbe.kr/bms/cz/cb/sanctn/retrieveSanctnWaitDocList.do?leftMenu=1',
    'https://klef.gbe.kr/portal/link.do?link=sanctnWait',
    'https://klef.gbe.kr/bms/cz/cb/wrt/retrieveSanctnWait.do',
    'https://klef.gbe.kr/bms/cz/cb/viw/retrieveSanctnWait.do'
  ];

  const probes = [];
  for (const u of candidates) {
    try {
      const r = await fetch(u, {credentials: 'include', redirect: 'follow'});
      const t = await r.text();
      const titleMatch = t.match(/<title>([^<]*)<\/title>/i);
      probes.push({
        url: u,
        finalUrl: r.url,
        status: r.status,
        title: titleMatch ? titleMatch[1].trim() : '',
        errPage: t.includes('정상적으로 처리되지'),
        hasWait: /결재대기|공람대기/.test(t),
        snippet: t.replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim().slice(0, 400)
      });
    } catch (e) {
      probes.push({url: u, error: String(e)});
    }
  }

  // restore 공람대기 iframe
  const iframes = [...document.querySelectorAll('iframe')];
  const target = iframes[2] || iframes.find(f => /retrieve|alimZon/.test(f.src||''));
  let restored = null;
  if (target) {
    target.src = CNRS;
    restored = CNRS;
  }

  return {probes, restored};
})()
"""

JS_PARSE_TABLE = r"""
(() => {
  const f = document.querySelectorAll('iframe')[2];
  if (!f) return {error: 'no iframe2'};
  try {
    const d = f.contentDocument;
    const w = f.contentWindow;
    const rows = [];
    d.querySelectorAll('tr').forEach(tr => {
      const tds = [...tr.querySelectorAll('td')].map(td => td.innerText.trim());
      if (tds.length < 4) return;
      const a = tr.querySelector('a');
      rows.push({
        title: ((a && (a.getAttribute('title') || a.innerText)) || tds[3] || '').trim(),
        tds
      });
    });
    return {
      href: w.location.href,
      title: d.title,
      heading: (d.body.innerText||'').split('\n').slice(0, 8),
      rows
    };
  } catch(e) { return {error: String(e)}; }
})()
"""

JS_PORTAL_LINKS = r"""
(() => {
  const as = [...document.querySelectorAll('a')].map(a => ({
    text: (a.innerText||'').trim().slice(0,80),
    href: (a.getAttribute('href')||'').slice(0,250),
    title: (a.getAttribute('title')||'').slice(0,80)
  })).filter(x => /결재|공람|대기|긴급|kedufine|klef|sanctn|dsplay/i.test(x.text+' '+x.href+' '+x.title));
  const iframes = [...document.querySelectorAll('iframe')].map(f => ({
    name: f.name, src: (f.getAttribute('src')||f.src||'').slice(0,300)
  }));
  const text = (document.body.innerText||'').replace(/\s+/g,' ').slice(0, 1500);
  return {title: document.title, href: location.href, iframes, as: as.slice(0, 40), text};
})()
"""


async def eval_on(ws, mid, expr):
    data = await cdp_call(
        ws,
        mid,
        "Runtime.evaluate",
        {"expression": expr, "returnByValue": True, "awaitPromise": True},
        timeout=40,
    )
    return val(data)


async def main():
    tabs = get_json("/json")
    print("ALL TARGETS:")
    klef = portal = kedufine_iframe = None
    for t in tabs:
        typ = t.get("type")
        url = t.get("url") or ""
        title = (t.get("title") or "")[:60]
        if typ in ("page", "iframe"):
            print(f"  {typ} {url[:140]} | {title}")
        if typ == "page" and "klef.gbe.kr/keris_ui" in url and klef is None:
            klef = t
        if typ == "page" and "eduptl.kr" in url and "bpm_man" in url and portal is None:
            portal = t
        if "kedufine" in url.lower() or ("klef.gbe.kr" in url and "retrieve" in url):
            kedufine_iframe = t
            print("  ** candidate iframe/page", typ, url[:180])

    result = {"collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    if klef:
        async with websockets.connect(klef["webSocketDebuggerUrl"]) as ws:
            probe = await eval_on(ws, 1, JS_RESTORE_AND_PROBE)
            print("\nPROBE:")
            if isinstance(probe, dict) and "probes" in probe:
                for p in probe["probes"]:
                    print(json.dumps(p, ensure_ascii=False)[:500])
            else:
                print(probe)
            result["probe"] = probe
            await asyncio.sleep(3)
            table = await eval_on(ws, 2, JS_PARSE_TABLE)
            print("\nRESTORED TABLE rows", len(table.get("rows", [])) if isinstance(table, dict) else table)
            if isinstance(table, dict):
                print(" href", table.get("href"), table.get("title"))
                for r in (table.get("rows") or [])[:15]:
                    print(" ", r.get("title") or r.get("tds"))
            result["cnrs_table"] = table

    if portal:
        async with websockets.connect(portal["webSocketDebuggerUrl"]) as ws:
            pl = await eval_on(ws, 1, JS_PORTAL_LINKS)
            print("\nPORTAL:", json.dumps(pl, ensure_ascii=False)[:2500])
            result["portal"] = pl

    # attach to iframe targets that look like wait lists
    iframe_scrapes = []
    for t in tabs:
        url = t.get("url") or ""
        if t.get("type") in ("page", "iframe") and ("retrieve" in url or "kedufine" in url or "sanctn" in url.lower()):
            try:
                async with websockets.connect(t["webSocketDebuggerUrl"]) as ws:
                    data = await eval_on(ws, 1, """(() => ({href: location.href, title: document.title, text: (document.body&&document.body.innerText||'').slice(0,2000)}))()""")
                    print("\nIFRAME TARGET", t.get("type"), json.dumps(data, ensure_ascii=False)[:800])
                    iframe_scrapes.append({"url": url, "type": t.get("type"), "data": data})
            except Exception as e:
                print("iframe attach fail", e)
    result["iframe_scrapes"] = iframe_scrapes

    path = RESULT_DIR / f"edufine_wait_probe3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("SAVED", path)


if __name__ == "__main__":
    asyncio.run(main())
