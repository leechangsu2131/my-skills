---
name: personal-video-note
description: >-
  Creates local, slide-linked lecture notes from a lecture video using LectureCapture.
  For YouTube URLs, checks and extracts available captions before speech recognition.
  Use for archiving, transcription, slide extraction, or Obsidian notes. Preserves
  timestamps and does not present automatic transcripts as fully accurate.
---

# 개인 강의 영상 노트

프로그램 경로: `skills/personal-video-note`

강의 영상을 슬라이드 캡처, 시간 정보가 있는 발언, Obsidian용 Markdown 노트로 정리하고, 사용자가 요청하면 슬라이드와 전사본에 근거한 강의 요약을 작성한다. 영상 분석과 기본 아카이빙은 로컬에서 수행한다. CLI는 외부 AI를 자동 호출하지 않으며, 요약은 현재 대화의 모델이 근거 자료를 검토해 별도 Markdown 파일로 작성한다.

## 작업 원칙

- 영상에 실제로 표시된 화면을 캡처한다. 슬라이드의 내용을 새로 그리거나 캡처에 없는 정보를 원본인 것처럼 만들지 않는다.
- 슬라이드와 발언은 원본 영상의 시간으로 연결한다. 전사 결과가 부정확할 수 있으므로 인명, 숫자, 날짜, 전문 용어를 확정된 사실처럼 다루지 않는다.
- 기본 입력은 사용자가 보유했거나 처리 권한이 있는 로컬 영상이다.
- YouTube 다운로드는 사용자가 해당 영상의 다운로드 권한과 적용되는 약관을 확인한 경우에만 진행한다. 로그인·접근 제한·DRM을 우회하지 않는다.
- 영상, 오디오, 자막을 클라우드 서비스로 보내지 않는다.
- 결과물은 자동 생성 초안이다. 사용자가 배포용 자료를 요청하면 원본 자료의 권리와 사용 허가를 먼저 확인하도록 안내한다.

## 실행 절차

