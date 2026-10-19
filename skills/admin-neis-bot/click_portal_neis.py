import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

os.environ['no_proxy'] = 'localhost,127.0.0.1'
opts = Options()
opts.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
driver = webdriver.Chrome(options=opts)

initial_handles = list(driver.window_handles)
print('Current handles:', len(initial_handles))

for h in initial_handles:
    driver.switch_to.window(h)
    if 'eduptl' in driver.current_url:
        print('Found eduptl! Clicking #1...')
        driver.execute_script("document.getElementById('1').click();")
        break

time.sleep(3)
current_handles = list(driver.window_handles)
print('Current handles after click:', len(current_handles))
for h in current_handles:
    driver.switch_to.window(h)
    print(f'Handle {h}: {driver.title} ({driver.current_url})')
