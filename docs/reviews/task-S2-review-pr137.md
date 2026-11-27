# S2 검토 — PR #137 지도서 받기 시험 (2026-11-27, claude-web-소연)

그 브랜치는 고치지 않았다. **합쳐도 됨. 단, ISSUES 한 줄은 고치는 것이 좋음.**

## 확인
- 새 시험 25 통과. `main` 을 합친 상태의 저장소 `tests/` 420 통과.
- 일부러 망가뜨려 확인: ZIP 이름의 UTF-8 표시 무시(1 실패), PDF 머리 검사 제거(2 실패).
- `check_privacy.py` 통과. 크롬·사이트 접속 없음.
- `ISSUE-34` 번호는 겹치지 않음(`main` 은 33 까지).

## 고칠 것
- `skills/teacherlesson-guide/ISSUES.md` ISSUE-34 의 "맨 위 `tests/` 는 CI 가 안 돌림"은 지금 `main` 과 다름: `.github/workflows/check.yml` 의 `tests` 묶음에 `dir: .` 칸이 있다. 그 말을 지우면 됨.

## 합칠 때
- 충돌은 `docs/worklog/claude-web-173.md` 하나(두 쪽 줄을 모두 남기면 됨). 브랜치가 `main` 보다 55 커밋 뒤.

## 못 한 것
- 윈도우, CI 환경과 똑같은 설치 상태에서의 실행.
