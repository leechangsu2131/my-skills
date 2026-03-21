@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>nul

set "PYTHON="

if exist "%USERPROFILE%\anaconda3\python.exe" (
    set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
    goto found
)

if exist "%USERPROFILE%\miniconda3\python.exe" (
    set "PYTHON=%USERPROFILE%\miniconda3\python.exe"
    goto found
)

where python >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%i in ('where python') do (
        set "PYTHON=%%i"
        goto found
    )
)

echo Python not found. Please install Python or Anaconda.
pause
exit /b 1

:found
echo Python: !PYTHON!

"!PYTHON!" -c "import pdfplumber" >nul 2>nul
if errorlevel 1 (
    echo Installing pdfplumber...
    "!PYTHON!" -m pip install pdfplumber --quiet
)

"!PYTHON!" -c "import pypdf" >nul 2>nul
if errorlevel 1 (
    echo Installing pypdf...
    "!PYTHON!" -m pip install pypdf --quiet
)

cd /d "%~dp0"
"!PYTHON!" app.py
if errorlevel 1 (
    echo Error occurred.
    pause
)
