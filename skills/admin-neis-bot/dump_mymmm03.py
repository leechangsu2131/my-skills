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
    var target = null;
    for (var i = 0; i < apps.length; i++) {
        if (apps[i].app && apps[i].app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_m00') {
            target = apps[i];
            break;
        }
    }
    if (!target) return {error: 'Target app not found'};
    
    var ctrls = [];
    var all = target.getContainer().getAllRecursiveChildren();
    for (var c = 0; c < all.length; c++) {
        var ctrl = all[c];
        ctrls.push({
            id: ctrl.id,
            type: ctrl.type,
            value: ctrl.value !== undefined ? ctrl.value : null,
            text: ctrl.text !== undefined ? ctrl.text : null,
            visible: ctrl.visible !== undefined ? ctrl.visible : null,
            enabled: ctrl.enabled !== undefined ? ctrl.enabled : null
        });
    }
    return ctrls;
"""
ctrls = driver.execute_script(js)
print(f'Controls in srv_mymmm03_m00: {len(ctrls)}')
for c in ctrls:
    if c.get('type') in ['button', 'combobox', 'dateinput', 'grid'] or (c.get('text') and any(w in c.get('text') for w in ['신청', '등록', '추가', '출장', '조회'])):
        print(c)
