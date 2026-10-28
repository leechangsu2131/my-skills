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
SKILL_DIR = Path(__file__).resolve().parent.parent
RESULT_DIR = SKILL_DIR / "result"

SANCTN_URL = "https://klef.gbe.kr/bms/cz/cb/viw/retrieveSanctnWaitDocList.do?leftMenu=1"
CNRS_URL = "https://klef.gbe.kr/bms/cz/cb/viw/retrieveCnrsWaitDocList.do?MENU_ID=A00AAB0103001&FILE_ID=AABCnrsWaitDocList&alimZon=alimZon"


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


JS_IFRAME_LIST = r"""
(() => {
  const rows = [];
  document.querySelectorAll('tr').forEach(tr => {
    const a = tr.querySelector('a.ellipsis, a');
    const tds = [...tr.querySelectorAll('td')].map(td => td.innerText.trim());
    if (!a && tds.length < 3) return;
    const title = ((a && (a.getAttribute('title') || a.innerText)) || '').trim();
    const writer = ((tr.querySelector('td.writer') || {}).innerText || '').trim();
    const date = ((tr.querySelector('td.date') || {}).innerText || '').trim();
    if (title || (tds.length >= 3 && tds[0] && !/상태|문서종류/.test(tds.join('')))) {
      rows.push({title, writer, date, tds, href: a ? (a.getAttribute('href')||a.getAttribute('onclick')||'') : ''});
    }
  });
  return {
    href: location.href,
    title: document.title,
    text: (document.body && document.body.innerText || '').trim().slice(0, 2500),
    rows
  };
})()
"""

JS_SET_IFRAME = r"""
(url) => {
  const iframes = [...document.querySelectorAll('iframe')];
  const target = iframes.find(f => /retrieveCnrsWait|retrieveSanctnWait|alimZon/.test((f.src||'')+(f.getAttribute('src')||''))) || iframes[2];
  if (!target) return {error:'no iframe'};
  const before = target.src;
  target.src = url;
  return {before, after: url};
}
"""

JS_PARSE_IFRAME2 = r"""
(() => {
  const f = document.querySelectorAll('iframe')[2];
  if (!f) return {error:'no iframe2'};
  try {
    const d = f.contentDocument;
    const w = f.contentWindow;
    const rows = [];
    d.querySelectorAll('tbody tr, tr').forEach(tr => {
      const tds = [...tr.querySelectorAll('td')].map(td => td.innerText.replace(/\s+/g,' ').trim());
      if (tds.length < 5) return;
      if (/상태/.test(tds.join(' ')) && /문서번호/.test(tds.join(' '))) return;
      const a = tr.querySelector('a');
      rows.push({
        title: ((a && (a.getAttribute('title') || a.innerText)) || '').trim(),
        tds
      });
    });
    return {href: w.location.href, title: d.title, text: (d.body.innerText||'').slice(0, 3000), rows};
  } catch(e) { return {error: String(e)}; }
})()
"""


async def eval_on(ws, mid, expr):
    data = await cdp_call(
        ws, mid, "Runtime.evaluate",
        {"expression": expr, "returnByValue": True, "awaitPromise": True},
        timeout=40,
    )
    return val(data)


def save_txt(key, docs, extra=""):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULT_DIR / f"edufine_{key}_{ts}.txt"
    names = {"sanctnWait": "결재대기", "dsplayWait": "공람대기"}
    lines = [
        f"K-에듀파인 {names.get(key, key)} 문서 목록",
        f"수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "처리 모드: dry-run",
        f"문서 수: {len(docs)}건",
        "=" * 60,
        "",
    ]
    for i, d in enumerate(docs, 1):
        date = d.get("date") or ""
        title = d.get("title") or ""
        writer = d.get("writer") or ""
        extra_tds = d.get("tds") or []
        if extra_tds and not title:
            title = " | ".join([x for x in extra_tds if x][:8])
        lines.append(f"{i:3}. [{date}] {title} ({writer})")
        if extra_tds:
            lines.append(f"     tds: {' | '.join(extra_tds)}")
    if extra:
        lines.append("")
        lines.append(extra)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


async def main():
    tabs = get_json("/json")
    klef = next((t for t in tabs if t.get("type") == "page" and "klef.gbe.kr/keris_ui" in (t.get("url") or "")), None)
    iframes = [t for t in tabs if t.get("type") == "iframe" and "retrieveSanctnWait" in (t.get("url") or "")]

    out = {"collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    sanctn_docs = []
    for t in iframes[:1]:
        async with websockets.connect(t["webSocketDebuggerUrl"]) as ws:
            data = await eval_on(ws, 1, JS_IFRAME_LIST)
            print("PORTAL IFRAME:", json.dumps(data, ensure_ascii=False)[:2000])
            out["portal_iframe"] = data
            for r in data.get("rows") or []:
                if r.get("title"):
                    sanctn_docs.append(r)

    if klef:
        async with websockets.connect(klef["webSocketDebuggerUrl"]) as ws:
            set1 = await eval_on(ws, 1, f"({JS_SET_IFRAME})({json.dumps(SANCTN_URL)})")
            print("SET SANCTN", set1)
            await asyncio.sleep(3.5)
            table = await eval_on(ws, 2, JS_PARSE_IFRAME2)
            print("SANCTN TABLE", json.dumps(table, ensure_ascii=False)[:2500])
            out["klef_sanctn"] = table
            if isinstance(table, dict):
                for r in table.get("rows") or []:
                    tds = r.get("tds") or []
                    # typical: 상태, 문서종류, 문서번호, 제목, ...
                    title = r.get("title") or (tds[3] if len(tds) > 3 else "")
                    writer = ""
                    date = ""
                    if len(tds) >= 8:
                        writer = tds[5] if tds[5] else tds[4]
                    sanctn_docs.append({"title": title, "writer": writer, "date": date, "tds": tds})

            # restore 공람대기
            set2 = await eval_on(ws, 3, f"({JS_SET_IFRAME})({json.dumps(CNRS_URL)})")
            print("RESTORE CNRS", set2)
            await asyncio.sleep(3.5)
            cnrs = await eval_on(ws, 4, JS_PARSE_IFRAME2)
            print("CNRS TABLE rows", len(cnrs.get("rows") or []) if isinstance(cnrs, dict) else cnrs)
            out["klef_cnrs"] = cnrs

    # dedupe sanctn
    uniq = []
    seen = set()
    for d in sanctn_docs:
        key = (d.get("title"), tuple(d.get("tds") or [])[:4])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(d)

    cnrs_docs = []
    if isinstance(out.get("klef_cnrs"), dict):
        for r in out["klef_cnrs"].get("rows") or []:
            tds = r.get("tds") or []
            title = r.get("title") or (tds[3] if len(tds) > 3 else "")
            writer = tds[6] if len(tds) > 6 else ""
            arrived = tds[9] if len(tds) > 9 else (tds[8] if len(tds) > 8 else "")
            docno = tds[2] if len(tds) > 2 else ""
            cnrs_docs.append({"title": title, "writer": writer, "date": arrived, "docno": docno, "tds": tds})

    p1 = save_txt("sanctnWait", uniq)
    p2 = save_txt("dsplayWait", cnrs_docs)
    print("SAVED", p1)
    print("SAVED", p2)

    json_path = RESULT_DIR / f"edufine_wait_docs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("JSON", json_path)


if __name__ == "__main__":
    asyncio.run(main())
