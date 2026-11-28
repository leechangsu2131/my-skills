---
name: personal-daily-intake
description: 그날 있었던 일을 제미나이(스킬)에 쭉 말해 받은 정리본(md)을 갈래별로 나눠 저장한다 — 할 일·일정은 일정DB 시트(카톡 아침 알림), 읽은 책은 Notion 독서 DB, 수업 후기·생각은 옵시디언 노트, 전체 원문은 볼트 daily/날짜.md. '하루 기록 저장해줘', '오늘 기록 넣어줘', '제미나이 정리본 저장', '하루 정리 넣어줘', '일일 기록' 같은 요청에 쓴다.
metadata:
  category: 개인·생활
  status: 개발
  version: v0.1.0
  summary: 제미나이 스킬이 받아쓰고 나눈 하루 기록 md를 일정DB 시트·Notion 독서 DB·옵시디언(daily/, 00_Inbox, 10_NOTE/수업)에 표로 확인받고 한 번에 나눠 넣는다. 같은 것을 두 번 넣지 않는다.
---

# personal-daily-intake — 하루 기록 나눠 넣기

말하기와 받아쓰기는 제미나이가, 저장은 이 스킬이 맡는다. 다시 찾는 곳은 옵시디언 볼트 하나로 모으고,
Notion·시트에는 처리할 것(할 일, 책 행)만 보낸다. mem 대신 볼트 `daily/`가 원시 기록 층이다
(볼트 운용지침 v15 보완 2026-11-27).

