@echo off
title NEIS Dedicated Debug Chrome Launcher (Port 9222)

echo ========================================================
echo  NEIS Dedicated Debug Chrome Launcher (Port 9222)
echo ========================================================
echo.

echo Launching Chrome in Dedicated Debugging Profile (Port 9222)...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\neis_chrome_profile_9222" --new-window "https://evpn.gbe.kr" "https://gbe.eduptl.kr/bpm_man_mn00_001.do"

echo.
echo ========================================================
echo [SUCCESS] Debug Chrome Launched (Port 9222 Active!)
echo Please login to EVPN and NEIS in this opened Chrome window.
echo ========================================================
echo.
pause
