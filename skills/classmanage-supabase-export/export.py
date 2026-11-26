import os
import json
import requests
import pandas as pd
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(next(p / "_shared" for p in _pl.Path(__file__).resolve().parents if (p / "_shared" / "skill_env.py").is_file())))
from skill_env import load_env, data_dir

def get_supabase_data():
    # 공용 중앙 .env 파일에서 Supabase 설정을 불러온다.
    load_env()
    
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    table = os.environ.get('SUPABASE_TABLE_NAME')
    
    if not url or not key:
        print("❌ .env 설정 (SUPABASE_URL, SUPABASE_KEY)이 존재하지 않습니다.")
        return []
    
    headers = {'apikey': key, 'Authorization': f'Bearer {key}'}
    res = requests.get(f'{url}/rest/v1/{table}?select=*', headers=headers)
    if not res.ok:
        print("❌ Failed to fetch data:", res.status_code, res.text)
        return []
    return res.json()

def _split_name_text(text):
    """JSON 이 아닌 이름 글을 나눈다.

    쉼표가 없으면 공백으로 나눈다. 쉼표가 있으면 쉼표로 먼저 나누고, 한 칸 안에
    한 글자짜리 토막이 있으면('학생 A', '김 철수') 한 이름 안의 공백으로 본다.
    토막이 모두 두 글자 이상이면('학생A 학생B') 여러 이름으로 나눈다.
    """
    if ',' not in text:
        return text.split()
    names = []
    for part in text.split(','):
        tokens = part.split()
        if any(len(t) == 1 for t in tokens):
            names.append(' '.join(tokens))
        else:
            names.extend(tokens)
    return names

def parse_names(raw_name):
    if not raw_name: return []
    text = raw_name.strip()
    if text.startswith('[') and text.endswith(']'):
        try:
            parsed = [str(p) for p in json.loads(text) if p is not None]
        except ValueError:
            parsed = _split_name_text(text[1:-1])
    else:
        parsed = _split_name_text(text)
    return [p.strip() for p in parsed if p.strip()]

def export_to_excel(records):
    # 1. 분리 작업 (선생님이 요청하신 낱개 형태 'A')
    student_records = {} # { "학생A": [record1, record2], ... }
    
    for rec in records:
        names = parse_names(rec.get("🧑‍🎓 이름", ""))
        for name in names:
            if name not in student_records:
                student_records[name] = []
            
            # 낱개의 기록으로 개인화 복제
            rec_copy = rec.copy()
            # 타 학생 지우고 해당 시트 주인의 이름으로만 덮어쓰기!
            rec_copy["🧑‍🎓 이름"] = name
            
            student_records[name].append(rec_copy)
            
    # 이름이 하나도 없으면 시트 없는 엑셀은 만들 수 없으므로 알리고 끝낸다.
    if not student_records:
        print("⚠️ 이름이 적힌 기록이 없어 엑셀 파일을 새로 만들지 않았습니다.")
        return

    # 2. 엑셀 파일 생성
    output_file = data_dir() / "student_records.xlsx"
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for student, rows in sorted(student_records.items()):
            df = pd.DataFrame(rows)
            
            # 가독성을 위해 불필요한 고유 ID, timestamp 등이 앞쪽에 있다면 재배열
            # 여기서는 편의상 그대로 쓰고 시트 제한에 맞춘 가공만 진행
            sheet_name = student[:31].replace('/', '_').replace('\\', '_')
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
    print(f"✅ 엑셀 추출 완료: 총 {len(student_records)}명의 시트가 개인 데이터 폴더에 생성되었습니다: {output_file}")

if __name__ == "__main__":
    records = get_supabase_data()
    if records:
        print(f"📥 Supabase에서 {len(records)}개의 기록을 성공적으로 불러왔습니다.")
        print("⚙️ 다중 학생 기록을 개별 낱개 형식으로 쪼개서 시트 구분을 시작합니다...")
        export_to_excel(records)
