@echo off
echo 1. Force closing all existing Chrome windows...
taskkill /f /im chrome.exe 2>nul
timeout /t 1 /nobreak > nul

echo 2. Clearing previous temp debug profile...
powershell -Command "Remove-Item -Path '$env:TEMP\neis_chrome_profile_9222' -Recurse -Force -ErrorAction SilentlyContinue"

echo 3. Launching fresh debugging Chrome on port 9222...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\neis_chrome_profile_9222" "https://evpn.gbe.kr/custom/index.html" "https://gbe.neis.go.kr/jsp/main.jsp"

echo.
echo ========================================================
echo Done. Please login and navigate to Club Record screen.
echo ========================================================
