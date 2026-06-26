import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

REMOTE_PORT = 9222

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    
    # We are switching tabs, which is in the main window (outer scope of the app)
    # Let's switch to the main NEIS window
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
    
    print(f"Active window: {driver.title}")
    
    # Find the tab item containing "교과학습발달상황"
    xpath = "//*[contains(text(), '교과학습발달상황')]"
    elements = driver.find_elements(By.XPATH, xpath)
    print(f"Found {len(elements)} elements containing '교과학습발달상황'")
    
    clicked = False
    for idx, el in enumerate(elements):
        try:
            text = el.text
            tag = el.tag_name
            class_name = el.get_attribute("class")
            print(f"  [{idx}] Tag: {tag}, Class: {class_name}, Text: '{text}'")
            
            # We want to click the tab button. Usually it has a class like 'cl-tabfolder-item' or is clickable.
            # Let's click it.
            driver.execute_script("arguments[0].click();", el)
            print(f"  Successfully clicked element {idx}")
            clicked = True
            break
        except Exception as e:
            print(f"  Failed to click element {idx}: {e}")
            
    if clicked:
        time.sleep(2)
        screenshot_path = "scratch/after_tab_switch.png"
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
    else:
        print("Could not click any tab element")

if __name__ == "__main__":
    main()
