# 오케스트레이션 — 교사 PC(집·학교)의 Claude Code 가 작업자들을 이끄는 방법

여러 AI 작업자(Codex, Antigravity, 웹 Claude, bizcoder 등)가 [TASKS.md](TASKS.md) 의 일을 브랜치·PR 로 올리면,
**교사 PC 의 Claude Code 가 검토하고 합치고 다음 일을 나눠 준다.** 집 PC·학교 PC 어디서든 이 문서대로 하면 같게 돈다.
필요한 것은 모두 저장소에 있다: 할 일 [TASKS.md](TASKS.md), 작업자 규칙 [WORKER_GUIDE.md](WORKER_GUIDE.md), 검토 에이전트 [`.claude/agents/reviewer.md`](../.claude/agents/reviewer.md).

## 0-0. 지금 방침 (교사 결정 2026-11-26)

- **수업 비서 위주.** 일을 만들고 나눠 줄 때 [TASKS.md 맨 위 ★ 묶음](TASKS.md) 스킬만. 묶음 밖 스킬에는 새 일을 만들지 않는다(이미 올라온 브랜치는 시험이 통과하면 합치되 다음 일은 안 만듦).
- **작업자 구성과 맡기는 법** (2026-11-26 교사 확인: Codex·Antigravity 각 2명, 토큰 넉넉 — 아끼지 말고 '이번 일' 뒤에도 스스로 이어서 하게).

| 도구 | 사용량 | 어디서 | 맡기는 일 |
|---|---|---|---|
| Antigravity (2명: ag-1·ag-2) | 넉넉함 — 쉬지 않고 씀 | 교사 PC, `start_worker.ps1 -Tool antigravity` 폴더(에이전트마다 하나) | P 일(D·I 의 P)·큰 기능(G·I). 크롬(9233)을 쓰는 일은 한 명에게만 |
| Codex (2명: codex-1·codex-2) | 넉넉함 — 쉬지 않고 씀 | 교사 PC 폴더(`-Tool codex`) 또는 웹 | R 일·mock 시험으로 확인되는 핵심 코드. 같은 파일을 고치는 일은 한 명에게 이어서 줌. 웹 Codex 가 푸시를 못 하면 오케스트레이터가 먼저 `python tools/claim_task.py <번호> <설명> --name codex-N` 으로 잡아 준 뒤 넘김 |
| Claude 웹·bizcoder | — | 웹·교사 PC | R 일 |
| ChatGPT 웹 | — | — | 맡기지 않음(저장소를 못 바꿈) |

## 0. 시작 위치

- Claude Code 는 **`my-skills` 폴더에서** 연다(그래야 저장소의 `CLAUDE.md` 와 `.claude/agents/reviewer.md` 를 읽음).
- 먼저 `git pull --rebase` 로 다른 PC·작업자의 변경을 받는다. 다른 세션이 커밋 안 한 파일 때문에 막히면 `git fetch` 후 **뒤처졌을 때만** `git pull --rebase --autostash`(그 파일을 넣었다 빼다 충돌이 날 수 있으므로 항상 붙이지 않는다).

## 0-1. 매일(또는 교사가 "현황" 할 때) 도는 순서

> 토큰 아끼기: 작업자 관리는 **새 대화**에서 한다(긴 대화는 답마다 앞 내용을 다시 읽어 비쌈). 필요한 것은 저장소(TASKS·일지·이 문서)와 기억에 다 있다.

