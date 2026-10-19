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
        var m00 = platform.getAllRunningAppInstances().find(function(a){ return a.app && a.app.id === 'edu/ga/tps/hrd/mm/tps_hrdmm01_m00'; });
        if (!m00) return 'No m00';
        
        var tabfolder = null;
        m00.getContainer().getAllRecursiveChildren().forEach(function(c){
            if (c.type === 'tabfolder') tabfolder = c;
        });
        
        if (!tabfolder) return 'No tabfolder';
        
        // Find "연수" tab (idx 4)
        var tabItems = tabfolder.getTabItems();
        var trainingTab = tabItems.find(function(ti){ return ti.text === '연수'; });
        if (!trainingTab) return 'No training tab';
        
        tabfolder.setSelectedTabItem(trainingTab);
        return { ok: true, selectedTab: trainingTab.text };
        """
        res = driver.execute_script(js)
        print('Tab selection result:', res)
        time.sleep(2)
        
        # Now check apps
        apps = driver.execute_script("""
            return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(function(a){ return a.app ? a.app.id : ''; });
        """)
        print('Running Apps after tab selection:', apps)
        break
