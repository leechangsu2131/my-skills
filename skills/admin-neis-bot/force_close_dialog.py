import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    try:
        d = webdriver.Chrome(options=o)
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # Find NEIS window
    found_handle = None
    for h in d.window_handles:
        try:
            d.switch_to.window(h)
            has_cpr = d.execute_script("return typeof cpr !== 'undefined';")
            if has_cpr:
                found_handle = h
                break
        except Exception:
            pass

    if not found_handle:
        print("NEIS window not found.")
        return

    print(f"Connected to NEIS: {d.title}")

    # Force click script trying multiple strategies
    force_script = """
    var clicked = [];
    
    // Strategy 1: raw DOM buttons with '확인'
    var btns = document.querySelectorAll('button, [role="button"], .kc-btn-blue, .cl-button');
    for (var i = 0; i < btns.length; i++) {
        var text = (btns[i].innerText || "").trim();
        if (text === "확인" || text === "OK" || text === "예") {
            try {
                btns[i].click();
                clicked.push("DOM Button click: " + text);
            } catch(e) {}
        }
    }
    
    // Strategy 2: any DOM element containing text '확인' that looks like a button
    var all = document.getElementsByTagName("*");
    for (var i = 0; i < all.length; i++) {
        var text = (all[i].innerText || "").trim();
        var cl = all[i].className || "";
        if (text === "확인" && (cl.indexOf("btn") >= 0 || cl.indexOf("button") >= 0 || cl.indexOf("control") >= 0 || cl.indexOf("text") >= 0)) {
            try {
                all[i].click();
                clicked.push("DOM Element click: " + all[i].tagName + "." + cl);
            } catch(e) {}
        }
    }
    
    // Strategy 3: eXBuilder framework confirmApp
    try {
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var confirmApp = instances.find(ai => ai.app && (ai.app.id === "app/cmn/confirm" || ai.app.id === "app/cmn/alert"));
        if (confirmApp) {
            var container = confirmApp.getContainer();
            if (container) {
                function findAndClick(ctrl) {
                    if (!ctrl) return;
                    var val = ctrl.value || ctrl.text || "";
                    var id = ctrl.id || "";
                    if (id === "btnOk" || id === "btnConfirm" || val === "확인" || val === "예") {
                        if (typeof ctrl.click === 'function') {
                            ctrl.click();
                            clicked.push("eXBuilder App control click: " + id + "(" + val + ")");
                        }
                    }
                    if (typeof ctrl.getChildren === 'function') {
                        var children = ctrl.getChildren();
                        for (var j = 0; j < children.length; j++) {
                            findAndClick(children[j]);
                        }
                    }
                }
                findAndClick(container);
            }
        }
    } catch(e) {
        clicked.push("Framework error: " + e.message);
    }
    
    return clicked;
    """
    
    res = d.execute_script(force_script)
    print("\n=== Force Click Results ===")
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
