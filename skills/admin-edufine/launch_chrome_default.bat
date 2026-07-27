@echo off
echo ========================================================
echo  K-Edufine Automation - Launching Chrome Default Profile
echo ========================================================
echo.
echo [IMPORTANT] Please close ALL active Chrome windows first!
echo If you have closed all Chrome windows, press any key.
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

start "" "%CHROME_EXE%" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" https://gbe.eduptl.kr/bpm_man_mn00_001.do

echo.
echo 3. Starting Python Flask app...
start "Edufine Bot Server" cmd /c "python app.py"

echo.
echo 4. Opening Web UI...
timeout /t 3 /nobreak > nul
start "" "http://localhost:5030"

echo.
echo ========================================================
echo [INSTRUCTION]
echo 1) Login to the portal (gbe.eduptl.kr) in the opened Chrome.
echo 2) Since we use your default profile, all security plugins work!
echo 3) After login, start automation at http://localhost:5030.
echo ========================================================
echo.
pause
