#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect 결재대기 list + APPRID via CDP websocket (no Playwright)."""
import asyncio
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import websockets

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

CDP_HTTP = "http://127.0.0.1:9222"
RESULT_DIR = Path(__file__).resolve().parent
SANCTN_URL = "https://klef.gbe.kr/bms/cz/cb/viw/retrieveSanctnWaitDocList.do?leftMenu=1"

JS_OPEN = r"""
(() => {
  const log = [];
  try {
    const app = nexacro.getApplication();
    const mf = app.mainframe.MainVFrameSet.SubHFrameSet.MainFrame;
    if (mf && mf.noticePopup0) { mf.noticePopup0.destroy(); log.push('notice destroyed'); }
  } catch (e) { log.push('notice: ' + e); }
  try {
    const app = nexacro.getApplication();
    const cbo = app.mainframe.TopFrame.form.cboJobList;
    if (cbo) {
      try { cbo.set_value('A00AA'); } catch (e) {}
      try { cbo.set_index(0); } catch (e) {}
      try {
        const ev = new nexacro.ItemChangeEventInfo(cbo, 'onitemchanged', 0, cbo.index, cbo.value, cbo.text);
        if (cbo.onitemchanged) cbo.onitemchanged(cbo, ev);
        if (app.mainframe.TopFrame.form.cboJobList_onitemchanged)
          app.mainframe.TopFrame.form.cboJobList_onitemchanged(cbo, ev);
      } catch (e) { log.push('cbo ev: ' + e); }
      log.push('cbo: ' + (cbo.value || cbo.text));
    }
  } catch (e) { log.push('cbo: ' + e); }
  try {
    nexacro.getApplication().mainframe.LeftFrame.form.gfnOpenMenu('A00AAB0102001');
    log.push('opened A00AAB0102001');
  } catch (e) { log.push('open: ' + e); }
  return log;
})()
"""

JS_IFRAMES = r"""
(() => {
  return [...document.querySelectorAll('iframe')].map((f, i) => {
    let href = '';
    try { href = f.contentWindow.location.href; } catch (e) { href = 'x:' + e.message; }
    return {i, name: f.name || '', src: (f.src || '').slice(0, 220), href: String(href).slice(0, 220)};
  });
})()
"""

JS_PARSE = r"""
(() => {
  const scan = (d, href, winFns) => {
    const rows = [];
    d.querySelectorAll('tr').forEach(tr => {
      const tds = [...tr.querySelectorAll('td')].map(td => td.innerText.replace(/\s+/g, ' ').trim());
      if (tds.length < 3) return;
      const joined = tds.join(' ');
      if (/상태/.test(joined) && /문서번호/.test(joined)) return;
      const a = tr.querySelector('a');
      const inp = tr.querySelector('input[type=checkbox], input[name*=chk], input[name*=APPR]');
      const onclick = a ? (a.getAttribute('onclick') || '') : '';
      const hrefA = a ? (a.getAttribute('href') || '') : '';
      rows.push({
        title: ((a && (a.getAttribute('title') || a.innerText)) || '').trim(),
        tds,
        onclick: onclick.slice(0, 400),
        href: hrefA.slice(0, 200),
        chk: inp ? (inp.value || inp.getAttribute('value') || inp.id || '') : '',
        html: tr.innerHTML.slice(0, 500)
      });
    });
    const fns = [];
    try {
      for (const k of ['fncSearch','fncBndeSanctn','doCallClientApp','doCallExtViewAttch','doCallEnrollPublicList','userId','UID']) {
        try { fns.push(k + ':' + typeof winFns[k]); } catch (e) {}
      }
    } catch (e) {}
    return {
      href,
      title: d.title,
      text: (d.body && d.body.innerText || '').slice(0, 2500),
      rows,
      fns,
      inputs: [...d.querySelectorAll('input')].slice(0, 30).map(el => ({
        name: el.name, id: el.id, type: el.type, value: (el.value||'').slice(0,80)
      }))
    };
  };
  const out = {top: scan(document, location.href, window), frames: []};
  document.querySelectorAll('iframe').forEach((f, i) => {
    try {
      out.frames.push({i, ...scan(f.contentDocument, f.contentWindow.location.href, f.contentWindow)});
    } catch (e) {
      out.frames.push({i, error: String(e), src: (f.src||'').slice(0,200)});
    }
  });
  return out;
})()
"""


