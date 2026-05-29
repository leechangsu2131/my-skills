# 체슬리 모닝 브리프 자동화 (v)

평일 지정 시각에 **오늘 라이브 VOD**를 찾아 자막을 뽑고, **Gemini Gem**으로 정리한 뒤 **Discord** 채널로 보내는 자동화입니다.

> 오류·개선 이력: [troubleshooting.md](./troubleshooting.md)

---

## 한눈에 보기

| 항목 | 내용 |
|------|------|
| 대상 채널 | 체슬리TV (`CHANNEL_URL`) |
| 영상 조건 | 제목이 `[체슬리모닝브리프]`로 시작 + 오늘 날짜 |
| 실행 시각 | `.env`의 `RUN_TIME` (기본 **16:00**, 평일) |
| 결과 전송 | Discord 웹훅 (`DISCORD_WEBHOOK`) |
| 자동 실행 | Windows 작업 **`ChesleyMorningBrief`** |

---

## 처음 한 번만 (설치)

### 1. 패키지

```powershell
cd v
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. 설정 파일

`.env.example`을 복사해 `.env`를 만든 뒤 아래를 채웁니다.

| 변수 | 설명 |
|------|------|
| `CHANNEL_URL` | 유튜브 채널 URL |
| `TITLE_PREFIX` | `[체슬리모닝브리프]` |
| `GEMINI_GEM_URL` | 사용할 Gem URL |
| `DISCORD_WEBHOOK` | Discord 웹훅 URL |
| `RUN_TIME` | 자동 실행 시각 (예: `16:00`) |
| `SEND_TARGET` | `discord` (권장) |

카카오 관련 변수는 학교망 등에서 막힐 수 있어 **코드는 남겨 두었고**, 지금은 Discord만 쓰면 됩니다.

### 3. Gemini 로그인 (최초 1회, 이후 자동)

```powershell
$env:SETUP_LOGIN_ONLY="1"
python main.py
```

브라우저에서 Google/Gemini 로그인을 마치면 **Enter 없이 자동으로** 세션이 저장됩니다.

```powershell
$env:SETUP_LOGIN_ONLY="0"
```

| 저장 위치 | 역할 |
|-----------|------|
| `chrome_profile/` | Playwright 영구 프로필 (스케줄러가 매번 재사용) |
| `gemini_storage_state.json` | 쿠키 백업 (프로필이 깨졌을 때 복원) |

**평소 자동 실행:** 로그인 상태면 브라우저를 띄우지 않고 진행합니다 (`HEADLESS=true` 가능).

**세션 만료 시 (수개월에 한 번):** 브라우저가 자동으로 열리고, Discord에 알림이 갑니다. 로그인만 완료하면 스크립트가 감지해 요약을 이어갑니다 (`AUTO_LOGIN_WAIT_SEC`, 기본 300초).

> Google 비밀번호를 `.env`에 넣는 방식은 2단계 인증·보안 정책 때문에 지원하지 않습니다. **한 번 로그인 → 오래 유지**가 안전하고 현실적인 자동화입니다.

### 4. Discord 연결 테스트

```powershell
powershell -ExecutionPolicy Bypass -File .\send_test_message.ps1
```

Discord에 한글이 깨지지 않고 오면 성공입니다.

### 5. 자동 실행 등록 (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File .\register_scheduled_task.ps1
```

- 작업 이름: **`ChesleyMorningBrief`**
- 스케줄: **월~금**, `.env`의 `RUN_TIME` (기본 16:00)
- 실행 파일: `run_once.ps1` → 로그는 **`run.log`**

---

## 자동 실행 — 자주 묻는 것

### 항상 알아서 돌아가나요?

**네.** `register_scheduled_task.ps1`로 등록해 두면, Windows 작업 스케줄러가 평일 지정 시각에 실행합니다.  
터미널을 켜 둘 필요는 **없습니다**.

다만 아래일 때는 실행되지 않습니다.

- PC가 꺼져 있거나 절전 상태
- 작업을 **사용 안 함**으로 꺼 둔 경우
- 주말 (스케줄이 월~금만)

### 어디서 확인하나요?

**1) 작업 스케줄러 (GUI)**

1. `Win + R` → `taskschd.msc` → Enter
2. **작업 스케줄러 라이브러리** → **`ChesleyMorningBrief`**
3. **마지막 실행 시간**, **마지막 실행 결과** 확인 (결과 `0` = 성공)

**2) 로그 파일**

```powershell
Get-Content .\run.log -Tail 40
```

`RUN_ONCE start` / `Run completed` 등이 보이면 실행된 것입니다.

**3) Discord**

설정한 채널(체슬리요약 등)에 요약 메시지가 오는지 확인.

**4) PowerShell**

