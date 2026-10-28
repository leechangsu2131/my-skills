---
description: [EduSearch] 새로운 PC에서 초기 설치 및 환경 설정
---
새로운 컴퓨터에서 처음으로 EduSearch를 실행하기 전 환경(패키지, 계정정보)을 세팅하는 워크플로우입니다.

1. 파이썬 필수 패키지들을 모두 설치합니다.
// turbo
```powershell
pip install -r requirements.txt
```

2. 기존 템플릿(`.env.example`)을 복사하여 내 로그인 정보를 담을 수 있는 `.env` 파일을 생성합니다.
// turbo
```powershell
if (!(Test-Path ".env")) { Copy-Item ".env.example" ".env" }
```

3. (알림) 지금 바로 VS Code 탐색기에서 `.env` 파일을 열고, 본인의 인디스쿨.수업나누리 아이디/비번을 입력한 후 꼭 저장해 주세요! 저장이 완료되면 이 창(워크플로우)을 닫거나, 검색앱을 실행(/run-edusearch)하면 됩니다.
