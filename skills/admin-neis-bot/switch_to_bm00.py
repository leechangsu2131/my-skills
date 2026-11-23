import urllib.request
import json
import time
import base64
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    # 1. Close active dialog / popup
    js_close = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        // find dialog or popup
        for (var i = 0; i < instances.length; i++) {
            var ai = instances[i];
            var btn = ai.lookup("btnCancel") || ai.lookup("btnCancle") || ai.lookup("btnClose");
            if (btn) {
                btn.click();
                return {closedBtn: btn.id};
            }
        }
        // or click cancel button by text
        for (var i = 0; i < instances.length; i++) {
            var ai = instances[i];
            var all = ai.getContainer().getAllRecursiveChildren();
            for (var j = 0; j < all.length; j++) {
                if (all[j].text === '취소' && all[j].type === 'button') {
                    all[j].click();
                    return {closedText: '취소'};
                }
            }
        }
        return {none: true};
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js_close, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Close popup:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(1)
    
    # 2. Switch MDI tab to 기본신상관리
    js_switch = """
    (() => {
        var idx = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("Index"));
        var mdi = idx.lookup("mdiCn");
        if (mdi) {
            for (var i = 0; i < mdi.getTabItemCount(); i++) {
                var ti = mdi.getTabItem(i);
                if (ti.text.includes("기본신상관리")) {
                    mdi.setSelectedTabItem(ti);
                    return {switched: true, text: ti.text};
                }
            }
        }
        return {switched: false};
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_switch, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Switch tab:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(2)
    
    # 3. Screenshot of 기본신상관리
    ws.send(json.dumps({'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_srgbm00_tab.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    ws.close()

if __name__ == '__main__':
    main()
