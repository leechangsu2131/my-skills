# 🛡️ 보안 사고 분석 및 재발 방지 가이드 (Security Lessons Learned)

> **문서 생성일**: 2026-10-17  
> **관련 저장소**: `my-skills` (GitHub 공개 저장소)  
> **목적**: 디스코드 웹후크 유출 사고를 계기로 저장소 전반에서 식별된 보안 및 개인정보 유출 사례를 기록하고, 동일한 실수를 방지하기 위한 보안 체크리스트를 정립함.

---

## 1. 사고 경과 (Incident Timeline)

1. **최초 증상**: 비공개 디스코드 채널(`#화천초메시지`)에 불특정 외부 디스코드 서버의 초대 링크 및 스팸 메시지 수백 건이 자동으로 유입됨.
2. **원인 추적**:
   - `skills/util-discord-memo/scripts/.env.example` 및 `SKILL.md`에 실제 디스코드 웹후크 URL이 하드코딩된 채 GitHub 공개(Public) 저장소로 푸시됨.
   - 공개 저장소를 실시간 크롤링하는 봇들이 디스코드 웹후크 패턴(`discord.com/api/webhooks/...`)을 스캔하여 수집.
   - 수집된 웹후크 URL로 무차별 POST 요청(스팸 및 서버 초대) 전송.
3. **추가 점검 결과**:
   - 웹후크 외에도 **브라우저 로그인 세션 쿠키**, **평문 비밀번호**, **교사 및 학생 개인정보**, **DOM 덤프 파일** 등이 함께 Git에 추적되어 원격 저장소에 노출되어 있던 것을 전수 식별함.

---

## 2. 노출되었던 취약 항목 상세 분석

### 🚨 1) 디스코드 웹후크 URL 노출 (스팸 폭격의 직접 원인)
- **노출 파일**:
  - `skills/util-discord-memo/scripts/.env.example` (`.../1477078821630120069/...`)
  - `skills/util-discord-memo/SKILL.md` (`.../1477089851928084664/...`)
- **위험성**:
  - 디스코드 웹후크는 서버 멤버십이나 권한 승인 절차 없이, **URL 주소만 알면 누구나 해당 채널에 메시지/임베드를 쏠 수 있는 마스터 키**입니다.
  - 공개 저장소에 단 한 번이라도 노출되면 수 초~수 분 내에 글로벌 스캐너 봇에게 탐지되어 영구 스팸 통로로 악용됩니다.

### 🚨 2) 브라우저 로그인 쿠키 및 세션 데이터 통째 노출 (세션 하이재킹 위험)
- **노출 파일**:
  - `skills/util-pdf-translator/scripts/auth/playwright_profile/` (약 450개 파일)
  - `skills/personal-youtube-gemini-kakao-automation/v/chrome_profile/` (약 1,100개 파일)
  - `skills/personal-youtube-gemini-kakao-automation/v/gemini_storage_state.json`
- **노출 내용**:
  - Chrome 브라우저의 `Default/Network/Cookies` (SQLite 쿠키 DB), `Default/Login Data`, `Default/History`, `Default/Sessions/`
  - `gemini_storage_state.json` 내 실제 구글 계정 세션 쿠키(`COMPASS`, `NID`, `_ga` 등) 평문 노출
- **원인 분석**:
  - `.gitignore`에 `!skills/**/scripts/auth/*`와 같은 광범위한 부정(예외) 규칙이 들어가 있어 하위의 `playwright_profile` 전체가 Git 추적에 포함됨.
  - 이전에 `git add`되었던 프로필 폴더가 `.gitignore` 추가 이후에도 캐시(`git rm --cached`)에서 제거되지 않고 계속 커밋됨.
- **위험성**:
  - 공격자가 아이디/비밀번호를 몰라도, 2단계 인증(2FA)을 통과한 유효 쿠키를 주입하여 피해자의 계정으로 즉시 로그인(Session Hijacking)할 수 있는 극도로 위험한 보안 사고입니다.

