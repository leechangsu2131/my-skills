#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import time

def main():
    os.system("taskkill /f /im chrome.exe 2>nul")
    time.sleep(1)
    
    cmd = r'"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\neis_chrome_profile_9222" https://evpn.gbe.kr'
    subprocess.Popen(cmd, shell=True)
    print("Direct Chrome Launch Completed")

if __name__ == "__main__":
    main()
