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

js_click = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    for (var i = 0; i < apps.length; i++) {
        if (apps[i].app && apps[i].app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_m00') {
            var btn = apps[i].lookup('btnAply');
            if (btn) {
                btn.click();
                return 'btnAply clicked';
            }
        }
    }
    return 'btnAply not found';
"""
ret = driver.execute_script(js_click)
print('Click result:', ret)

time.sleep(2)

js_apps = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    return apps.map(function(a){
        return {
            id: a.app ? a.app.id : '',
            ctrlCount: a.getContainer() ? a.getContainer().getAllRecursiveChildren().length : 0
        };
    });
"""
print('Running apps after click:', driver.execute_script(js_apps))
