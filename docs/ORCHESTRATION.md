# 오케스트레이션 — 교사 PC(집·학교)의 Claude Code 가 작업자들을 이끄는 방법

여러 AI 작업자(웹 Claude, bizcoder, Gemini CLI, ChatGPT 무료)가 [TASKS.md](TASKS.md) 의 일을 브랜치·PR 로 올리면,
**교사 PC 의 Claude Code 가 검토하고 합치고 다음 일을 나눠 준다.** 집 PC·학교 PC 어디서든 이 문서대로 하면 같게 돈다.
필요한 것은 모두 저장소에 있다: 할 일 [TASKS.md](TASKS.md), 작업자 규칙 [WORKER_GUIDE.md](WORKER_GUIDE.md), 검토 에이전트 [`.claude/agents/reviewer.md`](../.claude/agents/reviewer.md).

## 0. 시작 위치

- Claude Code 는 **`my-skills` 폴더에서** 연다(그래야 저장소의 `CLAUDE.md` 와 `.claude/agents/reviewer.md` 를 읽음).
- 먼저 `git pull --rebase --autostash` 로 다른 PC·작업자의 변경을 받는다.

## 1. 올라온 일 보기

```powershell
git fetch --all --prune
git branch -r --no-merged origin/main        # 아직 안 합친 작업자 브랜치
git log --oneline origin/main..origin/<브랜치>  # 그 브랜치의 커밋
git diff --stat origin/main...origin/<브랜치>   # 바뀐 파일
```
GitHub CLI(`gh`)가 있으면 `gh pr list`, `gh pr view <번호>` 도 쓸 수 있다(없어도 됨 — 브랜치를 main 에 합쳐 푸시하면 GitHub 가 그 PR 을 '합쳐짐'으로 바꿈).

## 2. 검토 (브랜치마다)

1. 범위 확인: TASKS 의 "고쳐도 되는 파일" 밖을 건드렸는지
2. `reviewer` 에이전트로 독립 검토(버그·개인정보·보안). 큰 변경일수록 꼭
3. 직접 확인: 그 스킬 시험 실행, `python tools/build_catalog.py --check`, `git diff` 에 이름·번호·키·절대 경로가 없는지
4. 교사 PC 에서만 되는 확인(실제 키·지도서·사이트)이 필요하면 여기서 해 본다. 실제 발송·제출은 교사 확인 뒤에만

## 3. 합치기

```powershell
git checkout main; git pull --rebase
git merge --no-ff origin/<브랜치> -m "merge: <TASKS 번호> <요약>"
# 시험·카탈로그 점검 다시 → 통과하면
git push
git push origin --delete <브랜치>     # 합친 작업자 브랜치 정리(선택)
```
- 충돌이 나면 작업자에게 되돌려 보내기보다, 작으면 여기서 고치고 크면 PR 에 이유를 적어 돌려보낸다.
- 고칠 점이 있으면 합치지 말고 작업자에게 넘길 **고칠 목록**을 만들어 교사에게 준다(작업자에게 그대로 붙여 넣을 수 있게).

## 4. 목록 정리와 다음 일 나눠 주기

- [TASKS.md](TASKS.md) 상태를 고친다(`검토 대기` → `완료`, 새로 생긴 일 추가). 작업자는 이 파일을 고치지 않는다.
- 교사가 "누가 비었다"고 하면, 그 작업자의 등급(R/P/T)에 맞는 `열림` 일을 골라 **붙여 넣을 프롬프트**를 만들어 준다.
  기본 틀은 [WORKER_GUIDE.md](WORKER_GUIDE.md) 의 "작업자 프로젝트에 넣을 지침 문구" + 그 일의 TASKS 줄.
- 서로 같은 파일을 두 작업자에게 주지 않는다.

## 5. PC 마다 한 번 준비할 것

| 무엇 | 왜 | 방법 |
|---|---|---|
| Claude Code 설치·로그인 | 오케스트레이터 | 같은 Pro 계정. 두 PC 에서 동시에 쓰면 사용량을 같이 씀 |
| git 사용자 이름·이메일 | 커밋 | `git config --global user.name/email` (GitHub 계정과 같게) |
| 중앙 `.env` | 실제 키가 필요한 확인 | 학교 OneDrive(`OneDrive - gyo6.net\96. 인증\.env`)로 이미 공유 |
| Python·Node·Gemini CLI·크롬 로그인 | 시험·실제 실행 | `teacherlesson-assistant` 의 학교 PC 점검 도구(T20)로 빠진 것 확인 |
| (선택) GitHub CLI `gh` + `gh auth login` | PR 목록·댓글 | 없어도 git 만으로 됨 |
| (선택) Claude 기억(memory) 공유 | 집·학교 Claude 가 같은 배경지식 | 아래 |

### Claude 기억 공유 (선택)
Claude Code 의 기억은 PC 의 `%USERPROFILE%\.claude\projects\<작업 폴더 이름>\memory\` 에 따로 쌓인다.
저장소 관련 사실은 이미 저장소 문서(TASKS·ISSUES·이 문서)에 있으므로 꼭 필요하지는 않다.
같이 쓰려면 두 PC 모두 그 `memory` 폴더를 OneDrive 의 한 폴더로 연결(junction)한다 — 교사 확인 뒤에 한다.
기억에는 비밀번호·키·학생 개인정보를 적지 않는 규칙이 있으므로 OneDrive 에 두어도 된다(교사 판단).
