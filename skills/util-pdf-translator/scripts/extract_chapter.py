#!/usr/bin/env python3
"""
extract_chapter.py - PDF에서 챕터별 텍스트를 추출합니다.

사용법:
  python extract_chapter.py --chapter 1       # 챕터 1 추출
  python extract_chapter.py --chapter all     # 전체 챕터 추출
"""

import json
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TOC_PATH = Path(__file__).parent / "toc.json"
OUTPUT_DIR = Path(__file__).parent / "output"


def load_toc() -> list[dict]:
    if not TOC_PATH.exists():
        print("❌ toc.json이 없습니다. 먼저 01_setup_toc.py를 실행하세요.")
        sys.exit(1)
    with open(TOC_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_chapter_text(pdf_path: str, start_page: int, end_page: int) -> str:
    """페이지 범위로 텍스트를 추출합니다. (1-indexed)"""
    try:
        import fitz
    except ImportError:
        print("❌ PyMuPDF가 설치되어 있지 않습니다: pip install PyMuPDF")
        sys.exit(1)

    doc = fitz.open(pdf_path)
    texts = []
    for page_num in range(start_page - 1, min(end_page, len(doc))):
        page = doc[page_num]
        texts.append(page.get_text("text"))
    doc.close()
    return "\n".join(texts)


def save_chapter(chapter_num: int, text: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"chapter_{str(chapter_num).zfill(2)}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path


def process_chapter(chapter: dict, pdf_path: str) -> None:
    num = chapter["chapter"]
    title = chapter["title"]
    start = chapter["start_page"]
    end = chapter.get("end_page") or start + 50

    print(f"  📄 챕터 {num} '{title}' (페이지 {start}~{end}) 추출 중...")
    text = extract_chapter_text(pdf_path, start, end)
    out_path = save_chapter(num, text)
    print(f"     ✅ 저장: {out_path} ({len(text)}자)")


def main():
    parser = argparse.ArgumentParser(description="PDF 챕터 텍스트 추출")
    parser.add_argument("--chapter", required=True,
                        help="추출할 챕터 번호 (예: 1) 또는 all")
    parser.add_argument("--pdf", type=str, help="PDF 경로 (.env의 PDF_PATH 대체)")
    args = parser.parse_args()

    pdf_path = args.pdf or os.getenv("PDF_PATH", "")
    if not pdf_path or not Path(pdf_path).exists():
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        print("   .env의 PDF_PATH 또는 --pdf 옵션을 설정하세요.")
        sys.exit(1)

    toc = load_toc()

    if args.chapter.lower() == "all":
        print(f"\n📚 전체 {len(toc)}개 챕터 추출 시작...")
        for ch in toc:
            process_chapter(ch, pdf_path)
        print("\n✅ 전체 챕터 추출 완료!")
    else:
        chapter_num = int(args.chapter)
        chapter = next((c for c in toc if c["chapter"] == chapter_num), None)
        if not chapter:
            print(f"❌ 챕터 {chapter_num}을 찾을 수 없습니다.")
            sys.exit(1)
        process_chapter(chapter, pdf_path)


if __name__ == "__main__":
    main()
