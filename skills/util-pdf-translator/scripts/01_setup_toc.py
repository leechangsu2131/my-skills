#!/usr/bin/env python3
"""
01_setup_toc.py - PDF 목차 생성 도구

디지털 목차가 없는 PDF에서 챕터 경계를 찾아 toc.json을 생성합니다.

사용법:
  python 01_setup_toc.py --auto            # PDF에서 챕터 헤딩 자동 감지
  python 01_setup_toc.py --manual          # 직접 목차 입력
  python 01_setup_toc.py --show            # 현재 toc.json 내용 출력
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TOC_PATH = Path(__file__).parent / "toc.json"

# 챕터 헤딩 감지 패턴
CHAPTER_PATTERNS = [
    r"^chapter\s+(\d+)",
    r"^챕터\s+(\d+)",
    r"^part\s+(\d+)",
    r"^(\d+)\.\s+[A-Z]",       # "1. Introduction"
    r"^section\s+(\d+)",
]


def detect_chapters_auto(pdf_path: str) -> list[dict]:
    """PDF에서 챕터 헤딩을 자동으로 감지합니다."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("❌ PyMuPDF가 설치되어 있지 않습니다. 먼저 설치하세요:")
        print("   pip install PyMuPDF")
        sys.exit(1)

    print(f"\n📄 PDF 분석 중: {pdf_path}")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"   총 페이지 수: {total_pages}")

    candidates = []
    for page_num in range(total_pages):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    font_size = span.get("size", 0)

                    # 폰트 크기가 크고(헤딩일 가능성), 패턴에 매칭되는 텍스트
                    if font_size >= 14:
                        for pattern in CHAPTER_PATTERNS:
                            if re.match(pattern, text, re.IGNORECASE):
                                candidates.append({
                                    "page": page_num + 1,  # 1-indexed
                                    "text": text,
                                    "font_size": round(font_size, 1)
                                })
                                break

    doc.close()
    return candidates


def save_toc(chapters: list[dict]) -> None:
    """챕터 목록을 toc.json으로 저장합니다."""
    with open(TOC_PATH, "w", encoding="utf-8") as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)
    print(f"\n✅ toc.json 저장 완료: {TOC_PATH}")


