#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
학교 전용 나이스 원격 디버깅 크롬 런처 (port 9222)
"""
import os
import sys
import time
import subprocess
from pathlib import Path

def main():
    print("[1/3] 백그라운드 Chrome 프로세스를 완전히 정리 중...")
    os.system("wmic process where name='chrome.exe' delete 2>nul")
    os.system("taskkill /f /im chrome.exe /t 2>nul")
    time.sleep(1.5)

    temp_dir = os.environ.get("TEMP", r"C:\Users\user\AppData\Local\Temp")
    profile_dir = Path(temp_dir) / "neis_chrome_profile_9222"
    profile_dir.mkdir(parents=True, exist_ok=True)
    lock_file = profile_dir / "SingletonLock"

    print("[2/3] 디버깅 프로필 싱글톤 락 파일 제거 중...")
    if lock_file.exists():
        try:
            lock_file.unlink()
            print("  ✓ SingletonLock 삭제 성공")
        except Exception as e:
            print("  ⚠ SingletonLock 삭제 제외:", e)

    chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    url = "https://gbe.neis.go.kr"

    print(f"[3/3] Chrome 9222 원격 디버깅 모드 기동 중: {url}")
    cmd = [
        chrome_exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        url
    ]

    proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0)
    time.sleep(2)
    print(f"[OK] Chrome 9222 기동 완료 (PID: {proc.pid})")

if __name__ == "__main__":
    main()
