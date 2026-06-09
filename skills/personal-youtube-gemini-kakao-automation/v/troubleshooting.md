# Troubleshooting & 개선 이력

`personal-youtube-gemini-kakao-automation/v` 프로젝트를 구축·운영하면서 발생한 오류, 원인, 해결 방법, 개선 사항을 정리한 문서입니다.

---

## 목차

1. [전체 파이프라인 개요](#전체-파이프라인-개요)
2. [YouTube 영상 탐지](#youtube-영상-탐지)
3. [자막 추출](#자막-추출)
4. [Gemini Gems (Playwright)](#gemini-gems-playwright)
5. [전송 채널 (Discord / Kakao)](#전송-채널-discord--kakao)
6. [스케줄 실행](#스케줄-실행)
7. [참고 프로젝트 (`chesley-morning-brief-main`)](#참고-프로젝트-chesley-morning-brief-main)
8. [환경 변수 빠른 참조](#환경-변수-빠른-참조)
9. [체크리스트](#체크리스트)

---

## 전체 파이프라인 개요

```
평일 지정 시각 (RUN_TIME, 기본 12:20 / 이전 16:00)
  → 오늘 [체슬리모닝브리프] 라이브 VOD 탐지
  → 자막 수집 (재시도)
  → Playwright로 Gemini Gem에 자막 입력
  → Gem 응답 추출
  → Discord 웹훅 전송
  → processed.json에 video_id 기록 (중복 방지)
```

**현재 권장 전송:** `SEND_TARGET=discord` + `DISCORD_WEBHOOK`  
**카카오 관련 설정/코드:** 학교 등 네트워크 차단 대비해 유지 (미사용 가능)

---

## YouTube 영상 탐지

### 증상: 오늘 라이브를 찾지 못함 (`None`)

**원인**

- `yt-dlp --flat-playlist` 결과에 `upload_date`, `was_live`가 없는 경우가 많음
- 채널 `/videos`만 보면 라이브 VOD가 `/streams`에만 있는 경우 있음
- **(2026-06-09)** flat 목록 제목이 **영어**(`[Cheslie Morning Brief] ...`)로만 나오고, 한국어 제목·`26/06/09` 날짜가 빠져 매칭 실패

**해결**

- 채널 URL → `{CHANNEL_URL}/streams` 탐색 (없으면 `/videos`도 확인)
- 제목 조건:
  - `TITLE_PREFIX`로 시작 (기본: `[체슬리모닝브리프]`)
  - 영어 제목 alias도 허용: `[Cheslie Morning Brief]`, `[Chesley Morning Brief]`, `[Chesly Morning Brief]`
  - 제목에 오늘 날짜 포함 (`26/06/09`, `2026/06/09`, `06/09/26` 등)
- flat 제목만으로 안 맞으면 **최근 10개에 대해 `upload_date` 메타데이터**로 오늘 업로드 + 브리프 prefix 재확인

**검증 예시 (2026-05-28)**

- 영상 ID: `vQ5Va_P-BNI`
- 채널: `UCXST0Hq6CAmG0dmo3jgrlEw` (@chesleytv)

---

### 증상: `yt-dlp` SSL 인증서 오류

```
SSL: CERTIFICATE_VERIFY_FAILED certificate verify failed: self-signed certificate in certificate chain
```

**원인**

- 학교/회사망 등에서 HTTPS 가로채기(프록시) 인증서 사용

**해결**

- `.env`: `YT_NO_CHECK_CERTIFICATES=true`
- `python -m yt_dlp`로 실행 (PATH에 `yt-dlp` 없어도 동작)
- `main.py`에서 `sys.executable -m yt_dlp` 사용

---

### 증상: `unknown option --no-check-certificates` (python에 옵션이 전달됨)

**원인**

- `--no-check-certificates`를 `python` 인자 위치에 삽입

**해결**

- `command.insert(3, "--no-check-certificates")` — `yt_dlp` 모듈 뒤에 삽입

---

## 자막 추출

### 증상: `YouTubeTranscriptApi has no attribute 'get_transcript'`

**원인**

- `youtube-transcript-api` 1.2.x API 변경: 클래스 메서드 `get_transcript` 제거

**해결**

```python
api = YouTubeTranscriptApi(http_client=session)  # SSL 이슈 시 session.verify=False
fetched = api.fetch(video_id, languages=["ko", "ko-KR", "en"])
text = " ".join(snippet.text.strip() for snippet in fetched if snippet.text)
```

**검증**

- `vQ5Va_P-BNI`: 약 **2847줄 / 50,680자**
- 샘플 파일: `last_transcript_vQ5Va_P-BNI.txt`

**참고**

- 자동 생성 자막은 고유명사 오인식 있음 (`채밀턴`, `채슬린` 등) → Gem 단계 품질과는 별개

---

### 증상: 자막 SSL 오류

**해결**

- `DISABLE_SSL_VERIFY=true`
- `YouTubeTranscriptApi(http_client=requests.Session())` + `session.verify=False`

---

## Gemini Gems (Playwright)

### 증상: 로그인 세션 없음 / Gem 접근 불가

**해결 (최초 1회)**

```powershell
$env:SETUP_LOGIN_ONLY="1"
python main.py
```

- 브라우저에서 Google/Gemini 로그인
- Enter 후 `chrome_profile`에 세션 저장

---

### 증상: 입력창 클릭 타임아웃 (`ql-clipboard`, not visible)

**원인**

- `div[contenteditable='true']` 마지막 요소가 숨겨진 클립보드용 div

**해결**

- 입력창 selector 다중 fallback:
  - `rich-textarea[aria-label*='메시지']`
  - `rich-textarea`
  - `div[contenteditable='true']:visible:not(.ql-clipboard)`
  - `textarea:visible`

---

### 증상: Discord 내용이 Gem 응답과 다름 (이전 대화 답변)

**원인**

- 전송 전후 응답 개수 비교 없이 "마지막 `model-response`"만 읽음

**해결**

- 전송 전 `previous_count = await response_nodes.count()`
- 전송 후 **개수가 증가할 때까지** 대기
- 새로 생긴 마지막 노드만 `inner_text()` 추출
- `networkidle` 대기 제거 (Gemini 페이지는 백그라운드 요청이 계속됨)

---

### 증상: 응답 대기 중 `networkidle` 타임아웃

**해결**

- `wait_for_load_state("networkidle")` 제거
- 로딩/중지 버튼 사라질 때까지 짧게 폴링 후 텍스트 추출

---

### 증상: Gem이 안 열리고 일반 Gemini(Flash)만 보임 → 답변 품질 낮음

**증상**

- 새 창이 떴지만 **Gem URL이 아닌** 일반 채팅 화면
- 모델이 **Flash(빠른 모드)** 로 남아 있음

**원인**

- `domcontentloaded`만 기다리고 Gem 진입 검증 없음
- Pro 모델 선택 단계 없음
- 자막만 넣고 Gem 지침용 프롬프트 prefix 없음

**해결 (2026-05-29 반영)**

- `_open_gem_page()`: `/gem/` URL 강제 이동 + URL 검증
- `_select_gemini_pro()`: Flash → Pro 선택 시도
- `build_gem_prompt()`: chesley-brief 스타일 지침 prefix
- `.env`: `GEMINI_FORCE_PRO=true`, `GEMINI_USE_GEM_PROMPT=true`

**확인 방법**

```powershell
$env:HEADLESS="false"
$env:GEMINI_DEBUG_HOLD_MS="120000"
$env:RUN_ONCE="1"
python main.py
```

브라우저에서 **Gem 화면 + Pro 모델**인지 직접 확인.

---

### 증상: 응답 품질 낮음 / 입력 누락

**개선 (chesley-morning-brief-main 반영)**

| 항목 | 내용 |
|------|------|
| 입력 | `fill()` 실패 시 클립보드 + `Ctrl+V` |
| 전송 | `Enter` + 전송 버튼 클릭 fallback |
| 대기 | Stop/로딩 표시 사라질 때까지 추가 대기 |
| 디버그 | `HEADLESS=false`, `GEMINI_DEBUG_HOLD_MS=180000` 으로 브라우저 확인 |

**미반영 (필요 시 추가)**

- 매 실행 **새 대화 스레드** 강제 생성
- Pro 모델 선택 로직
- `chesley_brief.py`의 긴 프롬프트 prefix (Gem 지침 강제)

---

### 증상: 프로세스가 출력 없이 오래 멈춤

**원인**

- headless 브라우저 + 긴 Gem 응답 생성

**해결**

- `python -u` (unbuffered)
- `TRANSCRIPT_MAX_TRIES=1`로 테스트 시 시간 단축
- 디버그 시 `GEMINI_DEBUG_HOLD_MS`로 창 유지

---

## 전송 채널 (Discord / Kakao)

### Kakao: `401 this access token does not exist`

**원인**

- `KAKAO_TOKEN`에 **Admin Key / REST API Key**를 넣음
- 나에게 보내기에는 **OAuth Access Token** 필요

**해결 (카카오 사용 시)**

1. 카카오 로그인 활성화 + Redirect URI 등록
2. 인가 코드 → `init_kakao_token.py`로 `kakao_token.json` 생성
3. `refresh_token`으로 자동 갱신 (`main.py` 내 `refresh_kakao_access_token`)

**현재 운영**

- 학교망 등에서 Kakao API 차단 가능 → **Discord 웹훅 사용**

---

### Discord: 웹훅 vs 봇 토큰

| 방식 | 필요 값 | 비고 |
|------|---------|------|
| 웹훅 (권장) | `DISCORD_WEBHOOK` | 채널에 바로 전송, 설정 간단 |
| 봇 API | `DISCORD_BOT_TOKEN` + `DISCORD_CHANNEL_ID` | Bot 권한·채널 ID 필요 |

---

### Discord: 한글 깨짐 (`?븧 ?ㅼ?以꾨윭...`)

**원인**

- PowerShell에서 `python -c "한글..."` 실행 시 인코딩 깨짐

**해결**

- 테스트/전송: `send_test_message.py` (UTF-8 소스 파일)
- `send_discord_message`: `json.dumps(..., ensure_ascii=False).encode("utf-8")` + `Content-Type: charset=utf-8`
- `run_once.ps1`: `PYTHONIOENCODING=utf-8`, `chcp 65001`

**정상 메시지 예**

```
[스케줄러 테스트] 2026-05-29 12:18:35 - ChesleyMorningBrief 동작 확인 (한글 인코딩 정상)
```

---

### Discord: `204` 응답

- 웹훅 성공 시 **본문 없이 204** 반환 → 정상

---

## 스케줄 실행

### 방식 A: 터미널 상시 실행

```powershell
python main.py
```

- `schedule` 라이브러리로 매일 `RUN_TIME`에 실행
- 터미널을 계속 켜 둬야 함

---

### 방식 B: Windows 작업 스케줄러 (권장)

```powershell
powershell -ExecutionPolicy Bypass -File .\register_scheduled_task.ps1
```

| 항목 | 값 |
|------|-----|
| 작업 이름 | `ChesleyMorningBrief` |
| 스케줄 | 월~금 `RUN_TIME` (`.env` 기준, 예: **16:00**) |
| 실행 스크립트 | `run_once.ps1` → `RUN_ONCE=1` + `main.py` |
| 로그 | `run.log` |

**수동 1회 실행**

```powershell
powershell -ExecutionPolicy Bypass -File .\run_once.ps1
# 또는
Start-ScheduledTask -TaskName ChesleyMorningBrief
```

**12:20 테스트 (2026-05-29)**

- `ChesleyMorningBrief-Test1220` 일회성 작업으로 12:20 자동 테스트
- `LastTaskResult: 0` 확인

**시각 변경**

1. `.env`에서 `RUN_TIME` 수정
2. `register_scheduled_task.ps1` 다시 실행

---

### 화면보호기 / 잠금 / 절전 (2026-06-01 정리)

스케줄 실행 시 PC 상태에 따른 동작 요약입니다.  
Playwright는 `.env`의 `HEADLESS` 설정에 따라 Chrome을 띄웁니다 (`false`면 창 표시 모드).

| PC 상태 | 스케줄러 실행 | Gemini(Chrome) 자동화 | 비고 |
|---------|---------------|------------------------|------|
| **화면보호기만** (로그인 유지) | 보통 됨 | 보통 됨 | 화면만 꺼진 것. 로그아웃 아님 |
| **Win+L 잠금** | 보통 됨 | **실패·멈춤 가능** | `HEADLESS=false`일 때 특히 민감 |
| **절전 / 최대 절전** | 안 됨 | 안 됨 | PC가 거의 꺼진 상태 |
| **로그아웃 / 재부팅 후 미로그인** | 안 됨 | 안 됨 | Windows 로그인 필요 |
| **노트북 덮개 닫힘** | 설정에 따라 | 설정에 따라 | “덮개 닫을 때 절전”이면 실패 |

**한 줄 요약:** 화면보호기만으로는 **대체로 문제 없음**. **잠금·절전·로그아웃**이면 **실패할 수 있음**.

**`RUN_TIME` 전후 권장 설정**

1. 해당 시각 **전후 30~40분**은 절전·최대 절전 끄기 (또는 “절전 안 함”)
2. 가능하면 **Win+L 잠금은 피하기** (화면보호기만은 괜찮은 편)
3. 노트북: **덮개를 닫아도 절전되지 않게** 전원 옵션 확인
4. (선택) 잠금 상태에서도 안정적으로 돌리려면 `.env`에서 `HEADLESS=true` — Gemini 세션이 `chrome_profile`에 저장돼 있을 때 유효

**실행 후 확인**

```powershell
Get-ScheduledTaskInfo -TaskName ChesleyMorningBrief | Format-List LastRunTime, LastTaskResult, NextRunTime
Get-Content .\run.log -Tail 25
```

- `LastTaskResult: 0` + `Run completed` + `Gemini response length:` **400자 이상** → 정상
- `Gemini response too short` 또는 `Run failed` → `run.log` 전문 확인

---

### 중복 전송 방지

- `processed.json`에 처리한 `video_id` 저장
- 같은 날 재실행 시 스킵

---

## 참고 프로젝트 (`chesley-morning-brief-main`)

경로: `../chesley-morning-brief-main/`

| 항목 | 기존 (잘 동작) | v 프로젝트 |
|------|----------------|------------|
| 영상 탐지 | YouTube RSS + 키워드 + 날짜 | yt-dlp `/streams` + 제목 prefix + 날짜 |
| 브라우저 | patchright sync | playwright async |
| 입력 | 클립보드 붙여넣기, 다중 selector | 부분 반영 |
| 전송 | Discord webhook embed | Discord plain text |
| 중복 방지 | processed.json | 동일 |

추가 이식 후보:

- RSS 기반 탐지 fallback
- Gem 프롬프트 prefix (지침 강제)
- 응답 추출 fallback (채팅 본문 split)
- 새 대화 스레드 매 실행

---

## 환경 변수 빠른 참조

| 변수 | 용도 |
|------|------|
| `CHANNEL_URL` | 유튜브 채널 |
| `TITLE_PREFIX` | `[체슬리모닝브리프]` |
| `GEMINI_GEM_URL` | Gem URL |
| `RUN_TIME` | 실행 시각 (`12:20`) |
| `ONLY_WEEKDAYS` | 평일만 (`true`) |
| `SEND_TARGET` | `discord` / `discord_bot` / `kakao` |
| `DISCORD_WEBHOOK` | 웹훅 URL |
| `PLAYWRIGHT_PROFILE_DIR` | `./chrome_profile` |
| `HEADLESS` | `false`(디버그) / `true`(스케줄) |
| `TRANSCRIPT_MAX_TRIES` | 자막 재시도 (기본 10) |
| `TRANSCRIPT_RETRY_INTERVAL_SEC` | 180 (3분) |
| `GEMINI_INPUT_MAX_CHARS` | 8000 |
| `RESPONSE_TIMEOUT_MS` | 120000 |
| `YT_NO_CHECK_CERTIFICATES` | yt-dlp SSL 우회 |
| `DISABLE_SSL_VERIFY` | requests SSL 우회 |
| `PROCESSED_FILE` | `./processed.json` |
| `RUN_ONCE` | `1`이면 1회 실행 후 종료 |
| `SETUP_LOGIN_ONLY` | `1`이면 로그인만 |
| `GEMINI_DEBUG_HOLD_MS` | 응답 후 브라우저 유지(ms) |

---

## 체크리스트

### 최초 설정

- [ ] `pip install -r requirements.txt`
- [ ] `playwright install chromium`
- [ ] `.env` 작성 (채널, Gem URL, Discord 웹훅)
- [ ] `SETUP_LOGIN_ONLY=1`로 Gemini 로그인
- [ ] `send_test_message.ps1`로 한글 테스트 메시지 확인
- [ ] `register_scheduled_task.ps1` 등록

### 실행 실패 시

- [ ] `run.log` 확인
- [ ] 오늘 영상 제목에 `[체슬리모닝브리프]` + 날짜 있는지
- [ ] `chrome_profile` 로그인 유효한지
- [ ] 학교망: SSL 관련 env `true`인지
- [ ] Discord: 깨진 한글이면 `send_test_message.py` 경로로 테스트

### Gem 응답이 이상할 때

- [ ] `HEADLESS=false`로 직접 화면 확인
- [ ] `GEMINI_DEBUG_HOLD_MS=180000`
- [ ] 이전 대화 영향 → 새 스레드/Gem URL 재진입 검토

---

## 파일 목록

| 파일 | 역할 |
|------|------|
| `main.py` | 메인 로직 |
| `run_once.ps1` | 스케줄러용 1회 실행 |
| `register_scheduled_task.ps1` | Windows 작업 등록 |
| `send_test_message.py` / `.ps1` | Discord 연결·한글 테스트 |
| `init_kakao_token.py` | 카카오 최초 토큰 (선택) |
| `run.log` | 실행 로그 |
| `processed.json` | 처리된 video_id |
| `chrome_profile/` | Gemini 로그인 세션 |
| `last_transcript_*.txt` | 자막 추출 검증용 |

---

## 변경 이력 (요약)

| 일자 | 내용 |
|------|------|
| 2026-05-28 | 프로젝트 `v` 생성, yt-dlp 탐지, 카카오→Discord 전환 |
| 2026-05-28 | Gem 입력/응답 추출 보강, chesley-morning-brief 참고 반영 |
| 2026-05-29 | Windows 작업 스케줄러 (12:20), UTF-8 Discord 수정 |
| 2026-06-01 | 화면보호기/잠금/절전 가이드, Gemini 짧은 응답(50자) 방지, Gem URL 세션 검증 |

---

*이 문서는 실제 디버깅 세션을 바탕으로 작성되었습니다. 새 오류가 생기면 증상·원인·해결을 아래에 이어서 추가하세요.*
