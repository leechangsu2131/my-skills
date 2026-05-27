@echo off
chcp 65001 > nul
echo =======================================================
echo [개발 모드] 에듀파인 다중 기안 자동화 웹 서버 (V4 하이브리드)
echo =======================================================
echo ※ 개발 모드에서는 코드를 수정하고 저장할 때마다 서버가 자동으로 재시작됩니다.
echo 접속 주소: http://localhost:5030
echo.

set FLASK_APP=app.py
set FLASK_DEBUG=1
flask run --host=0.0.0.0 --port=5030
