import os
import json
from ui import review_and_edit_bboxes
from data_manager import save_to_yolo_format
from aligner import align_image
from pdf_handler import convert_pdfs_to_images

def load_bboxes_from_json(json_path: str) -> list[dict]:
    """로컬 JSON 파일에서 BBox 데이터를 읽어옵니다."""
    if not os.path.exists(json_path):
        return []
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            bboxes = json.load(f)
            return bboxes
    except Exception as e:
        print(f"JSON 파싱 에러 ({json_path}): {e}")
        return []

def batch_align_images(raw_dir: str, template_path: str, aligned_dir: str):
    """raw_images 폴더의 모든 이미지를 템플릿에 맞춰 일괄 정렬합니다."""
    print("\n[🚀 Phase 0: 일괄 이미지 정렬(Batch Alignment) 시작]")
    images = [f for f in os.listdir(raw_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg')) and f.lower() != 'blank.jpg']
    
    if not images:
        print("정렬할 이미지가 없습니다.")
        return
        
    for image_name in images:
        image_path = os.path.join(raw_dir, image_name)
        aligned_image_path = os.path.join(aligned_dir, f"aligned_{image_name}")
        
        print(f"-> 정렬 시도: {image_name}")
        if align_image(image_path, template_path, aligned_image_path):
            print(f"   성공: aligned_{image_name}")
        else:
            print(f"   실패: {image_name} (건너뜀)")

def process_single_aligned_image(aligned_image_path: str, json_dir: str, label_output_dir: str):
    """정렬된 이미지 하나에 대해 JSON 검수 및 YOLO 포맷 저장을 수행합니다."""
    base_name = os.path.basename(aligned_image_path)
    # 'aligned_exam_01_page_01.jpg' -> 원본 이름인 'exam_01_page_01.json' 찾기
    original_name = base_name.replace("aligned_", "")
    file_name, _ = os.path.splitext(original_name)
    
    json_path = os.path.join(json_dir, f"{file_name}.json")
    
    print(f"\n[📝 Phase 1 검수: {base_name}]")
    predicted_bboxes = load_bboxes_from_json(json_path)
    
    if not predicted_bboxes:
        print(f"-> 💡 '{file_name}.json' 파일이 없습니다. 빈 화면에서 수동으로 그릴 수 있습니다.")
    else:
        print(f"-> {len(predicted_bboxes)}개의 BBox를 성공적으로 불러왔습니다.")
    
    print("-> OpenCV 검수 툴을 엽니다. (박스 수정 후 's' 저장, 'q' 취소/넘기기)")
    final_bboxes = review_and_edit_bboxes(aligned_image_path, predicted_bboxes)
    
    if final_bboxes:
        save_to_yolo_format(aligned_image_path, final_bboxes, label_output_dir)
    else:
        print("-> 저장된 박스가 없습니다.")

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PDF_DIR = os.path.join(BASE_DIR, "data", "raw_pdfs")
    RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw_images")
    ALIGNED_DATA_DIR = os.path.join(BASE_DIR, "data", "aligned_images")
    JSON_DIR = os.path.join(BASE_DIR, "data", "json_labels")
    LABEL_DIR = os.path.join(BASE_DIR, "data", "yolo_labels")
    TEMPLATE_PATH = os.path.join(BASE_DIR, "data", "template", "blank.jpg")
    
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    os.makedirs(ALIGNED_DATA_DIR, exist_ok=True)
    os.makedirs(JSON_DIR, exist_ok=True)
    os.makedirs(LABEL_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(TEMPLATE_PATH), exist_ok=True)
    
    if not os.path.exists(TEMPLATE_PATH):
        print(f"🚨 기준이 될 빈 시험지 템플릿 '{TEMPLATE_PATH}' 파일이 필요합니다. 먼저 추가해주세요.")
        exit(1)
        
    # 1. PDF -> Image 변환
    print(f"🔍 PDF 디렉토리({PDF_DIR})를 확인합니다...")
    converted_count = convert_pdfs_to_images(PDF_DIR, RAW_DATA_DIR, dpi=300)
    if converted_count > 0:
        print(f"✅ 총 {converted_count}장의 이미지가 PDF에서 변환되어 raw_images에 저장되었습니다.")
        
    # 2. 이미지 일괄 정렬 (Batch Alignment)
    batch_align_images(RAW_DATA_DIR, TEMPLATE_PATH, ALIGNED_DATA_DIR)
    
    # 3. 정렬된 이미지를 순회하며 수동 검수 (Phase 1)
    aligned_images = [f for f in os.listdir(ALIGNED_DATA_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if aligned_images:
        for img_name in aligned_images:
            aligned_path = os.path.join(ALIGNED_DATA_DIR, img_name)
            process_single_aligned_image(aligned_path, JSON_DIR, LABEL_DIR)
        print("\n[🎉 모든 파일 처리 및 검수 완료!]")
    else:
        print("\n🚨 정렬된 이미지가 없습니다. 변환된 원본 이미지가 있는지 확인해주세요.")
