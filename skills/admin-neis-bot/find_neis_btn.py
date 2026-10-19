import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

os.environ['no_proxy'] = 'localhost,127.0.0.1'
opts = Options()
opts.add_experimental_option('debuggerAddress', '127.0.0.1:9222')
driver = webdriver.Chrome(options=opts)

for h in driver.window_handles:
    driver.switch_to.window(h)
    if 'eduptl' in driver.current_url:
        elems = driver.find_elements('xpath', '//*[contains(text(), "나이스") or contains(@alt, "나이스") or contains(@title, "나이스")]')
        for el in elems:
            print(f'Tag: {el.tag_name}, id: {el.get_attribute("id")}, class: {el.get_attribute("class")}, onclick: {el.get_attribute("onclick")}, href: {el.get_attribute("href")}, text: {el.text}')
