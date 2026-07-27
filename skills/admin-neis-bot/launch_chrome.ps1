Stop-Process -Name "chrome" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
$tempDir = [System.IO.Path]::GetTempPath()
$profileDir = Join-Path $tempDir "neis_chrome_profile_9222"
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--remote-debugging-port=9222", "--user-data-dir=`"$profileDir`"", "https://evpn.gbe.kr"
