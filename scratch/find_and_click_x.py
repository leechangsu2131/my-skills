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

JS_FIND_AND_CLICK_X = """
var elements = [];
// close 단어가 포함된 클래스를 가진 엘리먼트 수집
document.querySelectorAll('[class*="close"], [id*="close"], .cl-dialog-close, button').forEach(function(el) {
    if (el.offsetWidth > 0) {
        elements.push({
            tagName: el.tagName,
            id: el.id,
            className: el.className,
            text: el.textContent.trim()
        });
    }
});

// X 버튼 찾아서 강제 클릭 시도
var clicked = false;
var xBtn = document.querySelector('.cl-dialog-close');
if (xBtn) {
    xBtn.click();
    clicked = true;
} else {
    // 대체 닫기 기법들
    var closeIcons = document.querySelectorAll('.cl-dialog-close, [class*="dialog-close"], [class*="dialog_close"]');
    if (closeIcons.length > 0) {
        closeIcons[0].click();
        clicked = true;
    }
}

// 만약 여전히 안 닫혔다면, appInstance.close() 실행
if (!clicked) {
    var pop = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
        return ai && ai.app && ai.app.id.indexOf("p11") !== -1;
    });
    if (pop && pop.close) {
        pop.close();
        clicked = "pop.close() called";
    }
}

return {clicked: clicked, elements: elements};
"""

try:
    res = driver.execute_script(JS_FIND_AND_CLICK_X)
    print("CLOSE X RESULT:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

# 메인 화면 조회를 위함
time.sleep(2.0)
JS_REFRESH = """
var main = cpr.core.Platform.INSTANCE.getAllRunningAppInstances().find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});
if (main) {
    var btnSearch = main.lookup("btnSearch");
    if (btnSearch) {
        btnSearch.click();
        return "Search clicked";
    }
}
return "Main search button not found";
"""

try:
    res2 = driver.execute_script(JS_REFRESH)
    print("Main refresh initiated:", res2)
except Exception as e:
    print("Error:", e)

time.sleep(4.0)
driver.save_screenshot("scratch/screenshot.png")
print("Verification screenshot saved.")
driver.quit()
