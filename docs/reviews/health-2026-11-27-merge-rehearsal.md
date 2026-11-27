# 합치기 예행연습 (S5, 2026-11-27, claude-web-소연)

임시 복사본에서 `origin/main`(9cc58c9) 위에 열린 PR 을 차례로 합치고 시험했다. `main` 과 남의 브랜치는 바꾸지 않았다.

## 합친 순서
#113 → #114 → #115 → #117 → #119 → #121 → #122 → #124 → #125 → #126 → #127 → #128
(#118·#123 은 겹쳐서 뺌 — #128 검토 참고)

## 충돌: 전부 "두 쪽 줄을 모두 남기기"로 풀림
- 작업 일지 `docs/worklog/claude-web-173.md`·`-162.md`·`-소연.md`
- `skills/teacherlesson-schedule/ISSUES.md` (#125 합칠 때). 코드 파일 충돌은 없음.
- 풀고 나면 `ISSUE-8` 제목 앞 빈 줄 하나가 없어진다(보기만의 문제).

## 합친 상태의 시험
| 대상 | 결과 |
|---|---|
| teacherlesson-assistant (`tests sites test_assistant_server.py test_supabase_schedule.py`) | 477 통과, 2 건너뜀, 1 xfail |
| teacherlesson-schedule `tests` | 138 통과, 6 xfail |
| teacherlesson-schedule (SKILL.md 의 unittest 명령) | 119 통과 |
| util-notebooklm | 41 통과 |
| teacherlesson-guide/splitter | 10 통과 |
| teacherlesson-guide/mapper | 34 통과, **2 실패** (`main` 에서도 같음. ISSUES 에 기록됨, 윈도우 경로 때문으로 추정) |
| 저장소 `tests/` | 395 통과 |
| `test_tools.js`, from-neis `popup.test.js` | 실패 0 |
| `build_catalog.py --check`, `check_privacy.py` | 통과 (카탈로그 경고 1: `util-school-print/ParameterSetObject.pdf` 추적 중) |

## 합친 뒤 작게 남는 것
- `teacherlesson-schedule/SKILL.md` 의 시험 명령에 `test_korean_restore`·`test_server_write_routes_schedule_error` 가 빠짐(CI 는 pytest 로 `tests` 전체를 돌려 영향 없음).
- #127 검토가 남긴 것: `auto_planner.py` 에 깨진 키 한 곳(`??⑥썝`, 506줄 근처).

## 확인 못 한 것
윈도우, 실제 시트·Supabase·NEIS, 화면 동작.
