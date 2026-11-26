# 설계: 저장한 녹음(WebM)을 클로바노트에 올릴 수 있는 형식으로 내려받기 (S7, ISSUE-039)

2026-11-27 · 설계만, 코드는 바꾸지 않음. **이 환경(리눅스)에서 직접 돌려 본 것**, **코드에서 확인한 것**, **확인 필요**를 나눠 적는다.

## 0. 먼저 알아 둘 것

- 클로바노트가 받는 형식은 `.m4a`, `.mp3`, `.aac`, `.amr`, `.wav` 로 ISSUE-039 에 적혀 있다(공식 안내를 인용한 것). 수업 비서 녹음은 `.webm`(Opus), Safari 계열은 `.mp4` 라서 그대로는 못 올린다.
- **교사 답(2026-11-27): 제한은 "600분".** 공식 안내 쪽은 이 환경에서 열리지 않아 우리가 따로 확인하지는 못했다. 50분 수업 하나는 600분 안에 들어가니 **한 파일을 쪼갤 필요는 없다**고 본다.
  - 다만 600분이 **파일 하나의 길이**인지 **달마다 쓸 수 있는 시간**인지는 답에 없었다. 달마다라면 50분 수업 12번이면 끝이라, 올릴 수업을 골라서 올려야 한다(수업 비서는 그날 녹음 목록에서 고르게만 한다).
  - **파일 크기(MB) 제한은 여전히 모른다.** 아래 표의 23 MB(50분)가 걸리는지는 첫 업로드 때 알게 된다.
- 올리는 일(업로드)은 **교사가 클로바노트에서 직접** 한다. 수업 비서는 올릴 수 있는 파일을 만들어 내려받게만 한다. 녹음에 학생 목소리가 들어 있으니 바깥 서비스에 올려도 되는지는 교사가 판단한다.

## 1. 지금 모양 (코드에서 확인)

- 저장: `assistant_server.py` `save_audio()` 가 10초마다(`web/index.html` `mr.start(10000)`) 오는 조각을 `sessions/<날짜>/<이름>.webm|mp4` 에 **이어 붙인다**. 이어 붙이는 중인지 알려 주는 표시는 파일에 없다(`_REC_STATE` 는 서버를 켜 둔 동안 계속 남아 '끝났는지'는 모른다).
- 목록: `recordings_for_day()` → `GET /api/recordings?date=` 가 `file`, `url`, `size`, `period`, `subject` … 를 준다. 확장자 `.webm`·`.mp4` 만 센다.
- 내려받기·재생: `do_GET` 의 `/api/recording/<날짜>/<파일>` — `safe_name`, `is_relative_to(SESSIONS)` 로 이름·경로를 검사하고 `_send_audio()` 가 Range 요청까지 처리한다.
- 화면: `web/index.html` `recordingMarkup()` 가 `<audio>` 와 **파일 저장** 링크(`download`)를 그린다. `refreshRecordings()` 안의 "N건 · MP3 변환 전 원본" 문구는 이 기능이 생기면 바꾼다.
- 보안: `do_GET` 맨 앞의 `_trusted()` 가 `Host`(127.0.0.1·localhost)와 `Origin` 을 검사한다. 새 경로도 그 아래에 둔다(따로 넓히지 않는다).
- 이미 있는 비슷한 코드: `subprocess` 로 숨은 창을 띄우는 `creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)` (`assistant_server.py` 640줄 근처). 같은 방식으로 쓴다.

## 2. 형식·용량 (이 환경에서 ffmpeg 6.1 로 60초 소리를 변환해 잰 값)

| 형식 | 60초 | 50분이면 | 변환 시간(60초 기준) | 비고 |
|---|---|---|---|---|
| webm 원본(Opus 48 kbps) | 0.33 MB | 약 16.7 MB | — | 지금 저장 형식 |
| **MP3 64 kbps · 24 kHz · 모노** | 0.46 MB | **약 22.9 MB** | 0.5초 | 제안 기본값 |
| MP3 96 kbps · 44.1 kHz · 모노 | 0.69 MB | 약 34.4 MB | 0.7초 | 음질 우선 |
| M4A(AAC) 64 kbps · 24 kHz · 모노 | 0.46 MB | 약 23.2 MB | 0.6초 | MP3 와 비슷 |
| WAV 16 kHz · 모노 | 1.83 MB | 약 91.6 MB | 0.3초 | 너무 큼 |
| WAV 44.1 kHz · 모노 | 5.05 MB | 약 252 MB | 0.3초 | 쓰지 않음 |

