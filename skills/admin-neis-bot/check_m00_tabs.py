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
        var m00 = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'edu/ga/tps/hrd/mm/tps_hrdmm01_m00'; });
        if (!m00) return 'No m00';
        
        var tabs = [];
        m00.getContainer().getAllRecursiveChildren().forEach(function(c){
            if (c.type === 'tabfolder') {
                c.getTabItems().forEach(function(ti, idx){
                    tabs.push({ idx: idx, text: ti.text, selected: ti.selected, userAttr: ti.userAttr });
                });
            }
        });
        return { tabs: tabs };
        """
        res = driver.execute_script(js)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        break
