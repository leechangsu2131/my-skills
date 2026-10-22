import io
import os
import sys
import time
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

# Open new apply popup
js_open = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var main = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_m00'; });
    if (!main) return 'main not found';
    
    // Check if popup already open
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) {
        var btnAply = main.lookup('btnAply');
        btnAply.click();
        return 'clicked btnAply';
    }
    return 'popup already open';
"""
print('Open popup:', driver.execute_script(js_open))
time.sleep(2)

# Inspect popup
js_inspect = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) return 'no popup';
    return 'popup ready';
"""
print('Popup status:', driver.execute_script(js_inspect))
