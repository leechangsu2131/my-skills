import json
import urllib.request
import websocket
import time

def get_browser_ws():
    version_info = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=3).read())
    return version_info["webSocketDebuggerUrl"]

def cdp_send(ws, msg_id, method, params=None, session_id=None):
    cmd = {"id": msg_id, "method": method}
    if params:
        cmd["params"] = params
    if session_id:
        cmd["sessionId"] = session_id
    ws.send(json.dumps(cmd))
    while True:
        res = json.loads(ws.recv())
        if res.get("id") == msg_id:
            return res

def click_neis_in_portal():
    ws_url = get_browser_ws()
    ws = websocket.create_connection(ws_url, timeout=5, suppress_origin=True)

    tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=3).read())
    portal_tab = next((t for t in tabs if "eduptl" in t.get("url", "")), None)
    if not portal_tab:
        print("Portal tab not found")
        ws.close()
        return

    # Attach to portal tab
    msg_id = 1
    attach_res = cdp_send(ws, msg_id, "Target.attachToTarget", {
        "targetId": portal_tab["id"],
        "flatten": True
    })
    session_id = attach_res.get("result", {}).get("sessionId")
    print("Attached session:", session_id)

    # 포털에서 나이스 클릭 스크립트 실행
    js = """
    (function(){
        var btn = document.querySelector('a.menuBtn[id*="neis"]') || 
                  document.querySelector('a[href*="neis"], a[onclick*="neis"]') ||
                  Array.from(document.querySelectorAll('a, button')).find(x => x.innerText.includes('나이스'));
        if (btn) {
            btn.click();
            return { ok: true, text: btn.innerText, id: btn.id };
        }
        return { ok: false };
    })()
    """
    msg_id += 1
    eval_res = cdp_send(ws, msg_id, "Runtime.evaluate", {
        "expression": js,
        "returnByValue": True
    }, session_id=session_id)
    print("Click result:", eval_res.get("result", {}).get("result", {}).get("value"))

    ws.close()

if __name__ == "__main__":
    click_neis_in_portal()
