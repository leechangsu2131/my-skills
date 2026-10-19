Add-Type @"
  using System;
  using System.Runtime.InteropServices;
  using System.Text;
  public class WindowFinder {
    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
  }
"@

[WindowFinder]::EnumWindows({
  param($hWnd, $lParam)
  if ([WindowFinder]::IsWindowVisible($hWnd)) {
    $sb = New-Object System.Text.StringBuilder 256
    $len = [WindowFinder]::GetWindowText($hWnd, $sb, 256)
    if ($len -gt 0) {
      $pid = 0
      [WindowFinder]::GetWindowThreadProcessId($hWnd, [ref]$pid)
      $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
      $pName = if ($proc) { $proc.ProcessName } else { "Unknown" }
      Write-Output "$($pName) (PID: $pid): $($sb.ToString())"
    }
  }
  return $true
}, [IntPtr]::Zero)
