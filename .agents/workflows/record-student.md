---
description: 클로바노트 텍스트나 메모를 학생별로 분류하여 노션에 저장
---

# 학생 기록 저장 워크플로우

선생님의 수업 메모, 클로바노트 텍스트, 또는 자유 메모를 학생별로 분류하고 노션 학생 기록 DB에 저장합니다.

## 사전 조건

- `skills/student-record-classifier/.env` 파일에 노션 설정이 입력되어 있어야 합니다 (`.env.example` 참고)
- 노션 🧑‍🎓 학생 데이터베이스에 학생 명단이 등록되어 있어야 합니다
- 노션에 📝 학생 기록 DB가 이미 생성되어 있어야 합니다

---

// turbo
## Step 1: 노션 학생 명단 확인

노션에서 등록된 학생 명단을 먼저 조회하여 이름을 확인합니다:

```
python skills/student-record-classifier/scripts/save_to_notion.py --list-students
```

또는 아래 코드로 직접 확인:

```python
# skills/student-record-classifier 폴더에서 실행
import urllib.request, json, ssl, sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

env_path = Path('skills/student-record-classifier/.env')
config = {}
for line in env_path.read_text(encoding='utf-8').splitlines():
    if line.strip() and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1); config[k.strip()] = v.strip()

API_KEY = config['NOTION_API_KEY']
STUDENT_DB_ID = config['NOTION_STUDENT_DB_ID']
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
data = json.dumps({}).encode()
req = urllib.request.Request(f'https://api.notion.com/v1/databases/{STUDENT_DB_ID}/query', data=data, method='POST',
    headers={'Authorization': f'Bearer {API_KEY}', 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json'})
with urllib.request.urlopen(req, context=ctx) as r:
    result = json.loads(r.read())
students = []
for page in result.get('results', []):
    for v in page.get('properties', {}).values():
        if v.get('type') == 'title':
            parts = v.get('title', []); name = parts[0].get('plain_text', '') if parts else ''
            if name: students.append(name); break
print(f'총 {len(students)}명:')
for i, s in enumerate(students, 1): print(f'  {i}. {s}')
```

---

## Step 2: 기록 텍스트 받기

사용자에게 정리할 텍스트를 요청합니다:

```
어떤 기록을 정리할까요? 아래 중 하나를 붙여넣어 주세요:
- 클로바노트 텍스트
- 수업 메모
- 자유 메모
- 구글폼 응답
```

날짜 정보도 함께 확인합니다. (미입력 시 오늘 날짜 기본값)

---

## Step 3: 학생별 분류

`@student-record-classifier` 스킬의 지침에 따라 텍스트를 분류합니다:

1. **Step 1에서 확인한 정확한 이름**으로 학생을 식별 (이름 오탈자 주의)
2. 학생별로 내용 분리
3. 각 기록에 메타데이터 태깅 (날짜, 분야, 긍정도)
4. **같은 행동을 한 학생이 여러 명이면 한 행으로 묶기**

분야 옵션: `수업태도`, `학습능력`, `교우관계`, `생활습관`, `특기사항`, `상담`, `작품관찰`
긍정도 옵션: `긍정✅`, `중립📋`, `관찰필요🔍`

---

## Step 4: 분류 결과 확인

분류 결과를 사용자에게 표로 보여주고 확인을 받습니다:

| 학생 | 기록제목 | 분야 | 긍정도 |
|------|---------|------|--------|
| 홍길동 | 발표 적극 참여 | 수업태도 | 긍정✅ |
| ... | ... | ... | ... |

```
위 분류 결과가 맞나요?
- 수정할 내용이 있으면 알려주세요
- "저장해줘" → 노션에 저장합니다
```

---

// turbo
## Step 5: 노션에 저장

분류된 기록을 `save_today.py` 스크립트로 저장합니다.
아래 형식으로 `skills/student-record-classifier/scripts/save_today.py` 파일을 **새로 생성**하여 실행합니다:

