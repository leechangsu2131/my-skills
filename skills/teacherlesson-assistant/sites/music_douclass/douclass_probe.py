"""이미 떠 있는 크롬(원격 디버깅 포트)에 붙어 동아 에듀 수업 자료 페이지에서 차시와 PPT 단추를 찾아 본다(누르지는 않음).

    python douclass_probe.py [--port 9222] [--lesson 1~2차시]

크롬을 --remote-debugging-port=<포트> 로 띄우고 해당 교과서 페이지를 열어 둔 뒤 실행한다. selenium 이 필요하다.
"""
import argparse
import sys

REMOTE_PORT = 9222
TARGET_URL = "https://ele.douclass.com/textbooks/30050/518?arch_id=12553"
TARGET_LESSON = "1~2차시"


def attach(port=REMOTE_PORT):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"localhost:{port}")
    try:
        driver = webdriver.Chrome(options=opts)
        print(f"[OK] Chrome connected: {driver.title}")
        return driver
    except Exception as e:
        print(f"[!] Failed to connect to Chrome on port {port}.")
        return None

def main(argv=None):
    ap = argparse.ArgumentParser(description="떠 있는 크롬에 붙어 동아 에듀 차시·PPT 단추를 찾아 본다(누르지 않음)")
    ap.add_argument("--port", type=int, default=REMOTE_PORT, help="크롬 원격 디버깅 포트(기본 %(default)s)")
    ap.add_argument("--lesson", default=TARGET_LESSON, help="찾을 차시 글(기본 %(default)s)")
    args = ap.parse_args(argv)
    try:
        from selenium.webdriver.common.by import By
    except ImportError:
        print("selenium 이 없어요. pip install selenium", file=sys.stderr)
        return 2
    driver = attach(args.port)
    if not driver:
        return 1
        
    print("\n--- Identifying Login URL ---")
    
    # We saw this in the dump: <a href="https://sign.douclass.com/authlogin/guest_login.donga?returl=https://promotion.douclass.com/pc"
    login_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'sign.douclass.com')]")
    if login_links:
        for link in login_links:
            print(f"Login Link text: '{link.text.strip()}' href: {link.get_attribute('href')}")
            # If we need to login, we can just navigate to this href or click it.
    else:
        print("No login links found. Maybe already logged in?")

    print("\n--- Finding Specific Unit and Lesson ---")
    
    # From the DOM dump, we have elements like:
    # <div class="textbook-chapter-title">
    #   <a href="javascript:void(0)" class="resource-title"><span class="resource-text">[1~2차시] 새 친구들과 함께</span></a>
    # </div>
    # Followed by PPT button:
    # <div class="btnwrap align-right textbook-chapter-btn">
    #   <a href="javascript:void(0)" class="btn btn-pill btn-sm">수업PPT</a>
    
    chapters = driver.find_elements(By.CLASS_NAME, "textbook-chapter")
    print(f"Found {len(chapters)} chapters in the DOM.")
    
    target_lesson = args.lesson
    
    for chapter in chapters:
        try:
            title_el = chapter.find_element(By.CLASS_NAME, "resource-title")
            title_text = title_el.text.strip()
            
            if target_lesson in title_text:
                print(f"\n[FOUND] Match for '{target_lesson}': {title_text}")
                
                # Find PPT buttons within this chapter block
                buttons = chapter.find_elements(By.XPATH, ".//a[contains(@class, 'btn')]")
                for btn in buttons:
                    btn_text = btn.text.strip()
                    print(f"  - Button: '{btn_text}'")
                    if "PPT" in btn_text.upper():
                        print("  => Found PPT button! Clicking it...")
                        # We don't click it yet in this test script
                        
        except Exception as e:
            pass
            

    return 0


if __name__ == "__main__":
    sys.exit(main())
