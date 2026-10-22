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
    if (!popup) return {error: 'Popup not found'};
    
    var sub = popup.lookup('subSave');
    
    // Check all properties of sub
    var info = {
        id: sub.id,
        action: sub.action,
        method: sub.method,
        mediaType: sub.mediaType
    };
    
    // Check requestData definitions
    // In cpr, sub._reqData or sub.getRequestDataControls or sub.getRequestDatas
    for (var k in sub) {
        try {
            var v = sub[k];
            if (typeof v !== 'function') {
                info[k] = v;
            }
        } catch(e) {}
    }
    
    // Check app's all submissions and their properties
    return info;
"""
res = driver.execute_script(js)
print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
