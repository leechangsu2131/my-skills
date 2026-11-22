@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   Guide Folder Auto Detect ^> Sheet Row Builder
echo ============================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 goto use_py

python map_general_guides_to_sheet.py
goto after_run

:use_py
py -3 map_general_guides_to_sheet.py

:after_run
if errorlevel 1 goto error

echo.
echo ??? ?????.
goto end

:error
echo.
echo ??? ??????.

:end
echo.
pause
