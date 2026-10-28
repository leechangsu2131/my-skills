# 에이전트 작업 규칙 (CONTRIBUTING)

> Antigravity, Cursor, Codex가 이 레포를 수정할 때 반드시 따르는 규칙

---

## 디렉터리 용도

| 폴더 | 용도 | 주로 수정하는 도구 |
|------|------|-------------------|
| `projects/[이름]/` | 프로젝트별 코드·문서 | Cursor, Codex |
| `docs/plans/` | 분기 기획 문서 | Antigravity |
| `docs/retrospectives/` | 완료 후 회고 | Antigravity |
| `.agents/workflows/` | Antigravity 워크플로우 | Antigravity |
| `archive/` | 완료 프로젝트 보관 | 사람 직접 |

---

## 절대 금지

- `main` 브랜치에 직접 push ❌
- `.env`, API 키, 비밀번호 커밋 ❌
- PR 리뷰 없이 머지 ❌

---

## 브랜치 네이밍

```
feature/ISSUE번호-한줄설명      예: feature/3-school-report-generator
fix/ISSUE번호-한줄설명          예: fix/7-date-parse-error
docs/한줄설명                   예: docs/q2-2026-plan
refactor/한줄설명               예: refactor/cleanup-scripts
```

---

## 커밋 메시지

```
feat: 새 기능 추가 설명
fix: 버그 수정 설명
docs: 문서 업데이트
refactor: 코드 정리
chore: 설정 변경 등 기타
```

---

## 도구별 담당 범위

### Antigravity
- `docs/plans/`, `docs/retrospectives/` 작성
- GitHub Issue 초안 생성
- 태스크 쪼개기 및 에이전트 할당 지시

### Cursor
- `projects/[이름]/` 안에서 코드 작업
- PR 생성까지 담당
- 소·중 규모 작업의 메인 구현 도구

### Codex
- 테스트 스크립트 작성
- 여러 파일 동시 리팩터링
- 반복 패턴 자동화

---

## 새 프로젝트 시작 순서

```
1. Antigravity로 docs/plans/ 에 플랜 작성
2. GitHub Issue 생성 (수락 기준 포함)
3. feature/ISSUE번호-설명 브랜치 생성
4. Cursor로 projects/[이름]/ 안에서 구현
5. PR → 사람 리뷰 → main 머지
6. Antigravity로 docs/retrospectives/ 회고 작성
```
