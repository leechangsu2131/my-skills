---
name: teacher-guide-sheet-mapper
description: "D:\\지도서의 지도서 원본과 분할 결과를 읽어 진도표 행을 만들고 업로드하는 전용 도구입니다."
---

# Teacher Guide Sheet Mapper

이 폴더는 지도서에서 진도표 데이터를 만드는 역할만 담당합니다.

## 역할

- `map_general_guides_to_sheet.py`
  - `D:\지도서` 자동 감지
  - 국어/도덕 포함 전체 과목 진도표 생성
  - 생성 결과를 `generated_rows/`에 스냅샷 저장
- `map_guides_to_sheet.py`
  - 국어/도덕 전용 생성
- `sheet_uploader/`
  - 생성된 JSON 업로드 전용 모듈/스크립트

## 실행 기준

```powershell
cd C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\skills\teacher-guide-sheet-mapper
python map_general_guides_to_sheet.py
```

## 메모

- 이 폴더는 “지도서 -> 진도표 데이터 생성” 전용입니다.
- `teacher-schedule`은 이미 들어간 진도표를 운영/조회/계획하는 쪽으로 분리합니다.
- `.env`가 없으면 `teacher-schedule\.env`를 fallback으로 읽습니다.
