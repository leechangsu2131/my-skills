from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=o)
    
    js = """
        const platform = window.cpr && cpr.core && cpr.core.Platform && cpr.core.Platform.INSTANCE;
        const app = platform.getAllRunningAppInstances().find(ai => ai.app && ai.app.id.includes('scres20_m00'));
        const ds = app.lookup('dsStdnt');
        return ds.getValue(0, 'stdntNm');
    """
    s = driver.execute_script(js)
    print("Type of s:", type(s))
    print("Value of s representation:", repr(s))
    print("Code points:", [hex(ord(c)) for c in s])

if __name__ == "__main__":
    main()
