---
name: teacher-schedule
description: "구글 시트(기초시간표, 진도표)와 연동하여 실제 수업 진도를 체크하고, 일정(계획일)을 동적으로 밀거나 관리할 수 있는 React-Python 풀스택 앱 모듈입니다."
---

# Teacher Schedule App (구글 시트 연동 스마트 진도표)

## 사전 준비 (Prerequisites)
1. **구글 서비스 계정 키**:
   - 구글 클라우드 콘솔(GCP)에서 `서비스 계정`을 만들고 JSON 키를 발급받습니다.
2. **구글 시트 세팅**:
   - `기초시간표`, `진도표`(시트1) 두 개의 시트를 가진 문서를 만듭니다.
   - 우측 상단 '공유' 버튼을 눌러 발급받은 서비스 계정 이메일(`xxx@yyy.iam.gserviceaccount.com`)을 초대하고 "편집자" 권한을 줍니다.

## .env 파일 설정 예시 (필수)
```env
SHEET_ID="선생님의 구글 시트 ID (URL 중간값)"
SHEET_NAME="진도표"  # (기본값 시트1)

# 서비스 계정 키 전체 복사/붙여넣기 (양끝을 꼭 홑따옴표로 감쌀 것)
GOOGLE_CREDENTIALS_JSON='{
  "type": "service_account",
  "project_id": "api-project-1234",
  ... (전체 내용) ...
}'
```

## 아키텍처 특장점 (Server-Driven UI 설계)
새로운 탭(예: "이번 달 수업 확인")을 추가하고 싶을 때는 React 컴포넌트를 손댈 필요가 없습니다! 
파이썬 `server.py`의 `dashboard()` 함수 내 `views` 배열에 딕셔너리를 하나 통째로 밀어넣어 주기만 하면, React UI에서 해당 데이터를 읽고 자동으로 메뉴 탭이 생겨납니다. 이것이 바로 유연성과 확장성이 돋보이는 `Server-Driven Architecture`의 핵심입니다.
