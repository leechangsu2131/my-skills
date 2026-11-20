@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 수업 비서 서버
rem 단원 개관 자동 갱신(12시간에 한 번, 실패해도 계속)
py -3.13 build_units.py --if-older 12
python assistant_server.py --open
pause
