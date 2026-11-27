param(
    [Parameter(Mandatory = $true)]
    [string]$Alias
)

$ErrorActionPreference = 'Stop'

if ($Alias -notmatch '^[a-zA-Z0-9\uAC00-\uD7A3_-]{1,40}$') {
    throw '별칭은 영문자, 숫자, 한글, 밑줄, 하이픈만 사용해 1~40자로 입력하세요.'
}

if ($Alias -match '^(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])$') {
    throw 'Windows에서 사용할 수 없는 별칭입니다. 다른 별칭을 사용하세요.'
}

if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
    throw 'LOCALAPPDATA 환경 변수를 찾을 수 없습니다.'
}

$chrome = (Get-Command 'chrome.exe' -ErrorAction SilentlyContinue).Source
if (-not $chrome) {
    $candidatePaths = @()
    if ($env:ProgramFiles) {
        $candidatePaths += Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'
    }
    if (${env:ProgramFiles(x86)}) {
        $candidatePaths += Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'
    }
    $candidatePaths += Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe'
    $candidates = $candidatePaths | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf }
    $chrome = $candidates | Select-Object -First 1
}

if (-not $chrome) {
    throw 'Google Chrome 실행 파일을 찾을 수 없습니다.'
}

$profileRoot = Join-Path $env:LOCALAPPDATA 'my-skills-data\admin-google-profile-picture\profiles'
$profileDir = Join-Path $profileRoot $Alias
if (Test-Path -LiteralPath $profileDir -PathType Leaf) {
    throw '프로필 경로에 같은 이름의 파일이 있습니다. 별칭을 확인하세요.'
}

New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
$arguments = @(
    "--user-data-dir=`"$profileDir`"",
    '--no-first-run',
    '--no-default-browser-check'
)

Start-Process -FilePath $chrome -ArgumentList $arguments
Write-Output "Chrome 프로필을 열었습니다: $Alias"
