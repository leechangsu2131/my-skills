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

js = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) return {error: 'Popup not found'};
    
    // Attach listener to subSave to intercept response
    var sub = popup.lookup('subSave');
    if (!sub) return {error: 'subSave not found'};
    
    window.__subSaveResponse = null;
    window.__subSaveError = null;
    
    sub.addEventListenerOnce('submit-done', function(e) {
        var s = e.control;
        window.__subSaveResponse = {
            metadata: s.getMetadata ? s.getMetadata() : null,
            xhrResponse: s.xhr ? s.xhr.responseText : null
        };
    });
    
    sub.addEventListenerOnce('submit-error', function(e) {
        var s = e.control;
        window.__subSaveError = {
            status: s.xhr ? s.xhr.status : null,
            statusText: s.xhr ? s.xhr.statusText : null,
            responseText: s.xhr ? s.xhr.responseText : null
        };
    });
    
    return {success: true, msg: 'Listener attached'};
"""
print('Attach listener:', driver.execute_script(js))

# Now click btnAply
js_click = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    var btn = popup.lookup('btnAply');
    btn.click();
    return 'btnAply clicked';
"""
print('Click:', driver.execute_script(js_click))

time.sleep(3)

js_get_res = """
    return {
        response: window.__subSaveResponse,
        error: window.__subSaveError
    };
"""
res = driver.execute_script(js_get_res)
print('Submission result:')
print(json.dumps(res, ensure_ascii=False, indent=2))
