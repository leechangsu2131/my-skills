import os
import glob
import re

edge_sessions = os.path.expanduser('~') + r'\AppData\Local\Microsoft\Edge\User Data\Default\Sessions'
files = glob.glob(edge_sessions + r'\*')
for f in files:
    print(f, os.path.getsize(f))
    try:
        with open(f, 'rb') as fp:
            content = fp.read()
            urls = re.findall(b'https?://[^\x00\r\n\t \"\'<>]+', content)
            matched = set([u.decode('latin1', errors='ignore') for u in urls if b'neis' in u or b'gbe' in u or b'keris' in u])
            print('  Matched urls:', matched)
    except Exception as e:
        print('  Error:', e)
