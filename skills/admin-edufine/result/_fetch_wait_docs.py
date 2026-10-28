#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect 결재대기/공람대기 from K-에듀파인 via CDP websocket (no Playwright)."""
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
RESULT_DIR = Path(__file__).parent


def get_json(path):
    return json.loads(urllib.request.urlopen(f"{CDP_HTTP}{path}", timeout=5).read().decode())


def find_ws(prefer):
    tabs = get_json("/json")
    for key in prefer:
        for t in tabs:
            if t.get("type") == "page" and key in t.get("url", ""):
                return t.get("webSocketDebuggerUrl"), t.get("url"), t.get("title")
    return None, None, None


async def cdp_eval(ws, msg_id, expr, timeout=20):
    cmd = {
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True,
        },
    }
    await ws.send(json.dumps(cmd))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        data = json.loads(raw)
        if data.get("id") == msg_id:
            return data


def dump_value(data):
    res = data.get("result", {}).get("result", {})
    if "exceptionDetails" in data.get("result", {}):
        return {"error": data["result"]["exceptionDetails"]}
    if res.get("subtype") == "error":
        return {"error": res.get("description")}
    return res.get("value")


JS_INSPECT = r"""
(() => {
  const out = {url: location.href, title: document.title, iframes: [], nexacro: false, banner: null};
  try { out.nexacro = typeof nexacro !== 'undefined'; } catch(e) {}
  document.querySelectorAll('iframe').forEach((f, i) => {
    let src = f.getAttribute('src') || f.src || '';
    let name = f.getAttribute('name') || f.name || '';
    let href = '';
    try { href = f.contentWindow.location.href; } catch(e) { href = 'cross-origin:' + e.message; }
    out.iframes.push({i, name, src: src.slice(0, 180), href: String(href).slice(0, 180)});
  });
  try {
    const app = nexacro.getApplication();
    out.appName = app ? app.id || app.name : null;
    try {
      const top = app.mainframe.TopFrame.form;
      const texts = [];
      const walk = (comp, depth) => {
        if (!comp || depth > 6) return;
        try {
          const t = (comp.text || comp.value || '') + '';
          if (t && /결재|공람|대기|긴급/.test(t)) texts.push(t.slice(0, 80));
        } catch(e) {}
        try {
          const n = comp.components ? comp.components.length : 0;
          for (let i = 0; i < n; i++) walk(comp.components[i], depth + 1);
        } catch(e) {}
      };
      walk(top, 0);
      out.banner = texts.slice(0, 20);
    } catch(e) { out.bannerErr = String(e); }
  } catch(e) { out.nxErr = String(e); }
  return out;
})()
"""

JS_OPEN_WAIT = r"""
(() => {
  const log = [];
  try {
    const app = nexacro.getApplication();
    const mf = app.mainframe.MainVFrameSet.SubHFrameSet.MainFrame;
    if (mf && mf.noticePopup0) { mf.noticePopup0.destroy(); log.push('notice destroyed'); }
    if (app && app.popupframes) {
      for (let k in app.popupframes) {
        try { app.popupframes[k].form.close(); } catch(e) {}
      }
    }
  } catch(e) { log.push('notice: ' + e); }
  try {
    const app = nexacro.getApplication();
    const cbo = app.mainframe.TopFrame.form.cboJobList;
    if (cbo) {
      log.push('cbo before: ' + (cbo.value || cbo.text));
      try { cbo.set_value('A00AA'); } catch(e) {}
      try { cbo.set_index(0); } catch(e) {}
      try {
        const ev = new nexacro.ItemChangeEventInfo(cbo, 'onitemchanged', 0, cbo.index, cbo.value, cbo.text);
        if (cbo.onitemchanged) cbo.onitemchanged(cbo, ev);
        if (app.mainframe.TopFrame.form.cboJobList_onitemchanged)
          app.mainframe.TopFrame.form.cboJobList_onitemchanged(cbo, ev);
      } catch(e) { log.push('cbo ev: ' + e); }
      log.push('cbo after: ' + (cbo.value || cbo.text));
    }
  } catch(e) { log.push('cbo: ' + e); }
  try {
    nexacro.getApplication().mainframe.LeftFrame.form.gfnOpenMenu('A00AAB0102001');
    log.push('opened A00AAB0102001');
  } catch(e) { log.push('open: ' + e); }
  return log;
})()
"""

