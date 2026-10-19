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
        
        // Find methods inside indexApp.app
        var appMethods = [];
        if (indexApp.app && indexApp.app._methods) {
            appMethods = Object.keys(indexApp.app._methods);
        }
        
        // Find tree or menu controls in indexApp
        var controls = [];
        indexApp.getContainer().getAllRecursiveChildren().forEach(function(c){
            if (c.id && (c.id.toLowerCase().indexOf('menu') !== -1 || c.id.toLowerCase().indexOf('tree') !== -1 || c.type === 'tree' || c.type === 'menu')) {
                controls.push({ id: c.id, type: c.type });
            }
        });
        
        return { appMethods: appMethods, controls: controls };
        """
        res = driver.execute_script(js)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        break
