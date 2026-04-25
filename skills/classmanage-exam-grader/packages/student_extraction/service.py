#!/usr/bin/env python3
"""Student OCR service built around blank-template alignment and PaddleOCR."""

from __future__ import annotations

import json
import os
import re
import subprocess
from statistics import median
from pathlib import Path
from typing import Any
from typing import Optional

import cv2
from packages.student_extraction.answer_region_detector import build_answer_region_detector
from packages.student_extraction.answer_regions import localize_multiple_choice_answer_bbox
from packages.student_extraction.paddle_backend import PaddleOcrBackend
from packages.student_extraction.pdf_text_layer import extract_line_detections_from_pdf_text_layer
from packages.student_extraction.pdf_text_layer import extract_text_from_render_bbox
from packages.student_extraction.pdf_text_layer import has_enough_text_layer_content
from packages.student_extraction.preprocessing import preprocess_student_page
from packages.student_extraction.question_layout import build_question_layout
from packages.student_extraction.question_layout import parse_question_anchor_text
from packages.student_extraction.question_layout import QuestionLayout
from packages.student_extraction.question_layout import QuestionRegion
from packages.student_extraction.student_pages import split_student_pages_for_template
from packages.student_extraction.template_alignment import align_page_images
from packages.student_extraction.template_alignment import render_pdf_pages
from packages.student_extraction.template_alignment import transform_bbox


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = PROJECT_ROOT / "prompts" / "ocr_student_exam.txt"
CONFIG_PATH = PROJECT_ROOT / "config.json"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def load_prompt(prompt_path: Optional[Path] = None) -> str:
    path = prompt_path or PROMPT_PATH
    with open(path, "r", encoding="utf-8") as file_obj:
        return file_obj.read().strip()


