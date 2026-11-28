# 작업자 하나를 자기 작업 폴더에서 시작한다 (까만 창 = PowerShell).
#
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool bizcoder -Name bizcoder-1
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool gemini   -Name gemini-1
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool claude   -Name claude-local-1
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool codex    -Name codex-1
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool antigravity -Name ag-1   # 폴더를 열고 첫 요청을 클립보드에
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool bizcoder -Name bizcoder-1 -Task T77   # 오케스트레이터가 정한 일
#
# 로컬 작업자는 이 스크립트가 정한 폴더에서만 일한다.
# 따로 받은 저장소·다른 폴더에서 일하면 남이 잡은 일을 못 봐서 같은 일을 또 한다(2026-11-25~26 T10·T11·T23·T25).
# -Task 를 주면 도구를 켜기 전에 tools\claim_task.py --check 로 그 일이 비었는지 보고, 누가 하고 있으면 켜지 않는다.
#
# 어디서 일하나
# - bizcoder: **원래 my-skills 폴더**에서 Codex·Antigravity 와 교대로(한 번에 하나) — 교사 결정 2026-11-27(작업 폴더를 더 만들지 않음).
#   폴더에 커밋 안 한 변경이 있거나 남의 브랜치가 걸려 있으면(앞 작업자가 sync_work end 를 안 함) 켜지 않는다.
#   bizcoder 를 여럿 동시에 돌려야 할 때만 -Separate 로 예전처럼 따로 폴더(my-skills-<이름>)를 만든다.
# - 그 밖의 CLI(gemini·claude·codex)·-Separate: 작업자마다 따로 쓰는 폴더(my-skills 옆의 my-skills-<이름>, git worktree, 처음 한 번만).
#   같은 폴더를 여러 작업자가 동시에 쓰면 서로 브랜치를 바꿔 버린다(2026-11-25 실제로 생김).
# 그 폴더에서 도구를 켜고 첫 요청(공용 첫 대화 문구 + 작업자 이름)을 넣는다. 도구는 CLAUDE.md·AGENTS.md·GEMINI.md 를 스스로 읽는다.
# -NoStart 를 주면 폴더 준비·확인만 하고 도구는 켜지 않는다.
param(
    [Parameter(Mandatory = $true)][ValidateSet("bizcoder", "gemini", "claude", "codex", "antigravity")][string]$Tool,
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$Task,
    [switch]$NoStart,
    [switch]$Separate
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot                  # 이 스크립트가 든 저장소(my-skills 또는 그 작업 폴더)
if (-not (Test-Path -LiteralPath (Join-Path $repo ".git"))) {
    $repo = git rev-parse --show-toplevel 2>$null          # 처음 실행할 때 TEMP 로 꺼낸 스크립트
    if ($LASTEXITCODE -ne 0) { throw "my-skills 저장소 폴더에서 실행해 주세요." }
}
$main = (git -C $repo rev-parse --path-format=absolute --git-common-dir) | Split-Path -Parent   # 원래 my-skills
$inPlace = ($Tool -eq "bizcoder") -and -not $Separate
$dir = Join-Path (Split-Path -Parent $main) ("my-skills-" + ($Name -replace '[\\/:*?"<>|\s]', '_'))

if ($inPlace) {
    # 원래 my-skills 폴더를 로컬 IDE 와 교대로 쓴다 — 앞 작업자가 sync_work end 로 비워 뒀는지 확인
    $dir = $main
    git -C $dir fetch --quiet --prune origin
    $dirty = git -C $dir status --porcelain
    if ($dirty) {
        Write-Host "❌ 원래 my-skills 폴더에 커밋 안 한 변경이 있어요(앞 작업자·IDE 가 끝내지 않음). bizcoder 를 켜지 않았어요."
        git -C $dir status --short | Select-Object -First 10 | ForEach-Object { Write-Host "   $_" }
        Write-Host "   그 도구(Codex·Antigravity 등)에서 커밋 → python tools/sync_work.py end 를 한 뒤 다시 실행하세요."
        exit 1
    }
    $cur = git -C $dir symbolic-ref -q --short HEAD
    if ($cur -and $cur -notin @("main", "master")) {
        $mine = git -C $dir log --format=%h "origin/main..HEAD" -- "docs/worklog/$Name.md"
        if (-not $mine) {
            Write-Host "❌ 원래 my-skills 폴더가 남의 브랜치($cur)에 있어요(앞 작업자가 sync_work end 를 안 함). bizcoder 를 켜지 않았어요."
            Write-Host "   그 작업자에게 끝내 달라고 하거나(python tools/sync_work.py end), 다 올린 브랜치면 교사 PC 의 Claude Code 에게 정리를 부탁하세요."
            exit 1
        }
        Write-Host "$Name 가 하던 브랜치($cur)에서 이어서 해요."
    } elseif ($cur) {
        git -C $dir merge --quiet --ff-only origin/main      # main 이면 최신으로(새 도구·TASKS 가 보이게)
    } else {
        git -C $dir switch --quiet --detach origin/main
    }
    Write-Host "원래 my-skills 폴더에서 일해요: $dir"
    Write-Host "   ⚠ Codex·Antigravity 가 이 폴더에서 일하는 중이면 지금 창을 닫고(Ctrl+C) 그쪽을 먼저 끝내세요 — 한 번에 하나."
} elseif (-not (Test-Path -LiteralPath $dir)) {
    git -C $main fetch --quiet origin
    git -C $main -c core.longpaths=true worktree add --detach $dir origin/main
    git -C $dir config core.longpaths true
    git -C $dir config core.quotepath false
    Write-Host "작업 폴더를 만들었어요: $dir"
} else {
    git -C $dir fetch --quiet origin
    $cur = git -C $dir symbolic-ref -q --short HEAD
    $dirty = git -C $dir status --porcelain
    if (-not $cur -and -not $dirty) {
        git -C $dir switch --quiet --detach origin/main      # 하던 일이 없는 폴더는 최신 main 으로(새 도구·TASKS 가 보이게)
    }
    Write-Host "작업 폴더가 이미 있어요(이어서 해요): $dir"
}
if ($Task) {
    $Task = $Task.ToUpper()
    $claimTool = @((Join-Path $dir "tools\claim_task.py"), (Join-Path $PSScriptRoot "claim_task.py"), (Join-Path $main "tools\claim_task.py")) |
        Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $claimTool) { Write-Host "확인 도구(tools\claim_task.py)를 찾지 못했어요. my-skills 를 최신으로 받은 뒤 다시 실행하세요."; exit 2 }
    Push-Location -LiteralPath $dir
    try { python $claimTool $Task --check --name $Name } finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "$Task 는 지금 맡길 수 없어요(위 이유). 다른 일을 정해 주세요. 작업자를 켜지 않았어요."
        exit 1
    }
}
if ($NoStart) { return }

