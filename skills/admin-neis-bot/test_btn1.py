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
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm02_m00"));
        if (!app) return {error: "app not found"};
        
        var btn1 = app.lookup("btn1");
        if (btn1) {
            btn1.click();
            return {clicked: true};
        }
        return {clicked: false};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Click btn1 result:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(2)
    
    # Check running apps and popups
    js_check = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        return instances.map(ai => {
            return {
                id: ai.app ? ai.app.id : 'no-id',
                children: ai.getContainer().getAllRecursiveChildren().map(c => ({
                    id: c.id,
                    type: c.type,
                    text: c.text,
                    value: c.value
                })).filter(c => c.text || c.type === 'checkbox' || c.type === 'button')
            };
        });
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_check, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value')
    
    # Screenshot
    ws.send(json.dumps({'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_btn1_popup.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    for item in data:
        if 'p0' in item['id'] or 'pop' in item['id'] or 'Dialog' in item['id']:
            print(f"Popup App: {item['id']}")
            for c in item['children']:
                print(f"  {c}")

    ws.close()

if __name__ == '__main__':
    main()
