@echo off
title Valuation App Dashboard

echo ===================================================
echo  Starting Valuation App Dashboard...
echo ===================================================
echo.

:: Change directory to the script's directory
cd /d "%~dp0"

:: 1. Check and activate virtual environment
if exist .venv\Scripts\activate.bat (
    echo [VENV] Activating .venv...
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    echo [VENV] Activating venv...
    call venv\Scripts\activate.bat
) else (
    echo [INFO] Local virtual environment not found. Using system Python.
)

:: 2. Check if streamlit is installed
python -c "import streamlit" 2>nul
if %errorlevel% neq 0 (
    echo [WARN] Streamlit is not installed.
    echo Installing required packages from requirements-valuation.txt...
    python -m pip install -r requirements-valuation.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install packages. Please check your Python environment.
        pause
        exit /b %errorlevel%
    )
)

:: 3. Run Streamlit Dashboard
echo [RUN] Launching Streamlit server...
echo Press Ctrl+C or close this window to stop.
echo.

python -m streamlit run valuation_app/dashboard.py

if %errorlevel% neq 0 (
    echo [ERROR] Dashboard failed to start.
    pause
)