JS_OPEN_DS = r"""
(() => {
  try {
    nexacro.getApplication().mainframe.LeftFrame.form.gfnOpenMenu('A00AAB0103001');
    return 'opened A00AAB0103001';
  } catch(e) { return 'open ds: ' + e; }
})()
"""

JS_COLLECT_GRID = r"""
(() => {
  const out = {frames: [], grids: [], datasets: [], titles: []};
  const iframes = document.querySelectorAll('iframe');
  for (let f of iframes) {
    let href = '';
    try { href = f.contentWindow.location.href; } catch(e) { continue; }
    out.frames.push(href.slice(0, 220));
    let win = null;
    try { win = f.contentWindow; } catch(e) { continue; }
    const scanWin = (w, tag) => {
      try {
        const nx = w.nexacro;
        if (!nx) return;
        const app = nx.getApplication ? nx.getApplication() : null;
        const forms = [];
        const pushDs = (ds, src) => {
          if (!ds) return;
          const cols = [];
          try {
            for (let c = 0; c < ds.getColCount(); c++) cols.push(ds.getColID(c));
          } catch(e) {}
          const rows = [];
          const n = ds.getRowCount ? ds.getRowCount() : 0;
          for (let r = 0; r < Math.min(n, 30); r++) {
            const row = {};
            for (const col of cols) {
              try { row[col] = ds.getColumn(r, col); } catch(e) {}
            }
            rows.push(row);
          }
          out.datasets.push({src, id: ds.id || ds.name, cols, count: n, rows});
        };
        const walk = (comp, depth, path) => {
          if (!comp || depth > 10) return;
          const id = comp.id || '';
          const p = path + '/' + id;
          try {
            if (comp._type_name === 'Grid' || (comp.getBindDataset && String(comp._type_name||'').toLowerCase().includes('grid'))) {
              out.grids.push({tag, path: p, type: comp._type_name, bind: (comp.binddataset || '')});
              try { pushDs(comp.getBindDataset(), p); } catch(e) {}
            }
          } catch(e) {}
          try {
            if (comp.components) {
              const n = comp.components.length;
              for (let i = 0; i < n; i++) walk(comp.components[i], depth + 1, p);
            }
          } catch(e) {}
        };
        if (app && app.mainframe) walk(app.mainframe, 0, tag);
        try {
          if (w.this && w.this.form) walk(w.this.form, 0, tag + ':this');
        } catch(e) {}
        try {
          const keys = Object.keys(w);
          for (const k of keys) {
            if (/ds|DS|Dataset/.test(k)) {
              try { pushDs(w[k], tag + ':' + k); } catch(e) {}
            }
          }
        } catch(e) {}
      } catch(e) {
        out.frames.push('scanerr ' + tag + ' ' + e);
      }
    };
    scanWin(win, href.slice(-80));
    // nested iframes
    try {
      const nested = win.document.querySelectorAll('iframe');
      nested.forEach((nf, ni) => {
        try { scanWin(nf.contentWindow, href.slice(-40) + '>n' + ni); } catch(e) {}
      });
    } catch(e) {}
  }
  // also scan top
  try {
    const texts = Array.from(document.querySelectorAll('a, span, td, div'))
      .map(el => (el.innerText || el.title || '').trim())
      .filter(t => t && t.length > 8 && t.length < 120)
      .slice(0, 40);
    out.titles = texts;
  } catch(e) {}
  return out;
})()
"""

