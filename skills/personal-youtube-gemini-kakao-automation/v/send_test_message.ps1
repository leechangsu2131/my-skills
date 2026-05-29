$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$env:PYTHONIOENCODING = "utf-8"
chcp 65001 | Out-Null

$Python = (Get-Command python).Source
& $Python (Join-Path $ScriptDir "send_test_message.py")
exit $LASTEXITCODE
