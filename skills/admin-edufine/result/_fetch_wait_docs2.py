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
        return {"error": data["result"]["exceptionDetails"].get("text") or data["result"]["exceptionDetails"]}
    res = data.get("result", {}).get("result", {})
    if res.get("subtype") == "error":
        return {"error": res.get("description")}
    return res.get("value")


JS_SCRAPE = r"""
(() => {
  const out = {href: location.href, title: document.title, frames: []};
  const iframes = document.querySelectorAll('iframe');
  iframes.forEach((f, i) => {
    const info = {i, name: f.name || '', src: (f.getAttribute('src')||'').slice(0, 250)};
    try {
      const w = f.contentWindow;
      const d = w.document;
      info.href = w.location.href;
      info.title = d.title || '';
      info.text = (d.body && d.body.innerText || '').replace(/\s+\n/g, '\n').trim().slice(0, 2500);
      const rows = [];
      d.querySelectorAll('tr').forEach(tr => {
        const a = tr.querySelector('a');
        const t = ((a && (a.getAttribute('title') || a.innerText)) || tr.innerText || '').trim();
        if (!t || t.length < 2) return;
        const tds = [...tr.querySelectorAll('td')].map(td => td.innerText.trim());
        rows.push({
          title: (a && (a.getAttribute('title') || a.innerText) || '').trim(),
          href: a ? (a.getAttribute('href') || a.getAttribute('onclick') || '') : '',
          tds: tds.slice(0, 12),
          text: t.slice(0, 200)
        });
      });
      info.rows = rows.slice(0, 40);
      info.rowCount = rows.length;
      // nexacro in this iframe
      try {
        info.hasNexacro = typeof w.nexacro !== 'undefined';
        if (info.hasNexacro) {
          const app = w.nexacro.getApplication();
          info.appKeys = app ? Object.keys(app).slice(0, 30) : null;
          try { info.mainframe = !!app.mainframe; } catch(e) {}
          try { info.left = !!(app.mainframe && app.mainframe.LeftFrame); } catch(e) {}
          try {
            const mf = app.mainframe;
            info.mfKeys = mf ? Object.keys(mf).slice(0, 40) : null;
          } catch(e) { info.mfErr = String(e); }
        }
      } catch(e) { info.nxErr = String(e); }
    } catch(e) {
      info.error = String(e);
    }
    out.frames.push(info);
  });
  return out;
})()
"""

JS_OPEN_SANCTN_IN_NX = r"""
(() => {
  const logs = [];
  const iframes = document.querySelectorAll('iframe');
  for (const f of iframes) {
    try {
      const w = f.contentWindow;
      if (typeof w.nexacro === 'undefined') continue;
      logs.push('nx iframe ' + w.location.href.slice(0, 120));
      const app = w.nexacro.getApplication();
      logs.push('app ' + (app && (app.id || app.name)));
      const dump = (obj, name) => {
        try { logs.push(name + ' keys ' + Object.keys(obj).slice(0, 25).join(',')); } catch(e) { logs.push(name + ' ' + e); }
      };
      dump(app, 'app');
      try { dump(app.mainframe, 'mainframe'); } catch(e) { logs.push('mf ' + e); }
      // try several paths
      const tries = [];
      try { tries.push(['LeftFrame.form', app.mainframe.LeftFrame.form]); } catch(e) { logs.push('LF ' + e); }
      try {
        const mv = app.mainframe.MainVFrameSet || app.mainframe.VFrameSet || app.mainframe;
        dump(mv, 'mv');
      } catch(e) {}
      try {
        if (app.mainframe && app.mainframe.LeftFrame && app.mainframe.LeftFrame.form && app.mainframe.LeftFrame.form.gfnOpenMenu) {
          app.mainframe.LeftFrame.form.gfnOpenMenu('A00AAB0102001');
          logs.push('gfnOpenMenu A00AAB0102001');
        }
      } catch(e) { logs.push('open ' + e); }
    } catch(e) {
      logs.push('outer ' + e);
    }
  }
  return logs;
})()
"""

JS_SET_SANCTN_IFRAME = r"""
(() => {
  const urls = [
    'https://klef.gbe.kr/bms/cz/cb/wrt/retrieveSanctnWaitDocList.do?MENU_ID=A00AAB0102001&FILE_ID=AABSanctnWaitDocList&alimZon=alimZon',
    'https://klef.gbe.kr/bms/cz/cb/wrt/retrieveSanctnWaitDocList.do?leftMenu=1'
  ];
  const iframes = [...document.querySelectorAll('iframe')];
  const target = iframes.find(f => {
    const s = (f.getAttribute('src')||'') + (f.src||'');
    return /retrieveCnrsWait|retrieveSanctnWait|alimZon/.test(s);
  }) || iframes[2];
  if (!target) return {error: 'no iframe'};
  const before = target.src;
  target.src = urls[0];
  return {before, after: target.src, i: iframes.indexOf(target)};
})()
"""


async def eval_on(ws, mid, expr):
    data = await cdp_call(
        ws,
        mid,
        "Runtime.evaluate",
        {"expression": expr, "returnByValue": True, "awaitPromise": True},
    )
    return val(data)


async def main():
    tabs = get_json("/json")
    print("TABS:")
    pages = []
    for t in tabs:
        if t.get("type") == "page":
            print(" ", t.get("url")[:140], "|", (t.get("title") or "")[:50])
            pages.append(t)

    result = {"collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tabs": []}

    for t in pages:
        url = t.get("url") or ""
        if "klef" not in url and "eduptl" not in url:
            continue
        print("\n====", url[:100], "====")
        async with websockets.connect(t["webSocketDebuggerUrl"]) as ws:
            scrape = await eval_on(ws, 1, JS_SCRAPE)
            print(json.dumps(scrape, ensure_ascii=False)[:3500])
            entry = {"url": url, "title": t.get("title"), "scrape": scrape}

            if "klef" in url and "keris_ui" in url:
                opened = await eval_on(ws, 2, JS_OPEN_SANCTN_IN_NX)
                print("OPEN NX", opened)
                entry["open_nx"] = opened
                setsrc = await eval_on(ws, 3, JS_SET_SANCTN_IFRAME)
                print("SET SRC", setsrc)
                entry["setsrc"] = setsrc
                await asyncio.sleep(3)
                scrape2 = await eval_on(ws, 4, JS_SCRAPE)
                print("AFTER", json.dumps(scrape2, ensure_ascii=False)[:3500])
                entry["scrape_after"] = scrape2

            result["tabs"].append(entry)

    path = RESULT_DIR / f"edufine_wait_probe2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("SAVED", path)


if __name__ == "__main__":
    asyncio.run(main())