## 흐름
1. 제미나이에서 [gem_prompt.md](gem_prompt.md)의 지침으로 만든 제미나이 스킬에 하루 일을 쭉 말한다 → md 한 장을 받는다.
2. 그 대화 화면에서 즐겨찾기 **'제미나이 내보내기'**(북마클릿)를 누른다 → 다운로드 폴더에 `하루기록-YYYY-MM-DD.md`(정리본)와
   `gemini-날짜-제목.json`(내가 쓴 말·답 전부)이 생긴다. `plan`·`apply` 가 다운로드 폴더에서 집어 inbox·대화 보관 폴더(`gemini\`)로 옮긴다.
   북마클릿 만들기: `python intake.py bookmarklet` → 클립보드의 주소를 Chrome 즐겨찾기 URL 칸에 붙여 넣기(한 번만).
   다운로드 대신 중앙 `.env` 의 `PERSONAL_DAILY_INTAKE__DROP` 폴더(예: 구글 드라이브 `my-skills-개인자료\노트`)에 둬도 된다 — 거기 것은 원본을 두고 복사만.
   **정리본 없이 그냥 나눈 대화**(하루 기록 스킬 전에 한 대화 등)는 `python intake.py convert` — 그 json 에서 내가 한 말만 모아
   Gemini CLI 에 같은 지침으로 다시 정리시켜 inbox 에 md 로 둔다(날짜를 모르면 '확인 필요'에 '날짜 확인').
   북마클릿 없이: md 를 복사해 `내 문서\my-skills-data\personal-daily-intake\inbox\YYYY-MM-DD.md`로 저장해도 된다.
3. Claude에게 "하루 기록 저장해줘" → Claude가 `plan`으로 표를 보여 준다 → 교사가 동의하면 `apply`.

## 언제 쓰나
- 제미나이 하루 기록 정리본을 저장할 때
- 쓰지 않음: 수업 중 메모·녹음(→ `teacherlesson-assistant`), 학생 기록 일괄 정리(→ `classmanage-student-classifier`),
  볼트 전체 재분류(→ `personal-obsidansystem-main`)

## 준비
- `pip install -r requirements.txt` (requests, gspread, google-auth)
- 중앙 `.env`: `DB_SHEET_ID`·`GOOGLE_SERVICE_ACCOUNT_FILE`(school-todo-kakao 와 같은 값), `NOTION_TOKEN`,
  `PERSONAL_DAILY_INTAKE__NOTION_READING_DB_ID`(독서 DB), 볼트 경로 `PERSONAL_OBSIDANSYSTEM_MAIN__VAULT`
  (이 스킬만 다른 볼트를 쓰려면 `PERSONAL_DAILY_INTAKE__VAULT`)
- **Notion 연결**: `NOTION_TOKEN` 의 연결 이름은 **`book manage`** 다(2026-11-28 확인). 이 연결에 공유된 DB 만 읽고 쓸 수 있다 —
  지금은 독서 DB 뿐. 업무일지·일기·습관 DB 를 쓰려면 Notion 에서 그 DB(또는 DB 가 든 페이지)를 열고
  오른쪽 위 ··· → 연결 → `book manage` 추가. 확인은 `python intake.py notion`(무엇이 보이고 무엇이 안 보이는지 + 연결 방법).
  공유한 뒤 업무·일기·습관에 실제로 쓰는 기능은 ISSUE-001 로 붙인다(그전까지 그 갈래는 daily 에만).

## 사용법
```powershell
python intake.py plan            # inbox 의 가장 최근 md → 표만 (아무것도 안 바꿈)
python intake.py apply           # 표대로 넣기
python intake.py apply 파일.md --skip notion   # 인터넷·권한 문제로 한쪽을 빼고
```

## 갈래 → 보낼 곳
| 갈래 | 보낼 곳 |
|---|---|
| 할일 | 일정DB 시트, 구분 `개인`, 날짜=기한 (카톡 아침 알림 `D-n`) |
| 일정 | 일정DB 시트, 구분 `학교`/`출장` |
| 수업 · 후기 | 새 노트 `10_NOTE/수업/<제목>.md` (`type: 후기`, `engine: experiment`) |
| 수업 · 다음 아이디어 | 새 노트 `00_Inbox/<제목>.md` (`type: idea`) |
| 수업 · 요령 | 후보만 — 과목 노트(`수학.md` 등) '진행 방식'에 덧붙이기는 교사 확인 뒤 |
| 생각 | 새 노트 `00_Inbox/<제목>.md` (`type: 단상`, domain 은 제미나이가 준 값) |
| 독서 | Notion 독서 DB 새 행(책제목·한줄평·읽은기간) |
| 학생 | 후보만 — `classmanage-student-classifier` |
| 투자 | 후보만 — 투자시트 분위기 일지(`personal-invest-sheet`) |
| 업무·일기·습관 | 지금은 daily 에만 (Notion DB 연결 공유 전, ISSUE-001) |
| 개선 | 데이터 폴더 `ideas.json` 에 적음(대상 스킬을 낱말로 짐작) → `python intake.py ideas` 로 보고, 교사가 고른 것을 그 스킬 `ISSUES.md` 📌 백로그로 옮김 → S8 로 작업자에게 감 |
| 모든 조각 | 볼트 `daily/YYYY-MM-DD.md` (원문 그대로 + '보낸 곳' 목록) |

## Claude 행동 지침
- 먼저 `plan` 표를 보여 주고 교사가 동의한 뒤에만 `apply`. 표를 고치고 싶다고 하면 inbox 의 md 를 고친 뒤 다시 `plan`.
- 원문은 고치지 않는다. 기존 노트는 고치지 않는다(새 파일만 만든다). 후보는 교사가 고르면 그때 손으로 반영한다.
- 공명은 교사가 직접 한 말만 — 제미나이가 `공명: 없음`이면 비워 둔다.
- 민감 조각(학생 이름·가족·건강·남의 사적인 일)은 화면 표에 제목을 내지 않는다. 볼트에는 넣되 `민감: true`를 단다.
- **개선 아이디어 옮기기**: apply 뒤 `python intake.py ideas` 표를 보여 주고, 교사가 고른 번호를 그 스킬 `ISSUES.md` 📌 백로그 맨 위에 `### ISSUE-<다음 번호>: <제목> (날짜)` + `- **상태**: 📌 백로그 — 교사 아이디어(하루 기록 <날짜>)` + 내용으로 적는다. my-skills 는 공개 저장소라 학생 이름·사적인 내용은 빼고 기능만 쓴다. 대상이 `HomePage`·`invest-sheet(GitLab)`이면 그 저장소의 ISSUES 에, `(대상 확인 필요)`면 교사에게 묻는다. 옮긴 뒤 `python intake.py ideas --done <번호들>`.
- 볼트 파일은 직접 커밋하지 않는다. 이창수의 Obsidian Git 자동 백업이 올린다(볼트 작업자 가이드).

## 문서
- [gemini_bookmarklet.js](gemini_bookmarklet.js) — 제미나이 대화 내보내기 북마클릿 원본(`python intake.py bookmarklet` 이 한 줄로 만듦)
- [gem_prompt.md](gem_prompt.md) — 제미나이 스킬 지침(형식을 바꾸면 `intake.py`도)
- [ISSUES.md](ISSUES.md) — 문제·해결 기록, 진행 중인 일
