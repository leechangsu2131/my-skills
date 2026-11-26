"""음악 지도서 PDF 에서 차시 이름이 나오는 쪽을 찾고, 쪽 머리말로 '진짜 수업 쪽'인지 가려 본다.

    python scan_music_pdf_header.py <지도서.pdf> [--target 찾을 말]

쪽 머리(앞 200자)에 '계획'·'부록'·'차례'가 있으면 수업 쪽이 아니라고 보고 건너뛴다.
--target 을 안 주면 예전에 쓰던 '길고짧은음높고낮은음'(띄어쓰기·기호를 뺀 글)으로 찾는다.
"""
import argparse
import pathlib
import re
import sys

DEFAULT_TARGET = "길고짧은음높고낮은음"


def header_flags(page_text: str) -> dict:
    """쪽 글에서 기호·띄어쓰기를 빼고 앞 200자에 계획/부록/차례가 있는지 본다."""
    header = re.sub(r"[^\w]", "", page_text)[:200]
    return {"is_plan": "계획" in header, "is_appendix": "부록" in header, "is_toc": "차례" in header}


def scan(doc, target: str):
    """(쪽 번호, 표시, 실제 수업 쪽인가) 목록. target 은 기호·띄어쓰기를 뺀 글이다."""
    found = []
    for p in range(len(doc)):
        norm_text = re.sub(r"[^\w]", "", doc[p].get_text())
        if target in norm_text:
            flags = header_flags(doc[p].get_text())
            found.append((p + 1, flags, not any(flags.values())))
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="음악 지도서 PDF 에서 차시 쪽을 찾고 머리말로 걸러 본다")
    ap.add_argument("pdf", nargs="?", help="지도서 PDF 파일 경로")
    ap.add_argument("--target", default=DEFAULT_TARGET, help="찾을 말(띄어쓰기·기호 없이). 기본: %(default)s")
    args = ap.parse_args(argv)
    if not args.pdf:
        ap.print_usage(sys.stderr)
        print("지도서 PDF 경로를 적어 주세요. 예: python scan_music_pdf_header.py 음악3_지도서.pdf", file=sys.stderr)
        return 2
    path = pathlib.Path(args.pdf)
    if not path.is_file():
        print(f"파일을 찾을 수 없어요: {path}", file=sys.stderr)
        return 2
    try:
        import fitz  # PyMuPDF — 도움말만 볼 때는 없어도 되게 여기서 불러온다
    except ImportError:
        print("PyMuPDF 가 없어요. pip install PyMuPDF", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    target = re.sub(r"[^\w]", "", args.target)
    print(f"Scanning for: {target}")
    with fitz.open(str(path)) as doc:
        for page_no, flags, is_lesson in scan(doc, target):
            print(f"Page {page_no}: is_plan={flags['is_plan']}, is_appendix={flags['is_appendix']}, is_toc={flags['is_toc']}")
            print("  -> MATCH! This must be the actual lesson." if is_lesson else "  -> SKIPPED due to header markers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
