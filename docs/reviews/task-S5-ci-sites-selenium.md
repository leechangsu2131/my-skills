# 검토: task/S5-ci-sites-selenium (PR #145)

- 검토: claude-web-yi2131@naver · 2026-11-27 (상시 일 S2)
- 참고: 이 검토를 올리기 전에 PR 이 이미 합쳐졌음(2026-11-28 확인). 아래 🟡 은 합쳐진 뒤에 남은 확인거리
- 대상: PR 머리 — main 기준. 이 브랜치는 고치지 않았음
- **판정: 🟢 합치기 권함**

## 확인한 것

- 바꾼 곳은 `.github/workflows/check.yml` 한 칸(`teacherlesson-assistant`)에 `extra: selenium` 추가와 안내 글 고침뿐(공용 파일을 한 작업자만 고치는 규칙: 브랜치 이름에 `ci` 있음).
- YAML 이 문법상 올바름. `extra` 는 같은 파일 161줄 `pip install -r … ${{ matrix.extra }} pytest` 로 설치되는 칸이라 쓰임이 맞음. 다른 칸(`httpx`, `pyyaml PyMuPDF` 등)과 같은 방식.
- selenium 을 설치한 환경에서 `sites` 시험이 **116 통과·건너뜀 0** (설치 전에는 98 통과·6 건너뜀). 즉 이 PR 이 합쳐지면 음악 도우미 시험이 CI 에서 실제로 돌게 됨. PR #143 의 음악 쪽 재현 시험(`expectedFailure` 4개 중 2개)도 CI 에서 비로소 확인됨.
- 비밀값·개인정보 없음.

## 🟡 작은 것

- selenium 을 `requirements.txt` 가 아니라 `extra` 로 넣었다 → 로컬에서 `pip install -r requirements.txt` 만 하면 음악 시험은 여전히 건너뜀. 요구 파일에 넣을지(교사 PC 실행에도 필요한 패키지라 맞을 수도 있음)는 교사 결정.
- selenium 새 판이 CI 에서 갑자기 바뀌어도 이 시험은 브라우저를 띄우지 않아(가짜) 영향이 작을 것으로 추정. 문제가 생기면 버전을 고정.

## 확인 못 한 것

- GitHub Actions 실제 실행(이 환경에서는 못 돌림). 합친 뒤 첫 실행 결과 확인 필요.
