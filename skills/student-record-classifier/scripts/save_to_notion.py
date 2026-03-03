import urllib.request
import json
import ssl
import sys
import time
from pathlib import Path

"""
학생 관찰 기록 → 노션 학생 기록 DB 저장 스크립트

사전 준비:
  - skills/student-record-classifier/.env 파일에 노션 설정 입력
  - .env.example 참고

사용법:
  python save_to_notion.py

입력 형식 예시:
  records = [
      (['학생이름1', '학생이름2'], '기록제목', '분야', '내용', '긍정도'),
      ...
  ]

분야 옵션:   수업태도, 학습능력, 교우관계, 생활습관, 특기사항, 상담, 작품관찰
긍정도 옵션: 긍정✅, 중립📋, 관찰필요🔍
출처 옵션:   음성메모, 직접메모, 사진, 구글폼, 상담기록
"""

sys.stdout.reconfigure(encoding='utf-8')

# ── 설정 로드 ──────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent / 'skills' / 'student-record-classifier' / '.env'
config = {}
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip()

API_KEY        = config.get('NOTION_API_KEY', '')
STUDENT_DB_ID  = config.get('NOTION_STUDENT_DB_ID', '')
RECORD_DB_ID   = config.get('NOTION_RECORD_DB_ID', '')
RELATION_FIELD = '🧑\u200d🎓 이름'

if not API_KEY:
    print('❌ .env 파일에 NOTION_API_KEY가 없습니다. .env.example을 참고하세요.')
    sys.exit(1)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def notion_post(endpoint, body, method='POST'):
    data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f'https://api.notion.com/v1/{endpoint}',
        data=data,
        method=method,
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json',
        }
    )
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.loads(r.read())

def load_student_map():
    """학생 이름 → 노션 페이지 ID 매핑 반환"""
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

def save_records(records: list, date: str):
    """
    records: list of (names, title, field, content, positivity)
      - names     : 학생명 리스트 (e.g. ['김민준', '이서연'])
      - title     : 기록 제목
      - field     : 분야
      - content   : 내용
      - positivity: 긍정도
    date: 'YYYY-MM-DD'
    """
    student_map = load_student_map()
    print(f'📚 학생 {len(student_map)}명 로딩 완료\n')

    ok = 0
    for names, title, field, content, positivity in records:
        relation_ids = [{"id": student_map[n]} for n in names if n in student_map]
        missing = [n for n in names if n not in student_map]
        if missing:
            print(f'  ⚠ 학생 ID 없음: {missing}')

        props = {
            "기록제목":      {"title": [{"text": {"content": title}}]},
            RELATION_FIELD:  {"relation": relation_ids},
            "날짜":          {"date": {"start": date}},
            "내용":          {"rich_text": [{"text": {"content": content}}]},
            "분야":          {"select": {"name": field}},
            "긍정도":        {"select": {"name": positivity}},
            "출처":          {"select": {"name": "직접메모"}},
        }
        try:
            notion_post('pages', {"parent": {"database_id": RECORD_DB_ID}, "properties": props})
            label = ' + '.join(names)
            print(f'  ✅ [{label}] {title}')
            ok += 1
        except Exception as e:
            print(f'  ❌ {title} → {e}')
        time.sleep(0.35)

    print(f'\n✅ {ok}/{len(records)}건 저장 완료')


# ── 실행 예시 (직접 수정해서 사용) ────────────────────────────────
if __name__ == '__main__':
    DATE = '2026-03-03'   # ← 날짜 변경

    records = [
        # (['학생이름'], '기록제목', '분야', '내용', '긍정도'),
        # 예시:
        # (['김민준', '이서연'], '쉬는 시간 뛰어다님', '생활습관', '쉬는 시간에 교실에서 뛰어다님.', '관찰필요🔍'),
    ]

    if not records:
        print('records 리스트를 채워주세요.')
    else:
        save_records(records, DATE)
