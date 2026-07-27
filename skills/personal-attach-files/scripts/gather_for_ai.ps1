# AI 전송용 파일 수집 스크립트 (gather_for_ai.ps1)

$ProjectRoot = "C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-free-parents-app"
$TargetDir = "$ProjectRoot\snapshot_to_ai"

# 1. 기존 임시 폴더 청소 및 신규 생성
if (Test-Path $TargetDir) {
    Remove-Item -Path $TargetDir -Recurse -Force
}
New-Item -Path $TargetDir -ItemType Directory -Force | Out-Null

# 2. 수집 대상 파일 리스트 정의 (원본 경로 -> 복사될 파일명)
$FilesToGather = @{
    "$ProjectRoot\SKILL.md" = "01_SKILL.md"
    "$ProjectRoot\supabase\migrations\00001_initial_schema.sql" = "02_initial_schema.sql"
    "$ProjectRoot\lib\features\group\presentation\group_matching_page.dart" = "03_group_matching_page.dart"
    "$ProjectRoot\lib\features\auth\presentation\login_page.dart" = "04_login_page.dart"
    "$ProjectRoot\lib\features\home\presentation\onboarding_page.dart" = "05_onboarding_page.dart"
}

# 3. 파일 복사 수행
Write-Host "📂 AI 검토용 최신 파일 수집을 시작합니다..." -ForegroundColor Green
foreach ($Source in $FilesToGather.Keys) {
    $DestName = $FilesToGather[$Source]
    $DestPath = "$TargetDir\$DestName"

    if (Test-Path $Source) {
        Copy-Item -Path $Source -Destination $DestPath -Force
        Write-Host "✅ 복사 완료: $DestName" -ForegroundColor Cyan
    } else {
        Write-Host "❌ 파일을 찾을 수 없음: $Source" -ForegroundColor Red
    }
}

# 4. 탐색기 자동 팝업
Write-Host "🚀 탐색기를 열어 수집된 폴더를 보여줍니다. [Ctrl+A] 후 브라우저에 던지세요!" -ForegroundColor Yellow
Start-Process explorer.exe -ArgumentList $TargetDir