JS_PORTAL = r"""
(() => {
  const out = {url: location.href, title: document.title, kedufine: null, links: []};
  const f = document.querySelector('iframe[name="kedufine"]');
  if (f) {
    out.kedufine = {src: (f.src||'').slice(0,200)};
    try {
      const doc = f.contentDocument || f.contentWindow.document;
      const rows = [];
      doc.querySelectorAll('tr').forEach(tr => {
        const a = tr.querySelector('a.ellipsis, a');
        if (!a) return;
        const title = (a.getAttribute('title') || a.innerText || '').trim();
        if (!title) return;
        const writer = (tr.querySelector('td.writer') || {}).innerText || '';
        const date = (tr.querySelector('td.date') || {}).innerText || '';
        rows.push({title, writer: writer.trim(), date: date.trim()});
      });
      out.kedufine.rows = rows;
      out.kedufine.htmlSnippet = (doc.body && doc.body.innerText || '').slice(0, 1500);
    } catch(e) {
      out.kedufine.error = String(e);
    }
  }
  document.querySelectorAll('a').forEach(a => {
    const t = (a.innerText || '').trim();
    if (/결재|공람|대기/.test(t) && t.length < 40) {
      out.links.push({text: t, href: (a.getAttribute('href')||'').slice(0, 180)});
    }
  });
  return out;
})()
"""


async def run_on(ws_url, label):
    print(f"\n===== {label} =====")
    async with websockets.connect(ws_url) as ws:
        mid = 1

        async def ev(expr, timeout=20):
            nonlocal mid
            data = await cdp_eval(ws, mid, expr, timeout=timeout)
            mid += 1
            return dump_value(data)

        inspect = await ev(JS_INSPECT)
        print("INSPECT:", json.dumps(inspect, ensure_ascii=False)[:2000])
        return ws, ev  # can't return ev after close


async def main():
    result = {"collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    klef_ws, klef_url, klef_title = find_ws(["klef.gbe.kr/keris_ui", "klef.gbe.kr"])
    portal_ws, portal_url, portal_title = find_ws(["eduptl.kr"])
    print("KLEF:", klef_url, klef_title)
    print("PORTAL:", portal_url, portal_title)

    if portal_ws:
        async with websockets.connect(portal_ws) as ws:
            data = await cdp_eval(ws, 1, JS_PORTAL)
            portal = dump_value(data)
            print("\nPORTAL:", json.dumps(portal, ensure_ascii=False)[:4000])
            result["portal"] = portal

    if klef_ws:
        async with websockets.connect(klef_ws) as ws:
            mid = 1

            async def ev(expr, timeout=25):
                nonlocal mid
                data = await cdp_eval(ws, mid, expr, timeout=timeout)
                mid += 1
                return dump_value(data)

            inspect = await ev(JS_INSPECT)
            print("\nKLEF INSPECT:", json.dumps(inspect, ensure_ascii=False)[:3000])
            result["klef_inspect"] = inspect

            opened = await ev(JS_OPEN_WAIT)
            print("OPEN WAIT:", opened)
            result["open_wait"] = opened
            await asyncio.sleep(3)

            grid1 = await ev(JS_COLLECT_GRID)
            print("GRID WAIT keys:", list(grid1.keys()) if isinstance(grid1, dict) else type(grid1))
            if isinstance(grid1, dict):
                print(" frames", len(grid1.get("frames", [])), "grids", len(grid1.get("grids", [])), "ds", len(grid1.get("datasets", [])))
                print(" frames sample", grid1.get("frames", [])[:8])
                print(" grids", json.dumps(grid1.get("grids", [])[:10], ensure_ascii=False)[:1500])
                for ds in grid1.get("datasets", [])[:8]:
                    print(" DS", ds.get("id"), ds.get("count"), ds.get("cols"))
                    if ds.get("rows"):
                        print("  row0", json.dumps(ds["rows"][0], ensure_ascii=False)[:500])
            result["wait_grid"] = grid1

            opened2 = await ev(JS_OPEN_DS)
            print("OPEN DSPLAY:", opened2)
            await asyncio.sleep(3)
            grid2 = await ev(JS_COLLECT_GRID)
            result["dsplay_grid"] = grid2
            if isinstance(grid2, dict):
                for ds in grid2.get("datasets", [])[:8]:
                    print(" DS2", ds.get("id"), ds.get("count"), ds.get("cols"))

    out_path = RESULT_DIR / f"edufine_wait_probe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("\nSAVED", out_path)


if __name__ == "__main__":
    asyncio.run(main())
