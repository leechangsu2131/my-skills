import subprocess
import os
import time

def main():
    cmd = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--remote-debugging-port=9222",
        "--user-data-dir=" + os.path.join(os.environ["TEMP"], "neis_chrome_profile"),
        "https://gbe.neis.go.kr/jsp/main.jsp"
    ]
    print("Launching cmd:", cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("PID:", p.pid)
    time.sleep(5)
    poll = p.poll()
    print("Poll status (None means running, otherwise exit code):", poll)
    
    # Read output
    stdout, stderr = p.communicate(timeout=2)
    print("--- STDOUT ---")
    print(stdout)
    print("--- STDERR ---")
    print(stderr)

if __name__ == "__main__":
    main()
