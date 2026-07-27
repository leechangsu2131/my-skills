import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException

def main():
    o = Options()
    o.add_experimental_option("debuggerAddress", "localhost:9222")
    
    # We use a try-catch because webdriver initialization itself might fail or succeed 
    # depending on whether the alert blocks the handshake.
    try:
        d = webdriver.Chrome(options=o)
    except Exception as e:
        print(f"Initial connection failed (expected if blocked by alert): {e}")
        # Re-try connection
        time.sleep(1)
        try:
            d = webdriver.Chrome(options=o)
        except Exception as e2:
            print(f"Second connection attempt failed: {e2}")
            return

    print("Connected to Chrome. Dismissing any system alerts...")
    
    # Loop to dismiss all active system alerts
    dismissed_count = 0
    for _ in range(5):
        try:
            alert = d.switch_to.alert
            text = alert.text
            print(f"  Dismissing alert: '{text}'")
            alert.accept()
            dismissed_count += 1
            time.sleep(1)
        except NoAlertPresentException:
            break
        except Exception as e:
            # Handle selenium's internal handling of unexpected alert open
            print(f"  Note during dismiss: {e}")
            break
            
    print(f"Alert cleanup completed. Dismissed {dismissed_count} alerts.")

if __name__ == "__main__":
    main()
