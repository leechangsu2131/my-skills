import cv2
import numpy as np

from ocr.template_alignment import align_page_images
from ocr.template_alignment import transform_bbox


def test_align_page_images_returns_homography_for_translated_page() -> None:
    template = np.full((300, 300), 255, dtype=np.uint8)
    cv2.putText(template, "1", (40, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.8, 0, 3)
    cv2.rectangle(template, (70, 60), (240, 120), 0, 2)

    student = np.full((300, 300), 255, dtype=np.uint8)
    cv2.putText(student, "1", (55, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.8, 0, 3)
    cv2.rectangle(student, (85, 70), (255, 130), 0, 2)

    result = align_page_images(template, student)

    assert result.matrix.shape == (3, 3)
    assert result.score > 0


def test_transform_bbox_projects_template_region_to_student_space() -> None:
    matrix = np.array(
        [
            [1.0, 0.0, 5.0],
            [0.0, 1.0, 7.0],
            [0.0, 0.0, 1.0],
        ]
    )

    projected = transform_bbox([10, 20, 30, 40], matrix, width=100, height=100)

    assert projected == [15.0, 27.0, 35.0, 47.0]
