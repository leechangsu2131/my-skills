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
- **복습하기(이수한 과정) 경로** (2026-11-22, AIEDAP 10~13차시로 확인):
  - 차시 창은 `POST /lh/ms/ac/selectPreViewPopupByCntsId.do` (`cntsId=<차시 번호>`). 응답 HTML의 `var getVideoList = [...]`에 영상 목록(`iem_nm`, `bgng_file_nm`, `plytm_ss`, `cnts_year`)이 있다. 차시 번호는 수강과정 페이지의 `$.openCnts(event, <cntsId>)`에서 얻는다.
  - 파일 위치: `/eduup_cmmn/contents/nonscorm/nonscorm<연도>/<cntsId>/mp4/<차시>_<순번>.mp4`, 같은 이름의 `.vtt`(**공식 자막, Whisper 불필요** → `--subtitle`), `<cntsId>.zip`(강의자료 PDF, 글자 추출 가능·도식은 그림), `/html/<차시>_quiz.html`(base64 iframe 안 `const quiz=[...]`에 정답·해설).
  - 한 차시의 학습 영상이 두 개로 나뉜 경우가 많다(도구 소개 + 본편). ffmpeg가 없어 `1부/`, `2부/` 하위 프로젝트로 처리하고 요약만 차시 폴더에 하나로 둔다. 이때 각 부의 note.md에 있는 요약 링크는 동작하지 않는다.
  - 공식 자막 일부 구간이 영어 번역문으로 들어 있는 경우가 있다(11·12차시). PDF로 보완한다.
- **로그인**: 중앙 `.env`의 `NETI_ID`/`NETI_PW`로 `POST /system/loginProcess.do`(JSON `userId`, `userPw`)를 보내 자동 로그인한다(확인됨). 요청 기록 스크립트에서는 로그인 요청 본문을 남기지 않는다.
- **주의(Playwright)**: 대기 루프에서 `time.sleep`을 쓰면 새 창(팝업)이 열리지 않는다. `page.wait_for_timeout`을 쓴다. PowerShell 5.1 스크립트(.ps1)에 한글이 있으면 UTF-8 BOM으로 저장한다.
- **할 일**: 시험 스크립트(`neti_review_fetch.py` 등)를 `lecturecapture` 명령(예: `fetch-neti --course-id … --sessions 10-13`)으로 옮기기. 퀴즈·PDF 글자 추출과 부별 처리도 포함.

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
