import pdfplumber
import os

pdf_files = [
    r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade\data\report\033500\DS투자증권_동성화인텍_260519.pdf",
    r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade\data\report\033500\미래에셋증권_동성화인텍_260327.pdf",
    r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade\data\report\033500\bbs_1774910948778.pdf"
]

output_path = r"C:\Users\lee21\.gemini\antigravity\scratch\my-skills\skills\personal-record-trade\data\report\033500\extracted_metrics.txt"

keywords = ["EPS", "PER", "ROIC", "영업이익률", "OP", "PBR", "ROE"]

with open(output_path, "w", encoding="utf-8") as out_f:
    for pdf_path in pdf_files:
        if not os.path.exists(pdf_path):
            out_f.write(f"File not found: {pdf_path}\n\n")
            continue
            
        out_f.write(f"--- Analysis for: {os.path.basename(pdf_path)} ---\n")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        for i, line in enumerate(lines):
                            if any(k.lower() in line.lower() for k in keywords):
                                # Print surrounding lines for context
                                start = max(0, i - 1)
                                end = min(len(lines), i + 3)
                                out_f.write(f"Page {page_num+1}:\n")
                                for j in range(start, end):
                                    out_f.write(f"  {lines[j]}\n")
                                out_f.write("-" * 20 + "\n")
                    
                    # Extract tables for better structure
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            row_text = " | ".join(str(cell).strip() for cell in row if cell)
                            if any(k.lower() in row_text.lower() for k in keywords):
                                out_f.write(f"Table Page {page_num+1}: {row_text}\n")
        except Exception as e:
            out_f.write(f"Error parsing PDF: {e}\n")
        
        out_f.write("\n\n")
        
print("Extraction complete.")
