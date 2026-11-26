@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 수업 비서 서버
rem Python 실행기는 하나만 쓴다: py -3.13 이 있으면 그것, 없으면 python (점검_PC.bat 과 같은 방식)
set "PY=python"
py -3.13 -c "import sys" >nul 2>nul && set "PY=py -3.13"
rem 단원 개관 자동 갱신(12시간에 한 번, 실패해도 계속)
%PY% build_units.py --if-older 12
rem 오늘 수업 중 흐름이 없는 차시만 뒤에서 자동 준비(Gemini, 서버가 뜰 때까지 30초 기다림, 실패해도 계속)
start "수업 준비" /min cmd /c "timeout /t 30 /nobreak >nul & %PY% prepare_lessons.py --date today"
%PY% assistant_server.py --open
pause
