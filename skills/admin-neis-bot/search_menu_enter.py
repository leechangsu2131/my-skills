import io
import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.environ['no_proxy'] = 'localhost,127.0.0.1'

opts = Options()
opts.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
driver = webdriver.Chrome(options=opts)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if 'neis.go.kr/jsp/main' in driver.current_url:
        # Find input corresponding to siFindMenu
        inp = driver.execute_script("""
            var el = document.querySelector('.cl-searchinput input, input[placeholder*="메뉴"]');
            if (el) {
                el.focus();
                return true;
            }
            return false;
        """)
        print('Input focused:', inp)
        
        # Click search icon or send ENTER
        res = driver.execute_script("""
            var btn = document.querySelector('.cl-searchinput-search-button, .cl-searchinput button');
            if (btn) {
                btn.click();
                return 'btn clicked';
            }
            return 'no btn';
        """)
        print('Button clicked:', res)
        time.sleep(2)
        
        # Check running apps or floating dialogs
        apps = driver.execute_script("""
            return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(function(a){ return a.app ? a.app.id : ''; });
        """)
        print('Apps:', apps)
        break
