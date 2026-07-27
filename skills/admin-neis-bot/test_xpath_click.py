import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=o)
    
    driver.switch_to.default_content()
    
    # Check if there are any frames
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for frame in frames:
        fid = frame.get_attribute("id") or frame.get_attribute("name")
        driver.switch_to.default_content()
        driver.switch_to.frame(frame)
        try:
            # Check if this frame has our app
            has_app = driver.execute_script("return typeof cpr !== 'undefined' && cpr.core.Platform.INSTANCE.getAllRunningAppInstances().some(ai => ai.app && ai.app.id.includes('scres20_m00'));")
            if has_app:
                print("Found app in frame:", fid)
                break
        except Exception:
            pass
    else:
        print("Staying in default content")
        driver.switch_to.default_content()

    # Search for element containing '김가을'
    try:
        # Find elements containing text '김가을'
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), '김가을')]")
        print("Found elements matching '김가을':", len(elements))
        for idx, el in enumerate(elements):
            tag = el.tag_name
            text = el.text
            class_name = el.get_attribute("class")
            print(f"  [{idx}] Tag: {tag}, Class: {class_name}, Text: '{text}'")
            
        if elements:
            # Let's click the first one
            print("Clicking element...")
            elements[0].click()
            print("Clicked!")
    except Exception as e:
        print("Error during find/click:", e)
        
    time.sleep(2)
    
    # Check if detail changed
    verify = driver.execute_script("""
        const platform = window.cpr && cpr.core.Platform && cpr.core.Platform.INSTANCE;
        const app = platform.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes('scres20_m00'));
        const ds = app.lookup('dsGnrlzOpinListByYear');
        return {
            rowCount: ds.getRowCount(), 
            studentInDetail: ds.getRowCount() > 0 ? ds.getValue(0, 'stuFlnm') : 'none',
            currentStudentInGrid: app.lookup('grdStdnt').getSelectedRowIndices()
        };
    """)
    print("Verification result:", verify)

if __name__ == "__main__":
    main()
