# 할 일 목록 (작업자 공용)

> 규칙은 [WORKER_GUIDE.md](WORKER_GUIDE.md). 등급: **R** 저장소 브랜치·PR 가능 / **P** 교사 PC 에서만 / **T** 글만(ChatGPT 무료 등).
> 상태: `열림` · `진행 중(브랜치)` · `검토 대기` · `완료`. 상태는 교사 PC 에서 합칠 때 고칩니다(작업자는 이 파일을 고치지 않음).
> 브랜치 이름: `task/<번호>-<짧은-설명>`. 같은 번호의 원격 브랜치가 있으면 이미 누가 하는 중입니다.
> 마지막 정리: 2026-11-25

## A. 자동 시험 쓰기 (R) — 소스는 고치지 말고 `tests/` 만. 네트워크·비밀값·실제 사이트 없이 가짜(mock)로. 버그는 그 스킬 ISSUES.md 에 기록하고 시험은 xfail

| 번호 | 스킬 | 시험할 것 | 상태 |
|---|---|---|---|
| T01 | util-notebooklm | `nlm.py` split_text·page_refs·parse_pages·compact·write_source·gemini_ask 모델 바꾸기 | 진행 중(작업자 2) |
| T02 | teacherlesson-assistant | `prepare_lessons.py` parse_flow·parse_day·lesson_section, `build_units.py` group_lessons | 진행 중(작업자 2) |
| T03 | teacherlesson-guide | `auto_split.py` 검사·정규화 함수 | 진행 중(작업자 2) |
| T04 | teacherlesson-schedule | `server.py` 의 `/api/lessons`·`/api/catch-up` (Flask test client, schedule 함수는 가짜) | 열림 |
| T05 | classmanage-supabase-export | `parse_names`(JSON 배열·쉼표·공백), 학생별 나누기 | 열림 |
| T06 | personal-library-search | 순수 함수(검색어 정리·결과 파싱) | 열림 |
| T07 | util-storagemap | 순수 함수 | 열림 |
| T08 | util-pdf-translator | 쪽 나누기·글 정리 함수(번역 API 는 가짜) | 열림 |
| T09 | personal-obsidansystem-main | 노트 묶음·파일 이름 규칙 함수 | 열림 |
| T10 | personal-youtube-gemini-kakao-automation | 자막 정리·메시지 만들기 함수(카카오·Gemini 는 가짜) | 열림 |
| T11 | admin-gbetalk | 받은 쪽지 정리·파싱 함수(실제 발송 금지, 화면 조작 부분은 제외) | 열림 |
| T12 | personal-carrot | 순수 함수 | 열림 |
| T13 | workflow-hub-main / util-webtoguide / util-web-scraper | 순수 함수(각각 따로 브랜치) | 열림 |
| T14 | teacherlesson-workspace | `scripts/sync_semester2.py` 의 대조·변환 함수(Supabase 가짜) | 열림 |
| T15 | teacherlesson-from-neis | 크롬 확장 JS 의 순수 함수(날짜·표 파싱) — Node 로 도는 시험 | 열림 |

## B. 작은 기능·정리 코드 (R) — 각자 적힌 파일만

