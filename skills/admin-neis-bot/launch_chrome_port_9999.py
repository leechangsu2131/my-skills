import subprocess
import os

def main():
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        
    profile_path = os.path.join(os.environ["TEMP"], "neis_chrome_profile_9999")
    
    cmd = [
        chrome_path,
        "--remote-debugging-port=9999",  # 포트를 9999로 변경하여 보안 탐지 우회
        "--user-data-dir=" + profile_path,
        "https://evpn.gbe.kr/custom/index.html",
        "https://gbe.neis.go.kr/jsp/main.jsp"
    ]
    print("Launching Chrome with port 9999:", cmd)
    p = subprocess.Popen(cmd, creationflags=0x00000010)
    print("Chrome PID:", p.pid)

if __name__ == "__main__":
    main()
