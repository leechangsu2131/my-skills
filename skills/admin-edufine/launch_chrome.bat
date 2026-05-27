@echo off
chcp 65001 > nul
echo ==========================================
echo  에듀파인 기안 자동화 통합 런처
echo ==========================================
echo.
echo 1. 나이스 접속용 크롬(디버깅 모드)을 실행합니다...

set "CHROME1=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "CHROME2=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set "CHROME3=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

set "CHROME_EXE="
if exist "%CHROME1%" set "CHROME_EXE=%CHROME1%"
if exist "%CHROME2%" set "CHROME_EXE=%CHROME2%"
if exist "%CHROME3%" set "CHROME_EXE=%CHROME3%"

if not defined CHROME_EXE (
    echo [오류] 크롬 실행 파일을 찾지 못했습니다.
    pause
    exit /b
)

start "" "%CHROME_EXE%" --remote-debugging-port=9222 --user-data-dir="%TEMP%\edufine_chrome_profile" https://gbe.eduptl.kr/bpm_man_mn00_001.do

echo.
echo 2. 파이프라인 웹 서버(app.py)를 구동합니다...
start "Edufine Bot Server" cmd /c "python app.py"

echo.
echo 3. 자동화 제어 웹(UI) 화면을 엽니다...
timeout /t 3 /nobreak > nul
start "" "http://localhost:5030"

echo.
echo ==========================================
echo [필독 - 작업 순서]
echo 1) 업무포털(NEIS) 크롬 창에서 로그인 후 [K-에듀파인] 메뉴를 클릭해 띄우세요.
echo 2) 자동으로 열린 'Edufine Flow V3' 브라우저 화면에서
echo    공문 폴더 경로를 적고 [일괄 실행]을 누르시면 됩니다!
echo ==========================================
echo.
pause
