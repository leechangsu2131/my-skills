from pathlib import Path
import fitz

src = Path(r"C:\Users\user\OneDrive - gyo6.net\20. 연수\2020 그림책 이현아")
dst = Path(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\scratch\picturebook-pdf-text")
dst.mkdir(parents=True, exist_ok=True)
for p in sorted(src.glob("*.pdf")):
    doc = fitz.open(p)
    text = "\n\n".join(f"--- PAGE {i+1} ---\n{page.get_text()}" for i, page in enumerate(doc))
    out = dst / (p.stem + ".txt")
    out.write_text(text, encoding="utf-8")
    print(f"{p.name}\tpages={len(doc)}\tchars={len(text)}\toutput={out}")
