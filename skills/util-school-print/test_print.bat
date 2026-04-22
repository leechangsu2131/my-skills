@echo off
chcp 65001 > nul
cd /d "%~dp0"
set PYTHONUTF8=1

echo.
echo =============================================
echo   한글 OLE 인쇄 단순 테스트
echo =============================================
echo.

python test_print.py
