from pathlib import Path
from docx import Document

downloads = Path(r"C:\Users\user\Downloads")
targets = [
    downloads / "\uC131\uC7A5\uBC1C\uD45C\uD68C_\uD559\uBD80\uBAA8\uC548\uB0B4\uBB38.docx",
    downloads / "\uC131\uC7A5\uBC1C\uD45C\uD68C_\uAD50\uC0AC\uBC1C\uBB38\uC790\uB8CC (1).docx",
    downloads / "\uC131\uC7A5\uBC1C\uD45C\uD68C_\uC791\uC131\uC608\uC2DC.docx",
    downloads / "\uC131\uC7A5\uBC1C\uD45C\uD68C\uACC4\uD68D\uC11C_\uBC1C\uD45C\uC900\uBE44 (1).docx",
]
chunks = []
for path in targets:
    doc = Document(path)
    chunks.append(f"===== {path.name} =====")
    chunks.extend(p.text for p in doc.paragraphs if p.text.strip())
    for i, table in enumerate(doc.tables, 1):
        chunks.append(f"[TABLE {i}]")
        for row in table.rows:
            chunks.append(" | ".join(cell.text.replace("\n", " / ") for cell in row.cells))
out = Path(r"C:\Users\user\.gemini\antigravity\scratch\repos\my-skills\scratch\growth-docs-extracted.txt")
out.write_text("\n".join(chunks), encoding="utf-8")
print(out)
