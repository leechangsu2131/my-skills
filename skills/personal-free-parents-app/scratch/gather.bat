@echo off
:: gather.bat - Double-click to run gather_for_ai.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0gather_for_ai.ps1"
pause
