import io, sys, time, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

driver_path = r"C:\Users\cache\selenium\chromedriver\win64\150.0.7871.115\chromedriver.exe"
# 실제 드라이버 경로는 이전 파이썬 파일의 것을 사용합니다.
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

JS_INTERACT = """
var buttonsInfo = [];
document.querySelectorAll('.cl-button, .cl-dialog-body .cl-button, button').forEach(function(el) {
    if (el.offsetWidth > 0) {
        buttonsInfo.push({
            text: el.textContent.trim(),
            className: el.className,
            tagName: el.tagName
        });
    }
});

// "확인" 버튼 클릭 시도
var clicked = false;
var buttons = document.querySelectorAll('.cl-button, button');
for (var i=0; i<buttons.length; i++) {
    var btn = buttons[i];
    var txt = btn.textContent.trim();
    if (txt === "확인" || txt === "예" || txt === "OK") {
        btn.click();
        clicked = true;
        break;
    }
}

return {
    clicked: clicked,
    foundButtons: buttonsInfo
};
"""

try:
    res = driver.execute_script(JS_INTERACT)
    print("INTERACT RESULT:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

# 2초 대기하여 "저장되었습니다" 팝업이 뜨는지 확인
time.sleep(2.0)

try:
    res2 = driver.execute_script(JS_INTERACT)
    print("SECOND INTERACT RESULT:")
    print(json.dumps(res2, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

driver.save_screenshot("scratch/screenshot.png")
driver.quit()
