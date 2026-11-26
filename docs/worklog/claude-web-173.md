# claude-web-173 일지

- 2026-11-25 19:19 T45 시작 (브랜치 task/T45-fix-catchup-tests)
- 2026-11-25 19:24 T45 PR 올림 — CatchUpTest 를 새 동작(요청 날짜 칸으로 옮기기·sort_order 기준 앞 차시 완료)에 맞게 다시 씀. test_supabase_schedule.py 41개 중 39 통과·1 건너뜀(PyMuPDF 없음)·1 알려진 실패(ISSUE-033, 코드 문제라 고치지 않고 기록). 소스를 일부러 틀리게 한 변이 9가지를 모두 시험이 잡음. 이 스킬 시험 전체 71 통과, build_catalog --check 문제 없음
- 2026-11-25 19:24 T47 시작 (브랜치 task/T47-memo-sync-fixes)
- 2026-11-26 04:12 T47 PR 올림 — memo_sync: 받은 메모에 서버 memo_key 저장·재사용(at 없는 메모 중복 해결), CLI 출력 UTF-8, 올리기 제외 종류 설정(MEMO_SKIP_KINDS, 학생 메모는 항상 제외), README·SKILL 사용법 절. tests/test_memo_sync.py 24→33개 통과, 변이 9가지 모두 시험이 잡음, build_catalog --check 문제 없음. 전체 시험의 실패 4개는 T45(PR #15) 대상으로 이 PR 과 무관
- 2026-11-26 04:13 T15 시작 (브랜치 task/T15-popup-pure-tests, 대상 teacherlesson-from-neis)
- 2026-11-26 04:15 T15 PR 올림 — teacherlesson-from-neis/tests/popup.test.js 새로 만듦(node:vm 에 가짜 document·chrome·Date 로 popup.js 를 그대로 불러옴, 소스 안 고침). 14개 통과, popup.js 를 일부러 틀리게 한 변이 22가지를 모두 시험이 잡음(처음엔 2개 놓쳐 시험을 보강). README 에 실행법 절. build_catalog --check 문제 없음
- 2026-11-26 04:50 T45 시작 — ISSUE-033 후속 (브랜치 task/T45-catchup-show-chosen-lesson, 교사가 '쓴다, 화면도 바뀌면 좋겠다'고 정함)
- 2026-11-26 04:55 T45 PR 올림 — day_schedule 이 따라잡기로 고른 예정 차시(manual_catch_up)를 먼저 보여 줌, LESSON_REL 에 source 추가. 시험 7개 추가·expectedFailure 제거, test_supabase_schedule.py 47 통과·1 건너뜀, 스킬 전체 150 통과. 변이 4가지 모두 잡힘. PR #15 위에 쌓은 PR
- 2026-11-26 05:05 T50 시작 (브랜치 task/T50-teacher-guide)
- 2026-11-26 05:15 T50 PR 올림 — teacherlesson-assistant README.md 에 '교사용 사용 설명서 (한 장)' 추가(날짜·교시 → 🌙 수업 준비 → 지금 할 일 → 메모 → 진도 조정, 그림 없이 쉬운 말), SKILL.md 에 안내 한 줄. 단추 이름·확인 창은 web/index.html 과 대조. 옛 이름 '여기부터 다시 잡기'를 화면 이름으로 표시. build_catalog --check 문제 없음
- 2026-11-26 10:53 T67 시작 (브랜치 task/T67-root-tests-xfail)
- 2026-11-26 10:54 T67 PR 올림 — teacherlesson-guide auto_split.json_object 가 설명 글의 중괄호에 걸리던 것을 고침(ISSUE-005 🟢). { 마다 raw_decode 로 읽어 lessons 목록 있는 첫 덩어리 사용. 루트 tests xfail 6개 중 이 2개의 xfail 을 지우고 시험 4개 추가(앞뒤 설명·문자열 속 중괄호·lessons 없는 덩어리 건너뛰기·안쪽 객체 거부). 변이 3가지 모두 잡힘, build_catalog --check 문제 없음. 이 PC 에 PyMuPDF 가 없어 json_object 시험만 가짜 fitz 로 돌림(10 통과) — 교사 PC·CI 에서 전체 확인 필요. 나머지 xfail 4개는 parse_flow(ISSUE-031·032)라 T68 이 맡고 있어 건드리지 않음
- 2026-11-26 10:55 T69 시작 (브랜치 task/T69-remaining-todo-xfail)
- 2026-11-26 11:00 T69 PR 올림 — 남은 todo·xfail 중 원인이 분명한 7개를 고침: util-storagemap(parseTags 배열 안 null 거르기 ISSUE-002, npm test 연결 ISSUE-003), teacherlesson-schedule(/api/catch-up 의 ScheduleError 를 JSON 오류로 ISSUE-001, /api/lessons 의 '날짜 시각' slot_date ISSUE-002), workflow-hub-main doc-indexer(ODT 제목 text:h 읽기 ISSUE-001, 프롬프트의 'None' ISSUE-003, 연도를 긴 숫자 속에서 읽던 것 ISSUE-004 ①). xfail·todo·expectedFailure 표시를 지우고 시험 추가. 시험: storagemap npm test 51 통과(todo 1), schedule 서버 시험 36 통과(전체 전·후 실패 목록 동일), doc-indexer 79 통과(xfail 2). 소스를 일부러 틀리게 한 변이(storagemap 2 + schedule 5 + doc-indexer 7)가지 모두 잡음, build_catalog --check 문제 없음. 이 PC 에 fitz·flask_cors 가 없어 schedule 시험은 저장소 밖 가짜 모듈로 돌림. 일부러 안 고친 것: storagemap 수량 빈칸(교사 확인 필요), doc-indexer 부서 순서·옛 조각 삭제(ISSUE-005)·유사도(ISSUE-006, 실제 ChromaDB 확인 필요), schedule 쓰기 경로 6개(T77 과 같은 함수 — 새 ISSUE-005 로 기록)
- 2026-11-26 11:00 T70 시작 (브랜치 task/T70-classroom-tools)
- 2026-11-26 16:22 T70 그만둠 — 시작 직후 TASKS 를 다시 확인하니 T70 은 ag-1 이 task/T89-classroom-tools-bundle 로 이미 완료·합침. 고친 파일 없음(브랜치에는 '시작' 줄만 있음, 지워도 됨). 다음엔 시작 전에 claim_task 로 다시 확인하고 다른 일(T71·T72·T73·T74·T76 중 빈 것)을 잡음
