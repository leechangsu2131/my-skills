$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$port = 3002
$env:PORT = [string]$port

try {
  $host.UI.RawUI.WindowTitle = 'StorageMap'
} catch {}

Write-Host '========================================='
Write-Host '      📦 StorageMap 로컬 서버 시작'
Write-Host '========================================='
Write-Host ''

$listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
  $health = $null
  try {
    $health = Invoke-RestMethod -Uri "http://localhost:$port/api/health" -TimeoutSec 2
  } catch {}

  $shouldRestart = $false
  if ($health -and $health.provider -eq 'supabase' -and $health.mode -eq 'sample' -and ($health.lastError -match 'fetch failed|TLS certificate')) {
    try {
      $processName = (Get-Process -Id $listener.OwningProcess -ErrorAction Stop).ProcessName
      $shouldRestart = $processName -eq 'node'
    } catch {}
  }

  if ($shouldRestart) {
    Write-Host "[안내] 기존 StorageMap 서버가 샘플 모드로 떠 있어서 다시 시작합니다."
    try {
      Stop-Process -Id $listener.OwningProcess -Force -ErrorAction Stop
      Start-Sleep -Seconds 1
    } catch {
      Write-Host "[오류] 기존 서버를 종료하지 못했습니다: $($_.Exception.Message)"
      Write-Host ''
      Read-Host '엔터를 누르면 창이 닫힙니다'
      exit 1
    }
  } else {
    Write-Host "[안내] http://localhost:$port 에 이미 서버가 실행 중입니다."
    Start-Process "http://localhost:$port" | Out-Null
    Write-Host ''
    Read-Host '엔터를 누르면 창이 닫힙니다'
    exit 0
  }
}

Write-Host '[1/2] 브라우저 자동 실행 예약 중...'
Start-Process powershell -WindowStyle Hidden -ArgumentList @(
  '-NoProfile',
  '-Command',
  "Start-Sleep -Seconds 3; Start-Process 'http://localhost:$port'"
) | Out-Null

Write-Host '[2/2] Node.js 서버 작동 중...'
Write-Host ''
Write-Host '이 창을 닫으면 StorageMap 연결이 끊어집니다! (최소화 해두세요)'
Write-Host '========================================='
Write-Host ''

& node --use-system-ca server.js
$exitCode = $LASTEXITCODE

Write-Host ''
if ($exitCode -eq 0) {
  Write-Host 'StorageMap 서버가 정상 종료되었습니다.'
} else {
  Write-Host "StorageMap 서버가 종료되었습니다. 종료 코드: $exitCode"
}

Read-Host '엔터를 누르면 창이 닫힙니다'
exit $exitCode
