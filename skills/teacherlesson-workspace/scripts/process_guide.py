import os
import re
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict

# Suppress InsecureRequestWarning for SSL bypass
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests

try:
    import pdfplumber
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("❌ 의존성이 설치되지 않았습니다. 먼저 다음을 실행하세요:")
    print("pip install pdfplumber pypdf requests python-dotenv")
    sys.exit(1)

# load ENV
def load_env():
    env_path = Path(__file__).parent.parent / ".env.local"
    if not env_path.exists():
        print("❌ .env.local 파일이 없습니다.")
        sys.exit(1)
    env = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env

ENV = load_env()
SUPABASE_URL = ENV.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = ENV.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

# ---------------------------------------------------------
# 1. PDF 추출 로직 (기존 호환)
# ---------------------------------------------------------

def normalize_space(text): return " ".join((text or "").split())

def sanitize_filename_part(value):
    cleaned = normalize_space(value)
    cleaned = re.sub(r'[<>:"/\\\\|?*]', "_", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" ._")

def parse_page_ranges(cell_text):
    t = normalize_space(cell_text or "")
    if not t: return []
    range_re = re.compile(r"(\d{1,3})\s*[-~–—]\s*(\d{1,3})")
    ranges = [(int(a), int(b)) for a, b in range_re.findall(t)]
    if not ranges:
        nums = [int(x) for x in re.findall(r"\b\d{1,3}\b", t)]
        if not nums: return []
        return [(min(nums), max(nums))]
    normalized = []
    for s, e in ranges:
        if e < s: s, e = e, s
        normalized.append((s, e))
    return normalized

def score_table_for_plan(table):
    if not table: return -1
    flat = []
    for row in table: flat.extend([c for c in row if c is not None])
    combined_norm = " ".join(normalize_space(str(x)) for x in flat if str(x).strip()).lower()
    page_score = len(re.findall(r"\d{1,3}\s*[-~–—]\s*\d{1,3}|\b\d{1,3}\b", combined_norm))
    hit_z = 2 if re.search(r"\b지\b", combined_norm) else 0
    hit_cols = 2 if ("교" in combined_norm and "지" in combined_norm) else 0
    hit_title = 4 if ("차시" in combined_norm and ("단원" in combined_norm or "지도" in combined_norm)) else 0
    return hit_cols + hit_z + hit_title + page_score // 2

def detect_guide_z_column(table):
    if not table: return None
    z_patterns = ("지", "지도서")
    col_scores = defaultdict(int)
    for row in table[:8]:
        for idx in range(len(row)):
            cell = normalize_space(row[idx] or "")
            if cell in z_patterns: col_scores[idx] += 4
            elif any(p in cell for p in z_patterns) and len(cell) <= 6: col_scores[idx] += 2
    if not col_scores: return None
    return max(col_scores.items(), key=lambda x: x[1])[0]

def extract_tables_from_page(page):
    tables = []
    try:
        for t in page.find_tables()[:5]:
            ext = t.extract()
            if ext: tables.append(ext)
    except: pass
    if not tables:
        try:
            for t in (page.extract_tables() or [])[:5]:
                if t: tables.append(t)
        except: pass
    return tables

def build_groups_from_tables(tables, z_col_opt):
    groups, current_group_key = {}, None
    for table in tables:
        if not table: continue
        z_col = z_col_opt if z_col_opt is not None else detect_guide_z_column(table)
        if z_col is None:
            z_col = max((len(r) for r in table if r), default=0) - 1
            if z_col < 0: continue

        for row in table:
            if not row: continue
            left_cell = normalize_space(row[0] if len(row) > 0 and row[0] is not None else "")
            z_cell = normalize_space(row[z_col] if len(row) > z_col and row[z_col] is not None else "")
            
            if not left_cell and not z_cell: continue
            if left_cell in ("교", "지", "차시", "단원"): continue
            if left_cell: current_group_key = left_cell
            if not current_group_key or not z_cell: continue

            page_ranges = parse_page_ranges(z_cell)
            if not page_ranges: continue

            if current_group_key not in groups:
                groups[current_group_key] = {"title": current_group_key, "page_ranges": [], "row_evidence": 0}
            groups[current_group_key]["page_ranges"].extend(page_ranges)
            groups[current_group_key]["row_evidence"] += 1

    out = []
    for key, g in groups.items():
        all_starts = [s for s, e in g["page_ranges"]]
        all_ends = [e for s, e in g["page_ranges"]]
        if all_starts and all_ends:
            out.append({
                "title": key, "start_page": min(all_starts), "end_page": max(all_ends),
                "row_evidence": g["row_evidence"]
            })
    out.sort(key=lambda x: (x["start_page"], x["title"]))
    return out


# ---------------------------------------------------------
# 2. Supabase 업로드 및 매핑
# ---------------------------------------------------------

