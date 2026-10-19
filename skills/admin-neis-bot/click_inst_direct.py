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
        var p14 = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'edu/ga/tps/hrd/mm/tps_hrdmm01_p14'; });
        if (!p14) return 'No p14';
        
        var btn = p14.lookup('btnEduInstCd');
        if (btn && typeof btn.click === 'function') {
            btn.click();
            return { ok: true, msg: 'btnEduInstCd clicked' };
        }
        return { ok: false };
        """
        res = driver.execute_script(js)
        print('Click result:', res)
        time.sleep(1)
        
        # Now check ipb and cmb visibility
        res2 = driver.execute_script("""
            var platform = cpr.core.Platform.INSTANCE;
            var p14 = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'edu/ga/tps/hrd/mm/tps_hrdmm01_p14'; });
            var btn = p14.lookup('btnEduInstCd');
            var cmb = p14.lookup('cmbTchTraiEduInstCd');
            var ipb = p14.lookup('ipbTraiInstNm');
            if (ipb) {
                ipb.setValue('동국대학교경주병원');
                ipb.redraw();
            }
            return {
                btnVal: btn ? btn.value : null,
                cmbVisible: cmb ? cmb.visible : null,
                ipbVisible: ipb ? ipb.visible : null,
                ipbVal: ipb ? ipb.value : null
            };
        """)
        print(json.dumps(res2, ensure_ascii=False, indent=2))
        break
