import urllib.request
import json
import time
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if t.get('id') == '95ECC5D4F751F9C6BFFEAC8B8DDF0490'), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    # Check how many students have parent info by selecting each row
    js = """
    (() => {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var app = instances.find(ai => ai.app && ai.app.id.includes("els_sdlpa00_m00"));
        if (!app) return {error: "app not found"};
        
        var grd = app.lookup("grdMain");
        var dsStu = app.lookup("dsStu");
        var dsSchpaAprv = app.lookup("dsSchpaAprv");
        var count = dsStu.getRowCount();
        
        // Let's check submission for detail
        var subDetail = app.lookup("subNeisPlusSchpaAprv");
        return {
            count: count,
            hasSubDetail: !!subDetail,
            action: subDetail ? subDetail.action : null
        };
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    print(res.get('result', {}).get('result', {}).get('value'))
    ws.close()

if __name__ == '__main__':
    main()
