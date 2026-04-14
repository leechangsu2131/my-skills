import os
import shutil
import re

base_dir = r"c:\Users\user\Desktop\cd"
target_dir = os.path.join(base_dir, "지도서")

if not os.path.exists(target_dir):
    os.makedirs(target_dir)

def get_unit_from_filename(filename, rel_path):
    # for 도덕
    if "도덕" in filename or "도덕" in rel_path:
        m = re.search(r'도덕3_(\d+)_', filename)
        if m:
            return m.group(1) + "단원"
        m2 = re.search(r'ch(\d+)', rel_path)
        if m2:
            return m2.group(1) + "단원"

    # for 국어
    if "국어" in filename or "국어" in rel_path:
        m = re.search(r'국어3-1지도서_(\d+)', filename)
        if m:
            return m.group(1) + "단원"
        m2 = re.search(r'(\d+)단원', rel_path)
        if m2:
            return m2.group(1) + "단원"
            
    return "기타기록"

copied_count = 0
for root, dirs, files in os.walk(base_dir):
    # Skip target_dir
    if target_dir in root:
        continue

    for file in files:
        if "지도서" in file and file.lower().endswith(".pdf"):
            rel_path = os.path.relpath(os.path.join(root, file), base_dir)
            if "국어" in file or "도덕" in file or "국어" in rel_path or "도덕" in rel_path:
                filepath = os.path.join(root, file)
                unit = get_unit_from_filename(file, rel_path)
                
                unit_dir = os.path.join(target_dir, unit)
                if not os.path.exists(unit_dir):
                    os.makedirs(unit_dir)
                    
                dest_path = os.path.join(unit_dir, file)
                if not os.path.exists(dest_path):
                    shutil.copy2(filepath, dest_path)
                    print(f"Copied: {file} -> {unit}")
                    copied_count += 1

print(f"Total files copied: {copied_count}")
