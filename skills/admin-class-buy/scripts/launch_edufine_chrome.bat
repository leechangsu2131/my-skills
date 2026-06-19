@echo off
chcp 65001 > nul
setlocal

set "CHROME1=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "CHROME2=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set "CHROME3=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
set "CHROME_EXE="

if exist "%CHROME1%" set "CHROME_EXE=%CHROME1%"
if exist "%CHROME2%" set "CHROME_EXE=%CHROME2%"
if exist "%CHROME3%" set "CHROME_EXE=%CHROME3%"

if not defined CHROME_EXE (
  echo [오류] Chrome 실행 파일을 찾지 못했습니다.
  pause
  exit /b 1
)

echo K-에듀파인 자동화용 Chrome을 엽니다.
echo 열린 창에서 업무포털/NEIS 로그인 후 K-에듀파인을 열어주세요.
start "" "%CHROME_EXE%" --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir="%TEMP%\admin_class_buy_chrome_profile" https://gbe.eduptl.kr/bpm_man_mn00_001.do

echo.
echo 확인 주소: http://127.0.0.1:9222/json/version
pause
