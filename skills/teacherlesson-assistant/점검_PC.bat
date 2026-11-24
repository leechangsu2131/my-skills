@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 학교 PC 점검
rem 수업 비서를 쓰기 전에 이 PC 에 빠진 것이 없는지 확인한다(읽기만 함, 설치·수정 없음)
set "PY=python"
py -3.13 -c "import sys" >nul 2>nul && set "PY=py -3.13"
%PY% check_setup.py %*
if errorlevel 9009 echo.& echo Python 을 찾지 못했어요. https://www.python.org/downloads/ 에서 설치하고 "Add to PATH" 를 체크하세요.
echo.
pause
