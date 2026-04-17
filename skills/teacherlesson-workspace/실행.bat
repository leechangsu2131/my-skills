@echo off
echo 패키지를 설치합니다 (npm install)...
call npm install

echo 3초 뒤 브라우저를 엽니다...
:: 3초 대기 후 브라우저를 여는 작업을 별도의 프로세스로 실행
start cmd /c "timeout /t 3 >nul && start http://localhost:3000"

echo 개발 서버를 시작합니다 (npm run dev)...
call npm run dev

pause