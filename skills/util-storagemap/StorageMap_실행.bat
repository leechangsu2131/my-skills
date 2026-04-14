@echo off
chcp 65001 > nul
title StorageMap 🚀
color 0B

echo =========================================
echo       📦 StorageMap 로컬 서버 시작
echo =========================================
echo.

cd /d "%~dp0"

echo [1/2] 브라우저 자동 실행 예약 중...
start /B cmd /c "ping 127.0.0.1 -n 4 > nul && start http://localhost:3001"

echo [2/2] Node.js 서버 작동 중...
echo.
echo 이 창을 닫으면 StorageMap 연결이 끊어집니다! (최소화 해두세요)
echo =========================================
echo.

:: 바로 node server.js를 실행 (창에 로그 출력)
npm start
