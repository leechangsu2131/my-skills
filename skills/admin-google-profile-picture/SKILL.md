---
name: admin-google-profile-picture
description: 학생 Google 계정별 Chrome 프로필을 만들고 Google 계정 프로필 사진을 바꾼다. 계정 사진을 Chrome과 Google 서비스에 표시하거나 학생별 Chrome 프로필을 준비해 달라는 요청에 사용한다.
metadata:
  category: 학교 행정
  status: 개발
  version: v0.1.0
  summary: 학생별 Chrome 프로필을 만들고 Google 계정 프로필 사진을 설정한다.
---

# Google 계정 프로필 사진과 Chrome 프로필 관리

학생 Google 계정마다 Chrome 프로필을 별도로 만들고, 선택한 사진을 해당 Google 계정의 프로필 사진으로 설정한다. Google 계정 사진과 Chrome 프로필 아이콘은 서로 다른 설정이다. Google 계정 사진은 Google 서비스 여러 곳에 표시되고, Chrome 프로필 아이콘은 이 컴퓨터의 해당 Chrome 프로필에 표시된다.

## 작업 흐름

1. 대상 Google 계정의 별칭과 사진 파일이 있는 폴더를 확인한다. 여러 계정을 다룰 때는 한 번에 하나씩 처리한다. 사진 폴더를 지정받지 못했으면 임의의 폴더를 검색하지 말고 위치를 묻는다.
2. 지정 폴더 안에서만 사진 파일을 찾는다. 후보가 여러 개면 미리보기와 파일명을 보여 주고 사용자가 고르게 한다. 새 사진을 웹에서 내려받는 일은 사용자가 요청한 경우에만 출처와 사용 조건을 확인해 진행한다.
3. 계정마다 별도 Chrome 사용자 데이터 폴더를 사용한다. 기본 경로는 `%LOCALAPPDATA%\my-skills-data\admin-google-profile-picture\profiles\<별칭>`이다. 브라우저 조작에는 Python Playwright의 persistent context를 우선 사용하고, 이 폴더를 해당 context의 사용자 데이터 경로로 연다. 이미 로그인된 세션은 headless로 조작해도 된다. Playwright를 쓸 수 없으면 [프로필 실행 스크립트](scripts/open_chrome_profile.ps1)를 사용한다. 기존 프로필은 그대로 다시 쓰고 초기화하거나 삭제하지 않는다. 저장소, OneDrive 동기화 폴더, 일상용 Chrome 프로필은 사용하지 않는다. 변경을 확인하기 전에 브라우저 context를 닫지 않는다.
4. Google 로그인 화면에서 사용자가 요청한 경우에만 해당 별칭의 아이디를 찾아 로그인 이메일 칸에 입력하거나 클립보드에 복사한다. 이메일은 채팅이나 터미널에 출력하지 않는다. 비밀번호를 파일, 채팅, 명령줄, 자동화 코드에 입력하거나 저장하지 않는다. CAPTCHA, 비밀번호, 패스키, 2단계 인증, 기기 확인은 자동으로 풀지 말고 사용자가 직접 완료하도록 안내한다. 로그인 후 계정이 요청한 대상인지 별칭으로 확인한다.
5. Google 계정의 [개인 정보 설정](https://myaccount.google.com/personal-info)을 열고 **기본 정보 → 프로필 사진**으로 이동한다. Playwright 파일 선택 대화상자를 통해 지정 폴더의 사진을 올리고 자르기 미리보기를 확인한다. 사용자가 직접 사진 변경을 요청한 경우 그 요청과 확인된 사진 선택을 저장 지시로 본다. 그 외에는 저장 직전에 대상 계정 별칭과 사진 미리보기를 보여 주고 확인을 받는다.
6. 사진을 Google 계정에 올려 저장하기 직전에 대상 계정 별칭과 사진 미리보기를 보여 주고 사용자 확인을 받는다. 확인 뒤 **다음 → 프로필 사진으로 저장**을 선택하고 계정에 반영됐는지 확인한다. 계정 사진은 Google 서비스에 표시될 수 있으므로 다른 Google 서비스에 미칠 영향도 설명한다. YouTube 채널 사진은 별도로 관리된다.
7. Chrome 시작 페이지 변경도 요청받으면 해당 Chrome 프로필에서 `chrome://settings/onStartup`을 열고 **특정 페이지 또는 페이지 모음 열기 → 새 페이지 추가**를 선택한다. Claude를 요청받은 경우 `https://claude.ai/`를 추가하고 설정 화면에서 목록에 들어갔는지 확인한다. 시작 페이지는 Chrome 프로필에 저장되는 설정이며 Google 계정 사진과는 별개다.
8. Chrome 프로필 아이콘도 바꾸려는 요청이면 Google 계정 사진과 혼동하지 말고 별도로 확인한다. Chrome에서 **프로필 → 프로필 맞춤설정**으로 현재 프로필의 사진과 색을 바꿀 수 있다.

## 계정 아이디 복사

Google 계정 아이디가 필요하면 사용자가 요청한 경우에만 로컬 `google.env`에서 해당 별칭의 이메일 값만 읽는다. 파일은 `GOOGLE_WALLPAPER_ENV`가 지정한 위치를 우선 사용하고, 없으면 `%OneDriveCommercial%\96. 인증\google.env`, `%OneDrive%\96. 인증\google.env`, `~/OneDrive - gyo6.net/96. 인증/google.env` 순서로 찾는다. 계정 키는 `GOOGLE_WALLPAPER_ACCOUNT_01_ALIAS`와 `GOOGLE_WALLPAPER_ACCOUNT_01_EMAIL` 형식이다. 이메일은 채팅이나 터미널에 출력하지 않는다. 사용자가 로그인 입력을 요청했다면 Playwright로 이메일 칸에 넣을 수 있고, 요청이 클립보드 복사라면 이메일만 복사한다. 비밀번호는 읽거나 복사하지 않는다.

## 프로필 실행

PowerShell에서 스크립트를 실행해 별칭별 Chrome 프로필을 연다. 처음 실행하면 폴더가 만들어지고, 다음 실행부터 같은 프로필을 다시 쓴다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\open_chrome_profile.ps1 -Alias student-a
```

별칭에는 영문자, 숫자, 한글, 밑줄, 하이픈을 쓴다. 스크립트는 비밀번호를 받거나 출력하지 않는다.

## 멈춰야 하는 경우

- Chrome 실행 파일이나 로컬 프로필 위치를 찾지 못한 경우
- 로그인 계정이 요청한 별칭과 다르거나 계정을 확인할 수 없는 경우
- Google 인증 단계나 학교 관리 정책이 추가 조치를 요구하는 경우
- 사진을 올리거나 저장하기 직전에 사용자 확인을 받지 못한 경우

## 문서

- [ISSUES.md](ISSUES.md) — 진행 중인 문제와 백로그
- [Google 계정 사진 도움말](https://support.google.com/accounts/answer/27442?co=GENIE.Platform%3DDesktop&hl=ko)
- [Chrome 프로필 관리 도움말](https://support.google.com/chrome/answer/2364824?co=GENIE.Platform%3DDesktop&hl=ko)
