# YouTube 자막을 먼저 가져오기

YouTube URL로 강의 요약을 요청받으면 영상 전체를 내려받기 전에 YouTube에서 제공하는 자막을 조회하고, 가능한 경우 자막 파일만 저장한다. `yt-dlp`의 공식 자막 옵션은 [README의 Subtitle Options](https://github.com/yt-dlp/yt-dlp#subtitle-options)를 참고한다.

## PowerShell 절차

1. 사용자 제공 URL과 결과 폴더를 정한다. 이 사용자에게 별도 위치가 없으면 `C:\Users\lee21\Documents\영상요약\<영상 제목>`을 사용하고, 자막은 `captions` 하위 폴더에 둔다.
2. `yt-dlp --list-subs "<YouTube URL>"`로 사용 가능한 자막 언어와 수동/자동 자막 구분을 확인한다. 한국어 태그는 `ko`, `ko-KR`, `ko-orig` 등 실제 목록에 나온 값을 기준으로 판단한다.
3. 자막 파일만 저장한다. `--skip-download`를 포함해 영상 스트림을 받지 않게 하고, `--write-subs`와 `--write-auto-subs`를 함께 사용해 수동 자막과 자동 생성 자막을 모두 조회한다.

```powershell
$url = "https://www.youtube.com/watch?v=VIDEO_ID"
$captionDir = "C:\Users\lee21\Documents\영상요약\영상 제목\captions"
New-Item -ItemType Directory -Force -Path $captionDir | Out-Null
yt-dlp --list-subs $url
yt-dlp --skip-download --write-subs --write-auto-subs `
  --sub-langs "ko.*" --sub-format "vtt/best" `
  -P $captionDir -o "%(id)s.%(ext)s" $url
```

4. `captions`에 생성된 파일의 언어·자막 종류·내용을 확인한다. 한국어 수동 자막이 있으면 우선 사용하고, 없으면 한국어 자동 자막을 사용한다. 언어 태그의 파일명만 보고 수동/자동 여부를 단정하지 말고 `--list-subs` 결과와 파일 내용을 대조한다.
5. VTT 또는 SRT 파일을 `lecturecapture run`의 `--subtitle`에 전달한다. 자막을 지정하면 Whisper는 기본적으로 생략된다. 결과 `transcript.txt`, `transcript.srt`, 노트에서 실제로 어떤 자막을 사용했는지 기록하고 자동 자막의 오인식 가능성을 알린다.

## 자막을 찾지 못할 때

- `yt-dlp`가 없으면 설치 여부를 확인한다. 설치·업데이트가 필요하면 환경에 맞는 패키지 설치 방법을 안내하고, 현재 환경을 임의로 변경하지 않는다.
- 자막 목록이 비거나 다운로드가 실패하면 URL, 로그인, 접근 제한을 우회하지 않는다. 오류 내용을 확인해 일시적인 추출 실패와 자막 부재를 구분하고, 사용자가 붙여넣은 전사본·기존 자막 파일·보유한 로컬 영상의 Whisper 전사 중 이용 가능한 대안을 쓴다.
- 한국어 자막이 없으면 다른 언어 자막을 한국어인 것처럼 사용하지 않는다. 대체 언어 사용 또는 로컬 전사를 선택하고 결과에 출처를 표시한다.
- 자막만으로 요약할 수 있으면 영상 다운로드를 하지 않는다. 슬라이드 캡처가 필요한 경우에만 로컬 영상 파일을 찾거나, 사용자가 다운로드 권한을 확인한 때에 한해 기존 `download-authorized` 절차를 따른다. 자막을 추출할 수 있다는 사실은 영상 다운로드 권한을 뜻하지 않는다.
- 자막 URL이나 자막 텍스트가 민감할 수 있는 외부 요약 서비스로 전송되지 않게 로컬에서 처리한다.
