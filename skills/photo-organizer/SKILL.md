---
name: photo-organizer
description: >-
  Pictures 폴더 아래 활동 폴더의 사진을 정리하는 스킬.
  중복 사진 제거, EXIF 제작 날짜 기반 폴더명 날짜 태그 추가,
  의미 없는 자동 파일명(KakaoTalk_, IMG_, DSC_ 등) 변경 작업을 수행한다.
  "사진 정리", "폴더에 날짜 붙이기", "중복 사진 제거", "파일명 변경" 관련 요청에 사용.
---

# 📸 사진 폴더 자동 정리 스킬

`C:\Users\user\Pictures\` 아래 활동 폴더의 사진을 세 단계로 자동 정리합니다.

## 정리 규칙 요약

| 항목 | 규칙 |
|------|------|
| 날짜 추출 | EXIF `DateTimeOriginal` → `DateTime` → 파일명 내 날짜 순으로 시도 |
| 폴더명 날짜 | `활동명 YYYY-MM-DD` 또는 `활동명 YYYY-MM-DD~YYYY-MM-DD` |
| 날짜 중복 방지 | 이미 날짜 패턴이 붙어 있으면 건너뜀 |
| 중복 제거 | MD5 해시 비교 — `파일명 (1).jpg` 형식 사본 우선 삭제 |
| 파일명 변경 | 자동 패턴(`KakaoTalk_`, `IMG_`, `DSC_`, `20xx-…` 등)만 변경 |
| 새 파일명 | `활동명_YYYYMMDD_3-2_01.jpg` 형식 (기본값 `3-2`, 옵션으로 변경 가능) |
| Screenshots 제외 | `Screenshots` 폴더는 자동으로 작업 대상에서 제외 |
| 의미 있는 이름 | 그대로 유지 (예: `현장체험학습_3학년2반_01.jpg`) |

---

## 사용 방법

### 1. 미리보기 (dry-run) — 실제 변경 없음

```powershell
python "C:\Users\user\.gemini\config\skills\photo-organizer\scripts\organize_photos.py" --dry-run
```

### 2. 전체 Pictures 폴더 정리 (실제 적용)

```powershell
# 기본 실행 (3-2반 기본 적용)
python "C:\Users\user\.gemini\config\skills\photo-organizer\scripts\organize_photos.py"

# 학급 지정 실행 (예: 3-1반 또는 3학년2반)
python "C:\Users\user\.gemini\config\skills\photo-organizer\scripts\organize_photos.py" --class-id "3-1"
python "C:\Users\user\.gemini\config\skills\photo-organizer\scripts\organize_photos.py" --class-id "3학년2반"

# 학급 표기 없이 날짜만 넣고 싶을 때
python "C:\Users\user\.gemini\config\skills\photo-organizer\scripts\organize_photos.py" --class-id ""
```

### 3. 특정 폴더 하나만 처리

```powershell
python "C:\Users\user\.gemini\config\skills\photo-organizer\scripts\organize_photos.py" --folder "게임만들기"
```

### 4. 파일명 변경 없이 폴더명 날짜만 추가

```powershell
python "C:\Users\user\.gemini\config\skills\photo-organizer\scripts\organize_photos.py" --skip-rename-files
```

### 5. 중복 제거 + 파일명 변경만 (폴더명은 유지)

```powershell
python "C:\Users\user\.gemini\config\skills\photo-organizer\scripts\organize_photos.py" --skip-rename-folder
```

### 6. 다른 루트 폴더 지정

```powershell
python "C:\Users\user\.gemini\config\skills\photo-organizer\scripts\organize_photos.py" "D:\사진모음"
```

---

## 처리 단계

1. **중복 제거** — `파일명 (1).jpg`, `파일명 (2).jpg` 등 사본을 원본과 MD5 비교 후 삭제
2. **파일명 변경** — 자동 생성 파일명만 `활동명_YYYYMMDD_순번.jpg` 형식으로 변경
3. **폴더명 날짜 추가** — 사진 EXIF에서 최소/최대 날짜 추출 후 폴더명 뒤에 추가

---

## 에이전트 실행 절차

사용자가 "사진 정리해줘", "폴더에 날짜 붙여줘", "중복 사진 지워줘" 등을 요청하면:

1. **항상 dry-run을 먼저 실행**하여 변경 목록을 사용자에게 보여준다.
2. 사용자 확인 후 실제 실행한다.
3. 특정 폴더만 처리할지, 전체 처리할지 먼저 묻는다.
4. 처리 완료 후 결과 요약을 출력한다.

> [!CAUTION]
> 중복 삭제는 되돌릴 수 없습니다. 반드시 `--dry-run` 먼저 실행 후 사용자 승인을 받으세요.

> [!NOTE]
> Pillow 라이브러리가 필요합니다. 없으면: `pip install Pillow`

---

## 자동 생성 파일명 패턴 (변경 대상)

- `KakaoTalk_20261104_142120253.jpg`
- `KakaoTalk_20261104_142120253_02.jpg`
- `IMG_20261104_142120.jpg`
- `DSC_1234.jpg`
- `20261104_142120.jpg`
- `Screenshot_2026...`
- `2022-어쩌구-저쩌구.jpg`

## 의미 있는 파일명 패턴 (유지)

- `현장체험학습_3학년2반_01.jpg`
- `수영교육_3반_단체사진.jpg`
- 사용자가 직접 붙인 모든 한글/영문 혼합 이름
