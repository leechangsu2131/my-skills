@echo off
chcp 65001 > nul
echo ========================================
echo   교사용 지도서 PDF 관리 시스템
echo   설치 스크립트 (Windows)
echo ========================================
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://python.org 에서 Python 3.10 이상을 설치해주세요.
    pause
    exit /b 1
)

echo [패키지 설치 중...]
pip install pypdf pdfplumber anthropic rich

if not exist .env (
    echo # Anthropic API 키 설정 (수업 내용 AI 요약 기능용) > .env
    echo # ANTHROPIC_API_KEY=sk-ant-여기에-키를-입력하세요 >> .env
    echo [.env 파일 생성됨]
)

echo.
echo ========================================
echo   설치 완료!
echo ========================================
echo.
echo [AI 분석 기능 사용 시]
echo   .env 파일을 메모장으로 열어서 아래 줄의 # 을 지우고 키 입력:
echo   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxx
echo.
echo [시작하기]
echo   python app.py          <- 대화형 모드
echo   python app.py help     <- 도움말
echo.
pause
