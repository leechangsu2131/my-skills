# -*- coding: utf-8 -*-
import re
from pathlib import Path

def parse_behavior_opinions(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # "## 행동특성 및 종합의견" 섹션 추출
    section = re.search(r'## 행동특성 및 종합의견.*?(?=## 창의적 체험활동|---|$)', content, re.DOTALL)
    if not section:
        return {}
        
    section_text = section.group(0)
    
    # **번호. 이름** \n 평어내용
    pattern = re.compile(r'\*\*\d+\.\s*([가-힣a-zA-Z\s]+)\*\*\n([^\n]+)')
    matches = pattern.findall(section_text)
    
    student_data = {}
    for name, text in matches:
        student_data[name.strip()] = text.strip()
        
    return student_data

file_path = r"C:\Users\lee21\Documents\GitHub"  # placeholder, will use absolute path
# 실제 경로
real_path = r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\classmanage-evaluate-to-neis\data\2026_1학기_행동특성_창체_수정.md"

data = parse_behavior_opinions(real_path)
print(f"파싱 성공 학생 수: {len(data)}명")
for name, text in list(data.items())[:5]:
    print(f"- {name}: {text[:60]}...")
