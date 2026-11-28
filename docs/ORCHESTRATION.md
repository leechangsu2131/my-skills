# 오케스트레이션 — 교사 PC(집·학교)의 Claude Code 가 작업자들을 이끄는 방법

여러 AI 작업자(Codex, Antigravity, 웹 Claude, bizcoder 등)가 [TASKS.md](TASKS.md) 의 일을 브랜치·PR 로 올리면,
**교사 PC 의 Claude Code 가 검토하고 합치고 다음 일을 나눠 준다.** 집 PC·학교 PC 어디서든 이 문서대로 하면 같게 돈다.
필요한 것은 모두 저장소에 있다: 할 일 [TASKS.md](TASKS.md), 작업자 규칙 [WORKER_GUIDE.md](WORKER_GUIDE.md), 검토 에이전트 [`.claude/agents/reviewer.md`](../.claude/agents/reviewer.md).

## 0-0. 지금 방침 (교사 결정 2026-11-26)

- **Codex·Antigravity 는 큰 프로젝트(TASKS '★ 큰 프로젝트' P1…)를 맡고, 작은 T 번호 일은 Claude 웹 작업자에게.** 오케스트레이터는 ① 프로젝트 표(맡은 이·영역 파일·흡수한 T 번호) 관리 ② `합칠 준비` 가 오면 그때그때 합치기(`--no-ff`) ③ `막힘` 도움(작업자 브랜치에 직접 커밋하지 않고 `help/` 브랜치나 설명으로) ④ 같은 공용 파일(`web/index.html`·`assistant_server.py`)을 두 프로젝트가 고치면 먼저 합친 뒤 다른 쪽에 main 받기를 알림 ⑤ 로컬 IDE 를 바꿀 때 앞 IDE 가 `python tools/sync_work.py end` 로 끝냈는지(원래 my-skills 폴더에 커밋 안 한 변경·브랜치가 남지 않았는지) 확인.
- **수업 비서 먼저.** 체크리스트 일(K 등)은 [TASKS.md 맨 위 ★ 묶음](TASKS.md) 스킬로 만든다. 다른 스킬은 따로 일을 만들지 않아도 된다 — TASKS 일이 떨어지면 `claim_task.py --next` 가 **S8**(열린 이슈가 있는 스킬 하나 맡기: 묶음 먼저, 그다음 열린 이슈·최근 커밋 많은 스킬, `--skills` 로 순위)을 준다. 그래서 교사가 바라는 기능은 그 스킬 `ISSUES.md` 에 적어 두면 된다(교사 결정 2026-11-28: 수업 비서만 고치니 일이 금방 떨어짐). S8 브랜치도 다른 브랜치처럼 검토·합치기.
- **작업자 구성과 맡기는 법** (2026-11-26 교사 확인: Codex·Antigravity 계정 각 2개, 토큰 넉넉. **로컬 IDE 는 교사 PC 의 원래 `my-skills` 폴더에서 한 번에 하나**(Codex 를 안 쓸 때 Antigravity), 받고 올리기는 `tools/sync_work.py start/save/end`).

| 도구 | 사용량 | 어디서 | 맡기는 일 |
|---|---|---|---|
| Antigravity (계정 2개) | 넉넉함 — 쉬지 않고 씀 | 교사 PC 원래 `my-skills` 폴더(로컬 IDE 는 한 번에 하나) | Codex 를 안 쓸 때. P 일(D·I 의 P)·큰 프로젝트 |
| Codex (계정 2개) | 넉넉함 — 쉬지 않고 씀 | 교사 PC 원래 `my-skills` 폴더(한 번에 하나) 또는 클라우드 | 교사와 함께 큰 프로젝트. 클라우드 Codex 는 GitHub 에서 바로 일해 로컬 IDE 와 동시에 돌려도 됨. 클라우드가 푸시를 못 하면 오케스트레이터가 `claim_task.py` 로 미리 잡아 줌 |
| bizcoder | — | 교사 PC 원래 `my-skills` 폴더 — Codex·Antigravity 와 교대로 한 번에 하나(교사 결정 2026-11-27, 따로 폴더 안 만듦) | R·P 의 작은 T 번호 일(`start_worker.ps1 -Task`) |
| Claude 웹 | — | 웹 | R 일 |
| ChatGPT 웹 | — | — | 맡기지 않음(저장소를 못 바꿈) |

