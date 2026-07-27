import subprocess
import os
import time

def main():
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    profile_path = os.path.join(os.environ["TEMP"], "edge_debug_profile")
    
    cmd = [
        edge_path,
        "--remote-debugging-port=9222",
        "--user-data-dir=" + profile_path,
        "https://gbe.neis.go.kr/jsp/main.jsp"
    ]
    print("Launching Edge:", cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("PID:", p.pid)
    time.sleep(5)
    poll = p.poll()
    print("Poll status:", poll)
    if poll is None:
        print("Edge is still running!")
    else:
        stdout, stderr = p.communicate()
        print("STDOUT:", stdout)
        print("STDERR:", stderr)

if __name__ == "__main__":
    main()
