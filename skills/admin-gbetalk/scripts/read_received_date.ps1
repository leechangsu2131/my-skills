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
    $x = [Math]::Max(0, [int]($source.Width * 0.80))
    $y = [Math]::Max(0, [int]($source.Height * 0.115))
    $width = [Math]::Min($source.Width - $x, [int]($source.Width * 0.195))
    $height = [Math]::Min($source.Height - $y, [int]($source.Height * 0.075))
    if ($width -lt 40 -or $height -lt 20) { throw '스크린샷 크기가 날짜 머리글을 읽기에 너무 작습니다.' }

    $crop = $source.Clone(
      [System.Drawing.Rectangle]::new($x, $y, $width, $height),
      $source.PixelFormat
    )
    try {
      # The header timestamp is small and light gray. Keep its antialiasing and
      # enlarge the isolated date region so OCR retains the shape of each digit.
      $scaled = [System.Drawing.Bitmap]::new($crop, $width * 5, $height * 5)
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

function Read-SenderHeaderText([string]$ImagePath, $Engine) {
  $source = [System.Drawing.Bitmap]::new($ImagePath)
  try {
    # The sender is the first label in the selected-message header, left of
    # the organization/address. Crop that label area, not the inbox body.
    $x = [Math]::Max(0, [int]($source.Width * 0.50))
    $y = [Math]::Max(0, [int]($source.Height * 0.11))
    $width = [Math]::Min($source.Width - $x, [int]($source.Width * 0.10))
    $height = [Math]::Min($source.Height - $y, [int]($source.Height * 0.08))
    if ($width -lt 40 -or $height -lt 20) { throw '스크린샷 크기가 발신자 머리글을 읽기에 너무 작습니다.' }

    $crop = $source.Clone(
      [System.Drawing.Rectangle]::new($x, $y, $width, $height),
      $source.PixelFormat
    )
    try {
      $scaled = [System.Drawing.Bitmap]::new($crop, $width * 8, $height * 8)
      try {
        $cropPath = Join-Path $env:TEMP ("gbtalk-sender-ocr-" + [Guid]::NewGuid().ToString('N') + '.png')
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

function Read-SenderRowText([string]$ImagePath, $Engine, [int]$Scale = 4) {
  $source = [System.Drawing.Bitmap]::new($ImagePath)
  try {
    # The selected inbox row shows the sender label at the left edge of the
    # message list. Keep the crop narrow enough to avoid the subject text, but
    # include the role suffix that helps distinguish similar Korean names.
    $x = [Math]::Max(0, [int]($source.Width * 0.165))
    $y = [Math]::Max(0, [int]($source.Height * 0.26))
    $width = [Math]::Min($source.Width - $x, [int]($source.Width * 0.095))
    $height = [Math]::Min($source.Height - $y, [int]($source.Height * 0.035))
    if ($width -lt 60 -or $height -lt 18) { throw '스크린샷 크기가 목록 발신자 표기를 읽기에 너무 작습니다.' }

    $crop = $source.Clone(
      [System.Drawing.Rectangle]::new($x, $y, $width, $height),
      $source.PixelFormat
    )
    try {
      $scaled = [System.Drawing.Bitmap]::new($crop, $width * $Scale, $height * $Scale)
      try {
        $cropPath = Join-Path $env:TEMP ("gbtalk-sender-row-ocr-" + [Guid]::NewGuid().ToString('N') + '.png')
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

$engine = $null
try {
  $ocrLanguage = [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]::new('en-US')
  $engine = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]::TryCreateFromLanguage($ocrLanguage)
} catch {
  $engine = $null
}
if (-not $engine) {
  $engine = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]::TryCreateFromUserProfileLanguages()
}
if (-not $engine) { throw 'Windows OCR 언어 엔진을 만들 수 없습니다.' }

$senderEngine = $null
try {
  $senderLanguage = [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]::new('ko-KR')
  $senderEngine = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]::TryCreateFromLanguage($senderLanguage)
} catch {
  $senderEngine = $null
}
if (-not $senderEngine) {
  $senderEngine = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]::TryCreateFromUserProfileLanguages()
}

while ($line = [Console]::In.ReadLine()) {
  $request = $null
  try {
    $request = $line | ConvertFrom-Json
    if ($request.op -eq 'stop') { break }
    $text = if ($request.op -eq 'sender') {
      if (-not $senderEngine) { throw '한국어 Windows OCR 언어 엔진을 사용할 수 없습니다.' }
      Read-SenderHeaderText ([string]$request.path) $senderEngine
    } elseif ($request.op -match '^sender-row(?:-(\d+))?$') {
      if (-not $senderEngine) { throw '한국어 Windows OCR 언어 엔진을 사용할 수 없습니다.' }
      $scale = if ($Matches[1]) { [int]$Matches[1] } else { 4 }
      if ($scale -lt 2 -or $scale -gt 8) { throw '목록 발신자 OCR 배율은 2~8이어야 합니다.' }
      Read-SenderRowText ([string]$request.path) $senderEngine $scale
    } else {
      Read-DateHeaderText ([string]$request.path) $engine
    }
    $response = @{ id = $request.id; text = $text; ok = $true }
  } catch {
    $response = @{ id = $request.id; error = $_.Exception.Message; ok = $false }
  }
  [Console]::Out.WriteLine(($response | ConvertTo-Json -Compress))
  [Console]::Out.Flush()
}
