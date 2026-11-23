import urllib.request
import json
import time
import base64
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    js = """
    (() => {
        try {
            var idx = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("Index"));
            var res = idx.callAppMethod("doOpenMenuToMdi", ["AMELS40004"]);
            return { success: true, res: res };
        } catch(e) {
            return { error: e.toString() };
        }
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Call AMELS40004:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(5)
    
    # Check apps
    js_apps = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_sdlpa00_m00"));
        if (!app) return {error: "not found", apps: instances.map(a => a.app ? a.app.id : '')};
        
        var ctrls = [];
        var all = app.getContainer().getAllRecursiveChildren();
        for (var i = 0; i < all.length; i++) {
            var c = all[i];
            if (c.type === 'button' || c.type === 'grid' || (c.text && (c.text.includes('다운') || c.text.includes('엑셀') || c.text.includes('조회')))) {
                ctrls.push({id: c.id, type: c.type, text: c.text, enabled: c.enabled});
            }
        }
        return {
            ctrls: ctrls,
            datasets: app.getAllDataControls().map(d => ({
                id: d.id,
                type: d.type,
                cols: d instanceof cpr.data.DataSet ? d.getColumnNames() : []
            }))
        };
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_apps, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value')
    print("App result:", json.dumps(data, ensure_ascii=False, indent=2))
    
    # Screenshot
    ws.send(json.dumps({'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_sdlpa00_screen.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    ws.close()

if __name__ == '__main__':
    main()
