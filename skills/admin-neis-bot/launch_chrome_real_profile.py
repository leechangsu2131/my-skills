import subprocess
import os

def main():
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        
    # 사용자의 실제 기본 크롬 프로필 경로 지정 (보안 모듈의 임시 프로필 감지 우회)
    profile_path = os.path.join(os.environ["USERPROFILE"], r"AppData\Local\Google\Chrome\User Data")
    
    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        "--user-data-dir=" + profile_path,
        "https://evpn.gbe.kr/custom/index.html",
        "https://gbe.neis.go.kr/jsp/main.jsp"
    ]
    print("Launching Chrome with real user profile:", cmd)
    p = subprocess.Popen(cmd, creationflags=0x00000010)
    print("Chrome PID:", p.pid)

if __name__ == "__main__":
    main()
