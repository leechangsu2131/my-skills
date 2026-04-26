@echo off
setlocal

cd /d "%~dp0"

set "APP_PYTHON=%~dp0.venv\Scripts\python.exe"

echo [1/3] Preparing Python 3.11 environment...
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

echo [2/3] Installing or updating required packages...
"%APP_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install requirements.
    pause
    exit /b 1
)

echo [3/3] Starting the web app (FastAPI)...
start "" http://127.0.0.1:8080
"%APP_PYTHON%" -m uvicorn webapp.main:app --port 8080 --reload

if errorlevel 1 (
    echo.
    echo The server stopped unexpectedly.
    pause
)

exit /b %errorlevel%
