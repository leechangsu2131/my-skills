import sys, os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

driver_path = r"C:\Users\lee21\.cache\selenium\chromedriver\win64\150.0.7871.115\chromedriver.exe"
print("Using chromedriver:", driver_path)
service = Service(executable_path=driver_path)

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")

try:
    driver = webdriver.Chrome(service=service, options=opts)
    print("Connected successfully! Title:", driver.title)
    driver.quit()
except Exception as e:
    print("Error:", e)
print("Done.")