def load_toc() -> list[dict]:
    """toc.json을 불러옵니다."""
    if not TOC_PATH.exists():
        return []
    with open(TOC_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def show_toc() -> None:
    """현재 toc.json 내용을 출력합니다."""
    toc = load_toc()
    if not toc:
        print("⚠️  toc.json이 없거나 비어있습니다. 먼저 --auto 또는 --manual로 생성하세요.")
        return

    print("\n📚 현재 목차 (toc.json):")
    print(f"{'번호':>4}  {'제목':<35} {'시작':>6} {'끝':>6}")
    print("-" * 60)
    for ch in toc:
        end = ch.get("end_page", "?")
        print(f"{ch['chapter']:>4}  {ch['title']:<35} {ch['start_page']:>6} {str(end):>6}")


def auto_mode(pdf_path: str) -> None:
    """자동 감지 모드: PDF에서 챕터를 찾아 사용자에게 확인받고 저장합니다."""
    candidates = detect_chapters_auto(pdf_path)

    if not candidates:
        print("\n⚠️  자동 감지된 챕터가 없습니다.")
        print("   헤딩 폰트가 14pt 미만이거나 패턴이 다를 수 있습니다.")
        print("   --manual 모드로 직접 입력해 주세요.")
        return

    print(f"\n🔍 감지된 챕터 후보 {len(candidates)}개:")
    print(f"{'번호':>4}  {'텍스트':<40} {'페이지':>6} {'폰트크기':>8}")
    print("-" * 65)
    for i, c in enumerate(candidates):
        print(f"{i+1:>4}  {c['text']:<40} {c['page']:>6} {c['font_size']:>8}")

    print("\n각 항목을 챕터로 사용하겠습니까?")
    print("사용할 항목 번호를 쉼표로 입력하세요 (예: 1,3,5), 전체: all, 취소: skip")
    choice = input("선택: ").strip().lower()

    if choice == "skip":
        print("취소되었습니다.")
        return

    if choice == "all":
        selected = candidates
    else:
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
            selected = [candidates[i] for i in indices if 0 <= i < len(candidates)]
        except ValueError:
            print("❌ 올바른 번호를 입력해주세요.")
            return

    # end_page 계산 (다음 챕터 시작 - 1)
    import fitz
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    chapters = []
    for i, c in enumerate(selected):
        end_page = selected[i + 1]["page"] - 1 if i + 1 < len(selected) else total_pages
        chapters.append({
            "chapter": i + 1,
            "title": c["text"],
            "start_page": c["page"],
            "end_page": end_page
        })

    save_toc(chapters)
    show_toc()


def manual_mode() -> None:
    """수동 입력 모드: 사용자가 직접 목차를 입력합니다."""
    print("\n📝 수동 목차 입력 모드")
    print("책의 목차를 보면서 챕터별로 입력해주세요.")
    print("입력 완료 후 엔터 두 번으로 종료합니다.\n")

    pdf_path = os.getenv("PDF_PATH", "")
    if pdf_path and Path(pdf_path).exists():
        try:
            import fitz
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            print(f"   PDF 총 페이지: {total_pages}")
        except Exception:
            total_pages = None
    else:
        total_pages = None

    existing = load_toc()
    if existing:
        print(f"기존 toc.json이 있습니다 ({len(existing)}개 챕터).")
        ans = input("이어서 추가하겠습니까? (y/n): ").strip().lower()
        chapters = existing if ans == "y" else []
        start_num = (chapters[-1]["chapter"] + 1) if chapters else 1
    else:
        chapters = []
        start_num = 1

    chapter_num = start_num
    while True:
        print(f"\n--- 챕터 {chapter_num} ---")
        title = input("  제목 (빈칸 입력 시 종료): ").strip()
        if not title:
            break

        while True:
            try:
                start_page = int(input("  시작 페이지: ").strip())
                break
            except ValueError:
                print("  숫자를 입력해주세요.")

        # end_page는 나중에 계산하거나 직접 입력
        end_hint = f" (최대 {total_pages})" if total_pages else ""
        end_input = input(f"  끝 페이지{end_hint} (모르면 엔터): ").strip()
        end_page = int(end_input) if end_input.isdigit() else None

        chapters.append({
            "chapter": chapter_num,
            "title": title,
            "start_page": start_page,
            "end_page": end_page
        })
        chapter_num += 1

    if len(chapters) > len(existing if existing else []):
        # 끝 페이지 없는 항목 자동 계산
        for i in range(len(chapters)):
            if chapters[i].get("end_page") is None:
                if i + 1 < len(chapters):
                    chapters[i]["end_page"] = chapters[i + 1]["start_page"] - 1
                elif total_pages:
                    chapters[i]["end_page"] = total_pages

        save_toc(chapters)
        show_toc()
    else:
        print("변경사항이 없습니다.")


def main():
    parser = argparse.ArgumentParser(description="PDF 목차 생성 도구")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--auto", action="store_true", help="PDF에서 챕터 자동 감지")
    group.add_argument("--manual", action="store_true", help="직접 목차 입력")
    group.add_argument("--show", action="store_true", help="현재 목차 출력")
    parser.add_argument("--pdf", type=str, help="PDF 파일 경로 (--auto 모드에서 필요)")

    args = parser.parse_args()

    if args.show:
        show_toc()
    elif args.manual:
        manual_mode()
    elif args.auto:
        pdf_path = args.pdf or os.getenv("PDF_PATH", "")
        if not pdf_path:
            print("❌ PDF 경로가 필요합니다. --pdf 옵션 또는 .env의 PDF_PATH를 설정하세요.")
            sys.exit(1)
        if not Path(pdf_path).exists():
            print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
            sys.exit(1)
        auto_mode(pdf_path)


if __name__ == "__main__":
    main()
