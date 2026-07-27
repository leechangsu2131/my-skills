#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
마스터 크롬 파이썬 런처
======================
배치 파일 인코딩 문제 없이 파이썬으로 크롬 9222 원격 디버깅을 실행합니다.
"""
import os
import subprocess
import time
from pathlib import Path

def main():
    print("[1/3] 기존 크롬 프로세스 강제 종료 중...")
    os.system("taskkill /f /im chrome.exe 2>nul")
    time.sleep(1)

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    lock_file = Path(local_app_data) / "Google" / "Chrome" / "User Data" / "SingletonLock"
    
    print("[2/3] 싱글톤 락 파일 제거 중...")
    if lock_file.exists():
        try:
            lock_file.unlink()
            print("  ✓ SingletonLock 삭제 완료")
        except Exception as e:
            print(f"  ⚠ SingletonLock 삭제 중 예외: {e}")

    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        rf"{local_app_data}\Google\Chrome\Application\chrome.exe"
    ]

    chrome_exe = None
    for p in chrome_paths:
        if os.path.exists(p):
            chrome_exe = p
            break

    if not chrome_exe:
        print("[오류] 크롬 실행 파일(chrome.exe)을 찾을 수 없습니다.")
        return

    temp_dir = os.environ.get("TEMP", r"C:\Users\lee21\AppData\Local\Temp")
    user_data_dir = rf"{temp_dir}\neis_chrome_profile_9222"
    url = "https://evpn.gbe.kr"

    print(f"[3/3] 크롬 디버깅 포트(9222) 실행 중: {chrome_exe}")
    cmd = [
        chrome_exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--new-window",
        url
    ]
    
    subprocess.Popen(cmd)
    print("\n[완료] 크롬이 성공적으로 실행되었습니다.")
    print("열린 크롬 창에서 EVPN 로그인 후 나이스 접속을 진행해 주세요.")

if __name__ == "__main__":
    main()
