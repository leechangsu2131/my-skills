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
            var res = idx.callAppMethod("doOpenMenuToMdi", ["AMELS40038"]);
            return { success: true, res: res };
        } catch(e) {
            return { error: e.toString() };
        }
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print("Call result:", res.get('result', {}).get('result', {}).get('value'))
    
    time.sleep(5)
    
    # Check apps
    js_apps = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_srgbm02_m00"));
        if (!app) return {error: "els_srgbm02_m00 not found", apps: instances.map(a => a.app ? a.app.id : '')};
        
        var ctrls = [];
        var allCtrls = app.getContainer().getAllRecursiveChildren();
        for (var i = 0; i < allCtrls.length; i++) {
            var c = allCtrls[i];
            var type = c.type;
            var id = c.id;
            var val = '';
            var text = '';
            try { if (c.value !== undefined) val = String(c.value); } catch(e){}
            try { if (c.text !== undefined) text = String(c.text); } catch(e){}
            ctrls.push({id: id, type: type, text: text, value: val, visible: c.visible, enabled: c.enabled});
        }
        return {
            ctrls: ctrls.filter(c => c.type === 'button' || c.type === 'checkbox' || c.type === 'combobox' || c.type === 'grid' || (c.text && (c.text.includes('다운') || c.text.includes('출력') || c.text.includes('조회') || c.text.includes('보호자') || c.text.includes('생년')))),
            datasets: app.getAllDataControls().map(d => ({id: d.id, type: d.type}))
        };
    })()
    """
    ws.send(json.dumps({'id': 2, 'method': 'Runtime.evaluate', 'params': {'expression': js_apps, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    data = res.get('result', {}).get('result', {}).get('value')
    print("App result:", json.dumps(data, ensure_ascii=False, indent=2))
    
    ws.close()

if __name__ == '__main__':
    main()
