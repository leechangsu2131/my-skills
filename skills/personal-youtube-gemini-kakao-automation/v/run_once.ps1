# Run automation once (for Windows Task Scheduler or manual test)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$LogFile = Join-Path $ScriptDir "run.log"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "`n===== $Timestamp RUN_ONCE start ====="

$env:RUN_ONCE = "1"
$env:PYTHONIOENCODING = "utf-8"
chcp 65001 | Out-Null

$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    Add-Content -Path $LogFile -Value "ERROR: python not found in PATH"
    exit 1
}

& $Python -u (Join-Path $ScriptDir "main.py") 2>&1 | Tee-Object -FilePath $LogFile -Append
$ExitCode = $LASTEXITCODE
Add-Content -Path $LogFile -Value "===== exit code: $ExitCode ====="
exit $ExitCode
