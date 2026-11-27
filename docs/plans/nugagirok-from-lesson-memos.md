# 설계 메모: 🙋 학생 발표·관찰 메모 → 누가기록 초안 (S7, ISSUE-008 8번)

claude-web-lee2131@hanmail · 2026-11-27 · 코드는 만들지 않음(설계만). 지어낸 곳은 "확인 필요"·"추정"으로 표시.

## 하려는 것
수업 중 🙋 로 남긴 학생 발표·관찰 메모를 학생별·날짜별로 모아 **누가기록 초안 글**을 만든다. 교사가 고쳐서 쓰는 초안까지만 — NEIS 입력은 이 일의 범위 밖(교사가 확인한 뒤 별도 일).

## 지금 있는 것 (코드에서 확인)
- 수업 기록: `데이터 폴더/sessions/<YYYY-MM-DD>/<교시>교시_<과목>.json`, 안에 `memos: [{t, at, kind, text, …}]`. 🙋 는 `kind == "student"` (`web/index.html` 의 `data-k="student"`, `addMemo()`).
- `weekly_report.py`: `load_sessions(sessions)` → 기록 목록(날짜는 폴더 이름), `student_name(text)`(첫 낱말), `known_names(records)`, `mask()`, `JOSA`. 학생 절 묶기 한계는 ISSUE-038.
- 명단: T89(교사 결정 2026-11-26)가 `…\my-skills-data\teacherlesson-assistant\학생명단.csv`(열 `번호,이름`)를 정함 — **아직 구현 전**. 이 일은 그 명단이 생긴 뒤가 쉽다.
- NEIS 쪽 화면 정보: `classmanage-evaluate-to-neis/SKILL.md` 169~176행 — 행동특성 누가기록 목록 열은 `ghvrDevEnfcYmd`(관찰일자 YYYYMMDD)·`ghvrDevCn`(내용), 입력 때 같은 날짜+같은 내용이면 건너뜀.
- **확인 필요**: SKILL 이 말하는 누가기록 파일(`2026_1학기_행동특성_누가기록.md`)의 글 모양, 그 파일을 읽어 NEIS 에 넣는 스크립트(`scripts/` 에는 성취·의견·교과 입력만 보임). 그래서 아래 출력 모양은 **임시 제안**이다.

## 설계

### 1. 새 파일 `skills/teacherlesson-assistant/nugagirok.py` (순수 함수 + 작은 CLI)
`weekly_report.py` 처럼 가짜 데이터로 시험할 수 있게 글만 다룬다. `weekly_report` 의 `load_sessions`·`student_name`·`JOSA` 는 **가져다 쓴다**(복사 금지, 이름 묶기 고침이 한 곳에 모이게).

| 함수 | 하는 일 |
|---|---|
| `collect(records, start, end, roster=None)` | 기간 안 기록에서 `kind == "student"` 메모만 뽑아 `{day, period, subject, student, text}` 목록. 학생 이름은 명단이 있으면 명단과 맞추고(조사 떼기: `학생A가` → `학생A`), 없으면 `student_name()`; 이름을 못 정하면 `student=None` → 초안에서 "이름 확인 필요" 절 |
| `by_student(items)` | 학생별 → 날짜순 묶기 (명단이 있으면 번호순) |
| `render_markdown(groups, term)` | 교사가 고치는 글. 학생마다 `### 번호. 이름`, 줄마다 `- YYYY-MM-DD 과목: 내용` |
| `render_rows(groups)` | NEIS 열 이름에 맞춘 목록 `[{"name":…, "ghvrDevEnfcYmd": "YYYYMMDD", "ghvrDevCn": …}]` (임시 제안, NEIS 입력 일이 생기면 맞춤) |
| `main(argv)` | `python nugagirok.py --from 2026-09-01 --to 2026-11-30` → `데이터 폴더/reports/nugagirok-<시작>_<끝>.md` 와 `.rows.json` 저장. 콘솔에는 학생 수·메모 수만 출력(메모 글·이름은 찍지 않음 — `weekly_report` 와 같은 방식) |

- 관찰일자 = 기록 폴더 날짜. 같은 날짜·같은 내용은 한 줄로(NEIS 중복 검사와 같은 기준).
- 이미 쓴 구간을 다시 돌려도 안전: 파일은 덮어쓰기만 하고 NEIS·Supabase 에는 아무것도 보내지 않음.

### 2. 메모 글 쓰는 법 (기록 문장 원칙은 T54 가 정할 일)
- 이 일은 **메모 글을 고쳐 쓰지 않는다**(AI 에 학생 이름을 보내지 않기 위해). 초안은 교사가 읽고 사실 위주로 다듬는다.
- 나중에 AI 로 다듬고 싶으면: 이름을 `학생1`… 으로 바꿔 보내고 돌려받은 뒤 되돌리는 방식만(이름·번호 그대로 전송 금지). 이는 교사 결정 필요.
- T54(기록 문장 원칙: 사실 위주·평가어 피하기)는 지금 **보류(묶음 밖)**. 초안 화면 위쪽에 "사실만 적기" 한 줄 안내만 넣고, 규칙 자체는 T54 결정 뒤.

### 3. 저장 위치·개인정보
- 결과는 `data_dir()` 아래 `reports/` 만(학생 이름이 들어가므로 저장소·Supabase·외부 서비스 금지). 파일 머리에 `weekly_report` 와 같은 경고 문구.
- 시험은 `학생A`·`학생B` 같은 가짜 이름과 임시 폴더만.

### 4. 시험 (`tests/test_nugagirok.py`, 가짜 sessions)
1. 🙋 메모만 모이고 다른 kind·`(표시)` 는 빠진다
2. 기간 밖 날짜 제외, 경계 포함
3. `학생A`·`학생A가` 가 한 학생으로 묶임(명단 있을 때), 명단 없을 때는 현재 한계대로(ISSUE-038 ③ 시험과 같이 움직임)
4. 같은 날 같은 내용 중복 제거, 날짜 순서
5. 이름 못 정한 메모는 "이름 확인 필요" 절로
6. `ghvrDevEnfcYmd` 가 `YYYYMMDD` 8자리
7. 콘솔 출력에 이름·메모 글이 없음
8. 깨진 JSON·빈 폴더에서도 멈추지 않음(`load_sessions` 의 broken 수 그대로 보고)

### 5. 나누기 (일 만들기 제안)
| 번호(제안) | 일 | 등급 | 선행 |
|---|---|---|---|
| N1 | `nugagirok.py` 순수 함수 + 시험 + 저장(위 1·3·4) | R | 명단은 없어도 되게(없으면 `student_name()`) |
| N2 | 수업 비서에 `/api/nugagirok`·단추("누가기록 초안 만들기", 기간 고르기) | P | N1, T89 |
| N3 | 초안을 NEIS 누가기록 화면에 넣기(`classmanage-evaluate-to-neis`) | P, **교사 확인 뒤에만** | N1, 누가기록 파일 모양 확인, `--dry-run` 먼저 |

## 교사가 정할 것
1. 초안 글 모양(위 임시 제안)으로 시작해도 되는지, 아니면 이미 쓰는 누가기록 파일 모양이 있는지(있으면 한 예를 가짜 이름으로 알려 주기).
2. 학생 메모 글을 AI 로 다듬는 것을 원하는지(원하면 번호 치환 방식만).
3. T54(기록 문장 원칙)를 지금 풀지.
