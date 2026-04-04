---
name: hitalk-score-sender
description: "구글시트의 시험점수를 읽어 하이클래스 하이톡(HiTalk)으로 학부모에게 개별 전송합니다."
---

# 하이톡 시험점수 개별 전송 스킬

구글시트에 입력된 시험 점수를 읽어, 하이클래스 하이톡으로 각 학부모에게 **자기 자녀의 점수와 코멘트만** 개별 메시지로 전송합니다.

---

## 🚀 빠른 시작

### 1. 사전 준비
- 구글시트에 시험 점수 입력 (A=번호, B=이름, C=점수)
- `config.json`에 구글시트 ID와 과목명 설정
- Python + Selenium + Chrome 필요
- 하이톡 탭은 1개만 열어 두기

### 1-1. 설치가 안 된 경우

```powershell
npm install -g @aspect-build/gws
cd C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\hitalk-score-sender
python -m pip install -r requirements.txt
```

- `gws` 설치 후에는 터미널을 새로 열어 주는 편이 안전합니다.

### 2. 실행 순서

```
📋 Step 1: config.json 설정
         ↓
🌐 Step 2: launch_chrome_hiclass.bat 실행
         ↓  
🔐 Step 3: 하이클래스 로그인 → 하이톡 페이지
         ↓
🔍 Step 4: python hitalk_sender.py --dry-run  (미리보기)
          ↓
🧪 Step 5: python hitalk_sender.py --rehearsal  (입력 후 즉시 삭제)
         ↓
📤 Step 6: python hitalk_sender.py  (실제 전송)
```

---

## ⚙️ config.json 설정

```json
{
  "spreadsheet_id": "구글시트_URL에서_복사한_ID",
  "range": "시트1!A1:C30",
  "subject": "수학 1단원 평가",
  "name_column": 1,
  "score_column": 2
}
```

| 항목 | 설명 |
|------|------|
| `spreadsheet_id` | 구글시트 URL → `https://docs.google.com/spreadsheets/d/**여기**` |
| `range` | 읽을 범위 (예: `시트1!A1:C30`) |
| `subject` | 과목/시험 이름 (메시지에 표시) |
| `name_column` | 이름이 있는 열 인덱스 (B열=1) |
| `score_column` | 점수가 있는 열 인덱스 (C열=2) |

---

## 🤖 AI 에이전트 실행 순서

사용자가 "하이톡으로 시험점수 보내줘" 또는 "학부모에게 점수 알려줘"라고 하면:

1. **config.json 확인** — 시트 ID, 과목명, 범위 설정 확인
2. **크롬 실행** — `launch_chrome_hiclass.bat` 실행 안내
3. **로그인 대기** — 사용자가 하이클래스 로그인 완료할 때까지 대기
4. **드라이런 실행**
   ```powershell
   cd C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\hitalk-score-sender
   python hitalk_sender.py --dry-run
   ```
5. **사용자 확인 후 실제 전송**
   ```powershell
   python hitalk_sender.py
   ```
6. **원하면 안전 리허설 먼저 실행**
   ```powershell
   python hitalk_sender.py --rehearsal
   ```
7. **결과 보고** — 성공/실패 건수 안내

---

## 📝 메시지 예시

```
📝 수학 1단원 평가 결과 안내

강시우 학생의 점수: 65점
💬 조금 더 노력해봐요! 화이팅! 🔥

궁금하신 점은 편하게 문의해 주세요. 😊
```

### 점수별 자동 코멘트

| 점수 | 코멘트 |
|------|--------|
| 100점 | 완벽해요! 정말 대단합니다! 👏 |
| 90~99점 | 아주 잘했어요! 훌륭합니다! 😊 |
| 80~89점 | 잘했어요! 조금만 더 힘내면 완벽해요! 💪 |
| 70~79점 | 괜찮아요! 복습하면 더 좋아질 거에요! 📚 |
| 60~69점 | 조금 더 노력해봐요! 화이팅! 🔥 |
| 0~59점 | 어려웠죠? 같이 복습해봐요! 선생님이 도와줄게요! 🤗 |

코멘트는 `config.json`의 `comments`와 `comment_thresholds`에서 자유롭게 수정 가능합니다.

---

## ⚠️ 주의사항

- 반드시 `--dry-run`으로 미리보기 확인 후 전송하세요
- 전송 사이 3초 간격을 두어 서버 부하를 방지합니다 (설정 가능)
- 실패한 학생은 전송 완료 후 재시도 가능
- 개인정보 보호: 각 학부모에게 자기 자녀 점수만 전송됩니다

## 🩹 자주 나는 오류

- `ModuleNotFoundError: No module named 'selenium'`
  → `python -m pip install -r requirements.txt`
- `'gws' 용어가 ... 인식되지 않습니다` 또는 `[✗] gws CLI를 찾을 수 없습니다.`
  → `npm install -g @aspect-build/gws` 실행 후 새 터미널에서 다시 실행
- 하이톡 탭이 여러 개 열려 있다는 메시지
  → 하이톡 탭을 하나만 남기고 다시 실행
- 실제 전송 없이 순회/입력/삭제만 점검하고 싶을 때
  → `python hitalk_sender.py --rehearsal`
