#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import time
import socket
from pathlib import Path

def is_port_open(port=9222):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        s.connect(('127.0.0.1', port))
        s.close()
        return True
    except Exception:
        return False

def main():
    print("[1] 모든 Chrome 프로세스 완전히 종료 중...")
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    time.sleep(2)

    local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\lee21\AppData\Local")
    lock_file = Path(local_app_data) / "Google" / "Chrome" / "User Data" / "SingletonLock"
    
    print("[2] SingletonLock 찌꺼기 파일 삭제...")
    if lock_file.exists():
        try:
            lock_file.unlink()
            print("  ✓ SingletonLock 삭제 성공")
        except Exception as e:
            print(f"  ⚠ SingletonLock 삭제 에러: {e}")

    chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = rf"{local_app_data}\Google\Chrome\User Data"
    url = "https://evpn.gbe.kr"

    print("[3] Chrome 9222 디버깅 포트로 시작...")
    cmd = [
        chrome_exe,
        "--remote-debugging-port=9222",
        "--remote-debugging-address=127.0.0.1",
        f"--user-data-dir={user_data_dir}",
        "--new-window",
        url
    ]
    
    subprocess.Popen(cmd)

    print("[4] 9222 디버깅 포트 활성화 여부 확인 중...")
    for i in range(15):
        time.sleep(1)
        if is_port_open(9222):
            print(f"\n  🎉 [성공] Port 9222 가 정상적으로 열렸습니다! ({i+1}초 소요)")
            print("  이제 브라우저에서 EVPN 및 나이스 로그인을 진행하시면 됩니다.")
            return True
        print(f"  ... 대기 중 ({i+1}/15초)")

    print("\n  ❌ [오류] Port 9222 활성화에 실패했습니다.")
    return False

if __name__ == "__main__":
    main()
