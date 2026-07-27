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

JS_FIND_MAIN_AND_NAV = """
// 현재 실행 중인 앱 인스턴스들 나열
var apps = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
var appList = apps.map(function(ai) {
    return {
        appId: ai.app ? ai.app.id : null,
        title: ai.title || ""
    };
});

// 동아리활동관리(m07) 메인 앱 찾기
var main = apps.find(function(ai) {
    return ai.app && ai.app.id === "edu/sw/els/sdl/ce/els_sdlce01_m07";
});

// 해당 화면에서 사용 가능한 데이터셋 확인
var mainDatasets = [];
if (main) {
    main.getAllDataControls().forEach(function(ds) {
        mainDatasets.push({
            id: ds.id,
            type: ds.type,
            rowCount: ds.getRowCount ? ds.getRowCount() : null
        });
    });
}

return {
    appList: appList,
    hasM07: !!main,
    mainDatasets: mainDatasets
};
"""

try:
    res = driver.execute_script(JS_FIND_MAIN_AND_NAV)
    print("APP STATE:")
    print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
    print("Error:", e)

driver.quit()
