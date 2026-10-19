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

target_sso_url = None
for h in driver.window_handles:
    driver.switch_to.window(h)
    if 'eduptl' in driver.current_url:
        sso_url = driver.execute_script("""
            var btn = document.querySelector('a.menuBtn[id*="neis"]');
            return btn ? btn.id : null;
        """)
        if sso_url:
            target_sso_url = sso_url
            print('Found SSO URL:', target_sso_url)
            break

if target_sso_url:
    print('Opening SSO URL in new tab...')
    driver.switch_to.new_window('tab')
    driver.get(target_sso_url)
    time.sleep(6)
    
    print('Title after SSO:', driver.title)
    print('URL after SSO:', driver.current_url)
    
    js_cpr = 'return Boolean(window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE);'
    has_cpr = driver.execute_script(js_cpr)
    print('CPR present:', has_cpr)
    if has_cpr:
        apps = driver.execute_script('return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(function(a){return a.app ? a.app.id : "";});')
        print('Apps:', apps)
