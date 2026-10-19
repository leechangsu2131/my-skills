# LectureCapture v0.2.6

개인 지식관리용 강의 노트 도구입니다. **기본 입력은 본인에게 사용 권한이 있는 로컬 영상 파일**입니다. 영상에서 안정된 슬라이드 화면을 뽑고, 같은 시간대의 발언(자막 또는 음성 인식)을 연결해 Obsidian에서 정리할 Markdown 노트(`note.md`)를 만듭니다. HTML 보고서는 추출 결과를 빠르게 확인하기 위한 보조 산출물입니다.

## 원칙

- 원본 화면 우선: AI가 슬라이드를 새로 그리지 않고, 영상에 실제로 표시된 화면을 캡처해 보존합니다.
- 시간 정보 보존: 모든 슬라이드와 발언은 원본 영상의 시각(초)으로 추적됩니다.
- 자동 결과를 확정하지 않음: 중복 후보는 삭제하지 않고 표시만 하며, 사람이 노트와 보고서를 검토합니다.
- 외부 전송 없음: 영상, 이미지, 음성을 클라우드 서비스로 자동 전송하지 않습니다.
- CLI가 외부 AI 서비스를 자동 호출하지는 않습니다. 요약을 요청하면 스킬이 `project.json`, 슬라이드 이미지, 전사본을 근거로 `summary.md`를 작성하고 노트와 보고서에서 연결합니다.

## 설치

Python 3.10 이상을 권장합니다. Windows PowerShell 예시입니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[transcribe,test]"
```

- `faster-whisper` 모델 파일은 최초 전사 때 내려받습니다.
- CUDA가 정상 설치되어 있으면 GPU에서 `int8_float16`으로 실행해 VRAM 사용량을 줄입니다(RTX 3070 8GB 기준 `large-v3` 사용 가능). GPU 실행에 실패하면 CPU(`int8`)로 재시도합니다.
- 너무 느리면 `--whisper-model small` 또는 `--no-transcribe`를 사용하세요. `--no-transcribe`에 자막 파일도 없으면 발언 텍스트 없이 노트가 만들어집니다.

## 빠른 시작

영상 하나만 지정해도 됩니다. 결과 폴더는 영상 옆에 `<영상이름>_LectureCapture`로 만들어집니다.

```powershell
lecturecapture run "C:\Videos\lecture.mp4"
```

실행하면 첫 프레임이 열리고 마우스로 슬라이드 영역을 선택합니다. 확정은 Enter/Space, 취소는 `c`입니다. 좌표를 알면 `--crop x,y,w,h`로 선택 창을 생략할 수 있습니다.

강의 정보, 자막, PDF, 용어 힌트, 전사 파일 내보내기를 함께 지정하는 예:

```powershell
lecturecapture run "C:\Videos\lecture.mp4" `
  --course "학급 경영 연수" `
  --lecturer "강사명" `
  --completed-on "2026-10-12" `
  --subtitle "C:\Videos\lecture.srt" `
  --pdf "C:\Videos\lecture.pdf" `
  --hotwords "교육연극, 행복교실, 형성평가" `
  --export-transcript
```

좌표로 화면 영역을 지정하고 감지 값을 조정하는 예:

```powershell
lecturecapture run "C:\Videos\lecture.mp4" `
  --crop 120,80,1450,820 `
  --interval 0.75 `
  --change-threshold 1.5 `
  --diagnose
```

## 옵션

### 슬라이드 감지

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--crop x,y,w,h` | 선택 창 | 슬라이드 영역(원본 영상 해상도 기준 좌표) |
| `--interval` | 0.75 | 샘플링 간격(초) |
| `--change-threshold` | 1.5 | 기준 프레임에서 변한 픽셀 비율(%). 낮추면 작은 변화에도 새 슬라이드로 나뉘고, 높이면 작은 전환을 놓칩니다 |
| `--removal-threshold` | 0.25 | 기준 프레임의 내용이 사라진 픽셀 비율(%). 글머리표 추가는 무시하고 글 교체형 슬라이드 전환을 잡아냅니다 |
| `--pixel-delta` | 30 | 픽셀이 변했다고 보는 밝기 차이(0~255). 옅은 글씨 슬라이드는 낮춰 보세요 |
| `--min-stable` | 2.5 | 슬라이드 최소 지속 시간(초). 디졸브 같은 전환 중간 화면을 거르는 기준도 겸합니다 |
| `--diagnose` | 꺼짐 | 샘플별 변화율을 `diagnostics.csv`로 저장(임계값 조정용) |

### 스크립트

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--subtitle` | 없음 | SRT/VTT 자막 파일. 지정하면 자동 전사는 기본적으로 생략합니다 |
| `--transcribe` / `--no-transcribe` | 자동 | 자막이 있어도 직접 전사 / 전사 생략 |
| `--whisper-model` | `large-v3` | `tiny`, `base`, `small`, `medium`, `large-v3` |
| `--language` | `ko` | 전사 언어 코드. 자동 감지는 `auto` |
| `--hotwords` | 없음 | 용어 힌트. **매 구간에 적용**되어 긴 강의에 적합합니다 |
| `--initial-prompt` | 없음 | 첫 구간부터 이어지는 문맥 힌트. 긴 강의에서는 효과가 약해질 수 있습니다 |
| `--export-transcript` | 꺼짐 | `transcript.txt`(시각 포함)와 `transcript.srt` 저장 |

### 기타

| 옵션 | 설명 |
|---|---|
| `--course`, `--lecturer`, `--completed-on` | 노트에 들어갈 과정명, 강사, 이수 일자 |
| `--pdf` | 강의 PDF를 `attachments/`에 복사하고 노트에서 링크 |
| `--reference` | 참고 교안/자료를 `attachments/`에 복사하고 노트에서 링크. 여러 번 지정 가능 |
| `--source-url` | 원본 YouTube URL이 있을 때만 지정(노트에 시간 링크 생성) |
| `--out` | 결과 폴더 직접 지정 |

