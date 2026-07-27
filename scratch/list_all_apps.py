from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=opts)
    
    handles = driver.window_handles
    print(f"Active handles: {handles}")
    for h in handles:
        driver.switch_to.window(h)
        print(f"\nWindow: {driver.title} ({h})")
        print(f"  URL: {driver.current_url}")
        
        # Main frame
        driver.switch_to.default_content()
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                apps = driver.execute_script("return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai => ai.app.id);")
                print(f"  Main frame apps: {apps}")
            else:
                print("  Main frame has no cpr.")
        except Exception as e:
            print(f"  Main frame exception: {e}")
            
        try:
            frames = driver.find_elements(by="tag name", value="iframe")
            print(f"  Found {len(frames)} iframes")
            for i, f in enumerate(frames):
                fid = f.get_attribute("id") or f.get_attribute("name") or f"index_{i}"
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(f)
                    has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
                    if has_cpr:
                        apps = driver.execute_script("return cpr.core.Platform.INSTANCE.getAllRunningAppInstances().map(ai => ai.app.id);")
                        print(f"    Frame '{fid}' apps: {apps}")
                    else:
                        print(f"    Frame '{fid}' has no cpr.")
                except Exception as e:
                    print(f"    Frame '{fid}' exception: {e}")
        except Exception as e:
            print(f"  iframe loop exception: {e}")

if __name__ == "__main__":
    main()
