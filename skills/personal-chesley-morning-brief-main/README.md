# 체슬리 모닝 브리프 자동 요약 에이전트 📰

유튜브 채널 [@chesleytv](https://www.youtube.com/@chesleytv)의 '체슬리모닝브리프' 영상을 매일 자동으로 감지하고, 영상 스크립트 전체를 추출하여 **Gemini Gems(스크립트 정리 도우미)**를 통해 심층 구조화 분석을 진행한 뒤, 결과를 Discord로 전송하는 자동화 파이프라인입니다.

## 기능 특징
- **전체 스크립트 기반 심층 분석:** 2시간 분량(약 4만자)의 유튜브 스크립트를 자르지 않고 전체 전송하여 완벽한 구조화 리포트 도출
- **Gems 자체 지침 우선 적용:** 짧은 요약을 방지하고 '스크립트 정리 도우미' 전용 지침(참여자의 2차 해석 등)을 100% 적용하는 강력한 프롬프트 강제화
- **브라우저 자동화 (Patchright):** Gemini API의 토큰 한계나 비용 문제 없이, 사용자의 Gemini Advanced(Pro) 웹 세션을 직접 조종하여 최고 품질의 요약본 추출

## 필수 조건
- Python 3.9 이상
- Google Chrome 브라우저 설치됨
- Gemini Gems(스크립트 정리 도우미) 접근 권한이 있는 Google 계정

## 설치 및 세팅 방법

**1. 프로젝트 클론 및 스크립트 실행 환경 구성**
```bash
git clone <repository-url>
cd chesley-morning-brief

# 가상환경 생성 및 의존성 설치 (최초 1회 실행)
./run.sh
```

**2. 브라우저 세션 (Google 로그인) 최초 1회 연동**
Gemini Gems에 자동으로 접속해 분석하려면 브라우저 쿠키(세션)가 필요합니다. 터미널에서 아래 코드를 실행해 딱 한 번만 구글 로그인을 진행하세요. (이후 `.chesley-brief-browser` 폴더에 세션이 영구 저장됩니다.)
```bash
.venv/bin/python -c "
from patchright.sync_api import sync_playwright
import os
with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=os.path.expanduser('~/.chesley-brief-browser'),
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()
    page.goto('https://gemini.google.com')
    input('👉 브라우저 창에서 Google 로그인을 완료한 후, 여기 터미널에서 Enter 키를 누르세요...')
    browser.close()
"
```

**3. 필수 환경변수 설정 (.env 파일 생성)**
디스코드 웹훅 주소 등 민감한 정보는 깃허브에 올라가지 않도록 제외되어 있습니다. 
프로젝트 최상단(chesley-morning-brief 폴더)에 `.env` 라는 이름의 빈 파일을 하나 만드신 후, 아래와 같이 본인의 디스코드 채널 웹훅 주소를 적어 저장하세요.
```env
DISCORD_WEBHOOK="https://discord.com/api/webhooks/본인의_웹훅_주소"
```

## 자동화 스케줄링 (Cron)
매일 오후 4시 등 원하는 시간에 맞춰 동작하도록 OS 스케줄러에 등록합니다.
(Mac/Linux 예시: `crontab -e` 실행 후 아래 라인 추가)
```text
0 16 * * * /절대/경로/chesley-morning-brief/run.sh >> /절대/경로/chesley-morning-brief/cron.log 2>&1
```

## 파일 설명
- `chesley_brief.py`: 유튜브 대본 추출, Gemini 웹 자동화 제어, Discord 전송을 담당하는 메인 파이썬 로직
- `run.sh`: 가상환경(`venv`) 생성과 패키지 설치를 자동으로 관리하고 메인 스크립트를 실행하는 래퍼(Wrapper) 스크립트
- `requirements.txt`: 의존성 패키지 목록 (`requests`, `youtube-transcript-api`, `patchright`)
- `processed.json`: 이미 처리된 유튜브 영상의 ID를 기록하여 중복 전송 방지 (자동 생성됨)
