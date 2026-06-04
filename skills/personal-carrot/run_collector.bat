@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ================================================
echo 🥕 당근마켓 매물 자동 수집 시스템
echo ================================================
echo.

REM venv가 있으면 활성화
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

python main.py %*

echo.
echo ------------------------------------------------
echo 완료! 아무 키나 누르면 창이 닫힙니다.
pause >nul
