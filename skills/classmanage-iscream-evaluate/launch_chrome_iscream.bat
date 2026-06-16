@echo off
chcp 65001 >nul 2>&1

echo.
echo ==========================================================
echo   i-scream Chrome Remote Debugging Launcher
echo ==========================================================
echo.

set CDP_PORT=9222
set USER_DATA_DIR=%TEMP%\iscream_chrome_profile
set START_URL=https://www.i-scream.co.kr
set FLASK_PORT=5028

echo 1. Clearing any existing Chrome debug processes...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name = ''chrome.exe''' | Where-Object { $_.CommandLine -like '*iscream_chrome_profile*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

set CHROME_PATH=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
    echo [✓] Chrome found: Program Files 64-bit
    goto :found
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    echo [✓] Chrome found: Program Files x86 32-bit
    goto :found
)
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
    echo [✓] Chrome found: User Local AppData
    goto :found
)

echo.
echo [✗] Error: Chrome browser not found!
echo.
pause
exit /b 1

:found
echo.
echo [Info] CDP Port: %CDP_PORT%
echo [Info] Profile Path: %USER_DATA_DIR%
echo [Info] Start URL: %START_URL%
echo.
echo 2. Launching Chrome in Remote Debugging Mode...
start "" "%CHROME_PATH%" --remote-debugging-port=%CDP_PORT% --user-data-dir="%USER_DATA_DIR%" --new-window %START_URL%

echo.
echo 3. Opening Web UI dashboard (http://localhost:%FLASK_PORT%)...
timeout /t 3 /nobreak > nul
start "" "http://localhost:%FLASK_PORT%"

echo.
echo 4. Starting i-scream Evaluation Server (Flask)...
python app.py