| 번호 | 할 일 | 고칠 파일 | 끝난 기준 | 상태 |
|---|---|---|---|---|
| T20 | 학교 PC 점검 도구 | teacherlesson-assistant `check_setup.py`, `점검_PC.bat` | 가짜 시험 통과 | 검토 대기(작업자 1, `feature/school-pc-check`) |
| T21 | 수업 메모 슈파베이스 동기화 부품 | teacherlesson-assistant `memo_sync.py`, `sql/lesson_memos.sql` | 가짜 HTTP 시험 통과 | 검토 대기(작업자 4, `feature/lesson-memo-sync`) |
| T22 | **개인정보 검사 도구**: 커밋 전에 바뀐 줄에서 전화번호·주민번호 모양·이메일·`sk-`/`AIza` 같은 키 모양·`C:\Users\<이름>` 을 찾아 경고 | 새 `tools/check_privacy.py` + 시험 | `git diff --staged` 를 읽어 경고, 가짜 예시 시험 | 열림 |
| T23 | **GitHub Actions**: PR 마다 `python tools/build_catalog.py --check` + 시험이 있는 스킬 pytest(비밀값 없이 도는 것만) + T22 | 새 `.github/workflows/check.yml` | PR 에서 초록불 | 열림 |
| T24 | `build_catalog.py --check` 강화: SKILL.md 없는 폴더·`generated_rows`/`tmp*`/`*.pdf` 같은 결과물이 추적되면 경고 | `tools/build_catalog.py` | 기존 통과 유지 + 새 경고 시험 | 열림 |
| T25 | classmanage-supabase-export: 결과 엑셀을 스킬 폴더가 아니라 `data_dir()` 에 저장, `verify=False` 없애기(학생 기록이 저장소 폴더에 생김) | `export.py` | 결과 경로 시험 | 열림 |
| T26 | util-notebooklm `gemini_ask` 에 모델별 대기 시간 인자(작은 글은 30~45초), 결과에 쓴 모델 돌려주기(전역 `LAST_MODEL` 대신) | `nlm.py` (+ 부르는 곳 `prepare_lessons.py`, `auto_split.py` 는 인자만) | 가짜 subprocess 시험 | 열림 (T01 끝난 뒤) |
| T27 | teacherlesson-schedule `/api/catch-up` 동시 요청 잠금(겹치면 수업배치 전체 다시 쓰기가 덮임) | `server.py` | 두 요청 동시 시험 | 열림 |
| T28 | teacherlesson-assistant `supabase_schedule.py` 진도 바꾸기 동시 요청 잠금 | `supabase_schedule.py` | 가짜 시험 | 열림 |
| T29 | 수업 비서 서버 `/favicon.ico` 404 → 작은 아이콘 | `assistant_server.py`, `web/` | 404 없음 | 열림 |

## C. 문서 정리 (R) — 정보는 빼지 말고 양식·쉬운 한국어로

| 번호 | 할 일 | 상태 |
|---|---|---|
| T30 | teacherlesson-assistant ISSUES 표준 양식·WORKLOG 겹침·SKILL/README 최신화 | 검토 대기(작업자 3, `docs/teacherlesson-assistant-cleanup`) |
| T31 | 영어 제목·문장이 섞인 SKILL.md/README.md 를 한국어로: admin-s2b-buyer, classmanage-iscream-evaluate, classmanage-student-classifier, classmanage-student-eval-generator, classmanage-student-photo-organizer, personal-record-trade (스킬마다 브랜치 따로 가능) | 열림 |
| T32 | teacherlesson-guide `splitter/README.md`(영어) → 한국어, 상위 SKILL.md 와 겹치는 부분 정리 | 열림 |
| T33 | 열린 항목이 많은 ISSUES.md 표준 양식으로: admin-neis-bot, school-todo-kakao, homepage-school-board, personal-video-note, teacherlesson-from-neis (스킬마다 따로) | 열림 |
| T34 | 스킬 58개 SKILL.md 앞머리 점검: description 이 "언제 쓰나"를 말하는지, summary 가 한두 문장인지, status 가 맞는지 → 고칠 목록을 `docs/reports/skill-meta-review.md` 로 (직접 고치지 말고 목록만) | 열림 |
| T35 | 코드가 없는 스킬(admin-buying-product, personal-attach-files, personal-free-parents-app, teacherlesson-aiep/classtool/courseware-builder 등) SKILL.md 가 실제 절차 문서로 충분한지 점검 목록 | 열림 |

## D. 교사 PC 에서만 (P) — Gemini CLI 작업자 등, 교사 PC 의 데이터를 씀

