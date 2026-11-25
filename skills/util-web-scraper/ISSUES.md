# util-web-scraper 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

_없음_

## 📌 백로그

### ISSUE-004: 인덱서가 실패해도 "완료! 검색 가능" 이라고 알린다 (2026-11-26)
- **상태**: 📌 백로그
- **증상**: `run_scraper_and_indexer()` 가 `indexer.py` 의 종료 코드를 확인하지 않고 항상 "✅ 완료!" 를 출력한다. 인덱스가 갱신되지 않았는데도 검색이 된다고 안내한다. 스크래퍼 실패 때도 종료 코드는 0 으로 끝난다.
- **원인**: 인덱서 결과(`returncode`) 확인과 종료 코드 전달이 없다.
- **해결/조치**: (미적용) 인덱서 실패 시 오류를 알리고 `sys.exit(1)`. 시험은 xfail.
- **관련 파일**: `scripts/add_urls.py`(`run_scraper_and_indexer`)

### ISSUE-003: 같은 사이트가 끝 슬래시·대소문자만 달라도 중복으로 들어간다 (2026-11-26)
- **상태**: 📌 백로그 (사소함)
- **증상**: `https://a.com` 이 있는데 `https://a.com/` 을 추가하면 새 URL 로 들어가 같은 사이트를 두 번 수집한다(수집 사이 5초 대기라 시간도 늘어남).
- **원인**: 문자열이 정확히 같을 때만 중복으로 본다.
- **해결/조치**: (미적용) 비교할 때만 끝 `/` 제거·호스트 소문자화. 시험은 xfail(현재 동작은 통과 시험으로 남김).
- **관련 파일**: `scripts/add_urls.py`(`add_urls`)

### ISSUE-002: 설정에 `target_sites` 가 없으면 URL 추가가 KeyError 로 멈춘다 (2026-11-26)
- **상태**: 📌 백로그
- **증상**: `config.json` 에 `target_sites` 키가 없으면 `config["target_sites"].append(...)` 에서 `KeyError`. 같은 함수 위쪽에서는 `get("target_sites", [])` 로 기본값을 쓴다. (`target_sites` 항목에 `url` 이 없어도 `item["url"]` 에서 같은 오류.)
- **원인**: 읽을 때와 추가할 때 처리가 다르다.
- **해결/조치**: (미적용) `config.setdefault("target_sites", [])` 사용. 시험은 xfail.
- **관련 파일**: `scripts/add_urls.py`(`add_urls`)

### ISSUE-001: EduSearch 경로가 코드·문서에 고정되어 있다 (2026-11-26)
- **상태**: 📌 백로그 (**교사 확인 필요**: EduSearch 위치)
- **증상**: `scripts/add_urls.py` 의 `EDUSEARCH_DIR` 와 `SKILL.md` 에 특정 계정의 절대 경로(`C:\Users\…\Documents\GitHub\edusearch`)가 그대로 적혀 있다. 다른 PC·계정에서는 동작하지 않고, 저장소 규칙("절대 경로 하드코딩 금지")에도 어긋난다. 그래서 시험은 이 값을 바꿔 끼워서 돌린다.
- **원인**: 처음 만든 PC 기준으로 적었다.
- **해결/조치**: (미적용) 중앙 `.env` 에 `UTIL_WEB_SCRAPER__EDUSEARCH_DIR` 를 두고 `load_env()` 로 읽기. `__main__`(argparse) 부분도 이때 함께 시험 가능하게 된다.
- **관련 파일**: `scripts/add_urls.py`, `SKILL.md`

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
