---
description: 사회 교과서 차시 자료를 빠르게 열고 반복 수업 구성을 저장하는 반자동 워크플로우
---

# 사회 수업 도우미 워크플로우

사회 수업 준비 때 교과서 차시 자료를 빠르게 열고, 자주 쓰는 구성을 저장해 다시 활용합니다.

## 사전 조건

- `skills/social-class-helper/.env` 파일이 준비되어 있어야 합니다
- `.env` 안에 `SOCIAL_CLASS_BASE_URL`이 입력되어 있어야 합니다
- 필요한 경우 `pip install selenium` 이 되어 있어야 합니다
- Douclass 로그인은 사용자가 직접 한 번 진행해야 합니다

---

## Step 1: 기본 설정 확인

먼저 아래 항목을 확인합니다:

1. `skills/social-class-helper/.env` 파일이 있는지 확인
2. `SOCIAL_CLASS_BASE_URL` 값이 올바른지 확인
3. 어떤 버튼을 열어야 하는지 `SOCIAL_CLASS_RESOURCE_KEYWORDS` 확인

기본값은 `music-class-helper`와 같은 Chrome 프로필 경로와 같은 디버그 포트를 재사용하므로, 이미 로그인해 둔 세션을 공유하기 좋습니다.

---

## Step 2: 대상 차시 확인

사용자에게 다음처럼 필요한 정보를 확인합니다:

```text
어떤 사회 수업을 준비할까요?
- 단원: 예) 1단원
- 차시: 예) 3~4차시
- 저장 이름이 필요하면: 예) 3학년 1단원 2주차
```

---

## Step 3: 프로그램 실행

대화형 메뉴가 필요하면:

```bash
python skills/social-class-helper/social_class_helper.py menu
```

바로 실행하려면:

```bash
python skills/social-class-helper/social_class_helper.py run "1단원" "3~4차시" --save "3학년 1단원 2주차"
```

자동 클릭이 잘 안 되면 수동 클릭 모드로 다시 실행합니다:

```bash
python skills/social-class-helper/social_class_helper.py run "1단원" "3~4차시" --manual
```

---

## Step 4: 로그인 및 자료 열기

프로그램은 다음 순서로 진행됩니다:

1. 원격 디버깅 Chrome에 연결
2. 수업 URL로 이동
3. 로그인 상태가 아니면 사용자가 브라우저에서 직접 로그인
4. 단원과 차시를 찾아 자료 버튼 클릭
5. 성공하면 최근 실행 기록 저장

---

## Step 5: 저장된 수업 재사용

자주 쓰는 수업은 저장한 뒤 다음 명령으로 다시 실행합니다:

```bash
python skills/social-class-helper/social_class_helper.py saved run "3학년 1단원 2주차"
```

목록 확인:

```bash
python skills/social-class-helper/social_class_helper.py saved list
```

---

## 주의사항

- `.env`와 `social_class_data.json`은 로컬 정보이므로 Git에 올리지 않습니다
- 사이트 구조가 바뀌면 `SOCIAL_CLASS_RESOURCE_KEYWORDS`를 먼저 조정합니다
- 자동 클릭이 실패해도 수동 클릭 모드로 이어서 사용할 수 있습니다
