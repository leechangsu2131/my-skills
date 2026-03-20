@echo off
chcp 65001 > nul
cd /d "%~dp0"
python social_class_helper.py menu
echo.
pause
