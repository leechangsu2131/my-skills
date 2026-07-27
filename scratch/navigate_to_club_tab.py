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

# 하단 탭에서 동아리활동관리 탭 찾아 클릭
JS_CLICK_CLUB_TAB = """
// 하단 탭바에서 동아리활동관리 탭 찾아 클릭하기
var tabItems = document.querySelectorAll('.cl-tabfolder-item');
var foundTab = null;
var tabTexts = [];

tabItems.forEach(function(tab) {
    var text = tab.textContent.trim();
    tabTexts.push(text);
    if (text.indexOf("동아리활동관리") !== -1 && !tab.classList.contains("unable-to-close")) {
        foundTab = tab;
    }
});

if (foundTab) {
    foundTab.click();
    return {clicked: true, text: foundTab.textContent.trim(), allTabs: tabTexts};
}

return {clicked: false, allTabs: tabTexts, error: "동아리활동관리 tab not found"};
"""

try:
    res = driver.execute_script(JS_CLICK_CLUB_TAB)
    print("TAB CLICK RESULT:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

# 탭이 활성화될 때까지 대기
time.sleep(3.0)

# 이제 동아리 관리 화면에서 누가기록 열기 시도
JS_OPEN_CLUB_MANAGEMENT = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (!main) return {error: "동아리활동관리(m07) not found"};

// 조회 버튼 클릭
var btnSearch = main.lookup("btnSearch");
if (btnSearch) {
    btnSearch.click();
}

return {found: true};
"""

try:
    res2 = driver.execute_script(JS_OPEN_CLUB_MANAGEMENT)
    print("MAIN SEARCH RESULT:", res2)
except Exception as e:
    print("Error:", e)

time.sleep(4.0)
driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved.")
driver.quit()
