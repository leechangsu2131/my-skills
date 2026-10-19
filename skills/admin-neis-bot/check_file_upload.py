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
        var res = {
            hasRaonk: typeof window.RAONKUpload !== 'undefined',
            raonkObjs: []
        };
        if (window.G_RAONK && window.G_RAONK.uploadArray) {
            res.raonkObjs = Object.keys(window.G_RAONK.uploadArray);
        }
        
        // Check input[type="file"] in document
        var fileInputs = [];
        document.querySelectorAll('input[type="file"]').forEach(function(fi){
            fileInputs.push({ id: fi.id, name: fi.name });
        });
        res.fileInputs = fileInputs;
        
        return res;
        """
        res = driver.execute_script(js)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        break
