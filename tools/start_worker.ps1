# 작업자 하나를 자기 작업 폴더에서 시작한다 (까만 창 = PowerShell).
#
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool bizcoder -Name bizcoder-1
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool gemini   -Name gemini-1
#   powershell -ExecutionPolicy Bypass -File tools\start_worker.ps1 -Tool claude   -Name claude-local-1
#
# 하는 일
# 1. 작업자마다 따로 쓰는 폴더(my-skills 옆의 my-skills-<이름>)를 만든다 — git worktree, 처음 한 번만.
#    같은 폴더를 여러 작업자가 쓰면 서로 브랜치를 바꿔 버린다(2026-11-25 실제로 생김).
# 2. 그 폴더에서 도구를 켜고 첫 요청(공용 첫 대화 문구 + 작업자 이름)을 넣는다.
#    도구는 그 폴더의 CLAUDE.md·AGENTS.md·GEMINI.md 를 스스로 읽는다.
# -NoStart 를 주면 폴더만 만들고 도구는 켜지 않는다.
param(
    [Parameter(Mandatory = $true)][ValidateSet("bizcoder", "gemini", "claude")][string]$Tool,
    [Parameter(Mandatory = $true)][string]$Name,
    [switch]$NoStart
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot                  # 이 스크립트가 든 저장소(my-skills 또는 그 작업 폴더)
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
    Write-Host "작업 폴더가 이미 있어요(이어서 해요): $dir"
}
if ($NoStart) { return }

$prompt = @"
너의 작업자 이름은 $Name 이야. 공용 저장소 https://github.com/leechangsu2131/my-skills 를 돕는 작업자야.
지금 폴더는 너만 쓰는 작업 폴더야(다른 작업자와 공유하지 않음).
1. docs/WORKER_GUIDE.md 와 docs/TASKS.md 를 읽어. 네 일지(docs/worklog/$Name.md)가 있으면 마지막 줄부터 이어서 해.
2. 너는 R 등급(브랜치를 푸시할 수 있음)이야. git fetch 후 아직 아무도 잡지 않은 '열림' 일을 하나 골라.
3. 시작하기 전에 세 줄로만 알려 줘: 고른 일 번호와 이유 / 고칠 파일 / 확인 방법. 그리고 바로 시작해.
4. 브랜치 task/<번호>-<설명> 과 일지 '시작' 줄을 먼저 푸시해 일을 잡고, 끝나면 PR. main 에 직접 올리지 마.
5. 하나를 끝내면 기다리지 말고 다음 일로 이어 가. 고를 일이 없으면 TASKS 맨 아래 '상시 일(S)'을 해.
막는 것은 학생·학부모 개인정보, 전화번호·집 주소, 키·비밀번호, 지도서 같은 저작물, 실제 제출·발송·결제뿐이야. 모르는 건 지어내지 말고 '확인 필요'라고 해.
"@

Set-Location -LiteralPath $dir
switch ($Tool) {
    "bizcoder" { bizcoder $dir --prompt $prompt }
    "gemini"   { gemini -i $prompt }
    "claude"   { claude $prompt }
}
