import urllib.request
import json
import base64
import websocket

def main():
    resp = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read().decode('utf-8'))
    neis_tab = next((t for t in resp if 'neis.go.kr' in t.get('url', '')), None)
    ws = websocket.create_connection(neis_tab['webSocketDebuggerUrl'], suppress_origin=True, timeout=15)
    
    ws.send(json.dumps({'id': 1, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
    res = json.loads(ws.recv())
    img_b64 = res.get('result', {}).get('data')
    if img_b64:
        img_path = r"C:\Users\user\.gemini\antigravity\brain\fde9f22d-fe7a-43bc-9514-58c8a0680c48\after_btn6_click.png"
        with open(img_path, 'wb') as f:
            f.write(base64.b64decode(img_b64))
        print("Saved screenshot to:", img_path)
    ws.close()

if __name__ == '__main__':
    main()
