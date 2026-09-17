@echo off
title NEIS School Network Debug Chrome Launcher

set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
set "PROFILE_DIR=%USERPROFILE%\neis_chrome_profile_9222"
set "PORT=9222"
set "PORTAL_URL=https://gbe.eduptl.kr/bpm_man_mn00_001.do"
set "NEIS_URL=https://gbe.neis.go.kr"

echo ========================================================
echo  NEIS School Network Debug Chrome Launcher
echo ========================================================
echo.
echo Chrome : %CHROME_EXE%
echo Profile: %PROFILE_DIR%
echo Port   : %PORT%
echo URL    : %PORTAL_URL%
echo.

if not exist "%CHROME_EXE%" (
  echo [ERROR] Chrome executable was not found.
  echo Check this path: %CHROME_EXE%
  echo.
  pause
  exit /b 1
)

if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"

echo [1/3] Closing only the previous debug Chrome profile, if any...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name = ''chrome.exe''' | Where-Object { $_.CommandLine -like '*neis_chrome_profile_9222*' -or $_.CommandLine -like '*remote-debugging-port=9222*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 1 /nobreak > nul

echo [2/3] Removing stale profile locks...
powershell -NoProfile -Command "Remove-Item -LiteralPath '%PROFILE_DIR%\SingletonLock' -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath '%PROFILE_DIR%\SingletonCookie' -Force -ErrorAction SilentlyContinue; Remove-Item -LiteralPath '%PROFILE_DIR%\SingletonSocket' -Force -ErrorAction SilentlyContinue"

echo [3/3] Launching Chrome with remote debugging...
start "NEIS Debug Chrome" "%CHROME_EXE%" --remote-debugging-address=127.0.0.1 --remote-debugging-port=%PORT% --user-data-dir="%PROFILE_DIR%" --no-first-run --no-default-browser-check --new-window --start-maximized "%PORTAL_URL%" "%NEIS_URL%"

echo.
echo ========================================================
echo [OK] Launch command was sent.
echo If Chrome did not appear, keep this window open and read any message above.
echo After login, tell Codex to continue the 9222 exploration.
echo ========================================================
echo.
pause
