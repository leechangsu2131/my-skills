param()

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
Add-Type -AssemblyName System.Drawing

$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime]

function Await-WinRt($Operation, [Type]$ResultType) {
  $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
      $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and
      $_.GetParameters().Count -eq 1 -and
      $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } | Select-Object -First 1
  if (-not $method) { throw 'Windows Runtime AsTask(IAsyncOperation<T>)을 찾지 못했습니다.' }
  $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
  $task.GetAwaiter().GetResult()
}

function Read-DateHeaderText([string]$ImagePath, $Engine) {
  $source = [System.Drawing.Bitmap]::new($ImagePath)
  try {
    # The message date is shown in the upper-right preview header. Crop that
    # region and upscale it so OCR does not mix it with the inbox rows/body.
    $x = [Math]::Max(0, [int]($source.Width * 0.81))
    $y = [Math]::Max(0, [int]($source.Height * 0.065))
    $width = [Math]::Min($source.Width - $x, [int]($source.Width * 0.185))
    $height = [Math]::Min($source.Height - $y, [int]($source.Height * 0.10))
    if ($width -lt 40 -or $height -lt 20) { throw '스크린샷 크기가 날짜 머리글을 읽기에 너무 작습니다.' }

    $crop = $source.Clone(
      [System.Drawing.Rectangle]::new($x, $y, $width, $height),
      $source.PixelFormat
    )
    try {
      $scaled = [System.Drawing.Bitmap]::new($crop, $width * 3, $height * 3)
      try {
        $cropPath = Join-Path $env:TEMP ("gbtalk-date-ocr-" + [Guid]::NewGuid().ToString('N') + '.png')
        try {
          $scaled.Save($cropPath, [System.Drawing.Imaging.ImageFormat]::Png)
          $file = Await-WinRt ([Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]::GetFileFromPathAsync($cropPath)) ([Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime])
          $bitmap = Await-WinRt ($file.OpenAsync([Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime]::Read)) ([Windows.Storage.Streams.IRandomAccessStream, Windows.Storage, ContentType=WindowsRuntime])
          try {
            $decoder = Await-WinRt ([Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime]::CreateAsync($bitmap)) ([Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime])
            $softwareBitmap = Await-WinRt ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType=WindowsRuntime])
            try {
              return (Await-WinRt ($Engine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime])).Text
            } finally {
              $softwareBitmap.Dispose()
            }
          } finally {
            $bitmap.Dispose()
          }
        } finally {
          Remove-Item -LiteralPath $cropPath -Force -ErrorAction SilentlyContinue
        }
      } finally {
        $scaled.Dispose()
      }
    } finally {
      $crop.Dispose()
    }
  } finally {
    $source.Dispose()
  }
}

$engine = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]::TryCreateFromUserProfileLanguages()
if (-not $engine) { throw 'Windows OCR 언어 엔진을 만들 수 없습니다.' }

while ($line = [Console]::In.ReadLine()) {
  $request = $null
  try {
    $request = $line | ConvertFrom-Json
    if ($request.op -eq 'stop') { break }
    $text = Read-DateHeaderText ([string]$request.path) $engine
    $response = @{ id = $request.id; text = $text; ok = $true }
  } catch {
    $response = @{ id = $request.id; error = $_.Exception.Message; ok = $false }
  }
  [Console]::Out.WriteLine(($response | ConvertTo-Json -Compress))
  [Console]::Out.Flush()
}