1. 영상 입력을 확인한다. 로컬 파일이 있으면 그 파일을 사용한다. YouTube URL이 있으면 영상 파일을 받기 전에 자막 목록을 확인하고, 사용 가능한 자막을 먼저 추출한다. 절차와 명령은 [references/youtube-captions.md](references/youtube-captions.md)를 따른다. 영상 다운로드는 자막 추출로 충분하지 않고 사용자의 다운로드 권한도 확인된 경우에만 `download-authorized`로 진행한다.
2. 프로그램을 설치하지 않았다면 프로젝트 README의 설치 절차를 따른다. 전사가 필요하면 `transcribe` 선택 항목을 설치한다.
3. 결과 저장 위치를 확인한다. 사용자가 별도 위치를 지정하지 않은 경우 `C:\Users\lee21\Documents\영상요약\<영상 제목>`에 영상별 결과 폴더를 만든다. 요약·노트·보고서·전사본은 해당 폴더에 두고, 슬라이드 이미지와 같은 다수의 보조 이미지는 `slides/` 아래에 둔다. Obsidian 링크는 노트 위치 기준 상대 경로로 유지하고 실제 파일 존재 여부를 확인한다.
4. 강의명·강사 정보, 자막 파일 유무, 영상에서 슬라이드가 표시되는 영역을 정한다. 크롭 좌표를 모르면 첫 프레임에서 직접 선택하게 둔다.
5. `lecturecapture run`을 실행한다. 자막이 있으면 `--subtitle`로 전달한다. 자막 대신 Whisper 전사를 강제로 쓰려면 `--transcribe`를 추가한다. 전사가 불필요하면 `--no-transcribe`를 사용한다.
6. 슬라이드 감지가 지나치게 분할되거나 전환을 놓치는 것 같으면 `--diagnose`로 `diagnostics.csv`를 만든다. 실제 영상에 맞춰 `--interval`, `--change-threshold`, `--removal-threshold`, `--min-stable`을 조정한다.
7. 완료 후 `report.html`과 `note.md`를 열어 슬라이드 캡처, 시간, 전사 연결을 확인한다. 자동 결과를 검토 없이 정확한 기록으로 소개하지 않는다.
8. 연속 캡처가 같은 슬라이드의 단계적 공개인지 비교한다. 앞 화면의 내용이 뒤 화면에 모두 포함되고 새 설명·도해 변화가 없다면, 요약과 대표 이미지에는 가장 완성된 마지막 화면 하나만 사용한다. 마지막 화면을 기준으로 전체 내용을 정리해 중복 항목을 줄인다. 중간 화면에만 있는 설명, 실제 상태 변화, 또는 마지막 화면에서 사라진 정보가 있으면 그 화면도 보존한다. 원본 캡처 파일은 사용자가 중복 파일 정리를 요청하지 않는 한 삭제하지 않는다.
9. 사용자가 제공한 교안이나 참고 자료는 `--reference`로 첨부한다(여러 파일이면 반복 지정). PDF는 `--pdf`로 첨부할 수 있다. `--export-transcript`는 TXT/SRT를 함께 저장하고, YouTube 원본 URL이 있으면 `--source-url`로 시간 링크를 기록한다.
10. 사용자가 요약을 요청하면 `project.json`의 전사 구간 전체와 대표 슬라이드들을 근거로 삼는다. 긴 강의는 결과물 작성을 시작하기 전에 전체 전사와 모든 대표 슬라이드의 핵심을 훑고, 핵심 주장·용어·시간대를 대조한다. 필요하면 제공된 교안도 확인한다.
11. `summary.md`에는 짧은 전체 요약, 핵심 개념, 강의에서 바로 쓸 수 있는 체크리스트(해당할 때), 강의자가 제시한 전망과 근거의 한계, 과정 구성(해당할 때), 슬라이드별 요약을 담는다. 각 슬라이드별 항목에는 `slide_0001` 형식의 안정적인 HTML 앵커와 시간 범위, 캡처 이미지 링크를 둬서 노트에서 바로 이동할 수 있게 한다. 자료가 다루지 않는 항목이나 부정확한 내용을 억지로 채우지 않는다.
12. 교안은 용어·목차 대조에 활용하고, 강의에서 실제로 말한 내용 및 외부 검증 사실과 구분한다. 전사 오인식이 의심되면 축어 인용이나 확정 사실로 옮기지 않는다. 맥락과 슬라이드로 뜻을 확인할 수 있으면 의미 중심으로 요약하고, 판단이 불가능하면 불확실성을 요약 또는 검토 메모에 표시한다. 수치·인명·날짜·인용·시장 전망은 근거가 확인될 때만 구체적으로 쓴다.
13. 요약 파일을 저장한 뒤 노트와 HTML 보고서를 다시 생성해 전체 요약 및 슬라이드 앵커 링크를 연결하고 링크를 확인한다. CLI는 외부 AI 서비스를 자동 호출하지 않는다.

## 명령 예시

로컬 영상:

```powershell
lecturecapture run "C:\Videos\lecture.mp4" `
  --course "강의명" `
  --subtitle "C:\Videos\lecture.srt" `
  --export-transcript
```

권한을 확인한 공개 YouTube 영상:

```powershell
lecturecapture download-authorized "https://www.youtube.com/watch?v=VIDEO_ID" `
  --out "C:\Videos\lecture.mp4" `
  --confirm-authorized
```

그 다음 내려받은 파일을 `lecturecapture run`에 입력한다. 다운로드 명령은 재생목록 일괄 처리나 접근 제한 우회를 시도하지 않는다.

## 결과 확인

기본 결과 폴더에는 `project.json`(기준 데이터), `note.md`, `report.html`, `slides/`가 생성된다. 전사를 내보내면 `transcript.txt`와 `transcript.srt`가 추가된다. `note.md`는 프로젝트 폴더를 Obsidian vault 안에 두면 상대 경로로 슬라이드 이미지를 표시한다.

영상마다 해상도와 레이아웃이 다르므로 슬라이드 글씨가 읽히는지 직접 확인한다. 현재 슬라이드 감지 검증은 합성 영상 중심이며, 실제 강의의 포인터·강사 움직임·복잡한 전환에서 누락이나 과분할이 생길 수 있다. 자막과 Whisper 전사도 검토가 필요하다.

세부 옵션과 알려진 한계는 [README.md](README.md)를 따른다.

