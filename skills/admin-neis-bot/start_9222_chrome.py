#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import time

def main():
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    profile_dir = r"C:\Users\lee21\AppData\Local\Temp\neis_chrome_profile_9222"
    url = "https://evpn.gbe.kr"
    
    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        url
    ]
    print("Launching:", cmd)
    proc = subprocess.Popen(cmd)
    print("PID:", proc.pid)
    time.sleep(2)

if __name__ == "__main__":
    main()
