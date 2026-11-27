# 검토: T92 teacherlesson-schedule 깨진 한글 되살림 (PR #113, `a91bf89`)

claude-web-lee2131@hanmail · S2 · 2026-11-27 · 코드는 고치지 않고 보고만 함

## 결론: 합쳐도 됨 🟢 (아주 작은 🟡 하나)

## 확인한 것
- 범위: `auto_planner.py`·`schedule.py`·`server.py`·`ISSUES.md`·새 시험 `tests/test_korean_restore.py`·일지만 바뀜. 식별자·로직은 그대로, 글자(문구·시트/칸 이름)만 바뀜.
- 시험: `pip install -r requirements.txt` 한 환경에서 `tests` 108 통과. `SHEET_NAME` 환경값을 빼고도 `test_auto_planner`·`test_korean_restore` 통과(ISSUE-003 해결 확인).
  (flask·PyMuPDF 가 없는 환경에서는 `test_server*` 수집 오류·`ServerPeriodFallbackTests` 2개 실패 — 코드 문제가 아니라 설치 문제, CI 의 schedule 칸은 설치하므로 영향 없음.)
- **시험이 정말 잡는지(일부러 망가뜨림)**: 휴업일 `날짜` 칸 이름을 다시 깨뜨림 → 2개 실패 / 기본 시트 이름을 `?쒗듃1` 로 → 4개 실패 / `server.py` 의 `계획교시` → 2개 실패 / 진도율 키 → 2개 실패. 원래대로 돌리면 17개 통과.
- 되살린 이름 대조: `시트1`, `날짜`, `과목`, `차시`, `계획교시`, `진도율`, `요일` 은 `schedule.py` 의 `COLUMN_*`·`get_progress` 키와 같음.
- 개인정보·비밀값 모양: 추가 줄에서 찾지 못함(전화번호·키 모양 0건).

## 🟡 남은 깨진 글자 1곳 (동작에는 영향 거의 없음)
`auto_planner.py` 506줄(미리보기 출력): `record.get('??⑥썝', '')` — 깨진 키가 그대로 남아 있어 '배정 미리보기'의 단원 칸이 늘 빈칸으로 나옴. 문맥상 `schedule.COLUMN_UNIT`(`대단원`)로 보임(추정). 같은 줄의 `차시`는 고쳐졌으니 이 한 줄만 빠진 것. 이 시험이 "소스에 한자·대체 문자 없음"을 보는데 `??` 모양은 못 잡아서 통과함 → 시험에 `\?\?[^\s,)'"]` 같은 모양 검사를 더하면 좋음(선택).

## 참고(고치라는 뜻 아님)
- 이모지 자리를 `[설정]`·`[안내]` 글자로 대신함 — 원래 무엇이었는지는 알 수 없어 문제 없음(ISSUES 에도 적혀 있음).
- `resolve_progress_worksheet` 가 두 번 정의된 것(앞 정의는 안 쓰임)은 ISSUES '남은 것'에 이미 기록됨.
- 실제 시트에서 휴업일 날짜 칸 위치 확인은 교사 PC 에서 필요(작업자도 '확인 필요'로 적음).
