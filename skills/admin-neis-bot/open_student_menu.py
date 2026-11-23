import urllib.request
import json
import time
import base64
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    if not neis_tab:
        print("No NEIS tab found!")
        return
        
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    # 1. Check openMdiMenu
    js_open = """
    (() => {
        if (typeof window.openMdiMenu === 'function') {
            window.openMdiMenu('AMELS40036');
            return {called: 'window.openMdiMenu'};
        }
        var idx = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("Index"));
        if (idx && typeof idx.callAppMethod === 'function') {
            idx.callAppMethod("doOpenMenuToMdi", ["AMELS40036"]);
            return {called: 'idx.doOpenMenuToMdi'};
        }
        return {error: 'no menu open function'};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js_open, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Open menu call:", res.get('result', {}).get('result', {}).get('value'))
    
    print("Waiting 5 seconds for menu to load...")
    time.sleep(5)
    
    # 2. Check running apps
    js_apps = """
    (() => {
        var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        return apps.map(a => a.app ? a.app.id : 'no-id');
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_apps, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    apps = res.get('result', {}).get('result', {}).get('value')
    print("Running apps now:", apps)
    
    # 3. Capture screenshot
    ws.send(json.dumps({'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_menu_AMELS40036.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    ws.close()

if __name__ == '__main__':
    main()
