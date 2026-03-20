import sys, json, ssl, time, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

env_path = Path(r'c:/Users/user/.gemini/antigravity/scratch/repos/my-skills/skills/student-record-classifier/.env')
config = {}
for line in env_path.read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        config[k.strip()] = v.strip()

API_KEY        = config.get('NOTION_API_KEY', '')
STUDENT_DB_ID  = config.get('NOTION_STUDENT_DB_ID', '')
RECORD_DB_ID   = config.get('NOTION_RECORD_DB_ID', '')
RELATION_FIELD = '🧑\u200d🎓 이름'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def notion_post(endpoint, body):
    data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f'https://api.notion.com/v1/{endpoint}',
        data=data, method='POST',
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json',
        }
    )
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.loads(r.read())

def load_student_map():
    result = notion_post(f'databases/{STUDENT_DB_ID}/query', {})
    mapping = {}
    for page in result.get('results', []):
        for v in page.get('properties', {}).values():
            if v.get('type') == 'title':
                parts = v.get('title', [])
                name = parts[0].get('plain_text', '') if parts else ''
                if name:
                    mapping[name] = page['id']
                break
    return mapping

DATE = '2026-03-06'

# (names, title, field, content, positivity[, subject])
# 분야: 수업태도, 학습능력, 교우관계, 생활습관, 특기사항, 상담, 작품관찰
# 긍정도: 긍정✅, 중립📋, 관찰필요🔍
records = [
    # ─── 교사 관찰 기록 ─────────────────────────────────────────────
    (['백다온'], '지각', '생활습관',
     '지각함.', '관찰필요🔍'),

    (['강시우', '백다온', '박현규'], '수학익힘책 숙제 미제출', '생활습관',
     '수학익힘책 숙제를 해오지 않음.', '관찰필요🔍', '수학'),

    (['강시우', '오지윤'], '국어 가 책 미지참', '생활습관',
     '국어 가 책을 빼먹고 가져감.', '관찰필요🔍', '국어'),

    (['박서우'], '수업 중 딴짓·따라 말하기 불참', '수업태도',
     '수업 중 딴짓이 매우 많으며, 선생님이 따라 말하라고 할 때 잘 따라 말하지 않음.', '관찰필요🔍'),

    (['천선율'], '가끔 수업 중 딴짓', '수업태도',
     '가끔 수업 중 딴짓을 함.', '관찰필요🔍'),

    (['이윤슬'], '급식 시간 수다', '생활습관',
     '밥 먹을 때 자기와 관련된 이야기를 하며 수다를 잘 떪.', '중립📋'),

    (['백다온'], '편부 가정', '특기사항',
     '편부 가정.', '중립📋'),

    (['김가을'], '긴장 시 화장실 자주 이용', '특기사항',
     '긴장하면 화장실을 자주 감.', '중립📋'),

    (['김가을'], '규칙 준수·바른 언어 사용', '생활습관',
     '규칙을 잘 지키고 바르게 말함.', '긍정✅'),

    (['박민서'], '성실하고 꼼꼼한 학습태도', '수업태도',
     '학업태도가 좋고 열심히 하며 꼼꼼하나 속도가 느린 편.', '긍정✅'),

    # ─── 부모님 제공 기록 ───────────────────────────────────────────
    (['이예나'], '꾸준한 노력·인사·자연사랑 (부모님)', '생활습관',
     '원하는 건 꾸준히 노력함. 인사성이 바르고 동식물·곤충을 아낌. 정리정돈은 배우는 중. (부모님 제공)', '긍정✅'),

    (['강시우'], '차분하고 생각이 깊음 (부모님)', '수업태도',
     '차분하고 생각이 깊음. (부모님 제공)', '긍정✅'),

    (['황보검'], '규칙적·순종적이나 겁과 눈물 많음 (부모님)', '생활습관',
     '규칙적이며 어른 말을 잘 듣고 착하나 겁이 많고 눈물이 많음. (부모님 제공)', '중립📋'),

    (['이서우'], '규칙 준수·친화적이나 정리 어려움 (부모님)', '생활습관',
     '정해진 규칙을 지키려 노력하며 친구와 잘 지냄. 정리정돈이 잘 안 되며, 기분이 좋으면 흥분하기도 함. (부모님 제공)', '중립📋'),

    (['조주아'], '규칙 준수 노력하나 소극적 (부모님)', '생활습관',
     '규칙을 지키려 하나 틀릴 것에 대한 두려움으로 소극적인 편. (부모님 제공)', '중립📋'),

    (['한예기'], '동생 돌봄·독서 집중 (부모님)', '생활습관',
     '동생들을 잘 돌보고 사이가 좋으며 책을 집중해서 잘 읽음. (부모님 제공)', '긍정✅'),

    (['박서우'], '차분·배려 있으나 눈물 많음 (부모님)', '생활습관',
     '차분하고 배려를 잘하나 눈물이 많다고 함. (부모님 제공)', '중립📋'),

    (['박현규'], '과묵하고 배려심 있음 (부모님)', '생활습관',
     '과묵하고 착하며 다른 사람을 생각할 줄 앎. (부모님 제공)', '긍정✅'),

    (['김주안'], '정리 노력·반복 습관 형성 (부모님)', '생활습관',
     '산만하지만 정리정돈을 노력 중이며 꾸준히 반복하는 습관이 생김. 의사소통이 안 될 때 잘 운다고 함. (부모님 제공)', '중립📋'),

    (['백다온'], '말을 잘 듣는다 (부모님)', '생활습관',
     '말을 잘 듣는다고 부모님이 전달함. (부모님 제공)', '긍정✅'),
]

student_map = load_student_map()
print(f'📚 학생 {len(student_map)}명 로딩 완료\n')

ok = 0
for record in records:
    if len(record) == 6:
        names, title, field, content, positivity, subject = record
    else:
        names, title, field, content, positivity = record
        subject = None

    relation_ids = [{"id": student_map[n]} for n in names if n in student_map]
    missing = [n for n in names if n not in student_map]
    if missing:
        print(f'  ⚠ 학생 ID 없음: {missing}')

    props = {
        "기록제목":     {"title": [{"text": {"content": title}}]},
        RELATION_FIELD: {"relation": relation_ids},
        "날짜":         {"date": {"start": DATE}},
        "내용":         {"rich_text": [{"text": {"content": content}}]},
        "분야":         {"select": {"name": field}},
        "긍정도":       {"select": {"name": positivity}},
        "출처":         {"select": {"name": "직접메모"}},
    }
    if subject:
        props["과목"] = {"select": {"name": subject}}

    try:
        notion_post('pages', {"parent": {"database_id": RECORD_DB_ID}, "properties": props})
        label = ' + '.join(names)
        subj_label = f' [{subject}]' if subject else ''
        print(f'  ✅ [{label}]{subj_label} {title}')
        ok += 1
    except Exception as e:
        print(f'  ❌ {title} → {e}')
    time.sleep(0.35)

print(f'\n✅ {ok}/{len(records)}건 저장 완료')
