---
name: personal-mp3-baby
description: Create Korean SRT subtitles for baby bedtime-story MP3s so a caregiver can identify stories and seek past unwanted sections. Use when the user provides audio files or asks to transcribe, subtitle, inspect, or skip stories in a bedtime-story recording.
---

# 아기 잠자리동화 MP3 자막

MP3를 한국어로 전사하고 타임코드가 있는 SRT를 오디오 파일과 같은 폴더에 만든다. 보호자가 이야기의 시작과 끝을 자막에서 확인해 플레이어에서 해당 구간을 넘길 수 있게 한다.

## 진행

1. 사용자가 지정한 MP3 파일 경로를 확인한다. 파일을 이동하거나 덮어쓰지 않는다.
2. `scripts/transcribe_mp3.py`로 SRT를 만든다. 기본 모델은 다국어 한국어를 지원하는 `small`이며, 더 나은 정확도가 필요하면 `medium`을 지정한다. 첫 실행 때 모델 파일을 내려받으므로 네트워크와 디스크 공간이 필요하다.
3. 생성된 SRT를 확인하여 시간 순서, 자막 번호, 타임코드, 빈 자막 여부를 검토한다. 인식이 부정확한 고유명사나 동화 제목은 오디오를 듣고 가능한 범위에서 교정한다. 추측으로 원문을 만들어 넣지 않는다.
4. 대화형 사용에서는 자막에 나온 이야기 제목/요약과 시작·끝 시각을 사용자에게 보여주고, 건너뛰고 싶은 이야기를 지정해 달라고 한다. 사용자가 지정한 구간만 별도의 목록으로 정리한다. SRT 자체는 전체 음성 전사로 유지한다.
5. SRT가 준비되면 파일 경로와 미검수/검수 상태를 알린다. 자막은 이야기 경계의 근사치를 제공하며 정확한 장면 전환 지점은 청취로 확인한다.

## 알송에서 사용

알송 PC는 같은 폴더의 SRT/LRC를 자동으로 해당 음원에 연결하는 자막 플레이어가 아니다. 알송 가사 서버에서 음원 고유 ID와 연결된 가사를 불러오므로, 외부 자막을 변환하는 것만으로 서버 등록이 되지 않는다. 공식 안내는 가사창의 `Ctrl+E` 싱크 가사 등록창에서 검색 후 연결하거나 직접 등록하는 절차를 설명한다.

알송 PC는 같은 폴더의 SRT/LRC를 싱크 가사 편집기 시작 시간 열로 가져오는 동작을 확인할 수 없다. `[분:초.백분초]문장` 문자열을 편집기에 붙여 넣으면 시간표시도 가사 텍스트로 들어갈 수 있으므로 이 형식을 가져오기 형식이라고 안내하지 않는다. 알송의 싱크 편집기에서 직접 가사를 등록할 수 있지만, 대량 타임코드 가져오기 방법이 확인되지 않으면 이를 지원한다고 단정하지 않는다. SRT 타임코드로 바로 재생/탐색하려면 SRT를 지원하는 미디어 플레이어를 안내한다.

## 실행

필요 패키지 설치:

```powershell
python -m pip install faster-whisper
```

한 파일 처리:

```powershell
python "<skill-folder>\scripts\transcribe_mp3.py" "C:\경로\이야기.mp3"
```

고정밀 모델 선택:

```powershell
python "<skill-folder>\scripts\transcribe_mp3.py" "C:\경로\이야기.mp3" --model medium
```

출력 파일은 원본과 같은 디렉터리에 같은 기본 이름의 `.srt`로 저장한다. 기존 SRT가 있으면 기본적으로 덮어쓰지 않고 종료하며, 교체 의사를 명시한 경우에만 `--overwrite`를 사용한다.

## 주의

- 전사는 자동 음성 인식 결과이므로 이야기 제목, 인물 이름, 고유명사와 구간 경계를 확인한다.
- `faster-whisper`의 `small` 모델은 속도와 한국어 인식 품질 사이의 기본 선택이다. GPU가 없으면 CPU와 int8을 사용한다.
- 이 스킬은 오디오를 자르거나 삭제하지 않는다. 사용자가 특정 이야기를 골라 달라고 하기 전에는 건너뛸 구간을 임의로 결정하지 않는다.
- 음악/효과음, 겹치는 목소리, 긴 무음 때문에 타임코드와 문장이 부정확할 수 있다.