## 0. 시작 위치

- Claude Code 는 **`my-skills` 폴더에서** 연다(그래야 저장소의 `CLAUDE.md` 와 `.claude/agents/reviewer.md` 를 읽음).
- 먼저 `git pull --rebase` 로 다른 PC·작업자의 변경을 받는다. 다른 세션이 커밋 안 한 파일 때문에 막히면 `git fetch` 후 **뒤처졌을 때만** `git pull --rebase --autostash`(그 파일을 넣었다 빼다 충돌이 날 수 있으므로 항상 붙이지 않는다).

## 0-1. 매일(또는 교사가 "현황" 할 때) 도는 순서

> **오케스트레이터는 한 번에 하나만** (2026-11-26 집·학교 두 세션이 같은 브랜치 13개를 동시에 합쳐 일이 두 번 됨).
> 합치기 전에 `docs/worklog/orchestrator.md` 맨 아래에 `- <날짜 시각> <PC·세션> 합치는 중` 한 줄을 적어 **바로 푸시**하고, 끝나면 `- … 합치기 끝` 을 적는다.
> 시작 전에 그 파일 마지막 줄이 1시간 안의 `합치는 중` 이면 기다리거나 교사에게 묻는다. 합치는 도중에도 `git fetch` 로 main 이 움직였는지 자주 본다.

> 토큰 아끼기: 작업자 관리는 **새 대화**에서 한다(긴 대화는 답마다 앞 내용을 다시 읽어 비쌈). 필요한 것은 저장소(TASKS·일지·이 문서)와 기억에 다 있다.

1. `python tools/work_status.py --fetch --md` → 진행 중 브랜치·작업자·충돌·멈춤·마지막 일지·안 잡힌 일 수
2. 임시 worktree 에서 `python tools/merge_ready.py --merge --push` → **문서·시험만** 바꾼 브랜치는 기계적으로 합침(내용은 읽지 않음, 시험·카탈로그만 확인). **코드 바뀜** 브랜치만 reviewer 에이전트 → 2·3번(검토·합치기). 같은 일로 브랜치가 둘이면 최신·충돌 없는 쪽만 합치고 나머지는 교사에게 정리 요청
3. **멈춤(3일 넘게)**·일지 `막힘` → 이유를 보고 풀 수 있으면 풀고, 아니면 교사에게 한 줄로
   - **이어받기 가능**(2시간 넘게 커밋 없음·`그만둠`)은 따로 시키지 않아도 다음 작업자의 `claim_task.py --next` 가 잡는다(2026-11-27). 오케스트레이터는 같은 일로 브랜치가 둘 생긴 것만 정리한다.
   - 작업자에게는 번호를 주지 말고 '⓪ 공용' 프롬프트(WORKER_INSTRUCTIONS)만 — 일은 TASKS K(체크리스트 큰 일)에 넣어 두면 `--next` 가 나눠 준다.
4. **안 잡힌 '열림' 일이 10개 아래**면 TASKS 를 채운다: ★ 수업 비서 묶음 스킬 ISSUES 의 🔵·📌, 검토에서 나온 🟡, 작업자 일지의 `막힘`·`그만둠` 에서 새 일을 만든다(번호·등급·고칠 파일·끝난 기준)
5. TASKS 상태 정리(`완료`, `검토 대기`) 후 푸시
6. 교사에게 짧게: 합친 것 · 막힌 것 · 교사 결정이 필요한 것 · 빈 작업자에게 줄 일

## 0-2. 교사 PC 에서 작업자 켜기 (까만 창)

