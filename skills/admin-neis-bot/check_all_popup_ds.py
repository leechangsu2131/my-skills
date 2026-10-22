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
    if (!popup) return {error: 'Popup not found'};
    
    // Check all data sets in popup
    var dm = popup.getDataManager ? popup.getDataManager() : null;
    var allData = {};
    
    // Look at all properties in popup
    for (var k in popup) {
        try {
            var obj = popup[k];
            if (obj && obj.getRowDataRanged) {
                allData[k] = obj.getRowDataRanged();
            }
        } catch(e) {}
    }
    
    // Check grdMain (기간정보 목록 그리드)
    var grd = popup.lookup('grdMain');
    if (grd) {
        allData._grdMainDataSet = grd.dataSet ? grd.dataSet.id : 'no dataset';
        if (grd.dataSet && grd.dataSet.getRowDataRanged) {
            allData._grdMainRows = grd.dataSet.getRowDataRanged();
        }
    }
    
    // Check grdTgpr (출장자 목록 그리드)
    var grdTgpr = popup.lookup('grdTgpr');
    if (grdTgpr) {
        allData._grdTgprDataSet = grdTgpr.dataSet ? grdTgpr.dataSet.id : 'no dataset';
        if (grdTgpr.dataSet && grdTgpr.dataSet.getRowDataRanged) {
            allData._grdTgprRows = grdTgpr.dataSet.getRowDataRanged();
        }
    }
    
    return allData;
"""
res = driver.execute_script(js)
print(json.dumps(res, ensure_ascii=False, indent=2))
