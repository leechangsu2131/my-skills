# Register Windows Task Scheduler job (weekdays at RUN_TIME from .env)
param(
    [string]$TaskName = "ChesleyMorningBrief",
    [string]$RunTime = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunScript = Join-Path $ScriptDir "run_once.ps1"

if (-not (Test-Path $RunScript)) {
    throw "run_once.ps1 not found: $RunScript"
}

# Read RUN_TIME from .env if not passed
if (-not $RunTime) {
    $EnvFile = Join-Path $ScriptDir ".env"
    if (Test-Path $EnvFile) {
        $line = Get-Content $EnvFile | Where-Object { $_ -match '^\s*RUN_TIME\s*=' } | Select-Object -First 1
        if ($line -match 'RUN_TIME\s*=\s*(.+)') {
            $RunTime = $Matches[1].Trim()
        }
    }
}
if (-not $RunTime) {
    $RunTime = "16:00"
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RunScript`"" `
    -WorkingDirectory $ScriptDir

$Trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
    -At $RunTime

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Chesley morning brief: YouTube transcript -> Gemini Gem -> Discord" `
    -Force | Out-Null

Write-Host "Registered task: $TaskName"
Write-Host "Schedule: Mon-Fri at $RunTime"
Write-Host "Script: $RunScript"
Write-Host ""
Write-Host "Test now:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "View log:  Get-Content '$ScriptDir\run.log' -Tail 50"
