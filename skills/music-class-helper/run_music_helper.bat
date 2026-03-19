@echo off
chcp 65001 > nul
cd /d "%~dp0"
python music_helper.py menu
echo.
pause
