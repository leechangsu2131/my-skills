@echo off
chcp 65001 > nul
setlocal

:: ── 스크립트 위치 기준으로 실행 ──────────────────────────
cd /d "%~dp0"
set PYTHONUTF8=1

echo.
echo =============================================
echo   학교 안내장 반별 자동 인쇄 (간지 포함)
echo =============================================
echo.

python batch_print_v2.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [오류] 스크립트 실행 중 문제가 발생했습니다.
)

echo.
pause
