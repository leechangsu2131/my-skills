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
    
    // Check all data managers or submission targets
    var res = {};
    
    // Let's inspect popup's subAply or submission
    // In CPR, app.lookup('subAply') or similar
    var sub = popup.lookup('subAply') || popup.lookup('subSave') || popup.lookup('sub_save');
    if (sub) {
        res.subId = sub.id;
        res.action = sub.action;
    }
    
    // Look at all submissions in popup
    for (var k in popup) {
        try {
            if (popup[k] && popup[k] instanceof cpr.protocols.Submission) {
                res[k] = popup[k].action;
            }
        } catch(e) {}
    }
    
    // Check error message in window or cpr
    if (window.__lastError) res.__lastError = window.__lastError;
    if (cpr.core.Platform.INSTANCE._lastError) res.platformLastError = cpr.core.Platform.INSTANCE._lastError;
    
    return res;
"""
print(driver.execute_script(js))
