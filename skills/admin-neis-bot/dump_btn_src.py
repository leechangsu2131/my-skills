import io
import os
import sys
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.environ['no_proxy'] = 'localhost,127.0.0.1'

opts = Options()
opts.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
driver = webdriver.Chrome(options=opts)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if 'neis.go.kr' in driver.current_url:
        break

js = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    var btn = popup.lookup('btnAply');
    var fn = btn._eventListenerList['click'][0].func || btn._eventListenerList['click'][0].handler || btn._eventListenerList['click'][0];
    return fn.toString();
"""
src = driver.execute_script(js)
with open('c:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/btnAply_src.js', 'w', encoding='utf-8') as f:
    f.write(src)
print(f'Length of handler: {len(src)}')
print(src[:3000])
