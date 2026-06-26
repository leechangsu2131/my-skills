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
        
    for h in d.window_handles:
        try:
            d.switch_to.window(h)
            res = d.execute_script("""
                var btns = document.querySelectorAll('button, [role="button"]');
                var clicked = false;
                for (var i = 0; i < btns.length; i++) {
                    var text = (btns[i].innerText || "").trim();
                    if (text === "확인" || text === "OK" || text === "예") {
                        btns[i].click();
                        clicked = true;
                    }
                }
                return clicked;
            """)
            if res:
                print(f"Clicked confirm modal in window '{d.title}': {res}")
        except Exception:
            pass

if __name__ == "__main__":
    main()
