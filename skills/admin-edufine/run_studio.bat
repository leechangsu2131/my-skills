@echo off
title Edufine Flow V5 - Smart Gongmun Studio
echo =======================================================
echo   Edufine Flow V5 - Smart Gongmun Studio
echo =======================================================
echo.
echo [1/2] Opening browser: http://localhost:5030
start "" "http://localhost:5030"

echo [2/2] Starting Flask server...
cd /d "%~dp0"
set FLASK_APP=app.py
set FLASK_DEBUG=1
python -m flask run --host=0.0.0.0 --port=5030
pause