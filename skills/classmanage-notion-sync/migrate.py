import os
import sys
import argparse
from pathlib import Path

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ python-dotenv가 설치되지 않았습니다. 의존성을 설치해주세요:")
    print("pip install -r requirements.txt")
    sys.exit(1)


def load_environment():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    config = {
        "NOTION_API_KEY": os.getenv("NOTION_API_KEY"),
        "NOTION_DATABASE_ID": os.getenv("NOTION_DATABASE_ID"),
        "SUPABASE_URL": os.getenv("SUPABASE_URL", "").rstrip("/"),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
        "SUPABASE_TABLE_NAME": os.getenv("SUPABASE_TABLE_NAME"),
    }
    return config


relation_cache = {}

def get_page_title(page_id, api_key):
    if page_id in relation_cache:
        return relation_cache[page_id]
        
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28"
    }
    
    try:
        res = requests.get(url, headers=headers, verify=False)
        if res.ok:
            page = res.json()
            for prop_name, prop_data in page.get("properties", {}).items():
                if prop_data.get("type") == "title":
                    title_list = prop_data.get("title", [])
                    name = "".join(t.get("plain_text", "") for t in title_list) if title_list else ""
                    relation_cache[page_id] = name
                    return name
    except Exception as e:
        print(f"  ⚠️ Warning: Could not fetch relation {page_id}")
        
    relation_cache[page_id] = page_id # fallback to ID
    return page_id

def parse_notion_property(prop, api_key=None):
    """노션 프로퍼티 구조를 파이썬의 단순 값(문자열, 숫자, 불리언 등)으로 변환합니다."""
    type_ = prop.get("type", "")
    if type_ == "title":
        title_list = prop.get("title", [])
        return "".join(t.get("plain_text", "") for t in title_list) if title_list else ""
    elif type_ == "rich_text":
        rt_list = prop.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in rt_list) if rt_list else ""
    elif type_ == "number":
        return prop.get("number")
    elif type_ == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else None
    elif type_ == "multi_select":
        ms = prop.get("multi_select", [])
        return [item.get("name") for item in ms] if ms else []
    elif type_ == "date":
        date_obj = prop.get("date")
        if not date_obj: return None
        return date_obj.get("start")
    elif type_ == "checkbox":
        return prop.get("checkbox", False)
    elif type_ == "url":
        return prop.get("url", "")
    elif type_ == "email":
        return prop.get("email", "")
    elif type_ == "phone_number":
        return prop.get("phone_number", "")
    elif type_ == "formula":
        form = prop.get("formula", {})
        ftype = form.get("type")
        return form.get(ftype) if ftype else ""
    elif type_ == "people":
        ppl = prop.get("people", [])
        return [p.get("name") for p in ppl if "name" in p] if ppl else []
    elif type_ == "rollup":
        rollup = prop.get("rollup", {})
        rtype = rollup.get("type", "")
        if rtype == "array":
            arr = rollup.get("array", [])
            res = []
            for item in arr:
                val = parse_notion_property(item, api_key)
                if val:
                    if isinstance(val, list): res.extend(val)
                    else: res.append(val)
            return res
        return None
    elif type_ == "relation":
        rels = prop.get("relation", [])
        if api_key:
            return [get_page_title(r.get("id"), api_key) for r in rels] if rels else []
        else:
            return [r.get("id") for r in rels] if rels else []
    else:
        return None


def fetch_notion_data(database_id, api_key):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    results = []
    has_more = True
    next_cursor = None
    
    print("📥 노션 DB에서 데이터를 가져옵니다...")
    
    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor
            
        res = requests.post(url, json=payload, headers=headers, verify=False)
        if not res.ok:
            print(f"❌ 노션 API 에러 ({res.status_code}): {res.text}")
            sys.exit(1)
            
        data = res.json()
        results.extend(data.get("results", []))
        
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
        
        print(f"  ... 현재까지 {len(results)}개 행 로드됨")
        
    return results


def upload_to_supabase(table, rows, url, key):
    # Supabase REST API (200개씩 일괄 배치 처리)
    batch_size = 200
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal" # 충돌 시 에러 반환 방식을 바꾸려면 resolution=merge-duplicates 등 사용
    }
    
    url_endpoint = f"{url}/rest/v1/{table}"
    
    print(f"\n📤 Supabase '{table}' 테이블로 업로드를 시작합니다 (총 {len(rows)}행)...")
    
    success_count = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        res = requests.post(url_endpoint, json=chunk, headers=headers, verify=False)
        
        if res.status_code in [200, 201]:
            success_count += len(chunk)
            print(f"  ✅ 배치 업로드 성공 [{i+1} ~ {i+len(chunk)}]")
        else:
            print(f"  ❌ 배치 업로드 실패 [{i+1} ~ {i+len(chunk)}] - Status: {res.status_code}")
            print(f"     내용: {res.text}")
            
    print(f"\n🚀 이관 완료: 총 {success_count} / {len(rows)} 성공")


def main():
    parser = argparse.ArgumentParser(description="Notion to Supabase 데이터 마이그레이션")
    parser.add_argument("--notion-db", help="Notion Database ID 무시 및 재지정")
    parser.add_argument("--table", help="Supabase 테이블 명 재지정")
    args = parser.parse_args()

    config = load_environment()
    
    notion_db_id = args.notion_db or config["NOTION_DATABASE_ID"]
    supabase_table = args.table or config["SUPABASE_TABLE_NAME"]
    notion_key = config["NOTION_API_KEY"]
    supabase_url = config["SUPABASE_URL"]
    supabase_key = config["SUPABASE_KEY"]
    
    if not all([notion_db_id, supabase_table, notion_key, supabase_url, supabase_key]):
        print("❌ 환경 변수나 인자가 누락되었습니다. .env 파일을 확인해 주세요.")
        sys.exit(1)

    # 1. 노션 데이터 로드
    raw_pages = fetch_notion_data(notion_db_id, notion_key)
    
    if not raw_pages:
        print("ℹ️ 노션 DB에 데이터가 없거나 접근 권한이 없습니다.")
        sys.exit(0)

    # 2. 데이터 가공
    parsed_rows = []
    for page in raw_pages:
        properties = page.get("properties", {})
        row = {}
        for prop_name, prop_data in properties.items():
            parsed_val = parse_notion_property(prop_data, notion_key)
            if isinstance(parsed_val, list):
                parsed_val = ", ".join(str(x) for x in parsed_val if x)
                
            # 프로퍼티 이름을 소문자화 + 밑줄 방식으로 바꿔서 컬럼명 매칭을 쉽게 할 수도 있습니다. 
            # (기본적으로는 노션 프로퍼티 이름을 그대로 씁니다)
            row[prop_name] = parsed_val
        parsed_rows.append(row)

    # 3. Supabase 업로드
    upload_to_supabase(supabase_table, parsed_rows, supabase_url, supabase_key)


if __name__ == "__main__":
    main()
