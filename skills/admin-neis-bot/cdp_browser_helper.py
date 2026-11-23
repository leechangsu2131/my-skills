import json
import urllib.request
import websocket
import time

def get_browser_ws():
    version_info = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=3).read())
    return version_info["webSocketDebuggerUrl"]

def run_browser_cdp():
    ws_url = get_browser_ws()
    print("Browser WS URL:", ws_url)
    ws = websocket.create_connection(ws_url, timeout=5, suppress_origin=True)

    # 1. 탭 목록 조회
    tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=3).read())
    portal_tab = next((t for t in tabs if "eduptl" in t.get("url", "")), None)
    neis_tab = next((t for t in tabs if "neis.go.kr" in t.get("url", "")), None)

    print("Portal tab:", portal_tab.get("id") if portal_tab else None)
    print("NEIS tab:", neis_tab.get("id") if neis_tab else None)

    if not neis_tab and portal_tab:
        print("NEIS 탭이 없습니다. 업무포털에서 나이스 버튼을 클릭하거나 나이스 탭을 열어주세요.")
    
    ws.close()

if __name__ == "__main__":
    run_browser_cdp()