```powershell
cd $env:USERPROFILE\Documents\GitHub\my-skills
powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool bizcoder -Name bizcoder-1 -Task T77
```
- `-Tool` 은 bizcoder / claude / gemini / codex(CLI). 로컬 IDE(Codex 앱·Antigravity)는 이 스크립트를 쓰지 않고 원래 `my-skills` 폴더에서 한 번에 하나(WORKER_GUIDE 2-2).
- **까만 창 CLI 작업자(bizcoder·로컬 Claude Code·Gemini CLI·Codex CLI)의 일은 오케스트레이터가 정한다** → `-Task <번호>`. 스크립트가 도구를 켜기 전에 `tools/claim_task.py <번호> --check` 로 확인하고, 누가 하고 있거나 완료·결정 대기면 켜지 않는다. 작업자는 시작 직전에 `claim_task.py` 로 일을 잡는다. `-Task` 없이 켜면 스스로 고르되 역시 `claim_task.py` 로 잡는다.
- **로컬 CLI 작업자는 이 스크립트가 정한 폴더에서만** 일한다. 따로 받은 저장소·다른 폴더에서 돌리면 원격 브랜치를 새로 받지 않아 남이 잡은 일을 못 본다(2026-11-25~26 T10·T11·T25 를 다른 폴더의 로컬 작업자가 다시 함).
- **bizcoder 는 원래 `my-skills` 폴더에서** (교사 결정 2026-11-27 — 작업 폴더를 더 만들지 않음). Codex·Antigravity 와 **교대로 한 번에 하나**. 스크립트는 폴더에 커밋 안 한 변경이 있거나 남의 브랜치가 걸려 있으면(앞 작업자가 `sync_work.py end` 를 안 함) 켜지 않는다. bizcoder 는 일 하나마다 `claim_task.py` 로 잡기 → 커밋 → 일지 `PR 올림` → `sync_work.py end`(올리고 폴더 비우기) → 다음 일.
- bizcoder 를 여럿 동시에 돌려야 할 때만 `-Separate` 를 붙이면 예전처럼 자기 작업 폴더 `GitHub\my-skills-<이름>`(git worktree)를 만든다. 그 밖의 CLI(gemini·claude·codex)는 늘 자기 작업 폴더. 같은 폴더를 여러 작업자가 동시에 쓰면 브랜치가 뒤섞인다.
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
- 충돌이 나면 작업자에게 되돌려 보내기보다, 작으면 여기서 고치고 크면 PR 에 이유를 적어 돌려보낸다. 일지·문서 충돌은 `python tools/resolve_conflicts.py`(아래 4-1).
- 고칠 점이 있으면 합치지 말고 작업자에게 넘길 **고칠 목록**을 만들어 교사에게 준다(작업자에게 그대로 붙여 넣을 수 있게).

## 4. 목록 정리와 다음 일 나눠 주기

- [TASKS.md](TASKS.md) 상태를 고친다(`검토 대기` → `완료`, 새로 생긴 일 추가). 작업자는 이 파일을 고치지 않는다.
- 교사가 "누가 비었다"고 하면, 그 작업자의 등급(R/P)과 사용량(0-0 표)에 맞는 `열림` 일을 골라 **붙여 넣을 프롬프트**를 만들어 준다.
  기본 틀은 [WORKER_GUIDE.md](WORKER_GUIDE.md) 의 "작업자 프로젝트에 넣을 지침 문구" + 그 일의 TASKS 줄.
- 서로 같은 파일을 두 작업자에게 주지 않는다.
- 일을 주기 전, 그리고 **오케스트레이터가 P 일을 직접 하기 전에도** `python tools/claim_task.py <번호> --check`. 2026-11-25 T23 은 작업자가 이미 PR 까지 올린 일을 교사 PC 가 main 에 따로 또 만들었다.

## 4-1. 오케스트레이터 노하우 (2026-11-25~26 실제로 겪은 것 — 다른 PC 의 Claude Code 도 같은 수준으로)

**일하는 곳**
- 합치기는 원래 `my-skills` 폴더가 아니라 **임시 작업 폴더**에서: `git worktree add --detach <임시경로>\orch origin/main`, 합칠 때마다 `git switch -C orch-<이름> origin/main`. 원래 폴더는 로컬 IDE(Codex·Antigravity)가 쓰는 중일 때가 많다. 끝나면 `git worktree remove`.
- 로컬 IDE 의 작업은 원격에 없을 수 있다 → `git worktree list`·`git -C <폴더> status`·`git stash list` 로 어디 있는지부터. 커밋 안 한 변경이면 그 IDE 에서 커밋·`sync_work.py save` 부터.

