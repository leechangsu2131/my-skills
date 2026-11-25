# classmanage-exam-graderV2 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

_없음_

## 📌 백로그

### ISSUE-002: 예전 Git 기록과 남아 있는 관련 파일 확인 (2026-11-26)
- **상태**: 📌 백로그 (교사 확인·결정 대기)
- **증상**: ① 뺀 PDF 2개는 예전 커밋에 남아 있어 내려받을 수 있음. ② 같은 폴더에 PDF 가 아닌 관련 파일이 아직 추적 중: `data_test/artifacts/gemini_review_packets/` 의 `.json`(검토 꾸러미), `logs/` 의 `2026-04-26.jsonl`·`server.log`(뺀 PDF 이름이 나옴).
- **원인**: Git 은 파일을 빼도 예전 기록을 보관함. ②는 은정이 파일 안을 열어 보지 않아 **학생 정보가 있는지 모름 — 확인 필요.**
- **해결/조치**: 하지 않음. 학생 이름·답안이 있었는지 교사 PC 에서 확인한 뒤, 있으면 추적 해제·`.gitignore`·기록 정리를 교사가 정함(되돌리기 어려운 일). 없으면 이 항목을 닫음.
- **관련 파일**: `skills/classmanage-exam-graderV2/logs/`, `skills/classmanage-exam-graderV2/data_test/artifacts/`

## 🟢 해결됨

### ISSUE-001: 시험지로 보이는 PDF 2개가 공개 저장소에 올라가 있음 (2026-11-25)
- **상태**: 🟢 해결 (2026-11-26, 교사 지시 "빼자" — 브랜치 fix/untrack-tracked-outputs)
- **증상**: `python tools/build_catalog.py --check` 의 새 경고(T24)가 `data/raw_pdfs/` 아래 PDF 1개와 `data_test/artifacts/gemini_review_packets/` 아래 PDF 1개가 git 에 추적된다고 알림.
- **원인**: 추정 — 시험용·검토용 자료가 `.gitignore` 에 없어 같이 커밋됨.
- **해결/조치**: PDF 2개를 저장소에서 빼고 `.gitignore` 에 `data/raw_pdfs/*.pdf`, `data_test/artifacts/**/*.pdf` 를 넣음(같은 폴더의 `dummy.png`·`.json` 등은 그대로 둠). 교사 PC 에 같은 이름 파일이 있으면 이 변경을 합칠 때 지워질 수 있으니, 필요하면 합치기 **전에** 다른 곳(`data_dir()`)에 복사해 둘 것. 예전 기록과 남은 파일은 ISSUE-002.
- **관련 파일**: `.gitignore`


<!--
항목 양식 (복사해서 사용)

### ISSUE-001: 한 줄 제목 (YYYY-MM-DD)
- **상태**: 🔵 진행 중 | 📌 백로그 | 🟢 해결 (YYYY-MM-DD)
- **증상**: 무엇이 어떻게 안 됐나 (오류 메시지 그대로)
- **원인**: 확인된 원인
- **해결/조치**: 무엇을 바꿨나, 재발 방지
- **관련 파일**: `script.py`, 커밋 해시
-->
