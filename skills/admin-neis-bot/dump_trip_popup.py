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
        if (apps[i].app && apps[i].app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00') {
            target = apps[i];
            break;
        }
    }
    if (!target) return {error: 'Target app not found'};
    
    var ctrls = [];
    var all = target.getContainer().getAllRecursiveChildren();
    for (var c = 0; c < all.length; c++) {
        var ctrl = all[c];
        var info = {
            id: ctrl.id,
            type: ctrl.type,
            value: ctrl.value !== undefined ? ctrl.value : null,
            text: ctrl.text !== undefined ? ctrl.text : null,
            visible: ctrl.visible !== undefined ? ctrl.visible : null,
            enabled: ctrl.enabled !== undefined ? ctrl.enabled : null
        };
        if (ctrl.type === 'combobox' && ctrl.getItems) {
            try {
                info.items = ctrl.getItems().map(function(it){
                    return {label: it.label, value: it.value};
                });
            } catch(e) {
                info.items = 'error: ' + e;
            }
        }
        ctrls.push(info);
    }
    return ctrls;
"""
ctrls = driver.execute_script(js)
with open('c:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/admin-neis-bot/trip_popup_dump.json', 'w', encoding='utf-8') as f:
    json.dump(ctrls, f, ensure_ascii=False, indent=2)

print(f'Total controls in popup: {len(ctrls)}')
for c in ctrls:
    if c.get('id') or c.get('text'):
        print(f"[{c.get('type')}] ID: {c.get('id')} | Text: {c.get('text')} | Val: {c.get('value')}")
