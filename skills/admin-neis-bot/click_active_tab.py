import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

REMOTE_PORT = 9222

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    
    handles = driver.window_handles
    target_handle = None
    for handle in handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        if "경상북도교육청" in driver.title or "나이스" in driver.title or "시스템" in driver.title:
            target_handle = handle
            break
            
    if not target_handle:
        print("Could not find NEIS window")
        return
        
    driver.switch_to.window(target_handle)
    driver.switch_to.default_content()
    
    # Find all elements containing text "교과학습발달상황"
    elements = driver.find_elements(By.XPATH, "//*[contains(text(), '교과학습발달상황')]")
    print(f"Found {len(elements)} elements")
    
    clicked = False
    for idx, el in enumerate(elements):
        try:
            if el.is_displayed():
                print(f"Clicking visible element [{idx}] (Tag: {el.tag_name}, Class: {el.get_attribute('class')})")
                driver.execute_script("arguments[0].click();", el)
                print("Clicked successfully!")
                clicked = True
                break
        except Exception as e:
            print(f"Failed to click [{idx}]: {e}")
            
    if clicked:
        time.sleep(3)
        screenshot_path = "scratch/current_screen.png"
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
    else:
        print("No visible tab element found to click")

if __name__ == "__main__":
    main()
