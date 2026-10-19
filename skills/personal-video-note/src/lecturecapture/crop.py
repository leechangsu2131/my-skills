from __future__ import annotations

from pathlib import Path

import cv2


def parse_crop(value: str) -> tuple[int, int, int, int]:
    try:
        x, y, width, height = (int(part.strip()) for part in value.split(","))
    except Exception as exc:
        raise ValueError("자르기 영역은 x,y,w,h 형식이어야 합니다. 예: 120,80,1450,820") from exc
    if x < 0 or y < 0 or width < 1 or height < 1:
        raise ValueError("x/y는 0 이상, w/h는 1 이상이어야 합니다.")
    return x, y, width, height


def select_crop(video_path: Path) -> tuple[int, int, int, int]:
    cap = cv2.VideoCapture(str(video_path))
    try:
        ok, frame = cap.read()
        if not ok or frame is None:
            raise ValueError("첫 프레임을 읽을 수 없어 영역을 선택할 수 없습니다.")
        window = "LectureCapture - 슬라이드 영역 선택 (Enter 확정, c 취소)"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        roi = cv2.selectROI(window, frame, showCrosshair=True, fromCenter=False)
        cv2.destroyWindow(window)
        x, y, width, height = map(int, roi)
        if width <= 0 or height <= 0:
            raise ValueError("화면 영역 선택이 취소되었거나 영역이 너무 작습니다.")
        return x, y, width, height
    finally:
        cap.release()
        cv2.destroyAllWindows()
