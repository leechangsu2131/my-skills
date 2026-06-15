@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 후지 Apeos C2561 트레이 진단...
echo.
python diagnose_apeos_tray.py
echo.
pause
