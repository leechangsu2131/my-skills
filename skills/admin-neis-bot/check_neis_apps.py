import io, sys, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os_env = __import__('os')
os_env.environ['no_proxy'] = 'localhost,127.0.0.1'

opts = Options()
opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=opts)

for handle in driver.window_handles:
    driver.switch_to.window(handle)
    if "neis.go.kr" in driver.current_url:
        print(f"Connected to NEIS tab: {driver.title} ({driver.current_url})")
        break

apps = driver.execute_script("""
    if (typeof cpr === 'undefined') return {error: "cpr not defined"};
    var platform = cpr.core.Platform.INSTANCE;
    return platform.getAllRunningAppInstances().map(a => ({
        id: a.id,
        appId: a.app ? a.app.id : null,
        title: a.app ? a.app.title : null
    }));
""")
print("Running NEIS apps:", json.dumps(apps, ensure_ascii=False, indent=2))