- MP3·M4A 는 **고정 비트레이트라 소리 내용과 상관없이 크기가 같다**(64 kbps = 초당 8,000바이트). 합성 소리로 잰 값이라 실제 수업 소리여도 크기는 같다.
- 변환은 매우 빠르다(60초 소리에 0.5초 안팎). 50분 녹음이면 이 PC 기준 30초 안팎, 학교 PC 는 더 걸릴 수 있다 → 화면에 "변환 중" 표시가 필요하고 서버 쪽 제한 시간은 넉넉히(예: 300초) 둔다.
- **제안**: 기본은 **MP3 64 kbps·24 kHz·모노**. 말소리용이라 모노로 충분하고 WAV 는 너무 크다. 클로바노트가 이 음질로 잘 알아듣는지는 교사에게 물었고 "그렇단다"라는 답을 받았다 — 직접 올려 본 결과가 아니라 들은 이야기로 적어 둔다. 첫 실제 업로드에서 알아듣는 정도가 나쁘면 96 kbps·44.1 kHz(50분 약 34 MB)로 올린다.
- ffmpeg 로 만든 `.webm`(머리 정보를 지워 MediaRecorder 파일처럼 흉내 냄)을 표준입력으로 넣어도, ffmpeg 로 만든 `.mp4`(AAC)에서도 MP3 로 바뀌는 것을 확인했다. 진짜 브라우저가 만든 수업 녹음 파일로는 **확인 필요**.

## 3. 변환 도구: ffmpeg

- 이 환경에서는 `ffmpeg`(libmp3lame, aac 포함)가 PATH 에 있었다. **학교·집 PC 에 있는지는 모른다 → 확인 필요.** 저장소 어디에도 `ffmpeg` 를 부르는 코드는 아직 없다.
- 없을 때 길 두 가지:
  - (가) 사용자가 ffmpeg 를 설치해 PATH 에 넣는다(예: `winget install Gyan.FFmpeg`). 설치 안내만 화면에 띄운다.
  - (나) `pip install imageio-ffmpeg` — ffmpeg 실행 파일을 같이 가져와 PATH 설정이 필요 없다. 윈도우용 설치 파일 37 MB(안의 ffmpeg 약 100 MB). 리눅스용 번들에서 `libmp3lame` 이 있는 것은 확인했고, **윈도우용 번들에 MP3 인코더가 있는지는 확인 못 함 → 교사 PC 에서 확인**(`python -c "import imageio_ffmpeg"` 후 그 파일에 `-encoders` 를 줘서 `mp3lame` 이 보이는지).
- **교사 결정(2026-11-27): "없으면 깔게"** — ffmpeg 가 없는 PC 에서는 교사가 직접 설치한다(위 (가)). 그래서 `requirements.txt` 에 `imageio-ffmpeg` 는 **넣지 않는다**(37 MB 를 모든 PC 에 깔지 않음). 위 (나)는 쓰지 않는 대안으로만 남긴다.
- 찾는 순서(제안): config 의 `ffmpeg_path` → `shutil.which("ffmpeg")` → 없으면 **설치 안내 오류**(`winget install Gyan.FFmpeg` 한 줄과, 설치 뒤 서버를 다시 켜라는 말). `imageio_ffmpeg` 를 찾는 단계는 만들지 않는다.

## 4. 만들 것 (파일·함수 이름 수준)

### 새 파일 `audio_export.py` (서버와 따로 두어 시험하기 쉽게)

- `find_ffmpeg(cfg) -> str | None` — 위 순서로 찾는다.
- `export_path(src, fmt) -> pathlib.Path` — `<녹음 폴더>/export/<원래이름>.<mp3|m4a>`. 원본 옆 `export/` 폴더에 둔다(원본은 건드리지 않는다).
- `is_still_recording(src, now=None, quiet_seconds=30) -> bool` — **마지막으로 바뀐 지 30초가 안 됐으면 녹음 중으로 본다**(조각이 10초마다 붙으니 3번 건너뛴 셈). 녹음 중인 파일을 변환하면 끝이 잘리고, 나중에 녹음이 더 붙어도 캐시가 옛것이라 헷갈린다.
- `convert(src, fmt="mp3", ffmpeg=None, timeout=300) -> pathlib.Path`:
  - 이미 만든 파일이 있고 **원본보다 새것이면 그대로 돌려준다**(원본이 더 붙으면 다시 만든다).
  - 명령: `ffmpeg -v error -y -i pipe:0 -vn -ac 1 -ar 24000 -c:a libmp3lame -b:a 64k <임시이름>.mp3` — 원본은 **표준입력으로 흘려 넣고**, 출력은 **영문 임시 이름**에 쓴 뒤 `os.replace()` 로 한글 이름으로 바꾼다. 윈도우에서 ffmpeg 가 한글 경로를 어떻게 읽는지 몰라도 되게 하려는 것(**윈도우 한글 경로는 확인 필요**, 이 방식이면 문제가 안 된다).
  - `subprocess.run(..., creationflags=CREATE_NO_WINDOW, timeout=...)`. 실패하면 임시 파일을 지우고 ffmpeg 의 마지막 오류 줄을 담은 `ExportError`.
  - 같은 파일을 두 요청이 동시에 변환하지 않게 파일마다 잠금(`threading.Lock` 을 파일 경로로 모아 둠). 서버는 `ThreadingHTTPServer` 라 동시 요청이 가능하다.
- 오류 종류: `ExportError`(변환 실패), `FfmpegMissing`(도구 없음 — 설치 안내 문구), `StillRecording`.

### `assistant_server.py`

