import json
import urllib.request
import websocket

def get_browser_ws():
    ver = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=3).read())
    return ver["webSocketDebuggerUrl"]

def cdp_send(ws, msg_id, method, params=None, session_id=None):
    cmd = {"id": msg_id, "method": method}
    if params:
        cmd["params"] = params
    if session_id:
        cmd["sessionId"] = session_id
    ws.send(json.dumps(cmd))
    while True:
        raw = ws.recv()
        res = json.loads(raw)
        if res.get("id") == msg_id:
            return res

def inspect_edufine():
    tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=3).read())
    edufine_tab = next((t for t in tabs if "klef" in t.get("url", "")), None)
    if not edufine_tab:
        print("Edufine tab not found")
        return

    ws_url = get_browser_ws()
    ws = websocket.create_connection(ws_url, timeout=5, suppress_origin=True)

    msg_id = 1
    att = cdp_send(ws, msg_id, "Target.attachToTarget", {"targetId": edufine_tab["id"], "flatten": True})
    sid = att["result"]["sessionId"]

    # 에듀파인(넥사크로) 내부 MDI 탭 및 버튼 검사
    js = """
    (function(){
        var res = { nexacro: false, buttons: [], activeWindow: null };
        var app = window.nexacro ? window.nexacro.getApplication() : (window._pApplication || window._application);
        if (app && app.mainframe) {
            res.nexacro = true;
            try {
                var mf = app.mainframe;
                var wf = mf.MainVFrameSet.SubHFrameSet.WorkVFrameSet.WorkFrame;
                if (wf && wf.getActiveFrame) {
                    var af = wf.getActiveFrame();
                    res.activeWindow = af ? af.id : null;
                }
            } catch(e) {
                res.err = e.toString();
            }
        }
        
        // DOM 내의 '다운', '엑셀', '저장', '출력' 버튼/텍스트 찾기
        var els = Array.from(document.querySelectorAll('div, button, a, span, input')).filter(el => {
            var t = el.innerText || el.value || el.getAttribute('title') || '';
            var r = el.getBoundingClientRect();
            return (r.x >= 0 && r.y >= 0 && r.width > 0 && r.height > 0) &&
                   (t.includes('다운') || t.includes('엑셀') || t.includes('받기') || t.includes('명단'));
        }).map(el => ({
            tag: el.tagName,
            id: el.id,
            text: (el.innerText || el.value || '').trim(),
            rect: { x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y) }
        }));
        res.buttons = els;
        return res;
    })()
    """
    msg_id += 1
    eval_res = cdp_send(ws, msg_id, "Runtime.evaluate", {"expression": js, "returnByValue": True}, session_id=sid)
    print("Edufine inspection:")
    print(json.dumps(eval_res.get("result", {}).get("result", {}).get("value"), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == "__main__":
    inspect_edufine()