if ($Task) {
    $pick = @"
2. 네 일은 교사(오케스트레이터)가 정해 준 $Task 하나야. 다른 일을 고르지 마. docs/TASKS.md 의 $Task 줄(고칠 파일·끝난 기준)을 그대로 따라.
3. 시작 직전에 python tools/claim_task.py $Task <짧은-영어-설명> --name $Name 로 일을 잡아(브랜치·일지 '시작' 줄을 올려 줌).
   ❌(이미 누가 함·완료·결정 대기)가 나오면 아무것도 고치지 말고 그 결과를 알려 준 뒤 멈춰.
"@
} else {
    $pick = @"
2. 너는 교사 PC 에서 도는 작업자라 R·P 일을 다 할 수 있어. 일은 직접 고르지 말고 도구가 고르게 해:
3. python tools/claim_task.py --next --name $Name --grade P
   (네가 하던 일 → 다른 작업자가 멈춘 일 이어받기 → TASKS 의 '열림' 일 순서). '이어받았어요'면 찍힌 앞 작업자 일지(다음에 할 것)와
   TASKS 체크리스트에서 안 된 칸부터 이어서 해. 'S8 (<스킬>)'을 잡았으면 그 스킬 ISSUES.md 의 🔵·📌 가운데 실제 실행·교사 결정 없이 고칠 수 있는 것부터 고쳐(docs/WORKER_GUIDE.md 맨 위). '고를 일이 없어요'면 TASKS 맨 아래 '상시 일(S)'을 --skill 로 잡아.
"@
}

