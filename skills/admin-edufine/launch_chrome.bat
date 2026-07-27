@echo off
echo ========================================================
echo  K-Edufine Automation - Launching Chrome Temp Profile
echo ========================================================
echo.

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

start "" "%CHROME_EXE%" --remote-debugging-port=9222 --user-data-dir="%TEMP%\edufine_chrome_profile" https://gbe.eduptl.kr/bpm_man_mn00_001.do

echo.
echo 2. Starting Python Flask app...
start "Edufine Bot Server" cmd /c "python app.py"

echo.
echo 3. Opening Web UI...
timeout /t 3 /nobreak > nul
start "" "http://localhost:5030"

echo.
echo ========================================================
echo [INSTRUCTION]
echo 1) Login to the portal (gbe.eduptl.kr) in the opened Chrome.
echo 2) Start automation at http://localhost:5030.
echo ========================================================
echo.
pause
