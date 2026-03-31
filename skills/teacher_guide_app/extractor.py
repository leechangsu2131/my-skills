"""
PDF 추출기: 특정 페이지 범위를 추출해서 새 PDF로 저장
"""

import os
import subprocess
from pathlib import Path
from pypdf import PdfReader, PdfWriter


class PDFExtractor:
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            app_dir = Path(__file__).parent
            output_dir = app_dir / "output"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract(self, pdf_path: str, pages: list, output_name: str) -> Path:
        """
        pages: [start, end] (1-based, inclusive)
        output_name: 저장할 파일명 (확장자 없이)
        """
        pdf_path = str(pdf_path)
        start_page, end_page = pages[0], pages[1]

        # 페이지 범위 보정
        reader = PdfReader(pdf_path)
        total = len(reader.pages)
        start_page = max(1, start_page)
        end_page = min(total, end_page)

        output_path = self.output_dir / f"{output_name}.pdf"

        writer = PdfWriter()
        for i in range(start_page - 1, end_page):
            writer.add_page(reader.pages[i])

        with open(output_path, "wb") as f:
            writer.write(f)

        return output_path

    def extract_lesson(self, pdf_path: str, lesson_info: dict) -> Path:
        """차시 정보를 받아서 해당 페이지 추출"""
        subject = lesson_info["subject"]
        grade = lesson_info["grade"]
        unit_no = lesson_info["unit_no"]
        lesson_no = lesson_info["lesson_no"]
        pages = lesson_info["pages"]

        # 파일명: 국어3_1단원_2차시
        output_name = f"{subject}{grade}학년_{unit_no}단원_{lesson_no}차시"
        return self.extract(pdf_path, pages, output_name)

    def open_file(self, path: Path):
        """OS에 맞게 파일 열기"""
        import platform
        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", str(path)])
            elif platform.system() == "Windows":
                os.startfile(str(path))
            else:  # Linux
                subprocess.run(["xdg-open", str(path)])
        except Exception as e:
            print(f"  파일을 열 수 없습니다: {e}")
