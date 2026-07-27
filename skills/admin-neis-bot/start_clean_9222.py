#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import time
from pathlib import Path

def main():
    os.system("taskkill /f /im chrome.exe /t 2>nul")
    time.sleep(1)
    
    profile_dir = Path(r"C:\Users\lee21\AppData\Local\Temp\neis_chrome_profile_9222")
    if profile_dir.exists():
        lock = profile_dir / "SingletonLock"
        if lock.exists():
            try: lock.unlink()
            except Exception as e: print("Lock unlink error:", e)
            
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    url = "https://evpn.gbe.kr"
    
    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_dir}",
        url
    ]
    subprocess.Popen(cmd)
    print("Launched clean 9222 Chrome")

if __name__ == "__main__":
    main()
