import urllib.request
import json
req = urllib.request.Request('http://localhost:5030/api/start', method='POST', data=b'{}', headers={'Content-Type': 'application/json'})
urllib.request.urlopen(req)
try:
    urllib.request.urlopen(req)
except Exception as e:
    print(e.read().decode())
