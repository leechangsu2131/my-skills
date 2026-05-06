from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from project_store import ProjectPaths


A4_WIDTH = 1240
A4_HEIGHT = 1754
MARGIN = 48
CARD_GAP = 18                                               # FIX: 22 → 18
CARD_HEIGHT = 320                                           # FIX: 225 → 320 (이미지 영역 확보)
CARD_WIDTH = (A4_WIDTH - (MARGIN * 2) - CARD_GAP) // 2
PACKET_DIR_NAME = "gemini_review_packets"


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/malgunbd.ttf") if bold else Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf") if bold else Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _line_height(font: ImageFont.ImageFont, spacing: int = 6) -> int:
    # FIX: load_default()는 .size 속성이 없으므로 getbbox로 안전하게 계산
    try:
        return font.size + spacing
    except AttributeError:
        bbox = font.getbbox("A")
        return (bbox[3] - bbox[1]) + spacing


def _packet_dir(paths: ProjectPaths) -> Path:
    out_dir = paths.artifacts_dir / PACKET_DIR_NAME
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_review_items(paths: ProjectPaths, item_ids: Iterable[str] | None = None) -> list[dict]:
    selected = set(item_ids or [])
    rows: list[dict] = []
    for submission_path in sorted(paths.submissions_dir.glob("*.json")):
        submission = _load_json(submission_path)
        student_id = str(submission.get("student_id") or submission_path.stem)
        for item in submission.get("items", []):
            item_id = str(item.get("item_id", ""))
            if selected:
                if item_id not in selected:
                    continue
            elif not item.get("needs_review"):
                continue
            crop_rel = str(item.get("crop_path") or "")
            crop_file = paths.crops_dir / crop_rel
            if not item_id or not crop_rel or not crop_file.exists():
                continue
            row = dict(item)
            row["student_id"] = str(row.get("student_id") or student_id)
            row["crop_file"] = crop_file
            rows.append(row)
    rows.sort(key=lambda row: (row.get("student_id", ""), int(row.get("page", 0) or 0), int(row.get("question_number", 0) or 0)))
    return rows


def _draw_multiline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    lines: list[str],
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> int:
    x, y = xy
    lh = _line_height(font, spacing=6)   # FIX: 안정적인 줄 간격 계산
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += lh
    return y


def _fit_crop(crop: Image.Image, max_width: int, max_height: int) -> Image.Image:
    image = crop.convert("RGB")
    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    return image


