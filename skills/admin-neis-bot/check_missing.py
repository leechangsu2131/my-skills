import urllib.request
import json
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if t.get('id') == '95ECC5D4F751F9C6BFFEAC8B8DDF0490'), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=10)
    
    js = """
    (() => {
        var missing = window.__parent_data.filter(s => !s.parents || s.parents.length === 0).map(s => s.name);
        return missing;
    })()
    """
    ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js, 'returnByValue': True}}))
    res = json.loads(ws.recv())
    missing_names = res.get('result', {}).get('result', {}).get('value', [])
    print("Students without parent in 학부모서비스:", missing_names)
    ws.close()

if __name__ == '__main__':
    main()
