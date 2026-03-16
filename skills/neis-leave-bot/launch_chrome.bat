@echo off
echo ==========================================
echo  나이스 자동화용 크롬 실행기
echo  (원격 디버깅 포트 9222 열림)
echo ==========================================
echo.
echo 이 창을 닫지 마세요!
echo 이 크롬에서 나이스(NEIS)에 직접 로그인 해주세요.
echo 로그인 완료 후 Python 스크립트를 실행하시면 됩니다.
echo.

REM 크롬 기본 설치 경로들 순서대로 탐색
set CHROME1="C:\Program Files\Google\Chrome\Application\chrome.exe"
set CHROME2="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set CHROME3="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if exist %CHROME1% (
    start "" %CHROME1% --remote-debugging-port=9222 --user-data-dir="%TEMP%\neis_chrome_profile" https://gbe.neis.go.kr/jsp/main.jsp
    goto done
)
if exist %CHROME2% (
    start "" %CHROME2% --remote-debugging-port=9222 --user-data-dir="%TEMP%\neis_chrome_profile" https://gbe.neis.go.kr/jsp/main.jsp
    goto done
)
if exist %CHROME3% (
    start "" %CHROME3% --remote-debugging-port=9222 --user-data-dir="%TEMP%\neis_chrome_profile" https://gbe.neis.go.kr/jsp/main.jsp
    goto done
)

echo [오류] 크롬 실행 파일을 찾지 못했습니다.
echo 크롬이 설치된 경로를 직접 확인해서 이 파일을 수정해 주세요.

:done
pause
