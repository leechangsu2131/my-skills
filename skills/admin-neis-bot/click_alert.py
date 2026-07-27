from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=opts)
    driver.execute_script("""
        const inst = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(ai => ai.app && ai.app.id === "app/cmn/alert");
        if (inst) {
            console.log("Found alert app, clicking btnConfirm");
            inst.lookup("btnConfirm").click();
        } else {
            console.log("No alert app found");
        }
    """)
    print("Executed alert dismiss script.")

if __name__ == "__main__":
    main()
