@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo A4 인쇄 트레이1 복구 (Windows + 한글 설정)
echo.
python fix_a4_tray1.py
echo.
pause