### ⚠️ 3) 계정 비밀번호 평문 하드코딩
- **노출 파일**:
  - `skills/classmanage-iscream-evaluate/iscream_evaluate.py`
  - `skills/classmanage-iscream-evaluate/scratch/final_verify_save.py`
  - `skills/classmanage-iscream-evaluate/SKILL.md` 및 `ing.md`
- **노출 내용**:
  - 환경변수 fallback 기본값으로 실제 비밀번호 문자열(`dlckdtn3`)을 지정 (`os.environ.get("ISCREAM_EVAL_PASSWORD", "dlckdtn3")`).
  - 안내 문서 및 구현 일지에 비밀번호를 평문으로 기재.
- **위험성**:
  - 소스코드나 문서 열람 권한이 있는 누구나 해당 교육 포털 계정에 침입 가능.

### ⚠️ 4) 웹 자동화 DOM 덤프 파일 내 교사 개인정보 & OAuth Token 노출
- **노출 파일**:
  - `skills/classmanage-iscream-evaluate/iscream_dom_dump.html`
  - `skills/classmanage-iscream-evaluate/iscream_pwd_check_dom.html`
  - `skills/classmanage-iscream-evaluate/iscream_verification_dom.html`
- **노출 내용**:
  - 브라우저 자동화 디버깅 중 저장된 DOM HTML 파일 내에 교사 로그인 ID(`lee2131`), 생년월일(`19851112`), 소속 학교(`화천초등학교`), 실제 만료 전 OAuth `idToken`(JWT)이 그대로 포함됨.
- **원인 분석**:
  - 셀렉터 디버깅용 임시 덤프 파일을 `.gitignore`에 등록하지 않고 Git에 커밋함.

### ⚠️ 5) 학생 실명 및 평가 기록 엑셀 파일 노출
- **노출 파일**:
  - `skills/classmanage-supabase-export/student_records.xlsx`
  - `skills/classmanage-iscream-evaluate/popup_subject_open.html`
- **노출 내용**:
  - 학생 번호, 실명(강시우 등 다수), 교과학습 발달상황 평가 기록이 담긴 실제 엑셀 파일 및 팝업 캡처 HTML.
- **위험성**:
  - 학생 개인정보는 교육기관 및 개인정보보호법상 엄격하게 보호되어야 하는 민감 정보로, 공개 저장소 노출 시 심각한 법적·행정적 문제가 발생할 수 있음.

### ℹ️ 6) 실제 인프라 엔드포인트 URL 노출
- **노출 파일**: `skills/classmanage-iscream-evaluate/.env.example`
- **노출 내용**: 실제 Supabase 프로젝트 고유 URL (`https://erzdvlcbjneabxqwnwfy.supabase.co`) 기재.

---

## 3. 취해진 대응 및 정화 조치

1. **웹후크 무효화 및 재발급**:
   - 디스코드 관리자 설정에서 유출된 구형 웹후크 즉시 삭제 완료.
   - 신규 발급된 비공개 웹후크는 로컬의 `.env` 파일에만 저장.
   - 공유 파일(`.env.example`, `SKILL.md`)은 더미 값(`YOUR_WEBHOOK_URL`)으로 완전 교체.
2. **Git 추적 해제 및 저장소 파일 제거 (`git rm --cached`)**:
   - `skills/util-pdf-translator/scripts/auth/playwright_profile/` (1,500여 개 파일)
   - `skills/personal-youtube-gemini-kakao-automation/v/chrome_profile/`
   - `skills/personal-youtube-gemini-kakao-automation/v/gemini_storage_state.json`
   - `skills/classmanage-supabase-export/student_records.xlsx`
   - `skills/classmanage-iscream-evaluate/*dom*.html`, `popup_*.html`
3. **코드 및 문서 내 민감정보 제거**:
   - `iscream_evaluate.py` 내 fallback 기본값을 빈 문자열(`""`)로 변경.
   - `SKILL.md` 및 `ing.md` 내 비밀번호 문자열 완전 마스킹.
   - `.env.example` 내 Supabase 실제 URL을 `https://your-project.supabase.co`로 치환.
