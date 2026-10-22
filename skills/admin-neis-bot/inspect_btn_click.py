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
    
    var btn = popup.lookup('btnAply');
    if (!btn) return {error: 'btnAply not found'};
    
    var listeners = [];
    if (btn._eventListenerList) {
        for (var evt in btn._eventListenerList) {
            var list = btn._eventListenerList[evt];
            for (var i = 0; i < list.length; i++) {
                var fn = list[i].func || list[i].handler || list[i];
                listeners.push({
                    event: evt,
                    src: fn.toString().slice(0, 1500)
                });
            }
        }
    }
    
    // Also inspect popup script / controller methods
    var methods = [];
    // In CPR, app.getScript() or app.exports
    return {
        listeners: listeners
    };
"""
res = driver.execute_script(js)
print(json.dumps(res, ensure_ascii=False, indent=2))
