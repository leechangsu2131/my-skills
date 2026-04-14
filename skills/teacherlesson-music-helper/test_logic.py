import fitz, re
import sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open(r"C:\Users\user\Downloads\music.pdf")
target = "길고짧은음높고낮은음"

print(f"Scanning for: {target}")
for p in range(len(doc)):
    page_text = doc[p].get_text()
    norm_text = re.sub(r"[^\w]", "", page_text)
    
    if target in norm_text:
        header_text = norm_text[:200]
        
        is_plan = "계획" in header_text
        is_appendix = "부록" in header_text
        is_toc = "차례" in header_text
        
        print(f"Page {p+1}: is_plan={is_plan}, is_appendix={is_appendix}, is_toc={is_toc}")
        
        if is_plan or is_appendix or is_toc:
            print("  -> SKIPPED due to header markers")
        else:
            print("  -> MATCH! This must be the actual lesson.")
            
