import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

os.environ['no_proxy'] = 'localhost,127.0.0.1'
opts = Options()
opts.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
driver = webdriver.Chrome(options=opts)

print('Opening gbe.neis.go.kr in Chrome...')
driver.execute_script("window.open('https://gbe.neis.go.kr');")
time.sleep(4)

driver.switch_to.window(driver.window_handles[-1])
print('New tab title:', driver.title, 'URL:', driver.current_url)

js_cpr = 'return Boolean(window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE);'
try:
    has_cpr = driver.execute_script(js_cpr)
    print('CPR present:', has_cpr)
    if has_cpr:
        apps = driver.execute_script('return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(function(a){return a.app ? a.app.id : "";});')
        print('Apps:', apps)
except Exception as e:
    print('CPR error:', e)
