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
│   ├── _shared/         ← 모든 스킬이 쓰는 공통 로더 (skill_env.py / skill_env.js)
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
