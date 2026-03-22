# 🏫 Teacher Schedule Full-Stack System (교사용 스마트 진도 관리 시스템)

구글 시트를 데이터베이스이자 관리자 화면으로 활용하면서, 파이썬 기반의 강력한 스케줄링 예측 알고리즘과 아름다운 React/Vite 프론트엔드가 결합된 풀스택 교육 과정 관리 앱입니다.

## ✨ 기획 의도 및 아키텍처
1. **Google Sheets (DB & Admin UI)**: 교사들에게 가장 친숙한 스프레드시트를 데이터 저장소로 사용하여 서버 유지비를 없애고, 필요할 땐 언제든 엑셀처럼 데이터를 직관적으로 수정할 수 있습니다.
2. **Python Backend (`schedule.py`, `server.py`)**: 요일별 기초 시간표와 실제 차시별 진도표를 결합하여, 오늘/내일/다음주의 스케줄을 "가상 큐(Virtual Queue)" 모델을 통해 동적으로 계산해 냅니다.
3. **React/Vite Frontend (`schedule_app.jsx`)**: 모바일과 데스크톱 어디서든 직관적이고 아름답게 수업 진도를 체크(완료)하고 날짜를 푸시(밀기) 할 수 있는 시각적 UI를 제공합니다. Python 백엔드가 내려주는 객체 기반 UI(Server-Driven UI)를 채택하여 백엔드 메뉴 확장이 자유롭습니다.

## 🚀 빠른 시작 가이드 (Quick Start)

본 시스템은 두 개의 터미널을 사용하여 백엔드와 프론트엔드를 각각 실행합니다.

### 1단계: 환경 변수 설정 `.env` 작성
폴더 내에 `.env` 파일을 만들고 아래 정보를 입력합니다.
```env
SHEET_ID="구글 시트 고유 ID (URL에서 복사)"
SHEET_NAME="진도표"
GOOGLE_CREDENTIALS_JSON='{ "type": "service_account", ... }'
```

### 2단계: 파이썬 API 서버 실행 (Backend)
```bash
pip install -r requirements.txt
python server.py
# (http://127.0.0.1:5000 포트에서 실행됩니다)
```

### 3단계: 리액트 앱 실행 (Frontend)
새로운 터미널 창을 열고 아래 명령어를 입력합니다.
```bash
npm install
npm run dev
```
표시되는 로컬 주소(예: `http://localhost:5173`)로 접속하시면 깔끔한 진도 관리 대시보드를 시각적으로 이용하실 수 있습니다!
