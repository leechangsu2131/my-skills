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

# 1. 브라우저 네이티브 Alert/Confirm 다이얼로그 처리 (안전장치)
alert_handled = False
try:
    alert = driver.switch_to.alert
    print(f"Native alert found: {alert.text}")
    alert.accept()
    alert_handled = True
    print("Native alert accepted.")
except Exception as e:
    print("No native alert at start:", e)

# 2. cl-dialog ("저장하시겠습니까?") 수락 클릭
JS_CLICK_DIALOG = """
var clicked = false;
var buttons = document.querySelectorAll('.cl-dialog .cl-button, .cl-dialog button, button');
var found = [];
buttons.forEach(function(b) {
    var txt = b.textContent.trim();
    found.push(txt);
    if (txt === "확인" || txt === "예" || txt === "OK") {
        b.click();
        clicked = true;
    }
});
return {clicked: clicked, foundButtons: found};
"""

try:
    res = driver.execute_script(JS_CLICK_DIALOG)
    print("Click first dialog result:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error clicking first dialog:", e)

# 3. 저장 완료 다이얼로그가 뜨기를 대기 (1.5초)
time.sleep(1.5)

try:
    res2 = driver.execute_script(JS_CLICK_DIALOG)
    print("Click second dialog result:")
    print(json.dumps(res2, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error clicking second dialog:", e)

driver.save_screenshot("scratch/screenshot.png")
print("Screenshot saved to scratch/screenshot.png")
driver.quit()
