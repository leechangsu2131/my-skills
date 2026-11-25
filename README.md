# my-skills

학교 행정·학생 기록·수업 준비·개인 생활을 돕는 자동화 스킬 모음입니다.
각 스킬은 `skills/` 아래에 **서로 독립된 폴더**로 있고, 모든 폴더가 **같은 문서 형식**을 따릅니다.

👉 **전체 목록: [CATALOG.md](CATALOG.md)** (분야별 · 상태 · 할 수 있는 일 · 문서 링크)

## 폴더 구조

```
my-skills/
├── README.md            ← 이 문서
├── CATALOG.md           ← 스킬 목록 (자동 생성 — 직접 고치지 않음)
├── CONTRIBUTING.md      ← AI 에이전트·작업 규칙
├── skills/
│   ├── _shared/         ← 공통 로더 (skill_env.py / skill_env.js), 사용자 Chrome 탭 CDP 도우미 (cdp_tab.py)
│   └── <스킬>/          ← 스킬 하나 = 폴더 하나 (아래 표준 형식)
├── tools/
│   └── build_catalog.py ← SKILL.md 들을 모아 CATALOG.md 생성·점검
├── docs/
│   ├── templates/       ← 새 스킬용 SKILL.md · ISSUES.md 양식
│   └── SECURITY_LESSONS_LEARNED.md
└── .agents/workflows/   ← Antigravity 워크플로우
```

## 스킬 폴더 표준 형식

```
skills/<스킬>/
├── SKILL.md        (필수) 무엇을·언제·어떻게. 앞머리 metadata 가 카탈로그의 원본
├── ISSUES.md       (필수) 문제·해결 기록, 진행 중인 일, 할 일
├── README.md       (선택) 사람용 상세 설명·설치 안내
├── .env.example    (선택) 필요한 설정 키 목록 (값은 비움)
└── 코드…
```

- **SKILL.md 앞머리**: `name`, `description`(AI가 언제 쓸지 판단) + `metadata`(`category`, `status`, `version`, `summary`)
- **ISSUES.md**: `🔵 진행 중` / `📌 백로그` / `🟢 해결됨` 세 절. 항목은 `ISSUE-번호: 제목 (날짜)` + 증상·원인·해결·관련 파일
- 양식: [docs/templates/SKILL.md](docs/templates/SKILL.md), [docs/templates/ISSUES.md](docs/templates/ISSUES.md)

## 비밀값과 개인정보

| 무엇 | 어디에 | 코드에서 |
|---|---|---|
| 토큰·API 키·비밀번호·시트 ID 등 모든 설정 | `OneDrive\96. 인증\.env` **한 파일** | `load_env()` / `env_values()` |
| 학생·학부모 정보, 실행 결과물, 로그인 세션 | `내 문서\my-skills-data\<스킬>\` | `data_dir()` |

- 윈도우 계정 이름이 달라도 `%OneDriveCommercial%`, 내 문서 위치를 자동으로 찾습니다.
- 한 스킬에서만 쓰는 설정은 `스킬폴더명대문자__KEY` 로 적습니다 (예: `UTIL_SCHOOL_PRINT__DRY_RUN=true`).
- 스킬 폴더에 `.env`를 만들지 않습니다 (`.gitignore`가 막습니다).
- 사용법은 [skills/_shared/skill_env.py](skills/_shared/skill_env.py) 맨 위 설명을 참고하세요.

## 업무 처리 흐름 (공문 → 처리 → 기록)

학교 업무를 AI와 함께 처리할 때는 **방법**과 **우리 학교 상황**을 나눠 기록합니다. 그래야 다음에 어떤 AI가 와도 이어서 일할 수 있습니다.

1. **공문 확인**: 공문 저장 폴더를 검색하고, 없으면 K-에듀파인 문서등록대장에서 찾아 직접 내려받습니다.
2. **요구사항 정리**: 무엇을, 언제까지, 누구에게 내는지 정리하고 우리 학교가 해당하는지 확인합니다.
3. **처리**: NEIS·에듀파인·서식 작업을 합니다. 제출·상신·발송은 사람에게 먼저 묻습니다.
4. **기록 두 갈래**

| 무엇 | 어디에 |
|---|---|
| 어떻게 하는가 (반복 절차, 화면 조작, 함정) — 이름·번호 없이 | 이 저장소 해당 스킬의 `SKILL.md` · `references/` · `ISSUES.md` |
| 우리 학교에서 무엇을 했는가 (공문번호, 학생·교사, 결재 상태, 남은 일) | 업무 폴더(OneDrive) `_업무기록\<연도> <업무> 처리기록.md` |

자세한 절차와 기록 양식: [skills/admin-edufine/references/gongmun-handling-workflow.md](skills/admin-edufine/references/gongmun-handling-workflow.md)

## 자주 하는 일

```powershell
# 카탈로그 다시 만들기 (SKILL.md 의 metadata 를 고친 뒤)
python tools/build_catalog.py

# 모든 스킬이 형식을 지키는지 점검
python tools/build_catalog.py --check

# 중앙 .env 와 데이터 폴더 위치, 특정 스킬이 보는 키 확인
python skills/_shared/skill_env.py admin-neis-bot
```

**새 스킬 추가**: `docs/templates/`의 두 양식을 새 폴더에 복사 → 내용 채우기 → `python tools/build_catalog.py`
