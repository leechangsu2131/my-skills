@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 수업 비서 서버
python assistant_server.py --open
pause
