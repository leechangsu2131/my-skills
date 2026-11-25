# personal-youtube-gemini-kakao-automation 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

_없음_

## 📌 백로그

### ISSUE-001: 영상 요약 문서의 저작권 확인 (2026-11-26)
- **상태**: 📌 백로그 (교사 확인 대기, 급하지 않음)
- **증상**: `v/backlog_summaries/` 의 요약 문서 17개(문서당 6~28KB)가 남의 영상 내용을 꽤 길게 정리한 것이라, 공개 저장소에 두어도 되는지 불확실함. 자막 원문과 달리 가공한 글이라 이번에는 그대로 둠.
- **원인**: 확인 필요.
- **해결/조치**: 하지 않음. 문제 되면 `.gitignore` 에 `v/backlog_summaries/` 를 넣고 추적을 끊음. 참고: `v/run.log`·`v/run_test_now.log`(실행 기록, 인코딩이 섞임)와 `debug_empty_response.png`(Gemini 화면)는 읽어 봤고 비밀값·학생 정보는 없었음.
- **관련 파일**: `skills/personal-youtube-gemini-kakao-automation/v/backlog_summaries/`

## 🟢 해결됨

### ISSUE-002: 남의 영상 자막 원문 39개(약 25MB)가 공개 저장소에 올라가 있음 (2026-11-26)
- **상태**: 🟢 해결 (2026-11-26, 교사 지시 "읽어보고 위험하면 지우자" — 브랜치 fix/untrack-tracked-outputs)
- **증상**: `v/.transcript_cache/*.vtt` 29개, `v/tmp_*.vtt` 2개(T24 경고), `v/backlog_transcripts/` 7개, `v/last_transcript_*.txt` 1개가 추적 중. 직접 읽어 보니 남의 유튜브 영상 자막 원문이고, 전화번호·키·학생 정보는 없었음. 문제는 저작권.
- **원인**: `main.py` 가 만드는 캐시 폴더(`.transcript_cache`)와 `fetch_july_transcripts.py` 가 만드는 폴더를 그대로 커밋함.
- **해결/조치**: 39개를 저장소에서 빼고 `.gitignore` 에 해당 폴더·파일 모양을 추가. `main.py` 는 자막이 없으면 스스로 다시 받아 만들므로 동작에는 영향 없음. **합치기 전에** 교사 PC 에서 보관하고 싶은 자막이 있으면 복사해 둘 것.
- **관련 파일**: `.gitignore`, `skills/personal-youtube-gemini-kakao-automation/v/main.py`

<!--
항목 양식 (복사해서 사용)

### ISSUE-001: 한 줄 제목 (YYYY-MM-DD)
- **상태**: 🔵 진행 중 | 📌 백로그 | 🟢 해결 (YYYY-MM-DD)
- **증상**: 무엇이 어떻게 안 됐나 (오류 메시지 그대로)
- **원인**: 확인된 원인
- **해결/조치**: 무엇을 바꿨나, 재발 방지
- **관련 파일**: `script.py`, 커밋 해시
-->
