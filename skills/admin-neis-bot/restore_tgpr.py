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
    if 'neis.go.kr' in driver.current_url:
        break

js = """
    var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var popup = apps.find(function(a) { return a.app && a.app.id === 'edu/ga/srv/mym/mm/srv_mymmm03_p00'; });
    if (!popup) return 'no popup';
    
    var dsTgpr = popup.lookup('dsTgpr');
    dsTgpr.clearFilter();
    
    // Clear and insert exactly 1 row for Lee Chang Su
    dsTgpr.clear();
    
    var rowData = {
        "bgngHh": "11",
        "bgngHm": "1100",
        "bgngMm": "00",
        "bgngYmd": "20261107",
        "bsrpSn": "0",
        "chgYn": "N",
        "cncdSn": "1",
        "dptCd": "R100006630",
        "dptNm": "화천초등학교",
        "emgCnctTelno": "010-4233-0844",
        "endHh": "18",
        "endHm": "1800",
        "endMm": "00",
        "endYmd": "20261107",
        "instCd": "R100006630",
        "invlFlnm": "이창수",
        "invlNo": "R101053140",
        "jbgdCd": "04147",
        "jbgdNm": "초등학교교사",
        "puoYn": "Y",
        "puoYnNm": "정규직원",
        "rprsYn": "Y",
        "sameBsrpPriodYn": "Y",
        "srvPsnScCd": ""
    };
    
    dsTgpr.insertRowData(0, true, rowData);
    
    var grdTgpr = popup.lookup('grdTgpr');
    if (grdTgpr) {
        grdTgpr.redraw();
        grdTgpr.setCheckRowIndex(0, true);
    }
    
    return dsTgpr.getRowDataRanged();
"""
res = driver.execute_script(js)
print('Restored dsTgpr:')
print(json.dumps(res, ensure_ascii=False, indent=2))

driver.save_screenshot('C:/Users/user/.gemini/antigravity/brain/0c28257f-d0fa-4331-a07e-b804c459ee32/restored_tgpr.png')
print('Screenshot saved!')
