# 검토: task/S3-sites-longer-lesson-name (PR #143)

- 검토: claude-web-yi2131@naver · 2026-11-27 (상시 일 S2)
- 대상: PR 머리 — main 기준. 이 브랜치는 고치지 않았음
- **판정: 🟢 합치기 권함** (소스 안 고침, 재현 시험 + ISSUES 기록)

## 확인한 것

- 고친 파일은 시험 1개(`sites/test_lesson_pick_longer_name.py`)·`ISSUES.md`·작성자 일지뿐. 개인정보·비밀값 없음(예시는 `우리 지역의 문화` 같은 일반 이름).
- selenium 이 있는 상태에서 `python -m unittest test_lesson_pick_longer_name` → 8개: 통과 4(대조) + 예상된 실패 4. selenium 이 없으면 음악 쪽 4개는 건너뜀(`sites` 전체: 98 통과·6 건너뜀·2 xfail).
- `expectedFailure` 표시를 모두 떼고 돌려 보니 4개 모두 `AssertionError: 0 != 1` 로 실패 → **오류가 아니라 설명한 증상(띄어쓰기만 다른 차시 대신 더 긴 이름이 열림) 때문**에 실패함. 음악·사회, 차시·단원 네 칸 모두 해당.
- 대조 시험 2개(띄어쓰기만 다른 이름은 열림, 글자 그대로 같은 이름이 더 긴 이름보다 우선)는 지금 동작을 지켜서, 고칠 때 깨지면 알려 줌.

## 🟡 작은 것

- 고치는 사람이 `expectedFailure` 를 지울 때 "unexpected success" 로 알려 주므로 안전함. 단 CI 에 selenium 이 없으면 음악 쪽은 건너뜀 → PR #145(S5, CI selenium)가 합쳐져야 음악 쪽도 자동으로 돎.
- `ISSUES.md` 의 "교사 결정 필요"(더 긴 이름만 있을 때 묻고 열지) 항목은 코드 고침 전에 교사가 정해야 함.
- 가짜로 만든 목록은 `chapter` 에 순번만 넣음 — 실제 사이트 목록 모양과 같은지는 **확인 필요**(교사 PC).

## 확인 못 한 것

- 실제 사이트(아이스크림·두클래스)에서의 동작.
