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
    if 'neis.go.kr/jsp/main' in driver.current_url:
        js = """
        var funcs = [];
        for (var k in window) {
            if (typeof window[k] === 'function' && (k.indexOf('menu') !== -1 || k.indexOf('Menu') !== -1 || k.indexOf('open') !== -1 || k.indexOf('Open') !== -1 || k.indexOf('tab') !== -1 || k.indexOf('Tab') !== -1)) {
                funcs.push(k);
            }
        }
        
        // Also check window.app or window.cpr.core
        var cprModules = [];
        if (window.cpr && window.cpr.core && window.cpr.core.Module) {
            // Check loaded modules
        }
        
        return { windowFuncs: funcs };
        """
        res = driver.execute_script(js)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        break
