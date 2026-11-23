import urllib.request
import json
import time
import os
import websocket

def main():
    download_dir = r"C:\Users\user\Downloads"
    files_before = set(os.listdir(download_dir))
    
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    # Enable download behavior
    ws.send(json.dumps({
        'id': 1,
        'method': 'Page.setDownloadBehavior',
        'params': {
            'behavior': 'allow',
            'downloadPath': download_dir
        }
    }))
    res = json.loads(ws.recv())
    print("setDownloadBehavior res:", res)
    
    # Click btn6 (엑셀내려받기) on els_srgbm02_m00
    js_click = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm02_m00"));
        if (!app) return {error: "app not found"};
        var btn = app.lookup("btn6");
        if (btn) {
            btn.click();
            return {clicked: true};
        }
        return {clicked: false};
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_click, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Click btn6 res:", res.get('result', {}).get('result', {}).get('value'))
    
    print("Waiting 6 seconds for download...")
    time.sleep(6)
    
    files_after = set(os.listdir(download_dir))
    new_files = files_after - files_before
    print("New files in Downloads:", new_files)
    
    ws.close()

if __name__ == '__main__':
    main()