| 번호 | 할 일 | 상태 |
|---|---|---|
| T40 | 🌙 자동 준비로 만든 `flows/*.json` 을 같은 차시 지도서 글(`notebooklm/<과목>/<단원>.md` 구간)과 대조 → 다른 차시 내용·지도서에 없는 내용·시간 합계 이상 목록(`데이터 폴더/reports/flow_check_<날짜>.md`). 흐름은 고치지 않음 | 열림 |
| T41 | 한 주 수업 메모(sessions)에서 출판사별로 반복되는 특징 후보 뽑기 → 교사가 골라 `publisher_notes.json` 에 | 열림 |
| T42 | `teacherlesson-guide/auto_split.py` 를 2학기 남은 단원마다 실행, 검사 실패 단원 목록 + 이유 | 열림 |
| T43 | 다음 주 수업을 `prepare_lessons.py --date` 로 하루씩 준비하고 실패 차시 목록(음악은 지도서 PDF 없음 알려진 문제) | 열림 |
| T44 | 미술 5·6교시 진도 확인: 슈파베이스 진도는 둘 다 '괴불주머니 만들기', 사이트는 5~6차시 '자개 무늬로 생활용품 꾸미기' → 대조표만 만들고 교사 확인 | 열림 |

## E. 글만 (T) — ChatGPT 무료 등. 결과를 마크다운으로 교사에게

| 번호 | 할 일 | 읽을 파일(원문 주소로) | 상태 |
|---|---|---|---|
| T50 | 수업 비서 **교사용 사용 설명서 한 장**(화면 순서대로: 날짜·교시 → 🌙 수업 준비 → 지금 할 일 → 메모 → 진도 조정). 그림 없이 쉬운 말 | teacherlesson-assistant `README.md`, `SKILL.md` | 열림 |
| T51 | **학교 PC 처음 설치 안내서**(Python·Node·Gemini CLI·크롬 로그인·OneDrive, 순서·확인 방법) | teacherlesson-assistant `README.md`, T20 결과 | 열림 |
| T52 | 🌙 자동 준비 질문문(PROMPT) 개선안: 좋은 발문 기준(열린 질문·학생 경험 연결), 3학년 수준 말, 시간 배분 원칙을 넣은 새 문안 + 이유 | teacherlesson-assistant `prepare_lessons.py` 의 `PROMPT` | 열림 |
| T53 | 수업 비서 **손으로 확인하는 점검표**(새 기능마다: 무엇을 누르면 무엇이 보여야 하는지) | teacherlesson-assistant `README.md`, `ISSUES.md` | 열림 |
| T54 | 학생 발표 메모를 누가기록으로 모을 때의 **기록 문장 원칙**(사실 위주, 평가어 피하기, 개인정보) 초안 | classmanage-student-eval-generator `SKILL.md` | 열림 |
| T55 | 저장소 전체 **용어 사전**: 진도표·수업배치·차시·흐름·단원 개관·슬롯·record_key/lesson_id 등 쉬운 설명 한 줄씩 | `README.md`, teacherlesson-* SKILL.md | 열림 |
| T56 | `docs/SECURITY_LESSONS_LEARNED.md` 를 읽고 **작업자용 개인정보 체크리스트** 1쪽 | 그 파일, `docs/WORKER_GUIDE.md` | 열림 |
| T57 | 스킬 하나를 골라 SKILL.md 를 **쉬운 한국어로 다시 쓴 안**(뜻은 그대로) — 스킬마다 따로 | 고른 스킬 `SKILL.md` | 열림 |

## 원래 큰 계획 (교사 PC 의 Claude Code 가 함 — 참고)

- 학교 PC 공용: 글(md)·흐름·설정은 OneDrive, PDF 는 집 PC, 녹음은 PC 에만 (teacherlesson-assistant ISSUES "지금 상태와 남은 일" 0번)
- 🙋 학생 메모 → 학생 기록 표(슈파베이스) — 표 이름·명단 출처 확인 필요
- 미술 아트앤컬쳐 e-book 차시 자동 열기, 하이클래스 알림장 자동 게시, 나이스 시간표 변경 표시, 녹음 받아쓰기
