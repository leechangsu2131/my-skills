import subprocess
import os

def main():
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    profile_path = os.path.join(os.environ["TEMP"], "edge_debug_profile")
    
    cmd = [
        edge_path,
        "--remote-debugging-port=9222",
        "--user-data-dir=" + profile_path,
        "https://gbe.neis.go.kr/jsp/main.jsp"
    ]
    print("Launching detached Edge:", cmd)
    # CREATE_NEW_CONSOLE = 0x00000010
    p = subprocess.Popen(cmd, creationflags=0x00000010)
    print("Edge PID:", p.pid)

if __name__ == "__main__":
    main()
