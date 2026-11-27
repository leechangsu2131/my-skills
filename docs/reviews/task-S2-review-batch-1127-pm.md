# S2 검토 묶음 — PR #114·#115·#117·#118·#122·#123·#124·#126 (2026-11-27, claude-web-소연)

그 브랜치들은 고치지 않았다. #113 은 다른 작업자가 검토를 잡아 뺐고, #125 는 내 PR 이라 뺐다.

## 합칠 때 순서 요약

| PR | 판단 | 한 줄 |
|---|---|---|
| #122 | 합침 | util-notebooklm SKILL.md. #118 내용을 포함 |
| #118 | **닫음** | #122 와 같은 줄을 고쳐 충돌. 더할 내용 없음 |
| #124 | 합침 | ISSUE-005 재현 시험(경로마다 따로 표시) |
| #123 | **닫거나 일부만** | #124 와 같은 일, `ISSUES.md` 충돌 |
| #114 | 합침 | from-neis SKILL.md 겹친 글 정리 |
| #117 | 합침 | guide SKILL.md 한 줄 |
| #115 | 합침 | build_units 시험 49개 |
| #126 | 합침 | nlm.py 시험 41개. CI 대상 아님(아래) |

## 공통 확인

- 8개 모두 지금 `main` 과 충돌 없음(`git merge-tree`).
- 각 브랜치에서 `check_privacy.py` 통과(모양 검사), `build_catalog.py --check` 오류 0.

## PR 별

- **#122 / #118**: 두 PR 을 서로 합치면 `util-notebooklm/SKILL.md` 충돌. #122 의 `--from`(범위 밖 쪽 제외, 없으면 멈춤), `--title`, 그림 PDF 이름, `split --pattern`·조각 이름·저장 폴더, `--note`·`--q` 선택, `--out` 이 파일/폴더인 구분을 `nlm.py` 와 대조해 맞음.
- **#123 / #124**: 둘 다 `/api/done` 등 6개 경로의 `ScheduleError` 재현. 시험 결과 #123 1 통과·2 xfail, #124 2 통과·6 xfail(pytest·unittest 모두).
  - #124 는 경로마다 표시가 있어 일부만 고쳐도 드러나고 `/api/catch-up` 회귀 시험이 있다.
  - #123 에만 있는 것: `load_all`(읽기 단계)에서 난 오류. 필요하면 #124 뒤에 그 시험만 옮긴다.
  - 원인 참고: `S3` 처럼 상시 일은 브랜치 이름에 스킬 전체 이름이 없으면 `claim_task.py --skill` 이 겹침을 못 볼 수 있다(추정: `S3-schedule-write-errors`, `S3-s3-write-paths` 둘 다 `teacherlesson-schedule` 이 이름에 없음).
- **#114**: 지운 옛 글의 주요 낱말(결재선 키·선택자, 12시간 갱신, 첨부 처리, 중단 조건, 저장하지 않는 정보)이 새 글에 남아 있음. 단추 이름 `결석·체험학습 접수·상신 대상 확인`, 버전 1.7.2 가 확장 파일과 같음. 문장 하나하나를 전부 대조하지는 않음. 실제 NEIS 는 확인 안 함.
- **#117**: 설명이 그 폴더 `.gitignore`(`output/`·`pdf_splits/`·`groups.json`)와 맞음. 실제 파일은 `*.pdf`·`*.part` 도 막으므로 원하면 한 마디 더할 수 있음(필수 아님).
- **#115**: 49 통과(pytest). pytest 방식이라 `python -m unittest` 로는 0개가 돈다. CI 의 수업 비서 칸은 pytest 라 돌아간다.
- **#126**: 41 통과(pytest·unittest). 데이터 폴더를 임시 폴더로 바꾸고 Gemini 는 가짜.
  - `.github/workflows/check.yml` 에 `util-notebooklm` 칸이 없어 자동 점검에서는 돌지 않는다 → 넣을지 결정(공용 파일).
  - 시험이 만든 임시 데이터 폴더(`mkdtemp`)는 지우지 않는다(사소함).

## 다른 PR 에서 본 것

- #113 은 #123·#124·#125 중 일부와 `ISSUES.md` 또는 작업 일지(`claude-web-173.md`)가 충돌한다. #113 을 합칠 때 일지는 두 쪽 줄을 모두 남기면 된다.
