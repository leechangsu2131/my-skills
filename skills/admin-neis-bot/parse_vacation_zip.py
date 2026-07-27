#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse docx using zipfile + xml (no external dependencies)"""
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def main():
    docx_path = Path(__file__).parent / "data" / "26학년도 여름방학교육계획.docx"
    if not docx_path.exists():
        print(f"Error: {docx_path} does not exist.")
        return
    
    nsmap = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    
    with zipfile.ZipFile(docx_path) as z:
        with z.open('word/document.xml') as f:
            tree = ET.parse(f)
    
    root = tree.getroot()
    lines = []
    
    # Extract paragraphs
    for i, para in enumerate(root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')):
        texts = []
        for run in para.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r'):
            for t in run.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                if t.text:
                    texts.append(t.text)
        line = ''.join(texts).strip()
        if line:
            lines.append(f"[{i}] {line}")
    
    # Extract tables
    lines.append("\n---TABLES---")
    for ti, table in enumerate(root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl')):
        rows = list(table.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr'))
        lines.append(f"\nTable {ti}: {len(rows)} rows")
        for ri, row in enumerate(rows):
            cells = []
            for cell in row.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc'):
                cell_texts = []
                for t in cell.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                    if t.text:
                        cell_texts.append(t.text)
                cells.append(' '.join(cell_texts))
            lines.append(f"  R{ri}: {cells}")
    
    out_file = Path(__file__).parent / "data" / "parsed_vacation_plan.txt"
    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(lines)} lines to {out_file}")

if __name__ == "__main__":
    main()