4. **`.gitignore` 규칙 대폭 강화**:
   ```gitignore
   # Browser profiles and storage state (NEVER commit)
   **/playwright_profile/
   **/chrome_profile/
   *_storage_state.json
   gemini_storage_state.json
   kakao_token.json
   *_dom*.html
   *_dump*.html
   iscream_*.html
   popup_*.html

   # Student personal data & administrative result outputs
   student_records*.xlsx
   **/result/*.xlsx
   **/result/*.csv
   ```
5. **원격 저장소 커밋 및 푸시 완료**:
   - 커밋 해시: `f7fdca60` 및 후속 커밋

---

## 4. 사용자 필수 안전 조치 (Checklist)

저장소의 최신 파일에서는 제거되었으나, **GitHub의 이전 커밋 히스토리에 한 번이라도 기록되었던 자격 증명은 이미 유출된 것으로 간주**해야 합니다.

- [ ] **디스코드 웹후크**: 유출된 기존 웹후크 삭제 완료 확인
- [ ] **i-scream 비밀번호**: i-scream 사이트 로그인 후 계정 비밀번호를 즉시 새로운 비밀번호로 변경
- [ ] **Google 계정 세션 무효화**:
  - `Google 계정 관리` → `보안` → `내 기기` 이동
  - `모든 기기에서 로그아웃` 수행
  - Google 계정 비밀번호 1회 변경 (이전 발급된 브라우저 쿠키/토큰 즉시 파기됨)
- [ ] **저장소 공개 여부 검토**:
  - 학교 업무/개인 자동화 도구가 포함된 본 저장소(`my-skills`)를 GitHub에서 **Private(비공개) 저장소**로 전환하는 것을 적극 권장합니다.

---

## 5. 다음번 개발 시 반드시 지켜야 할 "7대 보안 원칙"

1. **`.env` 파일은 절대 Git에 올리지 않는다.**
   - 실제 Key, Token, URL, PW는 로컬 `.env`에만 보관합니다.
   - `.env.example`에는 반드시 `YOUR_API_KEY_HERE`, `YOUR_WEBHOOK_URL` 같은 명백한 가짜 더미 값만 넣습니다.
2. **코드 fallback에 실제 비밀값을 넣지 않는다.**
   - 나쁜 예: `os.getenv("PW", "실제비밀번호")`
   - 좋은 예: `os.getenv("PW", "")` 또는 미설정 시 오류를 발생시키고 종료 (`raise ValueError(".env에 PW를 설정하세요")`).
3. **브라우저 프로필 폴더(`chrome_profile`, `playwright_profile`)는 코드 작성 전 `.gitignore`에 넣는다.**
   - 브라우저 프로필 안에는 사용자가 방문한 모든 사이트의 로그인 쿠키와 캐시가 자동 생성됩니다.
4. **웹 자동화 디버깅 산출물(`*.html`, `*.png`, `*.log`)을 Git에 올리지 않는다.**
   - DOM 덤프 HTML 파일에는 화면에 보이지 않는 hidden input, JWT 토큰, 사용자 개인정보가 그대로 들어있습니다.
5. **학생 실명, 학교 내부 공문, 행정 결과물(엑셀/CSV/PDF)은 Git 추적에서 제외한다.**
   - 결과물이 저장되는 폴더(`result/`, `output/`, `data/`)는 사전에 `.gitignore`에 등록합니다.
6. **`.gitignore`에서 화이트리스트(`!`) 규칙을 쓸 때 극도로 주의한다.**
   - `!skills/**/scripts/auth/*` 처럼 폴더 전체를 열어버리면 그 하위에 생성되는 브라우저 프로필까지 전부 커밋 대상이 됩니다.
   - 필요한 특정 파일(`!*.example` 등)만 좁은 범위로 화이트리스트를 지정해야 합니다.
7. **`git commit` 전에는 반드시 `git status`로 변경 파일 목록을 눈으로 확인한다.**
   - 내가 수정한 코드 외에 자동 생성된 세션 파일, 프로필, 덤프 파일이 포함되어 있지 않은지 최종 점검합니다.
