import io
import os
import sys
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.environ['no_proxy'] = 'localhost,127.0.0.1'

opts = Options()
opts.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
driver = webdriver.Chrome(options=opts)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if 'neis.go.kr/jsp/main' in driver.current_url:
        js = """
        var platform = cpr.core.Platform.INSTANCE;
        var alertApp = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'app/cmn/alert'; });
        if (alertApp) {
            var btn = alertApp.lookup('btnConfirm');
            if (btn && typeof btn.click === 'function') {
                btn.click();
                return 'btnConfirm clicked';
            }
        }
        return 'no alertApp or btnConfirm';
        """
        res = driver.execute_script(js)
        print('Alert dismiss result:', res)
        time.sleep(2)
        
        apps = driver.execute_script("""
            return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(function(a){ return a.app ? a.app.id : ''; });
        """)
        print('Running Apps after alert dismiss:', apps)
        break
