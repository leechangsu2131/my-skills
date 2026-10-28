"""로그인 테스트 스크립트"""
from dotenv import load_dotenv
import os, time
load_dotenv()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

ID = os.getenv("INDISCHOOL_ID")
PW = os.getenv("INDISCHOOL_PW")
print(f"ID 확인: {ID[:2]}***" if ID else "ID 없음 — .env 확인")
print(f"PW 확인: ****" if PW else "PW 없음 — .env 확인")

if not ID or not PW:
    exit(1)

options = Options()
options.add_argument("--window-size=1280,900")
# headless 없음 — 브라우저 보이게
driver = webdriver.Chrome(options=options)

try:
    driver.get("https://indischool.com/login")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "username")))
    print("로그인 페이지 도달 완료")
    
    driver.find_element(By.ID, "username").send_keys(ID)
    driver.find_element(By.ID, "password").send_keys(PW)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(4)
    
    current_url = driver.current_url
    print(f"로그인 후 URL: {current_url}")
    
    if "/login" not in current_url:
        print("✅ 로그인 성공!")
        # 검색 테스트
        driver.get("https://indischool.com/search?query=감각적+표현&page=1")
        time.sleep(3)
        print(f"검색 후 URL: {driver.current_url}")
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/boards/']")
        print(f"수집된 링크 수: {len(links)}개")
        for link in links[:5]:
            print(f"  • {link.text.strip()[:60]} → {link.get_attribute('href')}")
    else:
        print("❌ 로그인 실패 — 비번 또는 아이디 확인")
    
    time.sleep(5)
finally:
    driver.quit()
