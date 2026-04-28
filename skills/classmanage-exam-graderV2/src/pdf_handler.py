import os
import fitz  # PyMuPDF

def convert_pdfs_to_images(pdf_dir: str, image_output_dir: str, dpi: int = 300, cycle: int = None) -> int:
    """
    지정된 디렉토리의 모든 PDF 파일을 읽어와 각 페이지를 고화질 이미지(PNG)로 변환합니다.
    cycle이 주어지면 N장 단위로 학생을 분리하여 파일명을 부여합니다.
    반환값: 변환된 총 페이지(이미지) 수
    """
    if not os.path.exists(pdf_dir):
        return 0
        
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        return 0
        
    os.makedirs(image_output_dir, exist_ok=True)
    total_converted = 0
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_dir, pdf_file)
        base_name = os.path.splitext(pdf_file)[0]
        
        print(f"\n📄 PDF 변환 중: {pdf_file} ...")
        try:
            doc = fitz.open(pdf_path)
            # 해상도를 높이기 위한 매트릭스 설정 (DPI 300 수준: zoom_x, zoom_y = 300/72 ≈ 4.16)
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                if cycle is not None and cycle > 0:
                    stu_idx = (page_num // cycle) + 1
                    p_idx = (page_num % cycle) + 1
                    img_filename = f"{base_name}_stu{stu_idx:03d}_p{p_idx}.png"
                else:
                    img_filename = f"{base_name}_page_{page_num + 1:02d}.png"
                    
                img_path = os.path.join(image_output_dir, img_filename)
                
                pix.save(img_path)
                total_converted += 1
                print(f"  -> 저장 완료: {img_filename}")
                
            doc.close()
        except Exception as e:
            print(f"❌ PDF 처리 에러 ({pdf_file}): {e}")
            
    return total_converted
