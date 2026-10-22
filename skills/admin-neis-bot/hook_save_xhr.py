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
    if (!window.__hookedXHR) {
        window.__hookedXHR = true;
        var origOpen = XMLHttpRequest.prototype.open;
        var origSend = XMLHttpRequest.prototype.send;
        
        XMLHttpRequest.prototype.open = function(method, url) {
            this._url = url;
            this._method = method;
            return origOpen.apply(this, arguments);
        };
        
        XMLHttpRequest.prototype.send = function(data) {
            if (this._url && this._url.indexOf('srv_mym_mm03_004') !== -1) {
                window.__lastSaveReq = {
                    url: this._url,
                    method: this._method,
                    data: data
                };
                var self = this;
                this.addEventListener('load', function() {
                    window.__lastSaveRes = {
                        status: self.status,
                        text: self.responseText
                    };
                });
            }
            return origSend.apply(this, arguments);
        };
    }
    return 'hook installed';
"""
print(driver.execute_script(js))

# Dismiss any open alert
js_dismiss = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    for (var i = 0; i < apps.length; i++) {
        var a = apps[i];
        if (a.app && a.app.id && a.app.id.indexOf('alert') !== -1) {
            var btn = a.lookup('btnConfirm') || a.lookup('btnOk');
            if (btn) btn.click();
        }
    }
"""
driver.execute_script(js_dismiss)
time.sleep(1)

# Click btnAply
js_click = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    var btn = popup.lookup('btnAply');
    btn.click();
"""
driver.execute_script(js_click)
time.sleep(3)

js_get = """
    return {
        req: window.__lastSaveReq,
        res: window.__lastSaveRes
    };
"""
traffic = driver.execute_script(js_get)
print('XHR Traffic:')
print(json.dumps(traffic, ensure_ascii=False, indent=2))
