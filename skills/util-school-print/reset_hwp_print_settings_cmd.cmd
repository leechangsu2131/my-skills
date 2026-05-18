@echo off
cd /d "%~dp0"
echo.
echo Reset HWP print settings and printer tray...
echo.
python reset_hwp_print_settings.py
echo.
pause
