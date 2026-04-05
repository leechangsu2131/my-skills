---
description: 구글시트 시험점수를 하이클래스 하이톡(HiTalk)으로 학부모에게 개별 전송
---

# 하이톡 시험점수 개별 전송 워크플로우

## 사전 조건
- 구글시트에 시험점수 입력 완료 (A=번호, B=이름, C=점수)
- `gws` CLI 설치 및 인증 완료
- Python + Selenium 설치
- 하이톡 탭은 반드시 1개만 열기

## 설치가 안 된 경우

```powershell
npm install -g @aspect-build/gws
cd C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\hitalk-score-sender
python -m pip install -r requirements.txt
```

- `gws` 설치 후에는 터미널을 새로 열어 PATH를 반영하는 편이 안전합니다.

## 실행 순서

0. **창으로 실행하고 싶을 때**
```powershell
cd C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\hitalk-score-sender
python hitalk_sender_gui.py
```
   - 더블클릭은 `launch_hitalk_sender_gui.bat`

1. **config.json 설정 확인/수정**
   - 스킬 폴더: `C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\hitalk-score-sender\`
   - `spreadsheet_id`: 구글시트 ID
   - `range`: 데이터 범위 (예: `시트1!A1:C30`)
   - `subject`: 과목명 (예: `수학 1단원 평가`)
   - `custom_message_file`: 원하는 문구 파일 (예: `custom_message_template.txt`)

// turbo
2. **크롬 실행** (이미 열려있으면 생략)
```powershell
start "" "C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\hitalk-score-sender\launch_chrome_hiclass.bat"
```

3. **사용자가 직접 하이클래스 로그인** → 하이톡 페이지 이동
   - URL: https://www.hiclass.net/hitalk
   - 로그인 완료 & 하이톡 대화상대 목록이 보이면 준비 완료

// turbo
4. **드라이런 (미리보기)**
```powershell
cd C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\hitalk-score-sender
python hitalk_sender.py --dry-run
```

5. **안전 리허설 (입력 후 즉시 삭제)**
```powershell
cd C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\hitalk-score-sender
python hitalk_sender.py --rehearsal
```

6. **확인 후 실제 전송**
```powershell
cd C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\hitalk-score-sender
python hitalk_sender.py
```

7. **결과 확인** — 성공/실패 건수 보고

## 원하는 문구 넣는 방법

1. `custom_message_template.txt`를 수정합니다.
2. 아래 치환값을 쓸 수 있습니다.
   - `[학생]`
   - `[과목]`
   - `[점수]`
   - `[코멘트]`
3. 아래 순서로 확인 후 전송합니다.

```powershell
cd C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\hitalk-score-sender
python hitalk_sender.py --message-file custom_message_template.txt --dry-run
python hitalk_sender.py --message-file custom_message_template.txt --rehearsal
python hitalk_sender.py --message-file custom_message_template.txt
```

- 짧은 문구는 `--custom-message`로 바로 넣어도 됩니다.

## 자주 나는 오류

- `ModuleNotFoundError: No module named 'selenium'`
  → `python -m pip install -r requirements.txt`
- `'gws' 용어가 ... 인식되지 않습니다` 또는 `[✗] gws CLI를 찾을 수 없습니다.`
  → `npm install -g @aspect-build/gws` 실행 후 새 터미널에서 다시 실행
- 하이톡 탭이 여러 개 열려 있다는 메시지
  → 같은 계정의 하이톡 탭을 하나만 남기고 다시 실행
- 실제 발송 없이 화면 동선만 점검하고 싶을 때
  → `python hitalk_sender.py --rehearsal`
- 긴 문구를 매번 명령줄에 치기 불편할 때
  → `custom_message_template.txt`를 수정한 뒤 `--message-file`로 사용