def get_tabs():
    return json.loads(urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=5).read().decode())


async def cdp_eval(ws, mid, expr, timeout=30):
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
                ed = data["result"]["exceptionDetails"]
                return {"error": ed.get("exception", {}).get("description") or ed.get("text")}
            res = data.get("result", {}).get("result", {})
            if res.get("subtype") == "error":
                return {"error": res.get("description")}
            return res.get("value")


async def eval_tab(ws_url, expr, mid=1):
    async with websockets.connect(ws_url) as ws:
        return await cdp_eval(ws, mid, expr)


async def main():
    tabs = get_tabs()
    print("TABS:")
    for t in tabs:
        print(" ", t.get("type"), "|", (t.get("title") or "")[:50], "|", (t.get("url") or "")[:140])

    klef = next((t for t in tabs if t.get("type") == "page" and "klef.gbe.kr/keris_ui" in (t.get("url") or "")), None)
    out = {"collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    if not klef:
        print("NO KLEF TAB")
        Path(RESULT_DIR / "edufine_wait_live.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return

    async with websockets.connect(klef["webSocketDebuggerUrl"]) as ws:
        mid = 1

        async def ev(expr, timeout=30):
            nonlocal mid
            v = await cdp_eval(ws, mid, expr, timeout=timeout)
            mid += 1
            return v

        opened = await ev(JS_OPEN)
        print("\nOPEN:", opened)
        await asyncio.sleep(3)
        ifr = await ev(JS_IFRAMES)
        print("IFRAMES:", json.dumps(ifr, ensure_ascii=False)[:2000])
        parsed = await ev(JS_PARSE)
        print("PARSE top text:", (parsed.get("top") or {}).get("text", "")[:400] if isinstance(parsed, dict) else parsed)
        if isinstance(parsed, dict):
            for fr in parsed.get("frames") or []:
                print(" FRAME", fr.get("i"), (fr.get("href") or fr.get("error") or "")[:160])
                print("  text", (fr.get("text") or "")[:400])
                print("  rows", len(fr.get("rows") or []), "fns", fr.get("fns"))
        out["open"] = opened
        out["iframes"] = ifr
        out["parse"] = parsed

        # If iframe2 is cnrs, switch to sanctn and search
        need_switch = False
        if isinstance(ifr, list):
            for item in ifr:
                href = item.get("href") or item.get("src") or ""
                if "retrieveCnrsWait" in href or "CnrsWait" in href:
                    need_switch = True
        if need_switch or True:
            setr = await ev(
                "(() => { const f = document.querySelectorAll('iframe')[2]; if(!f) return 'no2';"
                f" const before = f.src; f.src = {json.dumps(SANCTN_URL)}; return {{before, after: f.src}}; }})()"
            )
            print("SET SANCTN:", setr)
            await asyncio.sleep(3.5)
            try:
                search = await ev(
                    "(() => { const w = document.querySelectorAll('iframe')[2].contentWindow;"
                    " const logs=[]; try { if (typeof w.fncSearch==='function') { w.fncSearch(); logs.push('fncSearch'); } }"
                    " catch(e){ logs.push('fncSearch '+e); }"
                    " const d=w.document; const btn=[...d.querySelectorAll('a,button,input')].find(el=>/조회/.test(el.innerText||el.value||''));"
                    " if(btn){ btn.click(); logs.push('clicked'); } return logs; })()"
                )
                print("SEARCH:", search)
            except Exception as e:
                print("SEARCH ERR", e)
            await asyncio.sleep(2)
            parsed2 = await ev(JS_PARSE)
            out["parse_after_search"] = parsed2
            if isinstance(parsed2, dict):
                for fr in parsed2.get("frames") or []:
                    print(" AFTER FRAME", fr.get("i"), (fr.get("href") or "")[:160])
                    print("  text", (fr.get("text") or "")[:600])
                    print("  rows", json.dumps((fr.get("rows") or [])[:8], ensure_ascii=False)[:2000])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULT_DIR / f"edufine_wait_live_{ts}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("SAVED", path)


if __name__ == "__main__":
    asyncio.run(main())
