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
        print('Calling openMdiMenu("AMCMC50044")...')
        js = """
        try {
            if (typeof window.openMdiMenu === 'function') {
                window.openMdiMenu('AMCMC50044');
                return { success: true };
            }
            return { success: false, err: 'no openMdiMenu' };
        } catch(e) {
            return { success: false, err: e.toString() };
        }
        """
        res = driver.execute_script(js)
        print('Result:', res)
        time.sleep(3)
        
        apps = driver.execute_script("""
            return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(function(a){ return a.app ? a.app.id : ''; });
        """)
        print('Running Apps:', apps)
        break
