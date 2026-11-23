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

def inspect_portal():
    tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=3).read())
    portal_tab = next((t for t in tabs if "eduptl" in t.get("url", "")), None)
    if not portal_tab:
        print("Portal tab not found")
        return

    ws_url = get_browser_ws()
    ws = websocket.create_connection(ws_url, timeout=5, suppress_origin=True)

    msg_id = 1
    att = cdp_send(ws, msg_id, "Target.attachToTarget", {"targetId": portal_tab["id"], "flatten": True})
    sid = att["result"]["sessionId"]

    js = """
    (function(){
        // 보이는 모든 버튼, 링크, 텍스트 수집
        var els = Array.from(document.querySelectorAll('button, a, input[type=button], input[type=submit], span, div')).filter(el => {
            var t = (el.innerText || el.value || el.getAttribute('title') || '').trim();
            var r = el.getBoundingClientRect();
            return (r.x >= 0 && r.y >= 0 && r.width > 0 && r.height > 0) &&
                   (t.includes('다운') || t.includes('엑셀') || t.includes('받기') || t.includes('저장') || t.includes('명단') || t.includes('학생'));
        }).map(el => ({
            tag: el.tagName,
            id: el.id,
            className: el.className,
            text: (el.innerText || el.value || '').trim(),
            rect: { x: Math.round(el.getBoundingClientRect().x), y: Math.round(el.getBoundingClientRect().y) }
        }));
        return {
            title: document.title,
            url: window.location.href,
            matches: els
        };
    })()
    """
    msg_id += 1
    eval_res = cdp_send(ws, msg_id, "Runtime.evaluate", {"expression": js, "returnByValue": True}, session_id=sid)
    print("Portal inspection:")
    print(json.dumps(eval_res.get("result", {}).get("result", {}).get("value"), ensure_ascii=False, indent=2))
    ws.close()

if __name__ == "__main__":
    inspect_portal()
