@echo off
echo ==========================================
echo  나이스 자동화용 크롬 실행기
echo  (원격 디버깅 포트 9222 열림)
echo ==========================================
echo.
echo [안내] 가정에서 접속하시는 경우 (EVPN 사용):
echo 1. 이 크롬 창이 열리면 먼저 구글 로그인을 진행합니다.
echo 2. EVPN 탭(https://evpn.gbe.kr)에서 로그인하여 연결을 완료합니다.
echo    (EVPN 연결 후에는 외부 인터넷이 차단되고 나이스만 접속 가능해집니다.)
echo 3. 나이스 탭(https://gbe.neis.go.kr)에서 나이스 로그인을 완료합니다.
echo.
echo [안내] 학교에서 접속하시는 경우:
echo - 바로 나이스 탭에서 로그인해 주시면 됩니다.
echo.
echo 이 창을 닫지 마시고, 나이스 로그인 완료 후 행동특성 입력 화면으로
echo 이동한 다음 Python 스크립트를 구동해 주세요.
echo.

REM 크롬 기본 설치 경로들 순서대로 탐색
set CHROME1="C:\Program Files\Google\Chrome\Application\chrome.exe"
set CHROME2="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
set CHROME3="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

set URLS="https://evpn.gbe.kr/custom/index.html" "https://gbe.neis.go.kr/jsp/main.jsp"

if exist %CHROME1% (
    start "" %CHROME1% --remote-debugging-port=9222 --user-data-dir="%TEMP%\neis_chrome_profile" %URLS%
    goto done
)
if exist %CHROME2% (
    start "" %CHROME2% --remote-debugging-port=9222 --user-data-dir="%TEMP%\neis_chrome_profile" %URLS%
    goto done
)
if exist %CHROME3% (
    start "" %CHROME3% --remote-debugging-port=9222 --user-data-dir="%TEMP%\neis_chrome_profile" %URLS%
    goto done
)

echo [오류] 크롬 실행 파일을 찾지 못했습니다.
echo 크롬이 설치된 경로를 직접 확인해서 이 파일을 수정해 주세요.

:done
pause

