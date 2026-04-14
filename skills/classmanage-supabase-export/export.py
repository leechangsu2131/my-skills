import os
import re
import urllib3
import requests
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_supabase_data():
    # 상위 폴더(classmanage-notion-sync)의 .env 파일 로드 시도
    env_path = Path(__file__).parent.parent / "classmanage-notion-sync" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    table = os.environ.get('SUPABASE_TABLE_NAME')
    
    if not url or not key:
        print("❌ .env 설정 (SUPABASE_URL, SUPABASE_KEY)이 존재하지 않습니다.")
        return []
    
    headers = {'apikey': key, 'Authorization': f'Bearer {key}'}
    res = requests.get(f'{url}/rest/v1/{table}?select=*', headers=headers, verify=False)
    if not res.ok:
        print("❌ Failed to fetch data:", res.status_code, res.text)
        return []
    return res.json()

def parse_names(raw_name):
    if not raw_name: return []
    try:
        if raw_name.strip().startswith('[') and raw_name.strip().endswith(']'):
            import json
            parsed = json.loads(raw_name)
        else:
            parsed = re.split(r'[,\s]+', raw_name)
    except:
        parsed = re.split(r'[,\s]+', raw_name)
    return [p.strip() for p in parsed if p.strip()]

def export_to_excel(records):
    # 1. 분리 작업 (선생님이 요청하신 낱개 형태 'A')
    student_records = {} # { "강시우": [record1, record2], ... }
    
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
            
    # 2. 엑셀 파일 생성
    output_file = Path(__file__).parent / "student_records.xlsx"
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for student, rows in sorted(student_records.items()):
            df = pd.DataFrame(rows)
            
            # 가독성을 위해 불필요한 고유 ID, timestamp 등이 앞쪽에 있다면 재배열
            # 여기서는 편의상 그대로 쓰고 시트 제한에 맞춘 가공만 진행
            sheet_name = student[:31].replace('/', '_').replace('\\', '_')
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
    print(f"✅ 엑셀 추출 완료: 총 {len(student_records)}명의 시트가 '{output_file.name}'에 생성되었습니다!")

if __name__ == "__main__":
    records = get_supabase_data()
    if records:
        print(f"📥 Supabase에서 {len(records)}개의 기록을 성공적으로 불러왔습니다.")
        print("⚙️ 다중 학생 기록을 개별 낱개 형식으로 쪼개서 시트 구분을 시작합니다...")
        export_to_excel(records)
