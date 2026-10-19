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
        print('Found NEIS main window!')
        js = """
        var platform = cpr.core.Platform.INSTANCE;
        var indexApp = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'app/com/main/Index'; });
        if (!indexApp) return 'No Index app';
        
        var datasets = indexApp.getAllDataControls().map(function(ds){
            return { id: ds.id, type: ds.type };
        });
        
        var menuList = [];
        indexApp.getAllDataControls().forEach(function(ds){
            if (typeof ds.getRowCount === 'function') {
                var count = ds.getRowCount();
                for (var i = 0; i < count; i++) {
                    var row = ds.getRowData(i);
                    var strRow = JSON.stringify(row);
                    if (strRow.indexOf('연수') !== -1 || strRow.indexOf('hrd') !== -1) {
                        menuList.push({ dsId: ds.id, row: row });
                    }
                }
            }
        });
        
        return { datasets: datasets, matchedMenus: menuList };
        """
        res = driver.execute_script(js)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        break
