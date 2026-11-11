from pathlib import Path
import re
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
folder=Path(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\scratch\picturebook-pdf-text")
for f in folder.glob("*.txt"):
    raw=f.read_text(encoding="utf-8")
    print("\n###",f.name)
    pages=re.split(r"--- PAGE (\d+) ---\n",raw)
    for i in range(1,len(pages),2):
        page=int(pages[i]); txt=pages[i+1]
        lines=[re.sub(r"\s+"," ",x).strip() for x in txt.splitlines() if x.strip()]
        if "창작 수업 계획서" in f.name:
            print(f"PAGE {page}: "+" | ".join(lines[:22]))
        elif "정리하기" in f.name:
            if any(k in txt for k in ["차시", "여섯 조각", "은유", "스토리보드", "재료", "만들기", "작가의 말", "작가의말"]):
                print(f"PAGE {page}: "+" | ".join(lines[:12]))
