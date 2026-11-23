import urllib.request
import json
import time
import base64
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    # Close any open dialogs
    js_close_all = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var closed = [];
        for (var i = 0; i < instances.length; i++) {
            var ai = instances[i];
            if (ai.app && (ai.app.id.includes('_p') || ai.app.id.includes('Dialog') || ai.app.id.includes('Pop') || ai.app.id.includes('pheam10'))) {
                try {
                    ai.close();
                    closed.push(ai.app.id);
                } catch(e) {
                    closed.push('err:' + e.toString());
                }
            }
        }
        return closed;
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js_close_all, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Closed popups:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(1)
    
    # Now switch to 기본신상관리 tab
    js_switch_tab = """
    (() => {
        var idx = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes("Index"));
        var mdi = idx.lookup("mdiCn");
        if (!mdi) {
            // Find mdi container in Index children
            var all = idx.getContainer().getAllRecursiveChildren();
            for (var i = 0; i < all.length; i++) {
                if (all[i].type === 'mdifolder') {
                    mdi = all[i];
                    break;
                }
            }
        }
        if (mdi) {
            var count = mdi.getTabItemCount();
            var tabNames = [];
            for (var i = 0; i < count; i++) {
                var ti = mdi.getTabItem(i);
                tabNames.push(ti.text);
                if (ti.text.includes("기본신상관리")) {
                    mdi.setSelectedTabItem(ti);
                    return {found: true, text: ti.text, all: tabNames};
                }
            }
            return {found: false, all: tabNames};
        }
        return {error: 'no mdi folder'};
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_switch_tab, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("MDI Switch:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(2)
    
    # Screenshot
    ws.send(json.dumps({'id': 3, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\neis_srgbm00_active.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
        
    ws.close()

if __name__ == '__main__':
    main()