1. `python tools/work_status.py --fetch --md` → 진행 중 브랜치·작업자·충돌·멈춤·마지막 일지·안 잡힌 일 수
2. 임시 worktree 에서 `python tools/merge_ready.py --merge --push` → **문서·시험만** 바꾼 브랜치는 기계적으로 합침(내용은 읽지 않음, 시험·카탈로그만 확인). **코드 바뀜** 브랜치만 reviewer 에이전트 → 2·3번(검토·합치기). 같은 일로 브랜치가 둘이면 최신·충돌 없는 쪽만 합치고 나머지는 교사에게 정리 요청
3. **멈춤(3일 넘게)**·일지 `막힘` → 이유를 보고 풀 수 있으면 풀고, 아니면 교사에게 한 줄로
4. **안 잡힌 '열림' 일이 10개 아래**면 TASKS 를 채운다: ★ 수업 비서 묶음 스킬 ISSUES 의 🔵·📌, 검토에서 나온 🟡, 작업자 일지의 `막힘`·`그만둠` 에서 새 일을 만든다(번호·등급·고칠 파일·끝난 기준)
5. TASKS 상태 정리(`완료`, `검토 대기`) 후 푸시
6. 교사에게 짧게: 합친 것 · 막힌 것 · 교사 결정이 필요한 것 · 빈 작업자에게 줄 일

## 0-2. 교사 PC 에서 작업자 켜기 (까만 창)

```powershell
cd $env:USERPROFILE\Documents\GitHub\my-skills
powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool bizcoder -Name bizcoder-1 -Task T77
```
- `-Tool` 은 antigravity / codex / bizcoder / claude / gemini. Antigravity 는 폴더를 만들어 열고 첫 요청을 클립보드에 넣어 준다(에이전트 창에 붙여 넣기).
- **로컬 작업자(Antigravity·Codex CLI·bizcoder·로컬 Claude Code·Gemini CLI)의 일은 오케스트레이터가 정한다** → `-Task <번호>`. 스크립트가 도구를 켜기 전에 `tools/claim_task.py <번호> --check` 로 확인하고, 누가 하고 있거나 완료·결정 대기면 켜지 않는다. 작업자는 시작 직전에 `claim_task.py` 로 일을 잡는다. `-Task` 없이 켜면 스스로 고르되 역시 `claim_task.py` 로 잡는다.
- **로컬 CLI 작업자는 이 스크립트가 만든 폴더에서만** 일한다. 따로 받은 저장소·다른 폴더에서 돌리면 원격 브랜치를 새로 받지 않아 남이 잡은 일을 못 본다(2026-11-25~26 T10·T11·T25 를 다른 폴더의 로컬 작업자가 다시 함). 같은 저장소의 작업 폴더끼리는 브랜치 목록을 같이 써서, 아직 안 올린 브랜치까지 `claim_task.py` 가 본다.
- 작업자마다 **자기 작업 폴더** `GitHub\my-skills-<이름>`(git worktree)를 처음 한 번 만들고, 거기서 도구를 켜고 첫 요청을 넣는다. 같은 폴더를 여러 작업자가 쓰면 브랜치가 뒤섞인다.
- 여러 명이면 까만 창을 여러 개 열어 이름만 바꿔 실행(`bizcoder-2`, `gemini-1` …). 이어서 할 때도 같은 명령.
- bizcoder 는 확인 없이 스스로 진행(`--auto`, 위험 명령·공개 배포만 물음). 사용량 `bizcoder usage`, 로그인 `bizcoder whoami`, 읽는 지침 `bizcoder compat`.
- 다 쓴 작업 폴더 지우기: `git worktree remove ..\my-skills-<이름>` (안 합친 브랜치가 없을 때).

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
- 합친 뒤 곧바로 `git push`. 그사이 원격이 바뀌어 푸시가 거절되면 `git pull --rebase=merges` 로 받는다(그냥 `--rebase` 는 합치기 커밋을 풀어 커밋 번호가 바뀌어, GitHub 가 그 PR·브랜치를 '안 합쳐짐'으로 보여 줌 — 2026-11-25 실제로 생김. 그때는 PR 을 손으로 닫으면 됨).
- 충돌이 나면 작업자에게 되돌려 보내기보다, 작으면 여기서 고치고 크면 PR 에 이유를 적어 돌려보낸다.
- 고칠 점이 있으면 합치지 말고 작업자에게 넘길 **고칠 목록**을 만들어 교사에게 준다(작업자에게 그대로 붙여 넣을 수 있게).

