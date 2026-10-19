import io
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.environ['no_proxy'] = 'localhost,127.0.0.1'

opts = Options()
opts.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
driver = webdriver.Chrome(options=opts)

for i, h in enumerate(driver.window_handles):
    driver.switch_to.window(h)
    print(f'Handle [{i}] Title: {driver.title} | URL: {driver.current_url}')
    txt = driver.execute_script('return (document.body ? document.body.innerText : "").substring(0, 150);')
    print('  Text:', txt.replace('\n', ' '))