```powershell
Get-ScheduledTask -TaskName ChesleyMorningBrief
Get-ScheduledTaskInfo -TaskName ChesleyMorningBrief | Format-List LastRunTime, LastTaskResult, NextRunTime
```

---

## 사용자 가이드 — 끄기 / 켜기 / 시각 변경

### 자동 실행 끄기

**GUI:** `taskschd.msc` → `ChesleyMorningBrief` 우클릭 → **사용 안 함**

**PowerShell:**

```powershell
Disable-ScheduledTask -TaskName ChesleyMorningBrief
```

### 다시 켜기

**GUI:** 우클릭 → **사용**

**PowerShell:**

```powershell
Enable-ScheduledTask -TaskName ChesleyMorningBrief
```

### 실행 시각 바꾸기 (예: 16:00 → 다른 시각)

1. `v\.env`에서 수정:

```env
RUN_TIME=16:00
```

2. 스케줄러에 다시 반영:

```powershell
cd v
powershell -ExecutionPolicy Bypass -File .\register_scheduled_task.ps1
```

GUI에서만 트리거를 바꿔도 되지만, **`.env`와 스크립트를 같이 맞추는 것**을 권장합니다.

### 작업 완전히 삭제

**GUI:** `ChesleyMorningBrief` 우클릭 → **삭제**

**PowerShell:**

```powershell
Unregister-ScheduledTask -TaskName ChesleyMorningBrief -Confirm:$false
```

### 지금 당장 한 번 실행 (시각 기다리지 않음)

```powershell
Start-ScheduledTask -TaskName ChesleyMorningBrief
```

또는:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_once.ps1
```

---

## 수동 실행 (터미널 방식, 선택)

터미널을 계속 켜 두고 매일 돌리려면:

```powershell
python main.py
```

한 번만 돌리고 끝:

```powershell
$env:RUN_ONCE="1"
python main.py
```

---

## 동작 흐름

1. 평일 `RUN_TIME`에 작업 스케줄러 실행
2. 채널 `/streams`에서 오늘 `[체슬리모닝브리프]` 영상 탐지
3. 자막 수집 (없으면 3분 간격 재시도, 최대 10회)
4. Playwright로 Gem에 자막 입력 → 응답 수집
5. Discord로 전송
6. `processed.json`에 영상 ID 저장 (같은 영상 중복 전송 방지)

---

## 주요 파일

| 파일 | 용도 |
|------|------|
| `main.py` | 메인 로직 |
| `.env` | 설정 (시각, 웹훅, 채널 URL 등) |
| `run_once.ps1` | 스케줄러가 호출하는 1회 실행 |
| `register_scheduled_task.ps1` | Windows 작업 등록/갱신 |
| `send_test_message.ps1` | Discord 테스트 메시지 |
| `run.log` | 실행 기록 |
| `processed.json` | 이미 보낸 영상 ID |
| `chrome_profile/` | Gemini 로그인 세션 |
| [troubleshooting.md](./troubleshooting.md) | 오류·해결 이력 |

---

## 환경 변수 (자주 쓰는 것)

| 변수 | 기본 | 설명 |
|------|------|------|
| `RUN_TIME` | `16:00` | 자동 실행 시각 |
| `ONLY_WEEKDAYS` | `true` | 평일만 (토·일 스킵) |
| `SEND_TARGET` | `discord` | 전송 방식 |
| `HEADLESS` | `false` | `true`면 브라우저 창 안 뜸 (스케줄 실행 시 권장) |
| `TRANSCRIPT_MAX_TRIES` | `10` | 자막 재시도 횟수 |
| `GEMINI_INPUT_MAX_CHARS` | `8000` | Gem에 넣는 최대 글자 수 |
| `GEMINI_FORCE_PRO` | `true` | Flash 대신 Pro 모델 선택 시도 |
| `GEMINI_USE_GEM_PROMPT` | `true` | Gem 지침용 프롬프트 prefix 사용 |

학교/회사망 SSL 오류 시: `YT_NO_CHECK_CERTIFICATES=true`, `DISABLE_SSL_VERIFY=true`  
(자세한 내용은 [troubleshooting.md](./troubleshooting.md))

---

## 카카오 사용 (선택, 현재 미사용 가능)

학교망 등에서 Kakao API가 막히면 Discord를 쓰세요.  
카카오를 쓰려면 OAuth 토큰(`kakao_token.json`)이 필요합니다. → `init_kakao_token.py`, [troubleshooting.md](./troubleshooting.md) 참고.

---

## 문제가 생기면

1. [troubleshooting.md](./troubleshooting.md)에서 증상 검색  
2. `run.log` 확인  
3. `HEADLESS=false`로 브라우저 화면 보며 Gem 동작 확인  
4. `send_test_message.ps1`로 Discord만 먼저 테스트