```python
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import urllib.request, json, ssl, time
from pathlib import Path

env_path = Path(__file__).parent.parent / '.env'
config = {}
for line in env_path.read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1); config[k.strip()] = v.strip()

API_KEY       = config['NOTION_API_KEY']
STUDENT_DB_ID = config['NOTION_STUDENT_DB_ID']
RECORD_DB_ID  = config['NOTION_RECORD_DB_ID']
RELATION_FIELD = '🧑‍🎓 이름'

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def notion_post(endpoint, body, method='POST'):
    data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(f'https://api.notion.com/v1/{endpoint}', data=data, method=method,
        headers={'Authorization': f'Bearer {API_KEY}', 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, context=ctx) as r: return json.loads(r.read())

def load_student_map():
    result = notion_post(f'databases/{STUDENT_DB_ID}/query', {})
    mapping = {}
    for page in result.get('results', []):
        for v in page.get('properties', {}).values():
            if v.get('type') == 'title':
                parts = v.get('title', []); name = parts[0].get('plain_text', '') if parts else ''
                if name: mapping[name] = page['id']; break
    return mapping

DATE = 'YYYY-MM-DD'   # ← 날짜 변경

# (이름목록, 기록제목, 분야, 내용, 긍정도)
records = [
    (['학생이름'], '기록제목', '분야', '내용', '긍정도'),
]

student_map = load_student_map()
print(f'📚 {len(student_map)}명 로딩 완료\n')
ok = 0
for names, title, field, content, positivity in records:
    relation_ids = [{"id": student_map[n]} for n in names if n in student_map]
    missing = [n for n in names if n not in student_map]
    if missing: print(f'  ⚠ 학생 ID 없음: {missing}')
    props = {
        "기록제목": {"title": [{"text": {"content": title}}]},
        RELATION_FIELD: {"relation": relation_ids},
        "날짜": {"date": {"start": DATE}},
        "내용": {"rich_text": [{"text": {"content": content}}]},
        "분야": {"select": {"name": field}},
        "긍정도": {"select": {"name": positivity}},
        "출처": {"select": {"name": "직접메모"}},
    }
    try:
        notion_post('pages', {"parent": {"database_id": RECORD_DB_ID}, "properties": props})
        print(f'  ✅ [{" + ".join(names)}] {title}'); ok += 1
    except Exception as e: print(f'  ❌ {title} → {e}')
    time.sleep(0.35)
print(f'\n🎉 {ok}/{len(records)}건 저장 완료!')
```

실행:
```
python skills/student-record-classifier/scripts/save_today.py
```

### 📝 학생 기록 DB 속성
| 속성 | 타입 | 비고 |
|------|------|------|
| 기록제목 | title | 기록 요약 제목 |
| 🧑‍🎓 이름 | **relation** | 학생 DB와 관계형 연결 (다중 연결 가능) |
| 날짜 | date | 관찰 날짜 |
| 분야 | select | 분야 옵션 중 선택 |
| 긍정도 | select | 긍정도 옵션 중 선택 |
| 내용 | rich_text | 구체적 관찰 내용 |
| 출처 | select | 직접메모 / 음성메모 등 |

---

## Step 6: 완료 보고

```
✅ 저장 완료!
- 총 ○건을 노션에 저장했습니다
```

---

## 주의사항

- 학생 이름은 반드시 **Step 1에서 확인한 노션 등록 이름**과 정확히 일치해야 합니다
- 한 번에 너무 많은 텍스트(A4 5장 이상)는 나눠서 처리합니다
- 학생 이름이 모호한 경우 사용자에게 확인 후 저장합니다
- `.env` 파일은 절대 깃허브에 올리지 않습니다 (`.gitignore`로 제외됨)
- `save_today.py`는 매일 새로 작성하는 용도이며 커밋하지 않아도 됩니다 (`.gitignore` 추가 권장)
