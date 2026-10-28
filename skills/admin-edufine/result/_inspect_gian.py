#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inspect Edufine draft/form screens via CDP."""
import asyncio
import json
import sys
import urllib.request
import websockets

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

CDP_HTTP = "http://127.0.0.1:9222"


def get_edufine_ws_url():
    req = urllib.request.urlopen(f"{CDP_HTTP}/json", timeout=3)
    tabs = json.loads(req.read().decode("utf-8"))
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
    ws_url = get_edufine_ws_url()
    print("WS:", ws_url)
    async with websockets.connect(ws_url) as ws:
        msg_id = 1

        async def call_eval(expr, timeout=12):
            nonlocal msg_id
            cmd = {
                "id": msg_id,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": expr,
                    "returnByValue": True,
                    "awaitPromise": True,
                },
            }
            msg_id += 1
            await ws.send(json.dumps(cmd))
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            data = json.loads(raw)
            if "error" in data:
                return {"_error": data["error"]}
            res = data.get("result", {})
            if res.get("exceptionDetails"):
                return {"_exc": res["exceptionDetails"].get("text") or res["exceptionDetails"]}
            return res.get("result", {}).get("value")

        inspect = """(() => {
            const out = {
                title: document.title,
                url: location.href,
                job: null,
                iframes: [],
                popupframes: [],
            };
            try {
                const app = nexacro.getApplication();
                const top = app.mainframe.MainVFrameSet.TopFrame.form;
                const cbo = top.cboJobList;
                out.job = {index: cbo.index, value: cbo.value, text: cbo.text};
                if (app.popupframes) {
                    for (let k in app.popupframes) {
                        try {
                            out.popupframes.push(k + ':' + (app.popupframes[k].id || '') + ':' + (app.popupframes[k].titletext || ''));
                        } catch(e) {}
                    }
                }
            } catch(e) {
                out.jobErr = String(e);
            }
            document.querySelectorAll('iframe').forEach((f, i) => {
                let info = {i, name: f.name, id: f.id, src: f.src};
                try {
                    info.href = f.contentWindow.location.href;
                    info.title = f.contentWindow.document.title;
                    const btns = [];
                    f.contentWindow.document.querySelectorAll('a, button, input[type=button], span, td').forEach(el => {
                        const t = (el.innerText || el.value || '').trim();
                        if (t && t.length < 40 && /기안|공용|서식|작성|결재|문서/.test(t)) {
                            btns.push({tag: el.tagName, id: el.id, name: el.name, text: t, onclick: (el.getAttribute('onclick')||'').slice(0,180)});
                        }
                    });
                    info.hits = btns.slice(0, 40);
                } catch(e) {
                    info.err = String(e);
                }
                out.iframes.push(info);
            });
            return out;
        })()"""
        print(json.dumps(await call_eval(inspect), ensure_ascii=False, indent=2))

        nav = """(() => {
            try {
                let app = nexacro.getApplication();
                try {
                    let mf = app.mainframe.MainVFrameSet.SubHFrameSet.MainFrame;
                    if (mf && mf.noticePopup0) { mf.noticePopup0.destroy(); }
                    if (app && app.popupframes) {
                        for (let k in app.popupframes) {
                            try { app.popupframes[k].form.close(); } catch(e) {}
                        }
                    }
                } catch(e) {}
                let top = app.mainframe.MainVFrameSet.TopFrame.form;
                let cbo = top.cboJobList;
                if (cbo && String(cbo.value) !== 'A00AA' && cbo.text !== '업무관리') {
                    let preIdx = cbo.index;
                    let preVal = cbo.value;
                    let preText = cbo.text;
                    cbo.set_index(0);
                    cbo.set_value('A00AA');
                    let evt = new nexacro.ItemChangeEventInfo(cbo, 'onitemchanged', preIdx, preText, preVal, 0, '업무관리', 'A00AA');
                    top.cboJobList_onitemchanged(cbo, evt);
                }
                let lf = app.mainframe.MainVFrameSet.SubHFrameSet.LeftFrame.form;
                lf.gfnOpenMenu('A00AAB0101001');
                return {ok: true, job: {index: cbo.index, value: cbo.value, text: cbo.text}};
            } catch(e) {
                return {ok: false, err: String(e)};
            }
        })()"""
        print("NAV:", json.dumps(await call_eval(nav), ensure_ascii=False))
        await asyncio.sleep(3)
        print("AFTER:", json.dumps(await call_eval(inspect), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
