import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    d = webdriver.Chrome(options=o)
    
    res = d.execute_script("""
        var instances = cpr.core.Platform.INSTANCE.getAllRunningAppInstances();
        var inst = instances.find(ai => ai.app && ai.app.id === "edu/sw/els/scr/es/els_scres00_m00");
        var ds = inst.lookup("dsMain");
        
        return {
            hasRevert: typeof ds.revert === 'function',
            hasReject: typeof ds.rejectChanges === 'function',
            hasUndo: typeof ds.undo === 'function',
            methods: Object.keys(ds).filter(k => typeof ds[k] === 'function').slice(0, 30)
        };
    """)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
