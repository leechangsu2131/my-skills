import io
import os
import sys
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
        var indexApp = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'app/com/main/Index'; });
        if (!indexApp) return 'No Index app';
        
        var btn = indexApp.lookup('btn_allMenu');
        if (btn && typeof btn.click === 'function') {
            btn.click();
            return 'btn_allMenu clicked';
        }
        return 'no btn_allMenu';
        """
        res = driver.execute_script(js)
        print('Result:', res)
        time.sleep(2)
        
        apps = driver.execute_script("""
            return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(function(a){ return a.app ? a.app.id : ''; });
        """)
        print('Apps:', apps)
        break
