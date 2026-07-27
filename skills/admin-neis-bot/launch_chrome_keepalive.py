import subprocess
import time
import sys
import os

def main():
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = os.path.join(os.environ.get("TEMP", r"C:\Temp"), "neis_fresh_profile")
    
    # Ensure profile directory exists
    os.makedirs(user_data_dir, exist_ok=True)
    
    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--restore-last-session=false",
        "https://gbe.neis.go.kr/jsp/main.jsp"
    ]
    
    print(f"Launching Chrome: {' '.join(cmd)}")
    
    # Launch Chrome as a subprocess
    process = subprocess.Popen(cmd)
    
    print("Chrome launched. Keeping this task running to prevent Chrome from being closed.")
    print("Press Ctrl+C or kill the task to stop.")
    
    try:
        while True:
            # Check if chrome process is still alive
            status = process.poll()
            if status is not None:
                print(f"Chrome exited with code {status}")
                break
            time.sleep(2)
    except KeyboardInterrupt:
        print("Terminating Chrome...")
        process.terminate()

if __name__ == "__main__":
    main()
