# 작업자 하나를 자기 작업 폴더에서 시작한다 (까만 창 = PowerShell).
#
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool bizcoder -Name bizcoder-1
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool gemini   -Name gemini-1
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool claude   -Name claude-local-1
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool codex    -Name codex-1
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool antigravity -Name ag-1   # 폴더를 열고 첫 요청을 클립보드에
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool bizcoder -Name bizcoder-1 -Task T77   # 오케스트레이터가 정한 일
#
# 로컬 작업자(Antigravity·Codex CLI·bizcoder·로컬 Claude Code·Gemini CLI)는 꼭 이 스크립트가 만든 폴더에서만 일한다.
# 따로 받은 저장소·다른 폴더에서 일하면 남이 잡은 일을 못 봐서 같은 일을 또 한다(2026-11-25~26 T10·T11·T23·T25).
# -Task 를 주면 도구를 켜기 전에 tools\claim_task.py --check 로 그 일이 비었는지 보고, 누가 하고 있으면 켜지 않는다.
#
# 하는 일
# 1. 작업자마다 따로 쓰는 폴더(my-skills 옆의 my-skills-<이름>)를 만든다 — git worktree, 처음 한 번만.
#    같은 폴더를 여러 작업자가 쓰면 서로 브랜치를 바꿔 버린다(2026-11-25 실제로 생김).
# 2. 그 폴더에서 도구를 켜고 첫 요청(공용 첫 대화 문구 + 작업자 이름)을 넣는다.
#    도구는 그 폴더의 CLAUDE.md·AGENTS.md·GEMINI.md 를 스스로 읽는다.
# -NoStart 를 주면 폴더만 만들고 도구는 켜지 않는다.
param(
    [Parameter(Mandatory = $true)][ValidateSet("bizcoder", "gemini", "claude", "codex", "antigravity")][string]$Tool,
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$Task,
    [switch]$NoStart
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot                  # 이 스크립트가 든 저장소(my-skills 또는 그 작업 폴더)
if (-not (Test-Path -LiteralPath (Join-Path $repo ".git"))) {
    $repo = git rev-parse --show-toplevel 2>$null          # 처음 실행할 때 TEMP 로 꺼낸 스크립트
    if ($LASTEXITCODE -ne 0) { throw "my-skills 저장소 폴더에서 실행해 주세요." }
}
$main = (git -C $repo rev-parse --path-format=absolute --git-common-dir) | Split-Path -Parent   # 원래 my-skills
$dir = Join-Path (Split-Path -Parent $main) ("my-skills-" + ($Name -replace '[\\/:*?"<>|\s]', '_'))

if (-not (Test-Path -LiteralPath $dir)) {
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
2. 너는 교사 PC 에서 도는 작업자라 R·P 일을 다 할 수 있어. docs/TASKS.md 맨 위 ★ 수업 비서 묶음 안에서, 아직 아무도 잡지 않은 '열림' 일을 하나 골라(순서는 TASKS 맨 위대로).
3. 시작 직전에 python tools/claim_task.py <번호> <짧은-영어-설명> --name $Name 로 일을 잡아(브랜치·일지 '시작' 줄을 올려 줌).
   ❌ 가 나오면 그 일은 하지 말고 다른 일을 골라 다시 잡아. 스킬마다 따로 잡는 일(T31·T33·S1 등)은 --skill <스킬>.
"@
}

$prompt = @"
너의 작업자 이름은 $Name 이야. 공용 저장소 https://github.com/leechangsu2131/my-skills 를 돕는 작업자야.
지금 폴더는 너만 쓰는 작업 폴더야(다른 작업자와 공유하지 않음). 다른 폴더·따로 받은 저장소에서 일하지 마.
1. docs/WORKER_GUIDE.md 와 docs/TASKS.md 를 읽어. 네 일지(docs/worklog/$Name.md)가 있으면 마지막 줄부터 이어서 해.
$pick
4. 잡은 뒤 세 줄로만 알려 줘: 일 번호 / 고칠 파일 / 확인 방법. 그리고 바로 시작해. 끝나면 일지 'PR 올림' 줄 → PR. main 에 직접 올리지 마.
   tools/claim_task.py 가 없으면(폴더가 예전 상태) 하던 일을 커밋·푸시한 뒤 git switch --detach origin/main 하고 다시 해.
5. 하나를 끝내면 기다리지 말고 다음 일로 이어 가(이때도 claim_task.py 로 잡기). 고를 일이 없으면 TASKS 맨 아래 '상시 일(S)'을 해(수업 비서 묶음 안에서만).
   사용량이 거의 끝나면 일지에 '그만둠 — 어디까지, 다음에 할 것'을 푸시하고 멈춰.
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