if ($inPlace) {
    $where = @"
지금 폴더는 교사 PC 의 원래 my-skills 폴더야. Codex·Antigravity 와 교대로 쓰는 폴더인데 지금은 너만 써. 다른 폴더·따로 받은 저장소에서 일하지 마.
이 폴더에 커밋 안 한 변경을 남기면 다음 작업자가 시작하지 못하니, 아래 4·5번의 sync_work 순서를 꼭 지켜.
"@
    $finish = @"
4. 잡은 뒤 세 줄로만 알려 줘: 일 번호 / 고칠 파일 / 확인 방법. 그리고 바로 시작해. main 에 직접 올리지 마.
   할 수 있는 데까지 해(나에게 다음 지시를 기다리지 마). 작은 단계(30분 안쪽)마다 고친 파일만 git add → commit →
   일지 '진행 — 한 것 / 다음: 할 것' 커밋 → python tools/sync_work.py save (끊겨도 다른 작업자가 그 줄부터 이어받음).
   일 하나가 끝나면: 고친 파일만 git add → commit → 일지 'PR 올림 — 무엇, 시험 결과' 커밋 → python tools/sync_work.py end(올리고 폴더를 비움).
5. 하나를 끝내면 기다리지 말고 다시 3번(--next) — end 로 폴더가 비어 있어야 잡혀.
   사용량이 거의 끝나거나 내가 멈추라고 하면: 커밋 → 일지 '그만둠 — 어디까지, 다음에 할 것' 커밋 → python tools/sync_work.py end. 커밋 안 한 변경을 남기고 끝내지 마.
"@
} else {
    $where = "지금 폴더는 너만 쓰는 작업 폴더야(다른 작업자와 공유하지 않음). 다른 폴더·따로 받은 저장소에서 일하지 마."
    $finish = @"
4. 잡은 뒤 세 줄로만 알려 줘: 일 번호 / 고칠 파일 / 확인 방법. 그리고 바로 시작해. 끝나면 일지 'PR 올림' 줄 → PR. main 에 직접 올리지 마.
   tools/claim_task.py 가 없으면(폴더가 예전 상태) 하던 일을 커밋·푸시한 뒤 git switch --detach origin/main 하고 다시 해.
   할 수 있는 데까지 해. 작은 단계(30분 안쪽)마다 커밋·푸시하고 일지에 '진행 — 한 것 / 다음: 할 것'.
5. 하나를 끝내면 기다리지 말고 다시 3번(--next).
   사용량이 거의 끝나면 일지에 '그만둠 — 어디까지, 다음에 할 것'을 푸시하고 멈춰.
"@
}

$prompt = @"
너의 작업자 이름은 $Name 이야. 공용 저장소 https://github.com/leechangsu2131/my-skills 를 돕는 작업자야.
$where
1. docs/WORKER_GUIDE.md 와 docs/TASKS.md 를 읽어. 네 일지(docs/worklog/$Name.md)가 있으면 마지막 줄부터 이어서 해.
$pick
$finish
막는 것은 학생·학부모 개인정보, 전화번호·집 주소, 키·비밀번호, 지도서 같은 저작물, 실제 제출·발송·결제뿐이야. 모르는 건 지어내지 말고 '확인 필요'라고 해.
"@

Set-Location -LiteralPath $dir
switch ($Tool) {
    "bizcoder" { bizcoder $dir --prompt $prompt }
    "gemini"   { gemini -i $prompt }
    "claude"   { claude $prompt }
    "codex"    { codex $prompt }
    "antigravity" {
        Set-Clipboard -Value $prompt
        Write-Host "첫 요청 글을 클립보드에 넣었어요. Antigravity 에서 이 폴더를 열고 에이전트 창에 붙여 넣으세요(Ctrl+V): $dir"
        $ag = Get-Command antigravity -ErrorAction SilentlyContinue
        if ($ag) { & $ag.Source $dir } else { Write-Host "antigravity 명령이 없어 자동으로 열지 못했어요 - Antigravity 에서 File > Open Folder 로 위 폴더를 여세요." }
    }
}
