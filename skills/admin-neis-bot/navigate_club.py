import io, sys, time, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

driver_path = r"C:\Users\lee21\.cache\selenium\chromedriver\win64\150.0.7871.115\chromedriver.exe"
service = Service(executable_path=driver_path)

opts = Options()
opts.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(service=service, options=opts)

# Find target window
target_handle = None
for handle in driver.window_handles:
    driver.switch_to.window(handle)
    driver.switch_to.default_content()
    try:
        if driver.execute_script("return typeof cpr !== 'undefined';") and "vpn" not in driver.current_url.lower():
            target_handle = handle
            break
    except: pass

if not target_handle:
    print("Error: Target window not found.")
    driver.quit()
    sys.exit(1)

# 동아리활동관리 화면 메뉴 클릭 
JS_NAVIGATE = """
// 왼쪽 메뉴에서 동아리활동관리 텍스트 찾아 클릭
var menuItems = document.querySelectorAll('.cl-tree-label, .cl-menu-item, .cl-menuitem, a, li, span');
var foundMenu = null;
var menuTexts = [];

menuItems.forEach(function(el) {
    var text = el.textContent.trim();
    if (text === "동아리활동관리" && el.offsetWidth > 0) {
        menuTexts.push({text: text, tag: el.tagName, className: el.className.substring(0,60)});
        if (!foundMenu) foundMenu = el;
    }
});

if (foundMenu) {
    foundMenu.click();
    return {clicked: true, text: foundMenu.textContent.trim(), menuTexts: menuTexts};
}

return {clicked: false, menuTexts: menuTexts.slice(0, 10), error: "메뉴를 찾지 못했습니다"};
"""

try:
    res = driver.execute_script(JS_NAVIGATE)
    print("NAVIGATION RESULT:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

time.sleep(4.0)
driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved.")
driver.quit()
