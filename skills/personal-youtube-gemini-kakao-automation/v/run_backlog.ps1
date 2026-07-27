# Run missed Chesley Morning Brief summaries (oldest first)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$LogFile = Join-Path $ScriptDir "run.log"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "`n===== $Timestamp BACKLOG start ====="

$env:RUN_BACKLOG = "1"
$env:PYTHONIOENCODING = "utf-8"
chcp 65001 | Out-Null

if (-not $env:BACKLOG_TO) {
    $env:BACKLOG_TO = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
}

$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    Add-Content -Path $LogFile -Value "ERROR: python not found in PATH"
    exit 1
}

$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $Python -u (Join-Path $ScriptDir "main.py") 2>&1 | ForEach-Object {
    $_ | Out-String | Tee-Object -FilePath $LogFile -Append
}
$ErrorActionPreference = $prevEap
$ExitCode = $LASTEXITCODE
Add-Content -Path $LogFile -Value "===== backlog exit code: $ExitCode ====="
exit $ExitCode
