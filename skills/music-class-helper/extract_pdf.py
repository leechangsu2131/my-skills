import os
import re
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF (fitz) is not installed. Please install it using: pip install pymupdf")
    sys.exit(1)


def parse_exact_title(exact_title):
    match = re.search(r"\[(.*?)\]\s*(.*)", exact_title or "")
    if match:
        lesson_label = match.group(1).strip()
        topic = match.group(2).strip()
        return lesson_label, topic
    return "", (exact_title or "").strip()


def normalize_unit_label(unit_text):
    normalized = " ".join((unit_text or "").split())
    if not normalized:
        return ""

    numbers = re.findall(r"\d+", normalized)
    if numbers:
        return f"{numbers[0]}단원"
    return normalized


def sanitize_filename_part(value):
    cleaned = " ".join((value or "").split())
    cleaned = re.sub(r'[<>:"/\\\\|?*]', "_", cleaned)
    cleaned = cleaned.replace("\n", " ").replace("\r", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
    return cleaned


def build_output_filename(pdf_path, exact_title, unit_text=None):
    lesson_label, topic = parse_exact_title(exact_title)
    base_name = os.path.basename(pdf_path)
    name, ext = os.path.splitext(base_name)

    parts = [name]
    unit_label = normalize_unit_label(unit_text)
    if unit_label:
        parts.append(unit_label)
    if lesson_label:
        parts.append(lesson_label)
    if topic:
        parts.append(topic)
    parts.append("추출본")

    safe_parts = [sanitize_filename_part(part) for part in parts if sanitize_filename_part(part)]
    return "_".join(safe_parts) + ext


def do_extract(pdf_path, exact_title, unit_text=None):
    """
    Search the PDF for the matching lesson topic and save a short extracted PDF.
    """
    lesson_label, topic = parse_exact_title(exact_title)
    search_target = re.sub(r"[^\w]", "", topic)

    print("\n[STEP 3] PDF에서 해당 차시를 추출합니다.")
    print(f"[{pdf_path}]에서 '{topic or exact_title}' 관련 실제 수업 페이지를 찾는 중...")

    try:
        doc = fitz.open(pdf_path)
        start_page = -1

        for page_num in range(len(doc)):
            page_text = doc.load_page(page_num).get_text()
            norm_text = re.sub(r"[^\w]", "", page_text)

            if search_target and search_target not in norm_text:
                continue

            header_text = norm_text[:200]
            is_plan = "계획" in header_text
            is_appendix = "부록" in header_text
            is_toc = "목차" in header_text

            if is_plan or is_appendix or is_toc:
                continue

            start_page = page_num
            print(f"  -> {start_page + 1} 페이지에서 실제 수업 내용을 찾았습니다.")
            break

        if start_page == -1:
            label = topic or exact_title
            print(f"\n[!] PDF 안에서 '{label}' 내용을 찾지 못했습니다.")
            return False

        end_page = min(start_page + 3, len(doc) - 1)

        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start_page, to_page=end_page)

        dir_name = os.path.dirname(pdf_path)
        out_filename = build_output_filename(pdf_path, exact_title, unit_text=unit_text)
        out_path = os.path.join(dir_name, out_filename)

        new_doc.save(out_path)
        new_doc.close()
        doc.close()

        print("\n" + "=" * 60)
        print("[OK] PDF 추출 완료")
        print(f"  - 추출 페이지: {start_page + 1} ~ {end_page + 1}")
        if unit_text or lesson_label:
            print(
                f"  - 파일명 정보: {normalize_unit_label(unit_text) or '단원 미지정'} / "
                f"{lesson_label or '차시 미지정'}"
            )
        print(f"  - 저장 위치: {out_path}")
        print("=" * 60)

        try:
            os.startfile(out_path)
        except Exception:
            pass

        return True

    except Exception as error:
        print(f"PDF 처리 오류: {error}")
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_pdf.py <pdf_path> <exact_title> [unit_text]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    exact_title = sys.argv[2]
    unit_text = sys.argv[3] if len(sys.argv) > 3 else None

    if not os.path.exists(pdf_path):
        print(f"\n[!] 파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)

    do_extract(pdf_path, exact_title, unit_text=unit_text)


if __name__ == "__main__":
    main()
