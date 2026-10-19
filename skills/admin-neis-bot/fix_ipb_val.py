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
        var p14 = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'edu/ga/tps/hrd/mm/tps_hrdmm01_p14'; });
        var ipb = p14.lookup('ipbTraiInstNm');
        var cmb = p14.lookup('cmbTchTraiEduInstCd');
        var btn = p14.lookup('btnEduInstCd');
        
        if (ipb) {
            ipb.value = '동국대학교경주병원';
            if (typeof ipb.redraw === 'function') ipb.redraw();
        }
        
        var dsMain = p14.lookup('dsMain');
        if (dsMain) {
            dsMain.setValue(0, 'traiInstNm', '동국대학교경주병원');
        }
        
        return {
            btnVal: btn ? btn.value : null,
            cmbVisible: cmb ? cmb.visible : null,
            ipbVisible: ipb ? ipb.visible : null,
            ipbVal: ipb ? ipb.value : null,
            dsInstNm: dsMain ? dsMain.getValue(0, 'traiInstNm') : null
        };
        """
        res = driver.execute_script(js)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        break
