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
        var platform = cpr.core.Platform.INSTANCE;
        var indexApp = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'app/com/main/Index'; });
        if (!indexApp) return 'No Index app';
        
        var methods = [];
        for (var k in indexApp) {
            if (typeof indexApp[k] === 'function') methods.push(k);
        }
        
        // Also check indexApp.callAppMethod or similar
        return {
            methods: methods,
            hasCallAppMethod: typeof indexApp.callAppMethod === 'function'
        };
        """
        res = driver.execute_script(js)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        break
