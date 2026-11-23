import time
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

REMOTE_PORT = 9222
TARGET_URL = "https://ele.douclass.com/textbooks/30050/518?arch_id=12553"

def attach():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    try:
        driver = webdriver.Chrome(options=opts)
        print(f"[OK] Chrome connected: {driver.title}")
        return driver
    except Exception as e:
        print(f"[!] Failed to connect to Chrome on port {REMOTE_PORT}.")
        return None

def main():
    driver = attach()
    if not driver:
        return
        
    print("\n--- Identifying Login URL ---")
    
    # We saw this in the dump: <a href="https://sign.douclass.com/authlogin/guest_login.donga?returl=https://promotion.douclass.com/pc"
    login_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'sign.douclass.com')]")
    if login_links:
        for link in login_links:
            print(f"Login Link text: '{link.text.strip()}' href: {link.get_attribute('href')}")
            # If we need to login, we can just navigate to this href or click it.
    else:
        print("No login links found. Maybe already logged in?")

    print("\n--- Finding Specific Unit and Lesson ---")
    
    # From the DOM dump, we have elements like:
    # <div class="textbook-chapter-title">
    #   <a href="javascript:void(0)" class="resource-title"><span class="resource-text">[1~2차시] 새 친구들과 함께</span></a>
    # </div>
    # Followed by PPT button:
    # <div class="btnwrap align-right textbook-chapter-btn">
    #   <a href="javascript:void(0)" class="btn btn-pill btn-sm">수업PPT</a>
    
    chapters = driver.find_elements(By.CLASS_NAME, "textbook-chapter")
    print(f"Found {len(chapters)} chapters in the DOM.")
    
    target_lesson = "1~2차시"
    
    for chapter in chapters:
        try:
            title_el = chapter.find_element(By.CLASS_NAME, "resource-title")
            title_text = title_el.text.strip()
            
            if target_lesson in title_text:
                print(f"\n[FOUND] Match for '{target_lesson}': {title_text}")
                
                # Find PPT buttons within this chapter block
                buttons = chapter.find_elements(By.XPATH, ".//a[contains(@class, 'btn')]")
                for btn in buttons:
                    btn_text = btn.text.strip()
                    print(f"  - Button: '{btn_text}'")
                    if "PPT" in btn_text.upper():
                        print("  => Found PPT button! Clicking it...")
                        # We don't click it yet in this test script
                        
        except Exception as e:
            pass
            

if __name__ == "__main__":
    main()
