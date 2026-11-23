import urllib.request
import json
import time
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    
    # 1. Get SSO URL from portal tab
    portal_tab = next((t for t in resp if 'eduptl' in t.get('url', '')), None)
    if not portal_tab:
        print("No portal tab found!")
        return
        
    ws_portal = websocket.create_connection(portal_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=5)
    ws_portal.send(json.dumps({
        'id': 1,
        'method': 'Runtime.evaluate',
        'params': {'expression': "document.querySelector('a.menuBtn[id*=\"neis\"]').id", 'returnByValue': True}
    }))
    res = json.loads(ws_portal.recv())
    sso_url = res.get('result', {}).get('result', {}).get('value')
    ws_portal.close()
    
    print("Obtained SSO URL:", sso_url)
    if not sso_url:
        return
        
    # 2. Find NEIS tab
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    if not neis_tab:
        print("No NEIS tab found, creating or navigating...")
        return
        
    ws_neis = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    print("Navigating NEIS tab to SSO URL...")
    ws_neis.send(json.dumps({
        'id': 2,
        'method': 'Page.navigate',
        'params': {'url': sso_url}
    }))
    res = json.loads(ws_neis.recv())
    print("Navigate response:", res)
    ws_neis.close()
    
    # 3. Wait for NEIS to load
    print("Waiting 8 seconds for NEIS to load...")
    time.sleep(8)
    
    # Check again
    resp2 = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab2 = next((t for t in resp2 if 'neis.go.kr' in t.get('url', '')), None)
    if neis_tab2:
        print("NEIS Tab after SSO:", neis_tab2['title'], neis_tab2['url'])
        ws2 = websocket.create_connection(neis_tab2['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
        js = """
        (() => {
            if (typeof cpr === 'undefined') return {cpr: false, title: document.title};
            var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
            return {
                cpr: true,
                title: document.title,
                apps: apps.map(a => a.app ? a.app.id : 'no-id')
            };
        })()
        """
        ws2.send(json.dumps({'id': 3, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
        res2 = json.loads(ws2.recv())
        print("NEIS State:", res2.get('result', {}).get('result', {}).get('value'))
        ws2.close()

if __name__ == '__main__':
    main()
