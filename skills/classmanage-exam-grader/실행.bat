@echo off
setlocal

cd /d "%~dp0"

echo [1/3] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found in PATH.
    echo Install Python first, then run this file again.
    pause
    exit /b 1
)

echo [2/3] Installing or updating required packages...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements.
    echo If OCR later reports Paddle errors, install a compatible paddlepaddle runtime too.
    pause
    exit /b 1
)

echo [3/3] Starting the web app...
start "" http://127.0.0.1:8000
python -m uvicorn webapp.main:app --reload

set "EXIT_CODE=%errorlevel%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo The server stopped with exit code %EXIT_CODE%.
    echo If you saw a PaddleOCR or paddlepaddle error, install a compatible paddlepaddle package for this Python environment.
    pause
)

exit /b %EXIT_CODE%
