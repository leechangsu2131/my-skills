# AGENTS.md

이 저장소에서 작업하는 모든 코딩 에이전트(Claude Code 등)가 따라야 할 규칙입니다.

## 프로젝트 개요

**Reading Tutor** — 긴 문서(소설, 논문, 실무 자료)를 음성으로 대화하듯 읽어주는 로컬 우선 도구.
핵심 목표: TTS로 원문을 기계적으로 낭독하는 게 아니라, 문서를 **이해한 뒤 설명**한다.
사용자가 중간에 끼어들어 질문하면 **지금까지 읽은 범위**만 근거로 답한다.

## 핵심 설계 원칙 (임의로 바꾸지 말 것)

1. **TTS는 원문(raw text)을 절대 직접 읽지 않는다.** 반드시 `cleaner.py`가 생성한 `narration` 필드만 읽는다.
   원문에는 구분선, 페이지 번호, 깨진 표/OCR 오류가 섞여 있어 그대로 읽으면 사용자 경험이 망가진다.
2. **Chunk가 아니라 Episode 단위로 관리한다.** 하나의 Episode는 `{narration, entities, summary}`를 갖는다.
   narration만 담은 배열로 단순화하지 말 것 — entities/summary는 질문 응답 품질에 직결된다.
3. **스포일러 방지: 질문 응답 컨텍스트에는 현재 읽은 지점(`progress.json`의 idx) 이하 Episode만 포함한다.**
   전체 문서를 vector DB에 미리 인덱싱해서 검색하는 방식은 금지한다 — 아직 안 읽은 뒷부분이 답변에 새어 들어갈 수 있다.
4. **외부 API 호출 최소화.** Claude API는 두 곳에서만 호출한다: (a) `cleaner.py`의 1회성 정제, (b) 실시간 질문 응답.
   낭독 루프 자체(재생 중)에는 API 호출이 없어야 한다 — 이미 정제된 텍스트만 순차 재생.
5. **음성 컴포넌트는 로컬/오프라인 우선.** STT는 `faster-whisper`, TTS는 1단계엔 `pyttsx3`(추후 `Piper`로 교체 가능). 브라우저 의존(Web Speech API) 방식으로 되돌리지 않는다.

## 폴더 구조

```
reading_tutor/
  main.py          # 런타임 루프: 낭독 <-> 질문 처리 상태머신
  cleaner.py        # 오프라인 1회 실행: 원본 문서 -> episodes.json
  episodes.json      # 정제된 Episode 배열 (cleaner.py 출력)
  progress.json      # 현재 읽은 위치(idx), 마지막 갱신 시각
  requirements.txt
```

## 셋업 / 실행

```bash
pip install -r requirements.txt
python cleaner.py <문서경로>   # 최초 1회, episodes.json 생성
python main.py                  # 낭독 루프 시작
```

## episodes.json 스키마

```json
[
  {
    "id": 0,
    "narration": "소리 내어 읽을 자연스러운 문장",
    "entities": ["등장인물/핵심 개념"],
    "summary": "이 블록 한 줄 요약"
  }
]
```

## 코드 스타일

- Python 3.10+, type hint 권장
- 상태는 당분간 JSON 파일로 관리 (SQLite 도입은 episodes 수가 수천 개 넘어갈 때 고려)
- 함수는 작게: 정제/재생/질문응답 로직을 하나의 함수에 섞지 말 것

## 회귀 테스트 시 반드시 확인할 것

- `episodes.json`의 `narration` 필드에 `===`, `---`, 페이지 번호 같은 잡음이 남아있지 않은가
- 질문 응답 시 아직 읽지 않은 Episode 내용이 답변에 등장하지 않는가 (스포일러 누출 여부)
- STT 대기 로직에 반드시 timeout이 있는가 (무한 대기 금지)

## 하지 말아야 할 것

- 원문을 그대로 TTS에 넘기기
- 전체 문서를 한 번에 vector DB에 인덱싱하기
- 브라우저 Web Speech API로 회귀하기 (이미 웹앱 방식에서 로컬 방식으로 전환 결정됨)
- cleaner.py 결과를 검증 없이 그대로 신뢰하기 (Claude 응답이 JSON 스키마를 안 지킬 수 있으니 파싱 실패 시 원문 fallback 필요)
