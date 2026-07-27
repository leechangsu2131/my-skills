@echo off
taskkill /f /im chrome.exe /t 2>nul
timeout /t 1 /nobreak >nul
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\neis_chrome_profile_9222" https://evpn.gbe.kr
