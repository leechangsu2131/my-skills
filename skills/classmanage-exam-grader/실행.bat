@echo off
setlocal

cd /d "%~dp0"

set "APP_PYTHON=%~dp0.venv\Scripts\python.exe"

echo [1/4] Preparing Python 3.11 environment...
if not exist "%APP_PYTHON%" (
    py -3.11 -c "import sys" >nul 2>nul
    if errorlevel 1 (
        echo Python 3.11 was not found.
        echo Install Python 3.11, then run this file again.
        pause
        exit /b 1
    )

    py -3.11 -m venv .venv
    if errorlevel 1 (
        echo Failed to create the local Python 3.11 virtual environment.
        pause
        exit /b 1
    )
)

"%APP_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>nul
if errorlevel 1 (
    echo The local virtual environment is not using Python 3.11.
    echo Delete the .venv folder and run this file again.
    pause
    exit /b 1
)

echo [2/4] Checking OCR runtime...
"%APP_PYTHON%" -c "import fastapi, uvicorn, paddleocr, paddle, certifi_win32, ultralytics" >nul 2>nul
if errorlevel 1 (
    echo [3/4] Installing or updating required packages...
    "%APP_PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install requirements for the Python 3.11 environment.
        pause
        exit /b 1
    )
) else (
    echo [3/4] Reusing the existing Python 3.11 environment...
)

echo [4/4] Starting the web app...
start "" http://127.0.0.1:8000
"%APP_PYTHON%" -m uvicorn webapp.main:app --reload
if errorlevel 1 (
    echo.
    echo The server stopped unexpectedly.
    echo If OCR model downloads fail on a school network, rerun once after the required packages are installed in .venv.
    pause
)

exit /b %errorlevel%
