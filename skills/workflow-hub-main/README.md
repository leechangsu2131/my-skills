# ai-workflow-hub

**Antigravity → Cursor → Codex** 삼각편대 + GitHub 중심 AI 협업 워크플로우

---

## 폴더 구조

```
ai-workflow-hub/
├── projects/              ← 프로젝트별 폴더 (각자 독립)
│   └── [프로젝트명]/
│       ├── README.md      ← 프로젝트 개요
│       └── ...
├── docs/
│   ├── plans/             ← 분기별 플랜 (Antigravity가 생성)
│   └── retrospectives/    ← 회고 문서
├── .agents/
│   └── workflows/         ← Antigravity 워크플로우 정의
├── archive/               ← 완료된 프로젝트 보관
├── CONTRIBUTING.md        ← 에이전트 공통 규칙
└── README.md
```

## 도구별 역할

| 도구 | 역할 | 주요 작업 |
|------|------|-----------|
| **Antigravity** | 기획·조율 | 이슈 생성, 플랜 문서, 에이전트 할당 |
| **Cursor** | 구현 | 브랜치 생성, 코딩, PR |
| **Codex** | 자동화 | 테스트, 리팩터, 반복 작업 |

## 브랜치 규칙

```
main                          ← 보호 브랜치 (직접 push 금지)
feature/ISSUE번호-설명         ← 새 기능
fix/ISSUE번호-설명             ← 버그 수정
docs/설명                      ← 문서 작업
```

## 시작하기

1. 이 레포를 GitHub에 push
2. `docs/plans/` 에 플랜 문서 추가 (Antigravity로)
3. GitHub Issue 생성 후 브랜치 따서 작업 시작
