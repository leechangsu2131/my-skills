import docx
from pathlib import Path
import re

def main():
    docx_path = Path("skills/classmanage-evaluate-to-neis/data/2026학년도 3학년 1학기 행동특성 및 종합의견(수정본).docx")
    doc = docx.Document(docx_path)
    
    name_pattern = re.compile(r"^(\d+)\.\s*([^\n]+)$")
    
    for idx, p in enumerate(doc.paragraphs[:5]):
        text = p.text.strip()
        print(f"Paragraph {idx}: text={repr(text)}")
        m = name_pattern.match(text)
        print(f"  Match: {m}")
        if m:
            print(f"  Groups: {m.groups()}")

if __name__ == "__main__":
    main()
