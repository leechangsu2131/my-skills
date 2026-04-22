@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PYTHONUTF8=1
echo.
echo =============================================
echo   프린터 용지함(트레이) 번호 목록 조회
echo =============================================
echo.
python list_trays.py
