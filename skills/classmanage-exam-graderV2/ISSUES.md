# classmanage-exam-graderV2 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

_없음_

## 📌 백로그

### ISSUE-001: 시험지로 보이는 PDF 2개가 공개 저장소에 올라가 있음 — 학생 정보 확인 필요 (2026-11-25)
- **상태**: 📌 백로그 (교사 확인 대기)
- **증상**: `python tools/build_catalog.py --check` 의 새 경고(T24)가 `data/raw_pdfs/` 아래 PDF 1개와 `data_test/artifacts/gemini_review_packets/` 아래 PDF 1개가 git 에 추적된다고 알림.
- **원인**: 추정 — 시험용·검토용 자료가 `.gitignore` 에 없어 같이 커밋됨. **학생 시험지(이름·답안)인지는 확인 필요**(은정은 파일을 열어 보지 않음). 학생 기록은 저장소에 두지 않는 규칙이 있음.
- **해결/조치**: 하지 않음. 교사 확인 뒤 학생 정보가 있으면 `git rm --cached` 와 `.gitignore`(`data/`, `data_test/artifacts/`) 정리, 기록 정리 방법을 따로 정함. 학생 정보가 없는 가짜 시험지라면 그대로 두고 이 항목을 닫음.
- **관련 파일**: `skills/classmanage-exam-graderV2/data/raw_pdfs/`, `skills/classmanage-exam-graderV2/data_test/artifacts/`

## 🟢 해결됨

_없음_

<!--
항목 양식 (복사해서 사용)

### ISSUE-001: 한 줄 제목 (YYYY-MM-DD)
- **상태**: 🔵 진행 중 | 📌 백로그 | 🟢 해결 (YYYY-MM-DD)
- **증상**: 무엇이 어떻게 안 됐나 (오류 메시지 그대로)
- **원인**: 확인된 원인
- **해결/조치**: 무엇을 바꿨나, 재발 방지
- **관련 파일**: `script.py`, 커밋 해시
-->
