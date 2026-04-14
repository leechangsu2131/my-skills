@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] python command was not found.
    echo Please install Python and make sure it is available in PATH.
    pause
    exit /b 1
)

where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm.cmd command was not found.
    echo Please install Node.js and make sure it is available in PATH.
    pause
    exit /b 1
)

start "Teacher Schedule Backend" cmd /k "cd /d ""%~dp0"" && python server.py"
start "Teacher Schedule Frontend" cmd /k "cd /d ""%~dp0"" && npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort"

echo Teacher Schedule UI is starting.
echo Backend and frontend windows should open separately.
echo Open http://127.0.0.1:5173 in your browser.

endlocal
