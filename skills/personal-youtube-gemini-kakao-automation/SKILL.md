---
name: personal-youtube-gemini-kakao-automation
description: >-
  Runs and catches up the Chesley Morning Brief YouTube→Gemini Gem→Discord
  pipeline in v/. Use when the user asks to summarize missed morning brief
  videos, run backlog/catch-up after downtime, fix personal-youtube-gemini-kakao-automation,
  or process 체슬리모닝브리프/모닝브리프 videos through Gemini and Discord.
---

# 체슬리 모닝 브리프 자동화 (백로그 포함)

프로젝트 경로: `my-skills/skills/personal-youtube-gemini-kakao-automation/v`

## 핵심 규칙 (밀린 요약)

1. **영상 1개 = 요약 1개** (여러 날을 한 응답으로 합치지 말 것)
2. **한 번에 몰아서 돌리지 말 것** — 1건 성공 → 문제 수정 → 2~3건 검증 → 나머지
3. **오늘 영상 제외** — `BACKLOG_TO`는 어제 이하
4. 이미 `backlog_summaries/YYYY-MM-DD_*.md`가 있으면 기본 스킵 (`BACKLOG_SKIP_EXISTING_SUMMARY=true`)
5. **엉성한/시험본 재생성** — 기존 md를 `_trial_*`로 옮긴 뒤 `BACKLOG_FORCE=1` + `BACKLOG_SKIP_EXISTING_SUMMARY=0`으로 **일자별 1건씩** 재실행

### 품질 기준 (재생성 시)

- 파일당 해당 날짜 영상만 다룰 것
- 한국어 종목명·수치 보존 (영어 오역 남발 금지)
- `GEMINI_MIN_RESPONSE_CHARS=1500` 미만이면 실패로 보고 재시도
- 매 영상 **새 Gemini 채팅**에서 처리 (이전 대화 오염 방지)

## 언제 백로그를 돌리나

- PC/스케줄러 중단 후 밀린 영상 요약
- `processed.json` / 요약 파일이 없는 날짜가 있을 때
- “밀린 것 요약”, “7/2~7/16 catch-up” 요청

## 권장 워크플로 (에이전트)

```
1) list_backlog.py 로 대상 확인
2) BACKLOG_LIMIT=1 로 가장 오래된 1건 실행
3) backlog_summaries + Discord + run.log 확인
4) 실패하면 원인 고치고 같은 1건 재시도
5) BACKLOG_LIMIT=2~3 으로 검증
6) 남은 구간을 LIMIT 단위로 이어 실행
7) troubleshooting.md / SKILL.md 에 새 이슈 기록
```

## 빠른 실행 (PowerShell)

```powershell
cd v

# 1) 대상만 확인
$env:BACKLOG_FROM="2026-07-02"
$env:BACKLOG_TO="2026-07-16"
python list_backlog.py

# 2) 1건만
$env:BACKLOG_FROM="2026-07-10"
$env:BACKLOG_TO="2026-07-10"
$env:BACKLOG_LIMIT="1"
$env:BACKLOG_STOP_ON_ERROR="1"
powershell -ExecutionPolicy Bypass -File .\run_backlog.ps1

# 3) 품질 나쁜 요약 재생성 (시험본 교체)
#    기존 md → backlog_summaries/_trial_*/ 로 이동 후:
$env:BACKLOG_FROM="2026-07-02"
$env:BACKLOG_TO="2026-07-02"
$env:BACKLOG_LIMIT="1"
$env:BACKLOG_FORCE="1"
$env:BACKLOG_SKIP_EXISTING_SUMMARY="0"
powershell -ExecutionPolicy Bypass -File .\run_backlog.ps1
```

## 환경 변수

| 변수 | 용도 |
|------|------|
| `BACKLOG_FROM` / `BACKLOG_TO` | 날짜 범위 `YYYY-MM-DD` |
| `BACKLOG_LIMIT` | 처리할 최대 건수 (1 → 한 영상씩) |
| `BACKLOG_STOP_ON_ERROR` | `true`(기본) — 실패 시 즉시 중단 |
| `BACKLOG_SKIP_EXISTING_SUMMARY` | `true`(기본) — 요약 md 있으면 스킵 |
| `BACKLOG_FORCE` | `true` — `processed.json` 무시하고 **재처리** (`process_video`까지 적용) |
| `BACKLOG_INCLUDE_WEEKENDS` | 주말·벨류체크 포함 |
| `TRANSCRIPT_PREFER_YTDLP` | `true` — 자막 API 대신 yt-dlp 우선 |
| `GEMINI_MIN_RESPONSE_CHARS` | 백로그 품질용 1500 권장 |
| `RUN_BACKLOG` | `1` — 백로그 모드 |

## 제목 탐지 (2026-07 이후 중요)

제목 형식이 바뀜:

- 예전: `[체슬리모닝브리프] ... [26/07/02]`
- 요즘: `... | 박세익 전무 & 체슬리투자자문 [모닝브리프 / 26.07.14.화]`
- English flat: 마커 없이 영어만 → `/streams` 최근 항목은 **메타데이터로 한국어 제목 재확인**

마커: `모닝브리프`, `Morning Brief`, `매일 아침 펀드매니저`, `Daily Morning Fund Manager`  
제외: `별난`/`학습부장` 학습 방송

날짜: `26/07/14`, `26.07.14` 모두 파싱.

## 출력

- `v/backlog_summaries/YYYY-MM-DD_{video_id}.md` — 영상당 1파일
- Discord — 헤더에 날짜|제목 붙인 뒤 Gem 응답
- `v/processed.json` — 성공한 video_id
- `v/run.log`

## Gemini 세션

```powershell
$env:SETUP_LOGIN_ONLY="1"
$env:HEADLESS="false"
python main.py
```

Gem 이름 검증이 깨져도 채팅 입력이 보이면 계속 진행함.

## 상세 트러블슈팅

[v/troubleshooting.md](v/troubleshooting.md)
