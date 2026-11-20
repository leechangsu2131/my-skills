# personal-video-note 이슈 로그

> 이 스킬에서 생긴 문제와 해결 과정, 진행 중인 일, 할 일을 기록한다.
> 새 항목은 해당 절의 맨 위에 추가하고, 해결되면 '🟢 해결됨'으로 옮긴다. 양식은 맨 아래 주석 참고.

## 🔵 진행 중

### ISSUE-003: 배움누리터(중앙교육연수원) 강의 입력 (2026-11-20)
- **상태**: 🔵 진행 중
- **내용**: learning.neti.go.kr 마이크로러닝 강의는 video.js가 연수원 서버의 mp4 한 개를 재생한다(자막 `.vtt`는 404, MarkAny DRM은 화면 캡처를 막지 않음). 로그인한 Playwright 창에서 mp4를 받아 `lecturecapture run`에 넣으면 된다.
- **함정**:
  - 강의 창 주소에 `playtmSs=<강의 길이(초)>`가 빠지면 "페이지를 찾을 수 없습니다"가 뜬다. 목록의 `$.openPlayer(event, cuiId, cntsId, '', operCntsId, playtmSs, ...)` 인자에서 값을 얻는다.
  - 로그인 안 된 상태로 강의 주소를 열면 첫 화면으로 돌려보낸다.
  - 영상이 계속 스트리밍되므로 `wait_until="networkidle"`은 끝나지 않는다. `domcontentloaded` 사용.
  - `--remote-debugging-port`로 따로 띄운 크롬에서는 로그인이 되지 않았다. Playwright `launch_persistent_context`(프로필은 `data_dir()/browser-profile`)를 쓴다.
- **할 일**: 시험 스크립트를 `lecturecapture` 명령(예: `fetch-neti`)으로 옮기기.

## 📌 백로그

### ISSUE-005: note.md의 "이 슬라이드 요약 보기" 링크가 없는 앵커를 가리킴 (2026-11-20)
- **상태**: 📌 백로그
- **증상**: 요약은 대표 슬라이드만 앵커를 두는데(예: 99장 중 13개), `note.md`는 모든 슬라이드에 `summary.md#slide_XXXX` 링크를 건다. 앵커가 없으면 요약 맨 위로 간다.
- **해결/조치 안**: `summary.md`에 실제로 있는 앵커만 링크하거나, 앵커가 없는 슬라이드는 바로 앞 대표 슬라이드 앵커로 연결.
- **관련 파일**: `src/lecturecapture/notes.py`

### ISSUE-004: 강사가 화면에 나오는 강의에서 슬라이드가 과분할됨 (2026-11-20)
- **상태**: 📌 백로그
- **증상**: 배움누리터 강의(24분)에서 99장이 나옴. 강사만 나오는 장면, 강사의 몸 움직임, 글머리표가 하나씩 나타나는 장면이 모두 새 슬라이드로 잡힘. 같은 형식의 다른 강의(21분)는 33장으로 적당했음.
- **해결/조치 안**: 강사 영역을 빼고 비교하기(사람 검출 또는 고정 마스크), 누적 공개를 마지막 화면으로 자동 병합, `--min-stable` 기본값 재검토.
- **관련 파일**: `src/lecturecapture/frames.py`

## 🟢 해결됨

### ISSUE-002: faster-whisper 전사 실패 — `metadata_errors` 인자 오류 (2026-11-20)
- **상태**: 🟢 해결 (2026-11-20)
- **증상**: `open() got an unexpected keyword argument 'metadata_errors'` (GPU·CPU 모두)
- **원인**: faster-whisper 1.2.1이 `av.open(..., metadata_errors=...)`를 쓰는데 PyAV 19에서 이 인자가 없어짐
- **해결/조치**: PyAV 16.1.0으로 낮춤. `pyproject.toml`의 `transcribe` 선택 항목에 `av>=11,<17` 고정
- **관련 파일**: `pyproject.toml`

### ISSUE-001: 한글 경로에서 슬라이드 이미지 저장 실패 (2026-11-20)
- **상태**: 🟢 해결 (2026-11-20)
- **증상**: `오류: 슬라이드 이미지 저장 실패: ...\영상요약\(중등) ...\slides\slide_0001.jpg`
- **원인**: Windows에서 `cv2.imwrite`가 비ASCII 경로에 쓰지 못함
- **해결/조치**: `cv2.imencode` 후 `Path.write_bytes`로 저장
- **관련 파일**: `src/lecturecapture/frames.py`

<!--
항목 양식 (복사해서 사용)

### ISSUE-001: 한 줄 제목 (YYYY-MM-DD)
- **상태**: 🔵 진행 중 | 📌 백로그 | 🟢 해결 (YYYY-MM-DD)
- **증상**: 무엇이 어떻게 안 됐나 (오류 메시지 그대로)
- **원인**: 확인된 원인
- **해결/조치**: 무엇을 바꿨나, 재발 방지
- **관련 파일**: `script.py`, 커밋 해시
-->
