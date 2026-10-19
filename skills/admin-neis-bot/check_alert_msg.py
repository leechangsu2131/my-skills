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
        var alertApp = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'app/cmn/alert'; });
        if (!alertApp) return 'No alert app';
        
        var msgs = [];
        alertApp.getContainer().getAllRecursiveChildren().forEach(function(c){
            if (c.type === 'output' || c.type === 'button') {
                msgs.push({ id: c.id, type: c.type, val: c.value || c.text });
            }
        });
        return msgs;
        """
        res = driver.execute_script(js)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        break