**합치기 전에 볼 것**
1. 같은 일이 이미 다른 판으로 들어갔나: TASKS 상태·`tools/merge_ready.py`(T81 뒤로 다른 판 합침은 건너뜀).
2. 충돌 미리 보기: `git merge-tree --write-tree --name-only origin/main origin/<브랜치>` (0 이면 깨끗).
3. 개인정보: `git diff --no-textconv origin/main...<브랜치> | python tools/check_privacy.py --stdin`. **학생 이름은 검사기가 못 찾는다** → 데이터 폴더(OneDrive)의 학생 명단과 대조해 **건수만** 본다(이름을 화면에 내지 않음). `--no-textconv` 를 빼면 PDF 가 낀 diff 가 잘린다.
4. 코드가 바뀐 브랜치는 진도·쓰기 경로(`supabase_schedule.py` 등)에 시험이 있는지 본다. 없으면 합치되 TASKS 에 시험 일을 남긴다.

**여러 브랜치를 한 번에 합칠 때**
- 통합 브랜치에서 하나씩 `git merge --no-ff`. 충돌은 `python tools/resolve_conflicts.py` (일지는 시간순으로 자동, `--keep-both docs/...ISSUES.md` 는 두 쪽 다 남김). 코드 충돌은 직접 판단하거나 작업자에게.
- ISSUES 충돌에서 한쪽이 **옛 백로그판**(이미 🟢 해결로 옮겨진 항목)을 들고 오면 새 항목만 남긴다. ISSUE 번호가 겹치면 합칠 때 다시 매긴다.
- 지운 원격 브랜치는 커밋 번호를 커밋 메시지에 남긴다(되살리기 `git push origin <커밋>:refs/heads/<브랜치>`).

**시험**
- 시험 돌리는 Python 을 고정한다(교사 PC: Python 3.11 — 기본 `python` 에는 fitz 등 몇 패키지가 없음). CI 와 같은 대상(.github/workflows/check.yml 의 matrix)을 돌린다.
- 이번에 안 바뀐 스킬이 실패하면 그 PC 의 패키지 문제일 수 있다: `git diff --stat origin/main HEAD -- skills/<스킬>` 이 비면 이번 합치기 탓이 아니다.
- node 시험은 파일을 직접: `node --test tests/<파일>.test.js` (폴더만 주면 '모듈 없음'으로 실패처럼 보임).

**올리기**
- main 직접 푸시는 교사가 "합쳐줘·푸시해" 한 뒤. 올리기 직전 `git fetch` 로 뒤처졌는지 보고, 뒤처졌으면 `git pull --rebase=merges`(그냥 `--rebase` 금지).
- 받는 PC 에서 파일이 지워지는 합치기(추적 해제 등)는 그 PC 에서 먼저 백업하라고 교사에게 알린다.

**윈도우에서 문서·스크립트 고칠 때의 함정**
- 한글이 든 파이썬을 bash 로 바로 넘기면(heredoc·`python -c`) cp949·이스케이프 문제가 난다(`"\t…"` 가 탭이 됨) → 파일로 써서 `python -X utf8 파일.py`, 경로 문자열은 raw string.
- 저장소 파일은 CRLF 가 섞여 있다(autocrlf). 고칠 때 `open(…, newline="")` 로 읽고 써서 줄 끝을 그대로 둔다. 표의 상태 칸을 정규식으로 바꿀 때 `\s*$` 가 `\r` 을 먹지 않게.
- PowerShell 은 변수 이름 대소문자를 구분하지 않는다(`$tool` = 매개변수 `$Tool`). PowerShell 5.1 스크립트(`.ps1`)는 BOM 을 유지해야 한글이 안 깨진다 — 고친 뒤 `[Parser]::ParseFile` 로 문법 확인.

**작업자 관리에서 배운 것**
- 같은 일 겹침은 거의 '다른 폴더에서 일함'·'잡았다는 표시를 바로 안 올림'에서 생긴다 → `claim_task.py`(작은 일), `sync_work.py`(로컬 IDE), 큰 프로젝트 표(영역 파일).
- 큰 프로젝트끼리는 `web/index.html` 같은 큰 공용 파일에서 제일 많이 부딪힌다 → 먼저 끝난 쪽을 그날 합치고, 다른 쪽에 "합쳤다 → `sync_work.py save`".
- 작업자에게 주는 규칙은 예외 없이 쓴다. "보통 ○○ 모양"처럼 쓰면 작업자가 그 모양이 아닐 때 의심하고 멈춘다(이름 규칙 사례).
- 교사에게는 짧은 한국어로: 한 일 → 확인한 것 → 교사가 할 일·결정할 것. 작업자에게 붙여 넣을 말은 코드 블록으로.

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
