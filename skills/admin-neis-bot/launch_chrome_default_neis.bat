@echo off
echo ========================================================
echo  NEIS Automation - Launching Chrome Default Profile
echo ========================================================
echo.
echo [IMPORTANT] Please close ALL active Chrome windows first!
echo After closing all Chrome windows, press any key in this window.
pause

echo.
echo 1. Closing remaining Chrome processes...
taskkill /f /im chrome.exe 2>nul
timeout /t 1 /nobreak > nul

echo.
echo 2. Launching Chrome with default profile in debug mode...
set "CHROME1=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "CHROME2=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set "CHROME3=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

set "CHROME_EXE="
if exist "%CHROME1%" set "CHROME_EXE=%CHROME1%"
if exist "%CHROME2%" set "CHROME_EXE=%CHROME2%"
if exist "%CHROME3%" set "CHROME_EXE=%CHROME3%"

if not defined CHROME_EXE (
    echo [ERROR] Chrome installation not found.
    pause
    exit /b
)

start "" "%CHROME_EXE%" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9225 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" "https://evpn.gbe.kr/custom/index.html" "https://gbe.neis.go.kr/jsp/main.jsp"



echo.
echo ========================================================
echo [INSTRUCTION]
echo 1) Login to the portal in the opened Chrome.
echo 2) Go to Club Activity Cumulative Record and search.
echo 3) Reply "Ready" when done.
echo ========================================================
echo.
pause
