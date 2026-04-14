---
name: social-class-helper
description: "사회 교과서 차시 자료를 빠르게 열고, 반복 수업 구성을 저장하는 반자동 수업 도우미입니다."
category: education
risk: medium
source: local
date_added: "2026-03-19"
tags: ["education", "social-studies", "douclass", "selenium", "classroom-management"]
---

# 사회 수업 도우미 (Social Class Helper)

## Overview

`music-class-helper`의 흐름을 바탕으로 만든 사회 수업용 반자동 도우미입니다. Douclass 차시 페이지에 접속해 원하는 단원과 차시를 찾아 자료 버튼을 열고, 자주 쓰는 수업 구성을 저장해 반복 준비 시간을 줄여 줍니다.

기본 설정은 **기존 `music-class-helper`의 Chrome 프로필 경로를 그대로 재사용**하도록 되어 있어, 이미 로그인해 둔 세션을 자연스럽게 공유할 수 있습니다.

## Setup

1. `skills/social-class-helper/.env.example`를 복사해 `skills/social-class-helper/.env`를 만듭니다.
2. `SOCIAL_CLASS_BASE_URL`에 사회 교과서 차시 첫 화면 URL을 넣습니다.
3. 지도서 PDF가 있다면 `SOCIAL_CLASS_GUIDE_PDF`에 경로를 넣습니다.
4. 필요하면 `SOCIAL_CLASS_RESOURCE_KEYWORDS`를 수정해 열고 싶은 버튼 이름에 맞춥니다.
5. 처음 한 번은 `pip install selenium` 이 필요합니다.

## Quick Start

대화형 메뉴:

```bash
cd skills/social-class-helper
python social_class_helper.py menu
```

바로 실행:

```bash
python skills/social-class-helper/social_class_helper.py run "1단원" "1~2차시" --save "3학년 1단원 첫 수업"
```

저장된 수업 실행:

```bash
python skills/social-class-helper/social_class_helper.py saved run "3학년 1단원 첫 수업"
```

## What It Stores

- `.env`: 교과서 URL, 크롬 프로필 경로, 자료 버튼 키워드
- `.env`: 교과서 URL, 크롬 프로필 경로, 지도서 PDF 경로, 자료 버튼 키워드
- `social_class_data.json`: 저장한 수업 구성과 최근 실행 기록

둘 다 로컬 전용 정보라서 Git에 올라가지 않도록 `.gitignore`에 반영되어 있습니다.

## Notes

- 사이트 구조가 바뀌면 `SOCIAL_CLASS_RESOURCE_KEYWORDS`를 먼저 조정해 보세요.
- `SOCIAL_CLASS_GUIDE_PDF`가 설정되어 있으면 차시를 찾은 뒤 지도서 PDF도 자동으로 발췌합니다.
- 자동으로 버튼을 못 찾으면 브라우저에서 직접 클릭한 뒤 Enter로 이어서 진행할 수 있습니다.
- 같은 디버그 포트와 같은 프로필을 쓰는 동안에는 다른 helper와 로그인 상태를 공유할 수 있습니다.
