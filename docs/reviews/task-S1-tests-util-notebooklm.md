# 검토: task/S1-tests-util-notebooklm (PR #126)

- 검토: claude-web-yi2131@naver · 2026-11-27 (상시 일 S2)
- 대상 커밋: `pr126` 머리 — main 기준. 이 브랜치는 고치지 않았음
- **판정: 🟢 합치기 권함**

## 확인한 것

- `skills/util-notebooklm` 에서 `python -m unittest discover -s tests` → 41개 통과.
- 고친 파일은 시험 1개(`tests/test_nlm.py`)와 작성자 일지뿐. 소스(`nlm.py`)는 그대로. 개인정보·전화번호·비밀값 없음(API 키는 `가짜키-테스트`).
- 시험이 진짜로 잡아내는지 `nlm.py` 를 임시로 망가뜨려 봄(확인 뒤 원상 복구). 전부 시험이 깨짐:
  - 시간 제한 최소값 60→30, 최대값 120→300
  - `page_refs` 의 끝 쪽 처리(`max(a, b) + 1` → `b + 1`)
  - 쪽 번호 0 거르기(`p >= 1` → `p >= 0`)
  - `is_low_text` 의 `and` → `or`
  - 제미나이 호출의 `-e none` 빼기
- PDF·제미나이 CLI·네트워크·실제 `.env` 를 쓰지 않음(가짜 쪽, 가짜 `subprocess.run`, 임시 데이터 폴더).

## 🟡 작은 것

- 시험 파일이 불러올 때 `os.environ["MY_SKILLS_DATA_DIR"]` 를 정하고 되돌리지 않음. 한 프로세스에서 다른 스킬 시험과 함께 돌리면 그 값이 남음(스킬별로 따로 돌리는 지금은 문제 없음).
- `tempfile.mkdtemp` 로 만든 임시 폴더를 시험 뒤 지우지 않음.
- 시험 중 `os.startfile` 은 `create=True` 로 가짜 처리해 리눅스에서도 돎. 윈도우의 실제 `startfile` 은 확인 못 함.

## 확인 못 한 것

- 진짜 제미나이 CLI 동작, 윈도우에서 노트북 열기(교사 PC).