def extract_json_from_response(text: str) -> Optional[dict]:
    json_block = re.search(r"```json\s*\n(.*?)```", text, re.DOTALL)
    if json_block:
        try:
            return json.loads(json_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    code_block = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def run_gemini_ocr(pdf_path: str, prompt: str, config: dict) -> dict:
    gemini_cli = config.get("gemini_cli_path", "gemini")
    model = config.get("gemini_model", "gemini-2.5-flash")
    abs_pdf = str(Path(pdf_path).resolve())
    full_prompt = f"{prompt}\n\n@{abs_pdf}"
    cmd_name = "gemini.cmd" if os.name == "nt" else "gemini"
    command = [cmd_name, "-p", full_prompt, "-m", model]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Gemini CLI timed out after 120 seconds: {pdf_path}") from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Gemini CLI was not found at '{gemini_cli}'. Install it before parsing PDF answer keys."
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(f"Gemini CLI failed with exit code {result.returncode}: {result.stderr}")

    parsed = extract_json_from_response(result.stdout.strip())
    if parsed is None:
        raise ValueError(f"Failed to parse JSON from Gemini response: {result.stdout[:500]}")

    return parsed


def extract_answers(
    pdf_path: str,
    *,
    blank_exam_path: str,
    answer_key: dict | None = None,
    metadata_dir: str | Path | None = None,
    student_page_offset: int | None = None,
    auto_pick_student_pages: bool | None = None,
) -> dict:
    grouped_answers = extract_answer_groups(
        pdf_path,
        blank_exam_path=blank_exam_path,
        answer_key=answer_key,
        metadata_dir=metadata_dir,
        student_page_offset=student_page_offset,
        auto_pick_student_pages=auto_pick_student_pages,
    )
    if not grouped_answers:
        raise ValueError(f"No student answer groups were extracted from {pdf_path}.")
    return grouped_answers[0]


def extract_answer_groups(
    pdf_path: str,
    *,
    blank_exam_path: str,
    answer_key: dict | None = None,
    metadata_dir: str | Path | None = None,
    student_page_offset: int | None = None,
    auto_pick_student_pages: bool | None = None,
) -> list[dict]:
    config = load_config()
    ocr_cfg = config.get("ocr", {})
    auto_pick = (
        auto_pick_student_pages
        if auto_pick_student_pages is not None
        else ocr_cfg.get("auto_pick_page_window", True)
    )
    effective_offset = (
        student_page_offset if student_page_offset is not None else ocr_cfg.get("student_page_offset")
    )
    backend = PaddleOcrBackend(lang=config.get("paddle_ocr_language", "korean"))
    render_dpi = int(ocr_cfg.get("render_dpi", 160))
    align_flag_below = float(ocr_cfg.get("flag_alignment_review_below", 0.35))
    layout_render_dpi = int(ocr_cfg.get("layout_render_dpi", render_dpi))
    blank_layout_ocr_mode = str(ocr_cfg.get("blank_layout_ocr_mode", "anchor_strips"))
    enable_translation_correction = bool(ocr_cfg.get("enable_translation_correction", True))

    blank_exam_file = Path(blank_exam_path)
    student_pdf_file = Path(pdf_path)

    blank_pages = render_pdf_pages(blank_exam_file, dpi=render_dpi)
    blank_layout_pages = blank_pages
    if layout_render_dpi != render_dpi:
        blank_layout_pages = render_pdf_pages(blank_exam_file, dpi=layout_render_dpi)
    student_pages_full = render_pdf_pages(student_pdf_file, dpi=render_dpi)
    student_groups = split_student_pages_for_template(
        blank_pages,
        student_pages_full,
        fixed_offset=effective_offset,
        auto_pick=auto_pick,
    )

    blank_text_detections = extract_line_detections_from_pdf_text_layer(blank_exam_file, dpi=render_dpi)
    use_blank_text_layer = has_enough_text_layer_content(
        blank_text_detections,
        min_lines_per_page=int(ocr_cfg.get("min_text_layer_lines_per_page", 4)),
    )
    detections_by_page: dict[int, list[dict[str, Any]]] = {}
    page_sizes: dict[int, tuple[int, int]] = {}
    if use_blank_text_layer:
        detections_by_page = blank_text_detections
        for page_index, blank_page in enumerate(blank_pages):
            page_sizes[page_index] = (blank_page.shape[1], blank_page.shape[0])
    else:
        for page_index, blank_page in enumerate(blank_layout_pages):
            if blank_layout_ocr_mode == "anchor_strips":
                detections = _detect_text_in_anchor_strips(blank_page, backend)
            else:
                detections = backend.detect_text(blank_page)
            detections_by_page[page_index] = detections
            page_sizes[page_index] = (blank_page.shape[1], blank_page.shape[0])

    layout = build_question_layout(detections_by_page, page_sizes)
    if not use_blank_text_layer and layout_render_dpi != render_dpi:
        layout = _scale_layout_to_render_pages(layout, blank_layout_pages, blank_pages)
    question_type_by_num = {
        int(question["q_num"]): str(question.get("type", "unknown"))
        for question in (answer_key or {}).get("questions", [])
        if question.get("q_num") is not None
    }
    question_spec_by_num = {
        int(question["q_num"]): dict(question)
        for question in (answer_key or {}).get("questions", [])
        if question.get("q_num") is not None
    }
    answer_region_detector = build_answer_region_detector(config)
    if question_type_by_num:
        layout = _complete_layout_with_expected_questions(
            layout,
            blank_pages,
            sorted(question_type_by_num),
        )
        layout = _refine_layout_answer_regions(
            layout,
            blank_pages,
            question_type_by_num,
            answer_region_detector=answer_region_detector,
        )
    metadata_root = Path(metadata_dir) if metadata_dir else None
    if metadata_root is not None:
        metadata_root.mkdir(parents=True, exist_ok=True)
        _write_layout_metadata(
            metadata_root,
            layout=layout,
            blank_layout_source="pdf_text_layer" if use_blank_text_layer else "paddle_ocr",
            render_dpi=render_dpi,
        )

    grouped_answers: list[dict] = []
    total_groups = len(student_groups)
    for group_index, (student_pages, page_meta) in enumerate(student_groups, start=1):
        group_metadata_root = metadata_root
        if metadata_root is not None and total_groups > 1:
            group_metadata_root = metadata_root / f"group_{group_index:02d}"
        grouped_answers.append(
            _extract_answers_from_selected_pages(
                pdf_path=pdf_path,
                blank_exam_path=blank_exam_path,
                student_pdf_file=student_pdf_file,
                blank_pages=blank_pages,
                student_pages=student_pages,
                page_meta={**page_meta, "group_index": group_index, "group_count": total_groups},
                metadata_root=group_metadata_root,
                detections_by_page=detections_by_page,
                layout=layout,
                backend=backend,
                render_dpi=render_dpi,
                highres_render_dpi=int(ocr_cfg.get("highres_render_dpi", max(render_dpi * 2, 300))),
                align_flag_below=align_flag_below,
                enable_translation_correction=enable_translation_correction,
                question_spec_by_num=question_spec_by_num,
            )
        )

    return grouped_answers


def _write_layout_metadata(
    metadata_root: Path,
    *,
    layout: Any,
    blank_layout_source: str,
    render_dpi: int,
) -> None:
    layout_payload = {
        "items": [
            {
                "q_num": item.q_num,
                "page_index": item.page_index,
                "anchor_bbox": item.anchor_bbox,
                "answer_bbox": item.answer_bbox,
                "question_text_snippet": item.question_text_snippet,
                "answer_marker_type": item.answer_marker_type,
                "question_text_bbox": item.question_text_bbox,
            }
            for item in layout.items
        ]
    }
    (metadata_root / "layout.json").write_text(
        json.dumps(layout_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (metadata_root / "layout_source.json").write_text(
        json.dumps(
            {
                "blank_layout_source": blank_layout_source,
                "render_dpi": render_dpi,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _detect_text_in_anchor_strips(page: Any, backend: PaddleOcrBackend) -> list[dict[str, Any]]:
    height, width = page.shape[:2]
    strip_regions = [
        (0, 0, max(width // 3, 1), height),
        (width // 2, 0, min(width, (width // 2) + max(width // 3, 1)), height),
    ]
    detections: list[dict[str, Any]] = []
    for x1, y1, x2, y2 in strip_regions:
        crop = page[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        for item in backend.detect_text(crop):
            bbox = [float(value) for value in item["bbox"]]
            detections.append(
                {
                    **item,
                    "bbox": [
                        bbox[0] + x1,
                        bbox[1] + y1,
                        bbox[2] + x1,
                        bbox[3] + y1,
                    ],
                }
            )
    return detections


def _scale_layout_to_render_pages(
    layout: QuestionLayout,
    source_pages: list[Any],
    target_pages: list[Any],
) -> QuestionLayout:
    scaled_items: list[QuestionRegion] = []
    for item in layout.items:
        source_page = source_pages[item.page_index]
        target_page = target_pages[item.page_index]
        scale_x = float(target_page.shape[1]) / max(float(source_page.shape[1]), 1.0)
        scale_y = float(target_page.shape[0]) / max(float(source_page.shape[0]), 1.0)
        scaled_items.append(
            QuestionRegion(
                q_num=item.q_num,
                page_index=item.page_index,
                anchor_bbox=_scale_bbox(item.anchor_bbox, scale_x, scale_y),
                answer_bbox=_scale_bbox(item.answer_bbox, scale_x, scale_y),
                question_text_snippet=item.question_text_snippet,
                answer_marker_type=item.answer_marker_type,
                question_text_bbox=_scale_bbox(item.question_text_bbox, scale_x, scale_y)
                if item.question_text_bbox
                else None,
            )
        )
    return QuestionLayout(items=scaled_items)


def _scale_bbox(bbox: list[float], scale_x: float, scale_y: float) -> list[float]:
    return [
        float(bbox[0]) * scale_x,
        float(bbox[1]) * scale_y,
        float(bbox[2]) * scale_x,
        float(bbox[3]) * scale_y,
    ]


def _complete_layout_with_expected_questions(
    layout: QuestionLayout,
    blank_pages: list[Any],
    expected_question_numbers: list[int],
) -> QuestionLayout:
    if not layout.items or not expected_question_numbers:
        return layout

    items_by_page: dict[int, list[QuestionRegion]] = {}
    for item in layout.items:
        region = _coerce_region(item)
        items_by_page.setdefault(region.page_index, []).append(region)

    sorted_pages = sorted(items_by_page)
    page_ranges = _infer_expected_page_ranges(items_by_page, expected_question_numbers)
    completed_items: list[QuestionRegion] = []
    for page_index in sorted_pages:
        page_items = items_by_page[page_index]
        page_items.sort(key=lambda item: item.q_num)
        page_start, page_end = page_ranges.get(
            page_index,
            (min(expected_question_numbers), max(expected_question_numbers)),
        )
        page_items = [item for item in page_items if page_start <= item.q_num <= page_end]
        if not page_items:
            continue

        page_height, page_width = blank_pages[page_index].shape[:2]
        split_x = _estimate_region_column_split(page_items, page_width)
        left_items = [item for item in page_items if _resolve_region_column(item, split_x) == "left"]
        right_items = [item for item in page_items if _resolve_region_column(item, split_x) == "right"]

        if left_items and right_items:
            right_start = min(item.q_num for item in right_items)
            left_expected = list(range(page_start, max(right_start - 1, page_start) + 1))
            right_expected = list(range(min(item.q_num for item in right_items), page_end + 1))
            filled = _fill_column_questions(left_items, left_expected, split_x, page_width)
            filled.extend(_fill_column_questions(right_items, right_expected, split_x, page_width))
        else:
            filled = _fill_column_questions(page_items, list(range(page_start, page_end + 1)), split_x, page_width)

        completed_items.extend(
            _recompute_page_regions(filled, page_width=page_width, page_height=page_height, split_x=split_x)
        )

    completed_items.sort(key=lambda item: (item.page_index, item.q_num))
    return QuestionLayout(items=completed_items)


def _infer_expected_page_ranges(
    items_by_page: dict[int, list[Any]],
    expected_question_numbers: list[int],
) -> dict[int, tuple[int, int]]:
    if not items_by_page or not expected_question_numbers:
        return {}

    pages = sorted(items_by_page)
    expected = sorted(int(value) for value in expected_question_numbers)
    total_expected = len(expected)
    page_qs: dict[int, list[int]] = {}
    observed_counts: list[int] = []

    for page_index in pages:
        q_nums = sorted(
            {
                int(getattr(item, "q_num"))
                for item in items_by_page[page_index]
                if expected[0] <= int(getattr(item, "q_num")) <= expected[-1]
            }
        )
        page_qs[page_index] = q_nums
        observed_counts.append(max(len(q_nums), 1))

    total_observed = max(sum(observed_counts), 1)
    target_sizes = [total_expected * count / total_observed for count in observed_counts]
    memo: dict[tuple[int, int], tuple[float, list[tuple[int, int]]]] = {}

    def solve(page_position: int, expected_start_index: int) -> tuple[float, list[tuple[int, int]]]:
        key = (page_position, expected_start_index)
        if key in memo:
            return memo[key]

        if page_position == len(pages):
            if expected_start_index == total_expected:
                return 0.0, []
            return float("-inf"), []

        remaining_pages = len(pages) - page_position
        max_end_index = total_expected - remaining_pages
        best_score = float("-inf")
        best_ranges: list[tuple[int, int]] = []

        for expected_end_index in range(expected_start_index, max_end_index + 1):
            start_q = expected[expected_start_index]
            end_q = expected[expected_end_index]
            range_len = expected_end_index - expected_start_index + 1
            q_nums = page_qs[pages[page_position]]
            in_range = [q_num for q_num in q_nums if start_q <= q_num <= end_q]
            out_range = len(q_nums) - len(in_range)
            score = (len(in_range) * 4.0) - (out_range * 5.0) - (abs(range_len - target_sizes[page_position]) * 0.8)
            if in_range:
                score -= max(0, min(in_range) - start_q) * 0.2
                score -= max(0, end_q - max(in_range)) * 0.15
            else:
                score -= 6.0

            tail_score, tail_ranges = solve(page_position + 1, expected_end_index + 1)
            if tail_score == float("-inf"):
                continue
            total_score = score + tail_score
            if total_score > best_score:
                best_score = total_score
                best_ranges = [(start_q, end_q)] + tail_ranges

        memo[key] = (best_score, best_ranges)
        return memo[key]

    _score, ranges = solve(0, 0)
    return {page_index: page_range for page_index, page_range in zip(pages, ranges)}


def _refine_layout_answer_regions(
    layout: QuestionLayout,
    blank_pages: list[Any],
    question_type_by_num: dict[int, str],
    *,
    answer_region_detector: Any | None = None,
) -> QuestionLayout:
    refined_items: list[QuestionRegion] = []
    for item in layout.items:
        region = _coerce_region(item)
        page = blank_pages[region.page_index]
        bounded_question_bbox = _bounded_question_bbox_from_region(region, page.shape[1], page.shape[0])
        base_question_bbox = list(region.question_bbox or bounded_question_bbox)
        content_question_bbox = _shrink_question_bbox_to_content(page, base_question_bbox)
        question_type = question_type_by_num.get(region.q_num)

        if question_type == "multiple_choice":
            prompt_question_bbox = list(bounded_question_bbox)
            fallback_bbox = _build_prompt_choice_bbox(region, prompt_question_bbox)
            if answer_region_detector is not None and hasattr(answer_region_detector, "localize_multiple_choice"):
                answer_bbox, marker_type = answer_region_detector.localize_multiple_choice(
                    page,
                    question_bbox=prompt_question_bbox,
                    anchor_bbox=region.anchor_bbox,
                    fallback_bbox=fallback_bbox,
                )
            else:
                answer_bbox, marker_type = localize_multiple_choice_answer_bbox(
                    page,
                    question_bbox=prompt_question_bbox,
                    anchor_bbox=region.anchor_bbox,
                    fallback_bbox=fallback_bbox,
                )
            refined_items.append(
                _copy_region(
                    region,
                    question_bbox=prompt_question_bbox,
                    answer_bbox=answer_bbox,
                    answer_marker_type=marker_type,
                    extraction_mode="prompt_choice",
                )
            )
            continue

        line_bbox = _detect_answer_line_bbox(page, content_question_bbox)
        if line_bbox is not None:
            refined_items.append(
                _copy_region(
                    region,
                    question_bbox=content_question_bbox,
                    answer_bbox=line_bbox,
                    answer_marker_type="answer_line",
                    extraction_mode="answer_line",
                )
            )
            continue

        refined_items.append(
            _copy_region(
                region,
                question_bbox=content_question_bbox,
                answer_bbox=content_question_bbox,
                extraction_mode="review_only",
            )
        )

    return QuestionLayout(items=refined_items)


def _coerce_region(item: Any) -> QuestionRegion:
    return QuestionRegion(
        q_num=int(getattr(item, "q_num")),
        page_index=int(getattr(item, "page_index")),
        anchor_bbox=list(getattr(item, "anchor_bbox")),
        answer_bbox=list(getattr(item, "answer_bbox")),
        question_text_snippet=str(getattr(item, "question_text_snippet", "")),
        answer_marker_type=str(getattr(item, "answer_marker_type", "blank")),
        question_text_bbox=list(getattr(item, "question_text_bbox"))
        if getattr(item, "question_text_bbox", None) is not None
        else None,
        question_bbox=list(getattr(item, "question_bbox"))
        if getattr(item, "question_bbox", None) is not None
        else None,
        extraction_mode=str(getattr(item, "extraction_mode", "crop_ocr")),
    )


def _copy_region(region: Any, **updates: Any) -> QuestionRegion:
    base = _coerce_region(region)
    payload = {
        "q_num": base.q_num,
        "page_index": base.page_index,
        "anchor_bbox": list(base.anchor_bbox),
        "answer_bbox": list(base.answer_bbox),
        "question_text_snippet": base.question_text_snippet,
        "answer_marker_type": base.answer_marker_type,
        "question_text_bbox": list(base.question_text_bbox) if base.question_text_bbox is not None else None,
        "question_bbox": list(base.question_bbox) if base.question_bbox is not None else None,
        "extraction_mode": base.extraction_mode,
    }
    payload.update(updates)
    return QuestionRegion(**payload)


def _estimate_region_column_split(items: list[QuestionRegion], page_width: int) -> float | None:
    centers = sorted((item.anchor_bbox[0] + item.anchor_bbox[2]) / 2.0 for item in items)
    if len(centers) < 2:
        return None
    gaps = [(centers[index + 1] - centers[index], index) for index in range(len(centers) - 1)]
    if not gaps:
        return None
    gap, index = max(gaps, key=lambda value: value[0])
    if gap < float(page_width) * 0.12:
        return None
    return (centers[index] + centers[index + 1]) / 2.0


def _resolve_region_column(region: QuestionRegion, split_x: float | None) -> str:
    if split_x is None:
        return "full"
    center_x = (region.anchor_bbox[0] + region.anchor_bbox[2]) / 2.0
    return "left" if center_x < split_x else "right"


def _fill_column_questions(
    items: list[QuestionRegion],
    expected_qs: list[int],
    split_x: float | None,
    page_width: int,
) -> list[QuestionRegion]:
    if not items:
        return []
    items = sorted((_coerce_region(item) for item in items), key=lambda item: item.q_num)
    by_q = {item.q_num: item for item in items}
    x1 = median(item.anchor_bbox[0] for item in items)
    x2 = median(item.anchor_bbox[2] for item in items)
    heights = [item.anchor_bbox[3] - item.anchor_bbox[1] for item in items]
    default_height = float(median(heights)) if heights else 12.0
    gaps = [
        items[index + 1].anchor_bbox[1] - items[index].anchor_bbox[1]
        for index in range(len(items) - 1)
        if items[index + 1].anchor_bbox[1] > items[index].anchor_bbox[1]
    ]
    default_gap = float(median(gaps)) if gaps else max(default_height * 4.0, 32.0)

    filled: list[QuestionRegion] = []
    for q_num in expected_qs:
        existing = by_q.get(q_num)
        if existing is not None:
            filled.append(existing)
            continue

        prev_item = next((by_q[value] for value in reversed(expected_qs) if value < q_num and value in by_q), None)
        next_item = next((by_q[value] for value in expected_qs if value > q_num and value in by_q), None)
        if prev_item is not None and next_item is not None:
            total_gap = max(next_item.q_num - prev_item.q_num, 1)
            ratio = float(q_num - prev_item.q_num) / float(total_gap)
            y1 = prev_item.anchor_bbox[1] + ((next_item.anchor_bbox[1] - prev_item.anchor_bbox[1]) * ratio)
        elif prev_item is not None:
            y1 = prev_item.anchor_bbox[1] + default_gap * float(q_num - prev_item.q_num)
        elif next_item is not None:
            y1 = next_item.anchor_bbox[1] - default_gap * float(next_item.q_num - q_num)
        else:
            y1 = default_gap * float(len(filled))
        filled.append(
            QuestionRegion(
                q_num=q_num,
                page_index=items[0].page_index,
                anchor_bbox=[float(x1), float(y1), float(x2), float(y1 + default_height)],
                answer_bbox=[float(x2 + 8.0), float(y1), float(page_width - 8), float(y1 + default_height * 3.0)],
                question_bbox=None,
            )
        )

    filled.sort(key=lambda item: item.q_num)
    return filled


def _recompute_page_regions(
    items: list[QuestionRegion],
    *,
    page_width: int,
    page_height: int,
    split_x: float | None,
) -> list[QuestionRegion]:
    anchors = sorted(items, key=lambda item: (item.anchor_bbox[1], item.anchor_bbox[0], item.q_num))
    rebuilt: list[QuestionRegion] = []
    for item in sorted(items, key=lambda region: region.q_num):
        column = _resolve_region_column(item, split_x)
        next_top_candidates = [
            other.anchor_bbox[1]
            for other in anchors
            if other.q_num != item.q_num
            and _resolve_region_column(other, split_x) == column
            and other.anchor_bbox[1] > item.anchor_bbox[1] + 2.0
        ]
        next_top = min(next_top_candidates) if next_top_candidates else float(page_height - 20)
        column_end = float(split_x) if column == "left" and split_x is not None else float(page_width)
        x1, y1, x2, y2 = [float(value) for value in item.anchor_bbox]
        question_bbox = _fallback_question_bbox(item, page_width, page_height, next_top=next_top, column_end=column_end)
        answer_bbox = [
            max(x2 + 10.0, question_bbox[0] + 12.0),
            max(y1 - 6.0, question_bbox[1]),
            max(question_bbox[2] - 10.0, x2 + 12.0),
            max(question_bbox[3] - 8.0, y2 + 8.0),
        ]
        rebuilt.append(
            _copy_region(
                item,
                question_bbox=question_bbox,
                answer_bbox=answer_bbox,
            )
        )
    return rebuilt


def _fallback_question_bbox(
    region: Any,
    page_width: int,
    page_height: int,
    *,
    next_top: float | None = None,
    column_end: float | None = None,
) -> list[float]:
    x1, y1, x2, y2 = [float(value) for value in region.anchor_bbox]
    bottom = float(next_top) - 4.0 if next_top is not None else max(float(getattr(region, "answer_bbox", [x2, y2, page_width, y2 + 32])[3]), y2 + 28.0)
    right = float(column_end) - 4.0 if column_end is not None else float(page_width - 4)
    return [
        max(0.0, x1),
        max(0.0, y1 - 8.0),
        max(x2 + 1.0, min(right, float(page_width - 1))),
        max(y2 + 1.0, min(bottom, float(page_height - 1))),
    ]


def _bounded_question_bbox_from_region(region: Any, page_width: int, page_height: int) -> list[float]:
    if getattr(region, "question_bbox", None):
        return [float(value) for value in region.question_bbox]

    boxes = [list(region.anchor_bbox), list(region.answer_bbox)]
    if getattr(region, "question_text_bbox", None):
        boxes.append(list(region.question_text_bbox))
    x1, y1, x2, y2 = _expand_bbox(_union_bboxes(boxes), pad_x=12.0, pad_y=8.0)
    return [
        max(0.0, x1),
        max(0.0, y1),
        min(float(page_width - 1), max(x1 + 1.0, x2)),
        min(float(page_height - 1), max(y1 + 1.0, y2)),
    ]


def _detect_answer_line_bbox(page: Any, question_bbox: list[float]) -> list[float] | None:
    crop = _crop_from_bbox(page, question_bbox)
    if crop.size == 0:
        return None
    height, width = crop.shape[:2]
    if height < 24 or width < 60:
        return None

    focus_y = int(round(height * 0.45))
    focus = crop[focus_y:, :]
    _, binary = cv2.threshold(focus, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(width // 4, 36), 1))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    candidates: list[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < max(int(width * 0.28), 46):
            continue
        if h > max(6, height // 12):
            continue
        line_y = y + focus_y
        left_x = max(x - 24, 0)
        bubble_probe = crop[max(line_y - 18, 0):min(line_y + 18, height), left_x:x]
        if bubble_probe.size == 0:
            continue
        ink_ratio = float((bubble_probe < 210).mean())
        if ink_ratio < 0.06:
            continue
        candidates.append((x, line_y, w, h))

    if not candidates:
        return None

    x, y, w, h = max(candidates, key=lambda item: (item[1], item[2]))
    qx1, qy1, _qx2, _qy2 = [float(value) for value in question_bbox]
    return [
        qx1 + float(max(x - 4, 0)),
        qy1 + float(max(y - 12, 0)),
        qx1 + float(min(x + w + 4, width)),
        qy1 + float(min(y + h + 12, height)),
    ]


def _shrink_question_bbox_to_content(page: Any, question_bbox: list[float]) -> list[float]:
    crop = _crop_from_bbox(page, question_bbox)
    if crop.size == 0:
        return question_bbox
    column_ink = (crop < 240).mean(axis=0)
    active_columns = [index for index, value in enumerate(column_ink.tolist()) if value > 0.01]
    if not active_columns:
        return question_bbox
    qx1, qy1, qx2, qy2 = [float(value) for value in question_bbox]
    content_right = min(qx1 + float(active_columns[-1] + 12), qx2)
    if content_right <= qx1 + 24.0:
        return question_bbox
    return [qx1, qy1, content_right, qy2]


def _build_prompt_choice_bbox(region: Any, question_bbox: list[float]) -> list[float]:
    qx1, qy1, qx2, qy2 = [float(value) for value in question_bbox]
    ax1, ay1, ax2, ay2 = [float(value) for value in region.anchor_bbox]
    question_width = max(qx2 - qx1, 1.0)
    question_height = max(qy2 - qy1, 1.0)
    answer_height = min(max((ay2 - ay1) * 3.0, 26.0), question_height * 0.45)
    x1 = max(ax2 + 18.0, qx2 - max(question_width * 0.26, 54.0))
    return [
        x1,
        max(qy1, ay1 - 6.0),
        max(x1 + 18.0, qx2 - 6.0),
        min(qy2, qy1 + answer_height),
    ]


def _extract_answers_from_selected_pages(
    *,
    pdf_path: str,
    blank_exam_path: str,
    student_pdf_file: Path,
    blank_pages: list[Any],
    student_pages: list[Any],
    page_meta: dict[str, Any],
    metadata_root: Path | None,
    detections_by_page: dict[int, list[dict[str, Any]]],
    layout: Any,
    backend: PaddleOcrBackend,
    render_dpi: int,
    highres_render_dpi: int,
    align_flag_below: float,
    enable_translation_correction: bool,
    question_spec_by_num: dict[int, dict[str, Any]],
) -> dict:
    page_alignments: dict[int, Any] = {}
    page_contexts: dict[int, dict[str, Any]] = {}
    for region in layout.items:
        if region.page_index in page_contexts:
            continue
        preprocess_meta = preprocess_student_page(
            blank_pages[region.page_index],
            student_pages[region.page_index],
            template_detections=detections_by_page.get(region.page_index, []),
            detect_text=backend.detect_text,
            enable_translation_correction=enable_translation_correction,
        )
        page_alignments[region.page_index] = align_page_images(
            blank_pages[region.page_index],
            preprocess_meta["image"],
        )
        page_contexts[region.page_index] = {
            "student_page": preprocess_meta["image"],
            "page_detections": preprocess_meta["page_detections"],
            "preprocess_meta": preprocess_meta,
        }

    student_pdf_offset = int(page_meta.get("student_page_offset") or 0)
    page_metrics = []
    for page_index in sorted(page_contexts):
        preprocess_meta = page_contexts[page_index]["preprocess_meta"]
        alignment = page_alignments[page_index]
        page_metrics.append(
            {
                "template_page": page_index + 1,
                "student_page": student_pdf_offset + page_index + 1,
                "alignment_score": round(float(alignment.score), 4),
                "preprocess_applied": list(preprocess_meta.get("preprocess_applied", [])),
                "anchor_count": int(preprocess_meta.get("anchor_count", 0)),
            }
        )

    if metadata_root is not None:
        metadata_root.mkdir(parents=True, exist_ok=True)
        (metadata_root / "student_pages.json").write_text(
            json.dumps(page_meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (metadata_root / "page_metrics.json").write_text(
            json.dumps(page_metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    answer_entries: list[dict[str, Any]] = []
    lowres_crop_images: list[Any] = []
    lowres_entry_indices: list[int] = []
    for region in layout.items:
        page_context = page_contexts[region.page_index]
        student_page = page_context["student_page"]
        alignment = page_alignments[region.page_index]
        template_review_bbox = _build_review_bbox(region)
        projected_bbox = transform_bbox(
            region.answer_bbox,
            alignment.matrix,
            alignment.width,
            alignment.height,
        )
        projected_review_bbox = transform_bbox(
            template_review_bbox,
            alignment.matrix,
            alignment.width,
            alignment.height,
        )
        source_page_index = student_pdf_offset + region.page_index
        extraction_mode = getattr(region, "extraction_mode", "crop_ocr")
        text_layer_answer = ""
        if extraction_mode != "review_only":
            text_layer_answer = extract_text_from_render_bbox(
                student_pdf_file,
                page_index=source_page_index,
                render_bbox=projected_bbox,
                dpi=render_dpi,
            )
        answer_entries.append(
            {
                "region": region,
                "alignment": alignment,
                "page_context": page_context,
                "projected_bbox": projected_bbox,
                "projected_review_bbox": projected_review_bbox,
                "template_review_bbox": template_review_bbox,
                "source_page_index": source_page_index,
                "text_layer_answer": text_layer_answer,
                "crop_lines": [],
                "highres_lines": None,
            }
        )
        if extraction_mode == "review_only" or text_layer_answer:
            continue
        crop = _crop_from_bbox(student_page, projected_bbox)
        if crop.size:
            lowres_entry_indices.append(len(answer_entries) - 1)
            lowres_crop_images.append(crop)

    for entry_index, crop_lines in zip(lowres_entry_indices, _detect_text_batch(backend, lowres_crop_images)):
        answer_entries[entry_index]["crop_lines"] = crop_lines

    highres_student_pages_full: list[Any] | None = None
    highres_crop_images: list[Any] = []
    highres_entry_indices: list[int] = []
    for entry_index, entry in enumerate(answer_entries):
        region = entry["region"]
        if getattr(region, "extraction_mode", "crop_ocr") == "review_only" or entry["text_layer_answer"]:
            continue
        crop_answer, crop_score = _answer_from_detections(entry["crop_lines"])
        if crop_answer and crop_score >= 0.6:
            continue
        entry["highres_lines"] = []
        if highres_student_pages_full is None:
            highres_student_pages_full = render_pdf_pages(student_pdf_file, dpi=highres_render_dpi)
        source_page_index = int(entry["source_page_index"])
        if 0 <= source_page_index < len(highres_student_pages_full):
            scale = float(highres_render_dpi) / max(float(render_dpi), 1.0)
            highres_bbox = [value * scale for value in entry["projected_bbox"]]
            highres_crop = _crop_from_bbox(highres_student_pages_full[source_page_index], highres_bbox)
            if highres_crop.size:
                highres_entry_indices.append(entry_index)
                highres_crop_images.append(highres_crop)

    for entry_index, highres_lines in zip(highres_entry_indices, _detect_text_batch(backend, highres_crop_images)):
        answer_entries[entry_index]["highres_lines"] = highres_lines

    answers = []
    for entry in answer_entries:
        region = entry["region"]
        alignment = entry["alignment"]
        page_context = entry["page_context"]
        extraction = _extract_answer_with_fallback(
            backend=backend,
            student_pdf_file=student_pdf_file,
            source_page_index=entry["source_page_index"],
            student_page=page_context["student_page"],
            projected_bbox=entry["projected_bbox"],
            page_detections=page_context["page_detections"],
            region=region,
            render_dpi=render_dpi,
            highres_render_dpi=highres_render_dpi,
            highres_pages_cache=highres_student_pages_full,
            text_layer_answer=entry["text_layer_answer"],
            crop_lines=entry["crop_lines"],
            highres_lines=entry["highres_lines"],
        )

        answer_text = extraction["answer"]
        confidence_score = float(extraction["confidence_score"])
        review_reasons = _finalize_review_reasons(
            extraction_method=extraction["extraction_method"],
            answer_text=answer_text,
            confidence_score=confidence_score,
            alignment_score=float(alignment.score),
            reasons=extraction["review_reason"]
            + _answer_shape_review_reasons(
                answer_text=answer_text,
                question_spec=question_spec_by_num.get(region.q_num),
            ),
            align_flag_below=align_flag_below,
        )
        answers.append(
            {
                "q_num": region.q_num,
                "type": "unknown",
                "answer": answer_text,
                "confidence": _bucket_confidence(confidence_score),
                "confidence_score": confidence_score,
                "page": region.page_index + 1,
                "bbox": entry["projected_bbox"],
                "review_bbox": entry["projected_review_bbox"],
                "template_bbox": entry["template_review_bbox"],
                "requires_review": bool(review_reasons),
                "alignment_score": alignment.score,
                "extraction_method": extraction["extraction_method"],
                "review_reason": review_reasons,
            }
        )

    ocr_meta = dict(page_meta)
    ocr_meta["page_metrics"] = page_metrics
    if ocr_meta.get("mean_alignment_score") is None and answers:
        ocr_meta["mean_alignment_score"] = round(
            sum(item.get("alignment_score", 0.0) for item in answers) / max(len(answers), 1),
            4,
        )

    return {
        "student_name": Path(pdf_path).stem,
        "student_number": None,
        "exam_title": Path(blank_exam_path).stem,
        "answers": answers,
        "ocr_meta": ocr_meta,
    }


def _bucket_confidence(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def _detect_text_batch(
    backend: PaddleOcrBackend,
    images: list[Any],
) -> list[list[dict[str, Any]]]:
    if not images:
        return []
    batch_detect = getattr(backend, "detect_text_batch", None)
    if callable(batch_detect):
        return batch_detect(images)
    return [backend.detect_text(image) for image in images]


def _extract_answer_with_fallback(
    *,
    backend: PaddleOcrBackend,
    student_pdf_file: Path,
    source_page_index: int,
    student_page: Any,
    projected_bbox: list[float],
    page_detections: list[dict[str, Any]],
    region: Any,
    render_dpi: int,
    highres_render_dpi: int,
    highres_pages_cache: list[Any] | None,
    text_layer_answer: str | None = None,
    crop_lines: list[dict[str, Any]] | None = None,
    highres_lines: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if getattr(region, "extraction_mode", "crop_ocr") == "review_only":
        return {
            "answer": "",
            "confidence_score": 0.0,
            "extraction_method": "manual_review_only",
            "review_reason": ["manual_review_required"],
            "highres_pages_cache": highres_pages_cache,
        }

    if text_layer_answer is None:
        text_layer_answer = extract_text_from_render_bbox(
            student_pdf_file,
            page_index=source_page_index,
            render_bbox=projected_bbox,
            dpi=render_dpi,
        )
    if text_layer_answer:
        return {
            "answer": text_layer_answer,
            "confidence_score": 0.99,
            "extraction_method": "pdf_text_layer",
            "review_reason": [],
            "highres_pages_cache": highres_pages_cache,
        }

    if crop_lines is None:
        crop = _crop_from_bbox(student_page, projected_bbox)
        crop_lines = backend.detect_text(crop) if crop.size else []
    crop_answer, crop_score = _answer_from_detections(crop_lines)
    if crop_answer and crop_score >= 0.6:
        return {
            "answer": crop_answer,
            "confidence_score": crop_score,
            "extraction_method": "crop_ocr",
            "review_reason": [],
            "highres_pages_cache": highres_pages_cache,
        }

    if highres_lines is None:
        if highres_pages_cache is None:
            highres_pages_cache = render_pdf_pages(student_pdf_file, dpi=highres_render_dpi)
        highres_lines = []
        if 0 <= source_page_index < len(highres_pages_cache):
            scale = float(highres_render_dpi) / max(float(render_dpi), 1.0)
            highres_bbox = [value * scale for value in projected_bbox]
            highres_crop = _crop_from_bbox(highres_pages_cache[source_page_index], highres_bbox)
            highres_lines = backend.detect_text(highres_crop) if highres_crop.size else []
    highres_answer, highres_score = _answer_from_detections(highres_lines)
    if highres_answer and highres_score >= 0.6:
        return {
            "answer": highres_answer,
            "confidence_score": highres_score,
            "extraction_method": "highres_crop_ocr",
            "review_reason": [],
            "highres_pages_cache": highres_pages_cache,
        }

    fallback_answer, fallback_score, ambiguous = _answer_from_page_fallback(
        page_detections=page_detections,
        projected_bbox=projected_bbox,
        region=region,
    )
    reasons: list[str] = ["fallback_used"]
    if ambiguous:
        reasons.append("ambiguous_candidates")
    if not fallback_answer and not crop_answer:
        reasons.append("empty_crop")
    elif not fallback_answer and crop_score < 0.6:
        reasons.append("low_ocr_confidence")

    return {
        "answer": fallback_answer or crop_answer,
        "confidence_score": fallback_score if fallback_answer else crop_score,
        "extraction_method": "page_fallback",
        "review_reason": _dedupe(reasons),
        "highres_pages_cache": highres_pages_cache,
    }


def _finalize_review_reasons(
    *,
    extraction_method: str,
    answer_text: str,
    confidence_score: float,
    alignment_score: float,
    reasons: list[str],
    align_flag_below: float,
) -> list[str]:
    final_reasons = list(reasons)
    if extraction_method != "pdf_text_layer" and alignment_score < align_flag_below:
        final_reasons.append("low_alignment")
    if extraction_method != "pdf_text_layer" and confidence_score < 0.6:
        final_reasons.append("low_ocr_confidence")
    if not answer_text:
        final_reasons.append("empty_crop")
    return _dedupe(final_reasons)


def _answer_shape_review_reasons(
    *,
    answer_text: str,
    question_spec: dict[str, Any] | None,
) -> list[str]:
    if not answer_text or not question_spec:
        return []

    expected_answer = str(question_spec.get("answer", "")).strip()
    question_type = str(question_spec.get("type", "unknown"))
    compact_answer = re.sub(r"\s+", "", answer_text)
    compact_expected = re.sub(r"\s+", "", expected_answer)

    reasons: list[str] = []
    if question_type == "multiple_choice":
        if not _looks_like_option_answer(compact_answer):
            reasons.append("answer_shape_mismatch")
    elif _contains_hangul(compact_expected):
        if compact_answer and not _contains_hangul(compact_answer):
            reasons.append("answer_shape_mismatch")
    elif _looks_numeric(compact_expected):
        if compact_answer and not any(character.isdigit() for character in compact_answer):
            reasons.append("answer_shape_mismatch")

    if compact_answer and len(compact_answer) > max(len(compact_expected) * 3, 8):
        reasons.append("answer_shape_mismatch")
    return _dedupe(reasons)


def _looks_like_option_answer(value: str) -> bool:
    if not value:
        return False
    if len(value) <= 3 and re.fullmatch(r"[\d①-⑤ㄱ-ㅎA-Ea-e,./]+", value):
        return True
    return False


def _contains_hangul(value: str) -> bool:
    return bool(re.search(r"[가-힣ㄱ-ㅎㅏ-ㅣ]", value))


def _looks_numeric(value: str) -> bool:
    return bool(re.fullmatch(r"[\d.,cmCM]+", value)) and any(character.isdigit() for character in value)


def _crop_from_bbox(image: Any, bbox: list[float]) -> Any:
    x1, y1, x2, y2 = [int(round(value)) for value in bbox]
    return image[max(y1, 0):max(y2, 0), max(x1, 0):max(x2, 0)]


def _build_review_bbox(region: Any) -> list[float]:
    boxes = [list(region.anchor_bbox), list(region.answer_bbox)]
    if getattr(region, "question_bbox", None):
        boxes.append(list(region.question_bbox))
    if getattr(region, "question_text_bbox", None):
        boxes.append(list(region.question_text_bbox))
    return _expand_bbox(_union_bboxes(boxes), pad_x=16.0, pad_y=10.0)


def _answer_from_detections(detections: list[dict[str, Any]]) -> tuple[str, float]:
    if not detections:
        return "", 0.0
    best = max(detections, key=lambda item: float(item.get("confidence", 0.0)))
    return str(best.get("text", "")).strip(), float(best.get("confidence", 0.0))


def _answer_from_page_fallback(
    *,
    page_detections: list[dict[str, Any]],
    projected_bbox: list[float],
    region: Any,
) -> tuple[str, float, bool]:
    expanded_bbox = _expand_bbox(projected_bbox, pad_x=24.0, pad_y=18.0)
    candidates = [
        detection
        for detection in page_detections
        if _bbox_intersects(expanded_bbox, [float(value) for value in detection["bbox"]])
        and not _looks_like_left_margin_anchor(detection, projected_bbox)
    ]

    if not candidates and getattr(region, "question_text_snippet", ""):
        token = str(region.question_text_snippet).split(" ")[0]
        candidates = [
            detection
            for detection in page_detections
            if token and token in str(detection.get("text", ""))
        ]

    if not candidates:
        return "", 0.0, False

    unique_texts: list[str] = []
    for detection in sorted(candidates, key=lambda item: (item["bbox"][1], item["bbox"][0])):
        text = str(detection.get("text", "")).strip()
        if not text or text == getattr(region, "question_text_snippet", "").strip():
            continue
        if text not in unique_texts:
            unique_texts.append(text)

    if not unique_texts:
        return "", 0.0, False

    if getattr(region, "answer_marker_type", "빈줄") in {"밑줄", "빈줄"}:
        answer_text = " ".join(unique_texts)
        confidence_score = max(float(item.get("confidence", 0.0)) for item in candidates)
    else:
        best = max(candidates, key=lambda item: float(item.get("confidence", 0.0)))
        answer_text = str(best.get("text", "")).strip()
        confidence_score = float(best.get("confidence", 0.0))
    ambiguous = len(unique_texts) > 1
    return answer_text, confidence_score, ambiguous


def _expand_bbox(bbox: list[float], *, pad_x: float, pad_y: float) -> list[float]:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    return [x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y]


def _union_bboxes(boxes: list[list[float]]) -> list[float]:
    return [
        min(float(box[0]) for box in boxes),
        min(float(box[1]) for box in boxes),
        max(float(box[2]) for box in boxes),
        max(float(box[3]) for box in boxes),
    ]


def _bbox_intersects(left: list[float], right: list[float]) -> bool:
    return not (
        left[2] < right[0]
        or right[2] < left[0]
        or left[3] < right[1]
        or right[3] < left[1]
    )


def _looks_like_left_margin_anchor(detection: dict[str, Any], projected_bbox: list[float]) -> bool:
    text = str(detection.get("text", "")).strip()
    if parse_question_anchor_text(text) is None:
        return False
    x1, _y1, x2, _y2 = [float(value) for value in detection["bbox"]]
    return x2 <= projected_bbox[0] or x1 < projected_bbox[0] - 8.0


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def extract_batch(
    input_dir: str,
    output_dir: str,
    *,
    blank_exam_path: str,
    metadata_dir: str | Path | None = None,
    student_page_offset: int | None = None,
    auto_pick_student_pages: bool | None = None,
) -> list[dict]:
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(input_path.glob("*.pdf"))
    if not pdf_files:
        return []

    results = []
    for pdf_file in pdf_files:
        try:
            answer_groups = extract_answer_groups(
                str(pdf_file),
                blank_exam_path=blank_exam_path,
                metadata_dir=metadata_dir,
                student_page_offset=student_page_offset,
                auto_pick_student_pages=auto_pick_student_pages,
            )
            for group_index, answers in enumerate(answer_groups, start=1):
                suffix = f"_g{group_index:02d}" if len(answer_groups) > 1 else ""
                out_file = output_path / f"{pdf_file.stem}{suffix}_answers.json"
                out_file.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
                results.append(
                    {
                        "file": pdf_file.name,
                        "status": "success",
                        "student_name": answers.get("student_name", ""),
                        "answer_count": len(answers.get("answers", [])),
                        "output": str(out_file),
                    }
                )
        except Exception as exc:
            results.append({"file": pdf_file.name, "status": "error", "error": str(exc)})
    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Blank-template-driven student OCR extraction")
    parser.add_argument("pdf", nargs="?", help="Single student PDF path")
    parser.add_argument("--blank-exam", required=True, help="Blank exam PDF path")
    parser.add_argument("--batch", type=str, help="Batch input directory")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--metadata-dir", type=str, help="Optional OCR metadata directory")
    parser.add_argument(
        "--student-page-offset",
        type=int,
        default=None,
        help="0-based index of the first exam page inside the student PDF (when scan has extra pages)",
    )
    parser.add_argument(
        "--no-auto-page-window",
        action="store_true",
        help="Disable automatic search when student PDF is longer than the blank template",
    )
    args = parser.parse_args()

    config = load_config()
    default_output = str(PROJECT_ROOT / config["paths"]["extracted"])

    if args.batch:
        results = extract_batch(
            args.batch,
            args.output or default_output,
            blank_exam_path=args.blank_exam,
            metadata_dir=args.metadata_dir,
            student_page_offset=args.student_page_offset,
            auto_pick_student_pages=False if args.no_auto_page_window else None,
        )
        summary_path = Path(args.output or default_output) / "_batch_summary.json"
        summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    if args.pdf:
        results = extract_answer_groups(
            args.pdf,
            blank_exam_path=args.blank_exam,
            metadata_dir=args.metadata_dir,
            student_page_offset=args.student_page_offset,
            auto_pick_student_pages=False if args.no_auto_page_window else None,
        )
        output_dir = Path(args.output or default_output)
        output_dir.mkdir(parents=True, exist_ok=True)
        if len(results) == 1:
            out_file = output_dir / f"{Path(args.pdf).stem}_answers.json"
            out_file.write_text(json.dumps(results[0], ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(results[0], ensure_ascii=False, indent=2))
        else:
            for group_index, result in enumerate(results, start=1):
                out_file = output_dir / f"{Path(args.pdf).stem}_g{group_index:02d}_answers.json"
                out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
