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
        var indexApp = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'app/com/main/Index'; });
        if (!indexApp) return 'No Index app';
        
        var si = indexApp.lookup('siFindMenu');
        if (si) {
            si.value = '개인정보변경신청';
            if (typeof si.search === 'function') si.search();
            else if (typeof si.dispatchEvent === 'function') {
                si.dispatchEvent(new cpr.events.CUIEvent('search'));
            }
            return { ok: true, val: si.value };
        }
        return { ok: false, err: 'no siFindMenu' };
        """
        res = driver.execute_script(js)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        break
