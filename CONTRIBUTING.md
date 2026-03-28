# 에이전트 작업 규칙 (CONTRIBUTING)

> Antigravity, Cursor, Codex가 이 레포를 수정할 때 반드시 따라야 할 규칙입니다.

---

## 디렉터리 구조

```
.agents/workflows/   → Antigravity 워크플로우 정의 (.md)
skills/[name]/       → 스킬 구현 (SKILL.md + scripts/)
docs/                → 기획 문서, 플랜, 회고
```

## 필수 규칙

- `main` 브랜치에 직접 push 금지 → 반드시 PR로 머지
- PR 머지 전 반드시 사람이 리뷰
- 새 스킬 추가 시 `skills/[name]/SKILL.md` 필수 포함
- `.env`, 시크릿, API 키 커밋 절대 금지

## 브랜치 네이밍

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
├── SKILL.md          ← 스킬 설명 + AI 행동 지침 (필수)
└── scripts/          ← 실제 코드
    ├── main.py
    └── .env.example  ← 환경 변수 예시 (실제 값 X)
```

## 도구별 역할 분담

| 단계 | 담당 도구 | 주요 작업 |
|------|-----------|-----------|
| 기획 | Antigravity | 이슈 생성, docs/ 플랜 작성 |
| 구현 | Cursor | 브랜치 생성, 코딩, PR |
| 자동화 | Codex | 테스트, 리팩터, 품질 점검 |
| 스킬화 | Antigravity + Codex | 워크플로우 등록, 문서화 |

## 태스크 크기 기준

- **소규모** (1~2파일, 30분): Cursor 단독으로 해결
- **중규모** (새 스킬, 2~4시간): Cursor 구현 + Antigravity SKILL.md
- **대규모** (여러 스킬, 하루+): Antigravity 기획 → Cursor/Codex 구현
