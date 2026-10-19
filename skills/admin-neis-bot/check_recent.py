import os
import glob
import time

def check_recent(path, name):
    files = glob.glob(path + '/**/*', recursive=True)
    recent = []
    now = time.time()
    for f in files:
        if os.path.isfile(f):
            try:
                mtime = os.path.getmtime(f)
                if now - mtime < 300: # modified in last 5 mins
                    recent.append((mtime, f))
            except Exception:
                pass
    recent.sort(reverse=True)
    print(f'=== {name} ({len(recent)} recent files) ===')
    for mtime, f in recent[:8]:
        t_str = time.strftime('%H:%M:%S', time.localtime(mtime))
        print(f'  {t_str} - {os.path.basename(f)}')

check_recent(os.path.expanduser('~') + r'\AppData\Local\Microsoft\Edge\User Data\Default', 'Edge')
check_recent(os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data', 'Chrome 9222')
