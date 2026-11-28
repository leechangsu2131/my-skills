# Teacher Guide Sheet Mapper

`D:\지도서`에 있는 지도서 원본/분할 결과를 읽어 진도표 행을 생성하고, 필요하면 구글 시트에 업로드하는 전용 폴더입니다.

`teacher-schedule`과 역할을 나눕니다.

- `teacherlesson-guide/mapper`(이 폴더): 지도서에서 진도표 데이터를 만든다
- `teacher-schedule`: 이미 입력된 진도표 데이터를 조회/운영/계획 관리한다

## 주요 파일

- `map_general_guides_to_sheet.py`
  - `D:\지도서`를 자동 감지해서 국어/도덕 포함 전체 과목 진도표를 한 번에 생성
- `map_guides_to_sheet.py`
  - 국어/도덕 전용 생성기
- `sheet_uploader/upload_generated_rows.py`
  - 저장된 JSON 결과를 다시 업로드하는 전용 스크립트
- `generated_rows/`
  - 생성 결과 스냅샷 저장 폴더

## 실행 위치

```powershell
cd my-skills\skills\teacherlesson-guide\mapper
```

가장 쉬운 실행 방법:

- [실행.bat](실행.bat) 더블클릭
- 미리보기 후 `업로드할까요? [y/N]` 에서 `Enter`(또는 `n`)를 누르면 업로드하지 않고 종료
- 업로드하려면 `y` → 방식 질문에서 `Enter`=그대로 추가(기존 행 안 지움). 기존 행을 지우고 올리는 방식은 `2`·`3` 을 직접 입력

## 설치

```powershell
pip install -r requirements.txt
```

비밀값·시트 설정은 교사 PC 의 중앙 `.env` 한 곳에서만 읽습니다(`skills/_shared/skill_env.py` 의 `load_env()`). 이 폴더에 `.env`를 따로 둘 필요가 없습니다.

## 사용 예시

미리보기 생성:

```powershell
python map_general_guides_to_sheet.py
```

바로 업로드:

```powershell
python map_general_guides_to_sheet.py --upload
```

저장된 최신 생성본 업로드:

```powershell
python .\sheet_uploader\upload_generated_rows.py --cleanup
```

## 현재 확인된 자동 감지 대상 예시

- 국어
- 도덕
- 수학
- 사회
- 음악
- 미술

자동 감지는 `D:\지도서` 안의 원본 PDF와 `groups.json` + `pdf_splits` 구조를 함께 사용합니다.
