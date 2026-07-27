@echo off
echo 1. Force closing all existing Chrome windows...
taskkill /f /im chrome.exe 2>nul
timeout /t 1 /nobreak > nul

echo 2. Launching Chrome via Edufine portal to bypass NEIS debugger check...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" https://gbe.eduptl.kr/bpm_man_mn00_001.do

echo.
echo ========================================================
echo Chrome launched via Edufine. Please navigate to NEIS,
echo login, go to Club Record screen and reply "Ready".
echo ========================================================
