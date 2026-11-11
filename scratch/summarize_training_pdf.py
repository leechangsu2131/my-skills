from pathlib import Path
import fitz, sys, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
src=Path(r"C:\Users\user\OneDrive - gyo6.net\20. 연수\2020 그림책 이현아")
for filename in ["그림책 연수_교안(합본).pdf", "정리하기_합본.pdf"]:
    doc=fitz.open(src/filename)
    print("\n###", filename, "pages",len(doc))
    for n,p in enumerate(doc):
        lines=[re.sub(r"\s+"," ",x).strip() for x in p.get_text().splitlines() if x.strip()]
        hits=[x for x in lines if re.match(r"^(\d{1,2}[.)]|\d{1,2}\s|[가-힣].{1,30}(차시|이야기|표현|책|그림|쓰기|창작|읽기))",x)]
        if hits:
            print(f"{n+1}: "+" | ".join(hits[:8]))
