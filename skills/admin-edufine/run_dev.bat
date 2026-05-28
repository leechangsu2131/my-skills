@echo off
chcp 65001 > nul
echo =======================================================
echo [개발 모드] 에듀파인 다중 기안 자동화 웹 서버 (V4 하이브리드)
echo =======================================================
echo.
echo 1. 원격 제어용 크롬 브라우저를 실행합니다...

set "CHROME1=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "CHROME2=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set "CHROME3=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

set "CHROME_EXE="
if exist "%CHROME1%" set "CHROME_EXE=%CHROME1%"
if exist "%CHROME2%" set "CHROME_EXE=%CHROME2%"
if exist "%CHROME3%" set "CHROME_EXE=%CHROME3%"

if not defined CHROME_EXE (
    echo [오류] 크롬 실행 파일을 찾을 수 없습니다.
) else (
    start "" "%CHROME_EXE%" --remote-debugging-port=9222 --user-data-dir="%TEMP%\edufine_chrome_profile" https://gbe.eduptl.kr/bpm_man_mn00_001.do
)

echo.
echo 2. 봇 제어용 웹 화면을 엽니다...
start "" "http://localhost:5030"

echo.
echo 3. 플라스크 개발 서버를 시작합니다... (코드 수정 시 자동 재시작)
set FLASK_APP=app.py
set FLASK_DEBUG=1
flask run --host=0.0.0.0 --port=5030
