@echo off
echo 패키지를 설치합니다 (npm install)...
call npm install

echo 3초 뒤 브라우저를 엽니다 (http://localhost:3001)...
:: 3초 대기 후 3001 포트로 브라우저 열기
start cmd /c "timeout /t 3 >nul && start http://localhost:3001"

echo 개발 서버를 시작합니다 (npm run dev -- -p 3001)...
call npm run dev -- -p 3001

pause