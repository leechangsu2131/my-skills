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
        print('Found NEIS tab')
        break

# Open AMCMC40046 (개인출장관리)
js_open = """
    if (window.openMdiMenu) {
        window.openMdiMenu('AMCMC40046');
        return 'openMdiMenu called';
    }
    return 'openMdiMenu not found';
"""
ret = driver.execute_script(js_open)
print('Open menu result:', ret)

time.sleep(3)

# Inspect apps
js_inspect = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var list = [];
    for (var i = 0; i < apps.length; i++) {
        var a = apps[i];
        var appId = a.app ? a.app.id : 'unknown';
        var ctrls = [];
        try {
            var all = a.getContainer().getAllRecursiveChildren();
            for (var c = 0; c < all.length; c++) {
                var ctrl = all[c];
                ctrls.push({
                    id: ctrl.id,
                    type: ctrl.type,
                    value: ctrl.value !== undefined ? ctrl.value : null,
                    text: ctrl.text !== undefined ? ctrl.text : null
                });
            }
        } catch(e) {
            ctrls.push({error: e.toString()});
        }
        list.push({appId: appId, ctrlCount: ctrls.length, ctrls: ctrls.slice(0, 30)});
    }
    return list;
"""
apps_info = driver.execute_script(js_inspect)
print(f'Total running apps: {len(apps_info)}')
for item in apps_info:
    print(f"App: {item['appId']}, Ctrls: {item['ctrlCount']}")
    for c in item['ctrls'][:10]:
        print('  ', c)
