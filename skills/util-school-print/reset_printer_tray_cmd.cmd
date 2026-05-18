@echo off
cd /d "%~dp0"
echo.
echo Reset printer tray to auto/default...
echo.
python reset_printer_tray.py
echo.
pause
