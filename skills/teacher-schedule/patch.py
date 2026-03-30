import sys
import os
import re

with open('map_guides_to_sheet.py', 'r', encoding='utf-8') as f:
    content = f.read()

chunk1 = '''    # 매체 단원 (10차시)
    for i in range(1, 11):
        rows.append({
            "수업내용": f"매체 단원 {i}차시",
            "과목": "국어",
            "대단원": "매체 단원",
            "소단원": "",
            "차시": str(i),
            "계획일": "",
            "실행여부": False,
            "pdf파일": "",
            "시작페이지": "",
            "끝페이지": "",
            "비고": "",
        })

    return rows'''

replacement1 = chunk1 + '''

# ══════════════════════════════════════════════════════════
#  범용 데이터 생성 (정규식 기본 추출)
# ══════════════════════════════════════════════════════════
def extract_general_titles(pdf_path):
    if not os.path.exists(pdf_path):
        return {}

    doc = fitz.open(pdf_path)
    titles = {}
    
    lesson_pattern = re.compile(r'(?:차시|단원|lesson|unit)\s*(\d+)', re.IGNORECASE)
    
    for page_num in range(min(5, len(doc))):
        text = doc[page_num].get_text()
        lines = [l.strip() for l in text.split('\\n') if l.strip()]
        
        for i, line in enumerate(lines):
            m = lesson_pattern.search(line)
            if m:
                lesson_num = int(m.group(1))
                if lesson_num not in titles:
                    for j in range(i + 1, min(i + 4, len(lines))):
                        cand = lines[j]
                        if cand.startswith('•') or cand.startswith('·'):
                            cand = cand.lstrip('•·\\t ')
                        if len(cand) > 2 and not cand.isdigit():
                            titles[lesson_num] = cand[:50]
                            break

    doc.close()
    return titles


def generate_general_data(subject_name, prefix, max_unit=5):
    rows = []
    
    for unit_num in range(1, max_unit + 1):
        candidates = [
            f"{prefix}3_{unit_num}_1_지도서.pdf",
            f"{prefix}3-1지도서_{unit_num}.pdf",
            f"{prefix}_{unit_num}단원지도서.pdf",
            f"{prefix}3-1_{unit_num}단원.pdf"
        ]
        
        pdf_path = None
        for cand in candidates:
            p = os.path.join(GUIDE_DIR, cand)
            if os.path.exists(p):
                pdf_path = p
                break
                
        titles = extract_general_titles(pdf_path) if pdf_path else {}
        unit_name = f"{unit_num}단원"
        
        max_lessons = max(titles.keys()) if titles else 3
        
        for lesson_num in range(1, max_lessons + 1):
            title = titles.get(lesson_num, f"{unit_name} {lesson_num}차시")
            rows.append({
                "수업내용": title,
                "과목": subject_name,
                "대단원": unit_name,
                "소단원": "",
                "차시": str(lesson_num),
                "계획일": "",
                "실행여부": False,
                "pdf파일": "",
                "시작페이지": "",
                "끝페이지": "",
                "비고": "",
            })
            
    return rows
'''

# Replace chunk1
# normalize line endings for match
normalized_content = content.replace('\r\n', '\n')
chunk1_norm = chunk1.replace('\r\n', '\n')
replacement1_norm = replacement1.replace('\r\n', '\n')

if chunk1_norm in normalized_content:
    normalized_content = normalized_content.replace(chunk1_norm, replacement1_norm)
else:
    print("Could not find chunk1")
    sys.exit(1)

chunk2 = '''    all_rows = korean_rows + moral_rows

    if not args.upload and not args.cleanup:'''

replacement2 = '''    # 3. 범용 과목 데이터 생성 (수학, 사회, 과학)
    print(f"\\n[3/4] 범용 데이터 생성 중 (수학, 사회, 과학)...")
    math_rows = generate_general_data("수학", "수학")
    social_rows = generate_general_data("사회", "사회")
    science_rows = generate_general_data("과학", "과학")
    general_rows = math_rows + social_rows + science_rows
    print(f"  기타 {len(general_rows)}행 생성됨")

    all_rows = korean_rows + moral_rows + general_rows

    if not args.upload and not args.cleanup:'''

chunk2_norm = chunk2.replace('\r\n', '\n')
replacement2_norm = replacement2.replace('\r\n', '\n')

if chunk2_norm in normalized_content:
    normalized_content = normalized_content.replace(chunk2_norm, replacement2_norm)
else:
    print("Could not find chunk2")
    sys.exit(1)

with open('map_guides_to_sheet.py', 'w', encoding='utf-8') as f:
    f.write(normalized_content)
    
print("Patch successful!")
