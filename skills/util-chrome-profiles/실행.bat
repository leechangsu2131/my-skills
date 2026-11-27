@echo off
cd /d "%~dp0"
python -c "import PySide6, win32gui" 2>nul
if errorlevel 1 (
  echo Installing required packages: PySide6, pywin32 ...
  python -m pip install -r requirements.txt
  if errorlevel 1 ( pause & exit /b 1 )
)
start "" pythonw chrome_profiles.py
