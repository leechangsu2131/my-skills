#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import time
import os
from pathlib import Path
import urllib.request

def launch_and_verify():
    print("[1] 기존 크롬 프로세스 전면 강제 종료...")
    subprocess.run(["taskkill", "/f", "/im", "chrome.exe"], capture_output=True)
    time.sleep(2)

    local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\lee21\AppData\Local")
    lock_file = Path(local_app_data) / "Google" / "Chrome" / "User Data" / "SingletonLock"
    
    print("[2] SingletonLock 파일 제거...")
    if lock_file.exists():
        try:
            lock_file.unlink()
            print("  ✓ SingletonLock 삭제 성공")
        except Exception as e:
            print(f"  ⚠ 삭제 예외: {e}")

    chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = rf"{local_app_data}\Google\Chrome\User Data"
    url = "https://evpn.gbe.kr"

    print("[3] 디버깅 포트(9222)로 크롬 런칭...")
    cmd = [
        chrome_exe,
        "--remote-debugging-port=9222",
        "--remote-debugging-address=127.0.0.1",
        f"--user-data-dir={user_data_dir}",
        "--new-window",
        url
    ]
    
    subprocess.Popen(cmd)
    
    # 9222 포트 활성화 될 때까지 최대 10초 대기 검증
    print("[4] 포트 9222 바인딩 검증 중...")
    for i in range(10):
        time.sleep(1)
        try:
            res = urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=1)
            if res.status == 200:
                print("  ✅ [검증 성공] 9222 포트 원격 디버깅 활성화 확인!")
                return True
        except Exception:
            pass
        print(f"  ... 대기 중 ({i+1}/10)")
        
    print("  ❌ [실패] 9222 포트가 활성화되지 않았습니다.")
    return False

if __name__ == "__main__":
    launch_and_verify()
