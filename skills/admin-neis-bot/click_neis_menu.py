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
    if 'eduptl' in driver.current_url:
        res = driver.execute_script("""
            var btn = document.querySelector('a.menuBtn[id*="neis"]');
            if (!btn) return 'btn not found';
            return {
                id: btn.id,
                text: btn.innerText
            };
        """)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        
        # Now click the button via selenium
        el = driver.find_element('css selector', 'a.menuBtn[id*="neis"]')
        print('Element found:', el.text)
        el.click()
        print('Clicked!')