## 4. 목록 정리와 다음 일 나눠 주기

- [TASKS.md](TASKS.md) 상태를 고친다(`검토 대기` → `완료`, 새로 생긴 일 추가). 작업자는 이 파일을 고치지 않는다.
- 교사가 "누가 비었다"고 하면, 그 작업자의 등급(R/P)과 사용량(0-0 표)에 맞는 `열림` 일을 골라 **붙여 넣을 프롬프트**를 만들어 준다.
  기본 틀은 [WORKER_GUIDE.md](WORKER_GUIDE.md) 의 "작업자 프로젝트에 넣을 지침 문구" + 그 일의 TASKS 줄.
- 서로 같은 파일을 두 작업자에게 주지 않는다.
- 일을 주기 전, 그리고 **오케스트레이터가 P 일을 직접 하기 전에도** `python tools/claim_task.py <번호> --check`. 2026-11-25 T23 은 작업자가 이미 PR 까지 올린 일을 교사 PC 가 main 에 따로 또 만들었다.

## 5. PC 마다 한 번 준비할 것

| 무엇 | 왜 | 방법 |
|---|---|---|
| Claude Code 설치·로그인 | 오케스트레이터 | 같은 Pro 계정. 두 PC 에서 동시에 쓰면 사용량을 같이 씀 |
| git 사용자 이름·이메일 | 커밋 | `git config --global user.name/email` (GitHub 계정과 같게) |
| 중앙 `.env` | 실제 키가 필요한 확인 | 학교 OneDrive(`OneDrive - gyo6.net\96. 인증\.env`)로 이미 공유 |
| Python·Node·Gemini CLI·크롬 로그인 | 시험·실제 실행 | `teacherlesson-assistant` 의 학교 PC 점검 도구(T20)로 빠진 것 확인 |
| (선택) GitHub CLI `gh` + `gh auth login` | PR 목록·댓글 | 없어도 git 만으로 됨 |
| Claude 기억(memory) 공유 | 집·학교 Claude 가 같은 배경지식 | 아래 (집 PC 는 2026-11-25 연결함) |

### Claude 기억 공유
Claude Code 의 기억은 **연 폴더마다** `%USERPROFILE%\.claude\projects\<폴더 경로를 - 로 바꾼 이름>\memory\` 에 따로 쌓인다.
그래서 `my-skills` 에서 열 때와 그 위 폴더에서 열 때 기억이 갈라지고, 집 PC 와 학교 PC 도 갈라진다.
→ 기억 원본은 **OneDrive `95. 개인\claude-memory`** 한 곳에 두고, 각 PC 의 `memory` 폴더를 그곳으로 연결(junction)한다(교사 결정 2026-11-25).
기억에는 비밀번호·키·학생 개인정보를 적지 않는다(비밀값은 `96. 인증` 의 `.env` 에만).

학교 PC 에서 한 번 (PowerShell, Claude Code 를 끈 상태에서. `<이름>` 은 그 PC 에서 my-skills 를 연 뒤 `projects` 아래 생긴 폴더 이름):
```powershell
$dst = "$env:OneDriveCommercial\95. 개인\claude-memory"
$m = "$env:USERPROFILE\.claude\projects\<이름>\memory"
if (Test-Path $m) { Copy-Item "$m\*" $dst -Exclude MEMORY.md; Rename-Item $m "memory.bak" }   # 학교 PC 에만 있던 기억은 합친 뒤 MEMORY.md 목록에 손으로 추가
New-Item -ItemType Directory -Force (Split-Path $m) | Out-Null
New-Item -ItemType Junction -Path $m -Target $dst
```
두 PC 에서 동시에 같은 기억 파일을 고치면 OneDrive 가 '충돌 사본'을 만든다. 보이면 합치고 사본은 지운다.
