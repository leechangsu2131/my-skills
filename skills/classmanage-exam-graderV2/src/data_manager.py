import os
import cv2

def save_to_yolo_format(image_path: str, bboxes: list[dict], output_dir: str):
    """
    검수가 완료된 BBox 리스트를 YOLO 형식(class_id x_center y_center width height)으로 
    변환하여 .txt 파일로 저장합니다. 
    값은 이미지 해상도 대비 0~1 사이의 정규화(Normalized) 값이어야 합니다.
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Cannot read image {image_path} for YOLO conversion.")
        return
        
    img_height, img_width = img.shape[:2]
    
    base_name = os.path.basename(image_path)
    file_name, _ = os.path.splitext(base_name)
    txt_path = os.path.join(output_dir, f"{file_name}.txt")
    
    # 답안 영역(Answer Box)은 단일 클래스이므로 0으로 통일
    CLASS_ID = 0
    
    yolo_lines = []
    for box in bboxes:
        x_min = box['x_min']
        y_min = box['y_min']
        x_max = box['x_max']
        y_max = box['y_max']
        
        # 1. 픽셀 단위 너비(width)와 높이(height) 계산
        box_width = x_max - x_min
        box_height = y_max - y_min
        
        # 2. 중심(Center) 좌표 계산
        x_center = x_min + (box_width / 2.0)
        y_center = y_min + (box_height / 2.0)
        
        # 3. 이미지 크기 대비 정규화(Normalization, 0.0 ~ 1.0)
        norm_x_center = x_center / img_width
        norm_y_center = y_center / img_height
        norm_width = box_width / img_width
        norm_height = box_height / img_height
        
        # 소수점 6자리까지 포맷팅
        yolo_line = f"{CLASS_ID} {norm_x_center:.6f} {norm_y_center:.6f} {norm_width:.6f} {norm_height:.6f}"
        yolo_lines.append(yolo_line)
        
    os.makedirs(output_dir, exist_ok=True)
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(yolo_lines))
        
    print(f"✅ YOLO 포맷 저장 완료: {txt_path} ({len(bboxes)} boxes)")
