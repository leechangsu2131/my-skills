Stop-Process -Name "chrome" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
$tempDir = [System.IO.Path]::GetTempPath()
$profileDir = Join-Path $tempDir "neis_chrome_profile_9222"
$lockFile = Join-Path $profileDir "SingletonLock"
if (Test-Path $lockFile) {
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
}
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222", "--user-data-dir=`"$profileDir`"", "--start-maximized", "https://gbe.neis.go.kr"
Write-Host "[OK] Debugging Chrome launched on port 9222"
