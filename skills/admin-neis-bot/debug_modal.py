import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    d = webdriver.Chrome(options=o)
    
    # 1. Inspect running app instances (dialogs might be registered as sub-apps)
    app_info = d.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        return instances.map(function(ai) {
            return {
                id: ai.app ? ai.app.id : "no-app",
                title: ai.title || "",
                controls: ai.getAllDataControls ? ai.getAllDataControls().map(c => c.id) : []
            };
        });
    """)
    print("\n=== Active App Instances ===")
    print(json.dumps(app_info, ensure_ascii=False, indent=2))
    
    # 2. Inspect DOM elements containing "확인" or "저장"
    dom_info = d.execute_script("""
        var elements = document.getElementsByTagName("*");
        var matched = [];
        for (var i = 0; i < elements.length; i++) {
            var el = elements[i];
            var text = (el.innerText || "").trim();
            if (text === "확인" || text === "저장하시겠습니까?") {
                // Return tag, classes, id, attributes
                var attrs = {};
                for (var j = 0; j < el.attributes.length; j++) {
                    attrs[el.attributes[j].name] = el.attributes[j].value;
                }
                matched.push({
                    tag: el.tagName,
                    text: text,
                    id: el.id || "",
                    className: el.className || "",
                    attributes: attrs
                });
            }
        }
        return matched.slice(0, 30);
    """)
    print("\n=== Matched DOM Elements ===")
    print(json.dumps(dom_info, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