## 결과 폴더

```text
lecture_LectureCapture/
├── project.json       # 슬라이드·발언·메타데이터 원본(단일 기준 데이터)
├── note.md            # Obsidian용 Markdown 노트
├── summary.md         # 요청 시 작성하는 전체·슬라이드별 요약
├── report.html        # 결과 확인용 정적 보고서
├── transcript.txt     # --export-transcript 사용 시
├── transcript.srt     # --export-transcript 사용 시
├── diagnostics.csv    # --diagnose 사용 시
├── slides/            # 대표 슬라이드 이미지
├── attachments/       # 선택한 PDF
└── backups/           # JSON 갱신 전 백업
```

`note.md`는 Obsidian vault 안에 프로젝트 폴더를 두면 `![slide_0001](slides/slide_0001.jpg)` 형태로 이미지가 표시됩니다.

## 시간 필드

모든 시간은 원본 영상 시작점 기준 초 단위입니다.

- `first_seen`: 해당 화면 상태가 처음 관찰된 시각
- `stable_from`: 최소 안정 시간을 충족한 시각
- `best_frame_time`: 대표 이미지 프레임의 시각(해당 상태의 마지막 정지 프레임)
- `start_time` / `end_time`: 해당 상태로 추정한 구간

## 슬라이드 감지 방식

1. 일정 간격으로 프레임을 읽고(순차 디코딩, 메모리는 영상 길이와 무관) 지정한 영역만 잘라 320×180 흑백으로 정규화합니다.
2. 현재 상태의 첫 프레임을 기준으로 두 가지를 계산합니다. 변한 픽셀 비율과, 기준의 내용이 사라진 비율입니다. 둘 중 하나가 기준을 넘으면 새 상태가 시작됩니다.
3. `--min-stable`보다 짧은 상태(전환 효과 등)는 버립니다.
4. 대표 이미지는 상태의 마지막 정지 프레임입니다. 글머리표 애니메이션은 완성된 화면이 대표가 됩니다.
5. 대표 이미지끼리 변한 픽셀 비율이 0.3% 이하면 중복 후보로 표시합니다(삭제하지 않음).

## 스크립트 확보 순서

1. `--subtitle`로 지정한 SRT/VTT가 있으면 우선 사용합니다.
2. 없으면 faster-whisper로 전사합니다(VAD 필터 사용).
3. 전사 결과는 `project.json`에 저장되고, `--export-transcript`로 TXT/SRT로도 내보낼 수 있습니다.

## YouTube 입력(선택 기능)

기본 실행 경로와 분리된 별도 명령입니다. 다운로드 권한과 적용되는 서비스 약관을 확인한 경우에만 사용하세요. 접근 제한, DRM, 로그인 요구를 우회하지 않습니다.

```powershell
python -m pip install -e ".[youtube]"
lecturecapture download-authorized "https://www.youtube.com/watch?v=VIDEO_ID" --out "C:\Videos\source.mp4" --confirm-authorized
```

다운로드가 항상 가능하다는 보장은 없습니다.

## 테스트

```powershell
python -m pytest -q
```

39개 테스트가 SRT/VTT 파싱, 타임라인 연결, JSON 저장과 백업, 슬라이드 감지(하드컷, 디졸브, 애니메이션, 노이즈), 중복 후보, 노트 구조와 참고 자료·요약 연결, 전사 옵션 전달, TXT/SRT 내보내기를 확인합니다.

## 알려진 한계

- 슬라이드 감지는 **합성 영상으로만 검증**했습니다. 실제 강의의 강사 움직임, 마우스 포인터, 사진·영상이 섞인 슬라이드, 어두운 배경 슬라이드는 확인하지 못했습니다. 영상마다 `--diagnose`로 변화율을 확인하고 임계값을 조정하세요.
- `--min-stable`보다 짧게 지나가는 슬라이드는 버려집니다.
- 디졸브 직후 슬라이드의 시작 시각은 샘플 간격 정도 어긋날 수 있습니다.
- 실제 `large-v3` 전사 정확도와 `--hotwords`의 효과는 실제 강의 음성으로 검증하지 못했습니다. 숫자, 날짜, 인명은 전사 후 한 번 확인하세요.
- 중복 표시는 대표 이미지가 거의 같을 때만 합니다. 같은 슬라이드를 다시 보여 주는 경우는 중복 후보로 표시됩니다.

## 변경 이력

- **v0.2.6**: `summary.md` 사이드카를 노트와 보고서에서 연결해 재실행 후에도 요약 파일을 보존
- **v0.2.5**: `--reference`로 참고 교안을 첨부하고 Obsidian 노트에서 링크
- **v0.2.4**: 슬라이드 제거율과 정지 프레임 변화율 임계값을 0~100 범위로 검증

- **v0.2.3**: `--hotwords` 추가(faster-whisper가 지원하지 않으면 경고 후 무시), SRT 번호가 건너뛰지 않도록 수정
- **v0.2.2**: `--export-transcript`, `--initial-prompt`, GPU `int8_float16`/CPU `int8` 설정
- **v0.2.1**: 슬라이드 감지 수정. 임계값 조정, 슬라이드 교체 감지(`--removal-threshold`), 마지막 정지 프레임 대표 선택, 픽셀 기준 중복 판정, `--diagnose`
- **v0.2**: 로컬 영상 중심 구조, 스트리밍 처리, 변한 픽셀 비율 비교, Obsidian 노트 생성