def _draw_card(page: Image.Image, item: dict, x: int, y: int) -> None:
    draw = ImageDraw.Draw(page)
    border = (71, 85, 105)
    panel = (248, 250, 252)
    text  = (15, 23, 42)
    muted = (71, 85, 105)
    blue  = (37, 99, 235)

    draw.rounded_rectangle(
        (x, y, x + CARD_WIDTH, y + CARD_HEIGHT),
        radius=12, fill=panel, outline=border, width=2,
    )

    title_font = _font(22, bold=True)
    body_font  = _font(18)
    small_font = _font(16)

    # ── 제목 ──────────────────────────────────────────────
    item_id = str(item.get("item_id", ""))
    draw.text((x + 16, y + 14), f"ID: {item_id}", font=title_font, fill=blue)

    # ── 메타 텍스트 (2열) ──────────────────────────────────
    meta_lines_left = [
        f"학생: {item.get('student_id', '-')}",
        f"문항: {item.get('page', '-')}p {item.get('question_number', '-')}번 / {item.get('type', '-')}",
    ]
    meta_lines_right = [
        f"현재 OCR: {item.get('recognized_answer', '') or '(빈값)'}",
        f"정답/배점: {item.get('expected_answer', '-')} / {item.get('points_possible', item.get('points', '-'))}",
    ]
    meta_y = y + 48
    _draw_multiline(draw, (x + 16, meta_y), meta_lines_left, small_font, muted)
    # FIX: 하드코딩 x+280 → 카드 절반 기준으로 정렬
    _draw_multiline(draw, (x + CARD_WIDTH // 2, meta_y), meta_lines_right, small_font, muted)

    # ── answer 라벨 ────────────────────────────────────────
    # FIX: 메타 2줄(각 ~22px) + 여유 → y+48+44+14 = y+106 정도로 조정
    answer_y = meta_y + _line_height(small_font) * 2 + 14
    draw.text((x + CARD_WIDTH - 130, answer_y), "answer: ____", font=body_font, fill=text)

    # ── 이미지 박스 ────────────────────────────────────────
    # FIX: answer 라벨 아래 12px 여백부터 카드 하단 16px 위까지 최대한 사용
    crop_box_x = x + 16
    crop_box_y = answer_y + _line_height(body_font) + 4
    crop_box_w = CARD_WIDTH - 32
    crop_box_h = (y + CARD_HEIGHT - 16) - crop_box_y   # 카드 하단 여백 16px
    draw.rounded_rectangle(
        (crop_box_x, crop_box_y, crop_box_x + crop_box_w, crop_box_y + crop_box_h),
        radius=8, fill=(255, 255, 255), outline=(203, 213, 225), width=1,
    )
    with Image.open(item["crop_file"]) as crop:
        fitted = _fit_crop(crop, crop_box_w - 12, crop_box_h - 12)
        px = crop_box_x + (crop_box_w - fitted.width) // 2
        py = crop_box_y + (crop_box_h - fitted.height) // 2
        page.paste(fitted, (px, py))


def _new_page(page_num: int, total_hint: int) -> Image.Image:
    page = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), "white")
    draw = ImageDraw.Draw(page)
    title_font = _font(30, bold=True)
    body_font  = _font(18)
    draw.text((MARGIN, 26), "Gemini 재판독용 답안 Crop PDF", font=title_font, fill=(15, 23, 42))
    draw.text(
        (MARGIN, 66),
        f"각 카드의 ID를 item_id로 사용해 JSON 배열만 반환하세요. 페이지 {page_num}, 총 선택 문항 {total_hint}개",
        font=body_font,
        fill=(71, 85, 105),
    )
    return page


def build_gemini_review_packet_pdf(
    paths: ProjectPaths,
    items: list[dict],
    packet_name: str | None = None,
) -> Path:
    if not items:
        raise ValueError("No review items selected")

    safe_name = packet_name or f"gemini_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    safe_name = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in safe_name)
    out_dir = _packet_dir(paths)
    pdf_path = out_dir / f"{safe_name}.pdf"
    manifest_path = pdf_path.with_suffix(".json")

    pages: list[Image.Image] = []
    page_num = 1
    page = _new_page(page_num, len(items))
    x_positions = [MARGIN, MARGIN + CARD_WIDTH + CARD_GAP]
    y = 112
    col = 0

    for item in items:
        if y + CARD_HEIGHT > A4_HEIGHT - MARGIN:
            pages.append(page)
            page_num += 1
            page = _new_page(page_num, len(items))
            y = 112
            col = 0
        _draw_card(page, item, x_positions[col], y)
        if col == 0:
            col = 1
        else:
            col = 0
            y += CARD_HEIGHT + CARD_GAP

    pages.append(page)
    first, rest = pages[0], pages[1:]
    first.save(pdf_path, "PDF", resolution=150.0, save_all=True, append_images=rest)
    for image in pages:
        image.close()

    manifest = {
        "packet": pdf_path.name,
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
        "items": [
            {
                "item_id": item.get("item_id"),
                "student_id": item.get("student_id"),
                "page": item.get("page"),
                "question_number": item.get("question_number"),
                "type": item.get("type"),
                "recognized_answer": item.get("recognized_answer", ""),
                "expected_answer": item.get("expected_answer", ""),
            }
            for item in items
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return pdf_path
