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
        var found = [];
        var all = document.querySelectorAll('*');
        for (var i = 0; i < all.length; i++) {
            var txt = (all[i].innerText || '').trim();
            if (txt === '개인정보변경신청' || txt === '기본사항' || txt === '교원연수' || txt === '연수') {
                found.push({ tag: all[i].tagName, text: txt, id: all[i].id, className: all[i].className });
            }
        }
        return found;
        """
        res = driver.execute_script(js)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        break