- 지금 `/api/recording/` 분기에 있는 이름·경로 검사를 `recording_file(day, name)` 같은 함수로 빼서 새 경로도 같이 쓴다(검사를 두 번 쓰지 않게).
- `GET /api/recording-export/<날짜>/<파일>?format=mp3` → `audio_export.convert()` → 파일을 `Content-Disposition: attachment; filename*=UTF-8''<이름>.mp3` 로 보낸다(한글 파일명). `format` 은 `mp3`·`m4a` 만 허용, 그 밖은 400.
- 오류 응답은 기존 `_json({"status":"error","message":...}, 코드)` 모양: 없는 파일 404, 녹음 중 409, ffmpeg 없음 501(설치 안내를 `message` 에), 변환 실패 500.
- `/api/recordings` 응답에는 칸을 더하지 않는다(내보내기 가능 여부는 누르면 알려 준다).

### `web/index.html`

- `recordingMarkup()` 의 **파일 저장** 옆에 **클로바노트용 MP3 받기** 단추(`download` 링크가 아니라 단추).
- 누르면 `fetch('/api/recording-export/…')` → "변환 중…"(단추 잠금) → 받은 데이터를 `Blob` 으로 만들어 `<a download>` 를 눌러 저장. 50분 MP3 는 약 23 MB 라 메모리에 올려도 된다.
- 오류 문구는 서버 `message` 를 그대로 보여 준다(ffmpeg 없음이면 설치 안내가 그대로 나온다).
- "N건 · MP3 변환 전 원본" 문구를 "N건 · 원본은 그대로 보관"처럼 바꾼다.

### 설정·문서

- `config.json` 에 선택 칸 `ffmpeg_path`(비어 있으면 자동으로 찾음). `README.md`·`SKILL.md` 에 "클로바노트에 올리기" 사용법 3줄, ISSUE-039 상태 갱신.

## 5. 시험 (구현할 때 같이)

`tests/test_audio_export.py` (진짜 소리·진짜 ffmpeg 는 일부만):

- 가짜 `subprocess.run` 으로: 명령에 `-ac 1`·`-ar 24000`·`libmp3lame`·`64k` 가 들어감, 입력이 표준입력, 임시 이름이 영문, 성공하면 한글 이름으로 바뀜, 실패하면 임시 파일이 안 남음, 시간 초과 처리.
- 캐시: 원본이 더 새것이면 다시 만들고, 아니면 변환을 안 부름.
- `is_still_recording`: 방금 바뀐 파일 True, 오래된 파일 False(시계를 인자로 넣어 시험).
- `find_ffmpeg`: 설정값 → PATH → imageio 순서, 아무것도 없으면 None.
- 서버 경로(임시 폴더 + 가짜 변환기): 날짜·이름 검사(`..`, 다른 확장자) 404, `format=wav` 400, 녹음 중 409, 성공 시 `Content-Disposition` 의 한글 이름과 `audio/mpeg`.
- 진짜 ffmpeg 가 있을 때만 도는 시험 하나: `ffmpeg -f lavfi -i sine` 으로 만든 작은 webm → mp3 로 바뀌고 앞 바이트가 `ID3` 또는 MP3 프레임(`0xFF 0xFB`/`0xFF 0xF3`).

## 6. 하지 않을 것

- 원본 녹음을 지우거나 덮어쓰지 않는다. 변환본은 `export/` 에만 둔다.
- 클로바노트에 자동으로 올리지 않는다(학생 목소리를 바깥으로 보내는 일은 교사가 직접).
- 변환본·녹음을 저장소에 올리지 않는다(`data_dir()` 아래 `sessions/` 에만).
- 브라우저 안에서 WAV/MP3 로 바꾸는 방법은 쓰지 않는다: 50분 WAV 가 90~250 MB 라 무겁고, MP3 는 별도 인코더 라이브러리를 화면 파일에 넣어야 한다.

## 7. 확인할 것 정리 (2026-11-27 교사 답 반영)

1. ~~클로바노트 제한~~ → 교사: "600분". **남은 것**: 그 600분이 파일 하나의 길이인지 달마다 쓰는 시간인지, 파일 크기(MB) 제한이 있는지(첫 업로드 때 확인).
2. ~~ffmpeg 가 없으면~~ → 교사: "없으면 깔게". `imageio-ffmpeg` 는 안 넣는다. **남은 것**: 학교·집 PC 에 이미 있는지는 `ffmpeg -version` 으로 보면 됨(구현 전에 알 필요는 없음, 없으면 설치 안내가 뜬다).
3. ~~64 kbps 모노 MP3 로 알아듣는지~~ → 교사: "그렇단다"(들은 이야기). 첫 업로드 결과로 확정.
4. 진짜 수업 녹음 `.webm`·`.mp4` 로 변환이 되는지, 변환 시간 → 구현 뒤 첫 실제 변환에서 확인.

이제 구현해도 되는 상태다. 구현 일은 위 4번 "만들 것"을 그대로 따른다(`audio_export.py` → 서버 경로 → 화면 단추 순서로 나눌 수 있다).
