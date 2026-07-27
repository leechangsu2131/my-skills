from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import time

REMOTE_PORT = 9222

JS_FIND_APP = """
    var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
    var inst = instances.find(ai => ai.app && ai.app.id.includes("scres10_m00"));
    if (!inst) return {error: "App instance scres10_m00 not found"};
"""

def main():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=opts)
    
    handles = driver.window_handles
    target_handle = None
    target_frame = None
    for handle in handles:
        driver.switch_to.window(handle)
        driver.switch_to.default_content()
        try:
            has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                app_info = driver.execute_script(JS_FIND_APP + "return {ok: true, appId: inst.app.id};")
                if "ok" in app_info:
                    target_handle = handle
                    target_frame = None
                    break
        except Exception:
            pass

        frames = driver.find_elements(by="tag name", value="iframe")
        for i, frame in enumerate(frames):
            fid = frame.get_attribute("id") or frame.get_attribute("name") or f"index_{i}"
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                has_cpr = driver.execute_script("return typeof cpr !== 'undefined';")
                if has_cpr:
                    app_info = driver.execute_script(JS_FIND_APP + "return {ok: true, appId: inst.app.id};")
                    if "ok" in app_info:
                        target_handle = handle
                        target_frame = fid
                        break
            except Exception:
                pass
        if target_handle:
            break
            
    if not target_handle:
        print("Could not find NEIS app window/frame")
        return
        
    driver.switch_to.window(target_handle)
    driver.switch_to.default_content()
    if target_frame:
        frames = driver.find_elements(by="tag name", value="iframe")
        for frame in frames:
            if frame.get_attribute("id") == target_frame or frame.get_attribute("name") == target_frame:
                driver.switch_to.frame(frame)
                break
                
    # Switch to 도덕: '0121621010102:0001000007:10048'
    osu_cd = "0121621010102:0001000007:10048"
    print(f"Switching subject to 도덕 (value: {osu_cd})")
    
    switch_res = driver.execute_script(JS_FIND_APP + f"""
        var udc = inst.lookup("udcSbjt");
        if (!udc) return {{error: "udcSbjt not found"}};
        
        var emb = udc.getEmbeddedAppInstance();
        var cmb = emb.lookup("cmbUdcAuth");
        if (!cmb) return {{error: "cmbUdcAuth not found"}};
        
        // Revert any unsaved changes in dsMain to prevent block
        var ds = inst.lookup("dsMain");
        if (ds && ds.isModified && ds.isModified()) {{
            ds.revert();
        }}
        
        cmb.selectItemByValue("{osu_cd}", true);
        return {{ok: true, selection: cmb.getSelectionFirst() ? cmb.getSelectionFirst().label : "none"}};
    """)
    print("Switch result:", switch_res)
    
    # Wait for subject switch to bind and refresh
    time.sleep(3)
    
    # Click search button
    search_res = driver.execute_script(JS_FIND_APP + """
        var btn = inst.lookup("btnSearch");
        if (!btn) return {error: "btnSearch not found"};
        btn.click();
        return {ok: true};
    """)
    print("Search click result:", search_res)
    
    # Wait for search data to load
    time.sleep(3)
    
    # Verify the current active subject and student 0 in dsMain
    verify_res = driver.execute_script(JS_FIND_APP + """
        var ds = inst.lookup("dsMain");
        if (!ds) return {error: "dsMain not found"};
        if (ds.getRowCount() === 0) return {error: "dsMain has 0 rows"};
        
        return {
            rowCount: ds.getRowCount(),
            subjectVal: inst.lookup("udcSbjt").getValue(),
            subjectText: inst.lookup("udcSbjt").getText(),
            firstStudentName: ds.getValue(0, "stdntNm"),
            firstStudentSubject: ds.getValue(0, "sbjtCdNm")
        };
    """)
    
    # Decode string values to prevent terminal printing issues
    def decode_cpr_str(s: str) -> str:
        if not isinstance(s, str):
            return s
        try:
            return s.encode('latin1').decode('euc-kr')
        except Exception:
            return s
            
    decoded_verify = {k: decode_cpr_str(v) for k, v in verify_res.items()}
    print("\nVerification result:")
    print(json.dumps(decoded_verify, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
