import subprocess
import os
import sys

def main():
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    profile_path = os.path.join(os.environ["TEMP"], "neis_chrome_profile")
    
    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        "--user-data-dir=" + profile_path,
        "https://gbe.neis.go.kr/jsp/main.jsp"
    ]
    
    print("Launching detached Chrome:", cmd)
    # DETACHED_PROCESS creation flag = 0x00000008
    p = subprocess.Popen(cmd, creationflags=0x00000008, close_fds=True)
    print("Detached process started with PID:", p.pid)

if __name__ == "__main__":
    main()
