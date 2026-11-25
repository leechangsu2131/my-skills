# 에이전트 작업 규칙 (CONTRIBUTING)

> Antigravity, Cursor, Codex가 이 레포를 수정할 때 반드시 따라야 할 규칙입니다.

---

## 디렉터리 구조

```
.agents/workflows/   → Antigravity 워크플로우 정의 (.md)
skills/_shared/      → 공통 로더 (skill_env.py / skill_env.js) — 비밀값·데이터 경로
skills/[name]/       → 스킬 하나 = 독립 폴더 (SKILL.md + ISSUES.md + 코드)
tools/               → build_catalog.py (CATALOG.md 생성·점검)
docs/                → 기획 문서, 플랜, 회고, templates/
CATALOG.md           → 자동 생성 목록 (직접 수정 금지)
```

## 필수 규칙

- 커밋·푸시는 아래 "커밋·푸시 방식"을 따른다 (현재: `main`에 바로 커밋)
- 새 스킬 추가 시 `skills/[name]/SKILL.md`와 `ISSUES.md` 필수 (양식: `docs/templates/`)
- 스킬 정보를 바꾸면 해당 `SKILL.md`의 `metadata`를 고치고 `python tools/build_catalog.py` 실행
- 문제를 해결하거나 막히면 그 스킬의 `ISSUES.md`에 기록 (증상·원인·해결·관련 파일)
- `.env`, 시크릿, API 키 커밋 절대 금지

## 비밀값·개인정보 규칙 (코드 작성 시 반드시)

- 비밀값·설정은 중앙 `OneDrive\96. 인증\.env` 한 곳에만 둔다. 스킬 폴더에 `.env`를 만들지 않는다.
- 코드는 공통 로더로 읽는다. 키·비밀번호·전화번호를 코드나 문서에 직접 쓰지 않는다.
  ```python
  import sys, pathlib; sys.path.insert(0, str(next(p / "_shared" for p in pathlib.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
  from skill_env import load_env, data_dir
  load_env()                          # 중앙 .env → os.environ
  out = data_dir() / "result"         # 내 문서\my-skills-data\<스킬>\result
  ```
  Node: `require('../_shared/skill_env.js').loadEnv('<스킬>')`
- 한 스킬 전용 설정은 `스킬폴더명대문자__KEY` 로 적는다 (DRY_RUN, PORT 같은 흔한 이름이 다른 스킬로 새지 않게).
- 학생·학부모 이름·연락처·평어, 화면 덤프, 로그인 세션, 실행 결과물은 `data_dir()` 아래에만 저장한다. 저장소에 커밋하지 않는다.
- `C:\Users\<이름>\...` 같은 절대 경로를 하드코딩하지 않는다 (`%OneDrive%`, `%USERPROFILE%`, `data_dir()` 사용).

## 커밋·푸시 방식

**현재 (임시, 2026-11-20~): 교사 PC 의 Claude Code 만 `main`에 바로 커밋·푸시**
- 교사 PC 의 Claude Code(오케스트레이터)는 브랜치·PR 없이 `main`에 바로 올린다.
- **다른 AI 작업자(웹 Claude, Gemini CLI, bizcoder, Codex 등)는 이 예외가 없다.** 반드시 `task/…` 브랜치 + PR 로 올린다([docs/WORKER_GUIDE.md](docs/WORKER_GUIDE.md)).
- 대신 커밋 전에 반드시
  1. `git diff --staged`로 학생·학부모 개인정보, 전화번호·집 주소, 비밀값이 없는지 확인한다. 저장소는 공개다(교사·교직원 이름, 이메일 주소, 학교 업무 정보는 막지 않음 — 2026-11-25 교사 결정).
  2. 내가 고친 파일만 `git add <파일>`로 고른다. 다른 도구·세션이 작업 중인 파일은 섞지 않는다(`git add -A` 금지).
  3. `python tools/build_catalog.py --check` 통과를 확인한다.
  4. 푸시 전 원격 변경을 받는다: `git pull --rebase` (다른 세션이 커밋 안 한 파일이 있어 막히면 `git fetch` 후 뒤처졌을 때만 `git pull --rebase --autostash`).

**나중에 (여럿이 쓰거나 작업이 커지면): PR 방식으로 복귀**
- `main` 직접 push 금지 → 아래 이름의 브랜치에서 작업하고 PR로 머지, 머지 전 사람이 리뷰.
- 복귀할 때는 이 절과 `CLAUDE.md`의 임시 규칙을 함께 고친다.

## 브랜치 네이밍 (PR 방식으로 돌아갈 때 사용)

| 패턴 | 용도 |
|------|------|
| `feature/ISSUE번호-설명` | 새 스킬/기능 |
| `fix/ISSUE번호-설명` | 버그 수정 |
| `refactor/설명` | 코드 정리 |
| `docs/설명` | 문서/플랜 작업 |

**예:** `feature/7-youtube-playlist-skill`

## 커밋 메시지 형식

```
feat: [스킬명] 새 기능 설명
fix: [스킬명] 버그 수정 설명
docs: 문서 업데이트 설명
refactor: 코드 정리 설명
```

## 스킬 폴더 구조 (필수 템플릿)

```
skills/[skill-name]/
├── SKILL.md          ← 스킬 설명 + AI 행동 지침 (필수, 앞머리 metadata 포함)
├── ISSUES.md         ← 문제·해결 기록, 진행 중/백로그 (필수)
├── README.md         ← 사람용 상세 안내 (선택)
├── .env.example      ← 필요한 키 목록 (실제 값 X, 실제 값은 중앙 .env)
└── scripts/          ← 실제 코드
```

문제 기록 파일은 `ISSUES.md` 하나로 통일한다 (`troubleshooting.md`, `ing.md`, `NEXT_STEPS.md` 등 새로 만들지 않음).

## 도구별 역할 분담

| 단계 | 담당 도구 | 주요 작업 |
|------|-----------|-----------|
| 기획 | Antigravity | 이슈 생성, docs/ 플랜 작성 |
| 구현 | Cursor | 코딩, 커밋 (PR 방식 복귀 시 브랜치·PR) |
| 자동화 | Codex | 테스트, 리팩터, 품질 점검 |
| 스킬화 | Antigravity + Codex | 워크플로우 등록, 문서화 |

## 태스크 크기 기준

- **소규모** (1~2파일, 30분): Cursor 단독으로 해결
- **중규모** (새 스킬, 2~4시간): Cursor 구현 + Antigravity SKILL.md
- **대규모** (여러 스킬, 하루+): Antigravity 기획 → Cursor/Codex 구현
