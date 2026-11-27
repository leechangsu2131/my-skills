@echo off
rem my-skills 의 bat 파일을 모아 보여 주는 스킬 실행기
cd /d "%~dp0"
python -c "import PySide6, win32com" 2>nul
if errorlevel 1 (
  echo Installing required packages: PySide6, pywin32 ...
  python -m pip install -r requirements.txt
  if errorlevel 1 ( pause & exit /b 1 )
)
start "" pythonw launcher.py