def supabase_get(path):
    url = f"{SUPABASE_URL}/rest/v1{path}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = requests.get(url, headers=headers, verify=False)
    return r.json() if r.status_code == 200 else []

def supabase_patch(table, row_id, payload):
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{row_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    requests.patch(url, headers=headers, json=payload, verify=False)

def upload_file_to_supabase(local_path, storage_path):
    # bucket: teacher_guides
    url = f"{SUPABASE_URL}/storage/v1/object/teacher_guides/{storage_path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/pdf"
    }
    with open(local_path, "rb") as f:
        r = requests.post(url, headers=headers, data=f, verify=False)
    
    # If already exists, we will update it or ignore. It returns 400 if it exists.
    if r.status_code in (400, 409):
        # try overwrite/put
        requests.put(url, headers=headers, data=open(local_path, "rb"), verify=False)
        
    return f"{SUPABASE_URL}/storage/v1/object/public/teacher_guides/{storage_path}"

# ---------------------------------------------------------
# 3. 메인 실행
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="지도서 파싱 및 Supabase 업로드")
    parser.add_argument("--pdf", required=True, help="입력 PDF 경로")
    parser.add_argument("--subject", required=True, help="과목명 (예: 과학)")
    parser.add_argument("--scan-pages", default=60, type=int)
    parser.add_argument("--page-offset", default=0, type=int, help="오프셋 (PDF쪽수와 실제숫자 차이)")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        sys.exit(f"❌ PDF 파일이 없습니다: {pdf_path}")

    # 1. 대상 과목 찾기
    print(f"🔍 Supabase에서 '{args.subject}' 과목 검색 중...")
    subjects = supabase_get(f"/subjects?name=eq.{args.subject}&select=id,name")
    if not subjects:
        sys.exit(f"❌ DB에 '{args.subject}' 과목이 없습니다. Dashboard에서 먼저 생성하세요.")
    subject_id = subjects[0]["id"]

    # 2. 테이블 파싱
    print(f"\n📑 '{pdf_path.name}'에서 '단원의 지도 계획' 찾는 중...")
    candidates = []
    with pdfplumber.open(pdf_path) as doc:
        for i in range(min(args.scan_pages, len(doc.pages))):
            text = (doc.pages[i].extract_text() or "").lower()
            if "단원의 지도 계획" in text or "주제의 지도 계획" in text:
                candidates.append(i)
        
        if not candidates:
            sys.exit("❌ '단원의 지도 계획' 표를 찾지 못했습니다.")

        tables = []
        for c in candidates:
            tables.extend(extract_tables_from_page(doc.pages[c]))
        
        scored = [(score_table_for_plan(t), t) for t in tables]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_tables = [t for s, t in scored[:5]]

        groups = build_groups_from_tables(top_tables, None)

    if not groups:
        sys.exit("❌ 표는 찾았으나 페이지 범위를 분석하지 못했습니다.")

    # 3. PDF 자르기 및 업로드 준비
    splits_dir = Path("scripts/guide_splits")
    splits_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    print(f"\n🚀 총 {len(groups)}개 소단원 PDF 분할 및 Supabase 업로드 시작...")
    
    # 해당 과목의 Lessons 가져와서 유사도 매칭 수행 준비
    db_lessons = supabase_get(f"/lessons?subject_id=eq.{subject_id}&select=id,title")

    for i, g in enumerate(groups, 1):
        s_page = max(1, g["start_page"] + args.page_offset)
        e_page = min(total_pages, g["end_page"] + args.page_offset)
        if e_page < s_page: s_page, e_page = e_page, s_page
        
        # PDF 분할 저장
        writer = PdfWriter()
        for p in range(s_page - 1, e_page):
            writer.add_page(reader.pages[p])
            
        clean_title = sanitize_filename_part(g["title"])
        local_filename = f"{args.subject}_{i:02d}_{clean_title[:30]}.pdf"
        local_path = splits_dir / local_filename
        with open(local_path, "wb") as f:
            writer.write(f)

        # Supabase Storage 업로드
        storage_path = f"{args.subject}/{local_filename}"
        public_url = upload_file_to_supabase(local_path, storage_path)

        # DB 매핑 (정교한 매핑은 Dashboard UI에서 하도록 하거나, 단순 매칭)
        # title에 clean_title의 일부가 포함된 최신 Lesson 찾기
        matched_id = None
        for l in db_lessons:
            if l["title"] and (clean_title in sanitize_filename_part(l["title"]) or sanitize_filename_part(l["title"]) in clean_title):
                matched_id = l["id"]
                break

        if matched_id:
            supabase_patch("lessons", matched_id, {
                "pdf_path": public_url,
                "start_page": s_page,
                "end_page": e_page
            })
            print(f"  ✅ [매핑됨] {clean_title} -> {public_url}")
        else:
            print(f"  ⚠️ [업로드됨(매핑실패)] {clean_title} -> {public_url}")

if __name__ == "__main__":
    main()
