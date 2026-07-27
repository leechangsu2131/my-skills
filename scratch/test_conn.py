import sys, os
os.environ['WDM_LOCAL'] = '1'
print("Importing selenium...")
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
print("Initializing webdriver...")
opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
try:
    driver = webdriver.Chrome(options=opts)
    print("Connected! Title:", driver.title)
    driver.quit()
except Exception as e:
    print("Error:", e)
print("Done.")
