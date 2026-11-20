# Gemini 추천표 적용기 사용법

이 스크립트는 Gemini가 만든 추천표를 읽어서 실제 Obsidian Vault에 반영합니다.

대상 열:

- `bundle_file`
- `source_path`
- `현재 제목`
- `제안 제목`
- `domain`
- `engine`
- `topic`
- `type`
- `연결 후보`
- `처리 제안`
- `확신도`
- `이유`

## 지원 동작

- `제안 제목` 기준 파일명 변경
- 제목과 같은 첫 번째 H1 자동 수정
- `domain / engine / topic / type` frontmatter 반영
- `처리 제안`에 따라 폴더 이동
  - `10_NOTE 승격`
  - `20_THINKING 승격`
  - `30_SYSTEM 승격`
  - `Inbox 보류`
  - `유지`
  - `제목 수정 후 유지`
- 이동 후 `path` 속성 자동 갱신
- `_PKM_BACKUP` 백업 생성
- 적용 이력 저장

## 자동으로 하지 않는 것

- `기존 노트에 흡수`
  - 이 경우는 자동 병합하지 않고 수동 처리 대상으로 남깁니다.

## 중복 추천 처리

- 같은 노트가 축약 경로와 정식 경로로 두 번 들어와도 가능한 한 실제 파일 기준으로 하나로 합칩니다.
- 같은 노트에 대해 서로 다른 추천이 여러 번 들어오면 마지막 행을 우선합니다.
- 이미 같은 추천이 적용된 경우에는 `state.json`을 보고 다음 실행에서 자동으로 건너뜁니다.

## 실행 예시

미리보기:

```powershell
python apply_gemini_recommendations.py "<볼트 경로>" "C:\path\to\gemini_output.csv" --dry-run
```

실제 적용:

```powershell
python apply_gemini_recommendations.py "<볼트 경로>" "C:\path\to\gemini_output.csv"
```

낮은 확신도까지 포함:

```powershell
python apply_gemini_recommendations.py "<볼트 경로>" "C:\path\to\gemini_output.csv" --min-confidence 하
```

## 결과물

- 보고서:
  - `Vault/reports/gemini-applied/gemini_apply_*.md`
- 적용 상태:
  - `Vault/reports/gemini-applied/state.json`

같은 `source_path`와 같은 추천 fingerprint가 다시 들어오면, 다음 실행에서는 자동으로 건너뜁니다.
