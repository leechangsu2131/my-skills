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
    
    # Let's search for ALL elements that have the text "교과학습발달상황"
    # and print their tag, class, parent info, and see if they are displayed.
    elements = driver.find_elements(By.XPATH, "//*[contains(text(), '교과학습발달상황')]")
    print(f"Total elements found: {len(elements)}")
    
    for idx, el in enumerate(elements):
        try:
            tag = el.tag_name
            class_name = el.get_attribute("class") or ""
            text = el.text
            displayed = el.is_displayed()
            
            # Get parent element info
            parent = driver.execute_script("return arguments[0].parentElement;", el)
            parent_tag = parent.tag_name if parent else "None"
            parent_class = parent.get_attribute("class") if parent else ""
            
            print(f"[{idx}] Tag: {tag} | Class: {class_name} | Text: '{text}' | Displayed: {displayed}")
            print(f"    Parent: Tag={parent_tag} Class={parent_class}")
        except Exception as e:
            print(f"[{idx}] Error: {e}")

if __name__ == "__main__":
    main()
