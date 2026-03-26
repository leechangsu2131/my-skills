import os
import shutil
import re

pdf_dir = r"c:\Users\user\Desktop\cd\국어\assets\data\학습_자료\국어3-1지도서\pdf"
target_dir = r"c:\Users\user\Desktop\cd\지도서"

if not os.path.exists(target_dir):
    os.makedirs(target_dir)

def get_korean_unit(filename):
    if filename == "국어3-1지도서_1.pdf":
        return "총론"
    elif filename == "국어3-1지도서_3.pdf":
        return "부록"
    m = re.search(r'국어3-1지도서_2_(.+)\.pdf', filename)
    if m:
        unit = m.group(1)
        if unit.isdigit():
            return f"{unit}단원"
        else:
            return f"{unit} 단원"
    return None

copied_count = 0
for file in os.listdir(pdf_dir):
    if file.endswith(".pdf"):
        unit = get_korean_unit(file)
        if unit:
            unit_dir = os.path.join(target_dir, unit)
            if not os.path.exists(unit_dir):
                os.makedirs(unit_dir)
            src_path = os.path.join(pdf_dir, file)
            dest_path = os.path.join(unit_dir, file)
            shutil.copy2(src_path, dest_path)
            print(f"Copied {file} to {unit}")
            copied_count += 1

print(f"Total Korean files copied: {copied_count}")
