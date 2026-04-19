#!/usr/bin/env python3
"""
OCR helpers for exam parsing.

The answer-key PDF path still uses Gemini CLI-compatible helpers for legacy
teacher workflows. Student answer extraction now uses the blank-template-aware
Paddle OCR pipeline.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from typing import Optional

from ocr.paddle_backend import PaddleOcrBackend
from ocr.question_layout import build_question_layout
from ocr.template_alignment import align_page_images
from ocr.template_alignment import render_pdf_pages


SKILL_DIR = Path(__file__).parent
PROMPT_PATH = SKILL_DIR / "prompts" / "ocr_student_exam.txt"
CONFIG_PATH = SKILL_DIR / "config.json"


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
    metadata_dir: str | Path | None = None,
) -> dict:
    config = load_config()
    backend = PaddleOcrBackend(lang=config.get("paddle_ocr_language", "korean"))

    blank_pages = render_pdf_pages(Path(blank_exam_path))
    student_pages = render_pdf_pages(Path(pdf_path))
    if len(blank_pages) != len(student_pages):
        raise ValueError("Blank exam and student exam page counts do not match")

    metadata_root = Path(metadata_dir) if metadata_dir else None
    detections_by_page: dict[int, list[dict[str, Any]]] = {}
    page_sizes: dict[int, tuple[int, int]] = {}
    for page_index, blank_page in enumerate(blank_pages):
        detections = backend.detect_text(blank_page)
        detections_by_page[page_index] = detections
        page_sizes[page_index] = (blank_page.shape[1], blank_page.shape[0])

    layout = build_question_layout(detections_by_page, page_sizes)
    if metadata_root is not None:
        metadata_root.mkdir(parents=True, exist_ok=True)
        layout_payload = {
            "items": [
                {
                    "q_num": item.q_num,
                    "page_index": item.page_index,
                    "anchor_bbox": item.anchor_bbox,
                    "answer_bbox": item.answer_bbox,
                }
                for item in layout.items
            ]
        }
        (metadata_root / "layout.json").write_text(
            json.dumps(layout_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    answers = []
    for region in layout.items:
        blank_page = blank_pages[region.page_index]
        student_page = student_pages[region.page_index]
        alignment = align_page_images(blank_page, student_page)
        x1, y1, x2, y2 = [int(value) for value in region.answer_bbox]
        crop = student_page[max(y1, 0):max(y2, 0), max(x1, 0):max(x2, 0)]
        if crop.size == 0:
            answer_text = ""
            confidence_score = 0.0
        else:
            lines = backend.detect_text(crop)
            answer_text = " ".join(line["text"] for line in lines).strip()
            confidence_score = max((line["confidence"] for line in lines), default=0.0)

        answers.append(
            {
                "q_num": region.q_num,
                "type": "unknown",
                "answer": answer_text,
                "confidence": _bucket_confidence(confidence_score),
                "page": region.page_index + 1,
                "bbox": region.answer_bbox,
                "requires_review": confidence_score < 0.6 or not answer_text,
                "alignment_score": alignment.score,
            }
        )

    return {
        "student_name": Path(pdf_path).stem,
        "student_number": None,
        "exam_title": Path(blank_exam_path).stem,
        "answers": answers,
    }


def _bucket_confidence(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def extract_batch(
    input_dir: str,
    output_dir: str,
    *,
    blank_exam_path: str,
    metadata_dir: str | Path | None = None,
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
            answers = extract_answers(
                str(pdf_file),
                blank_exam_path=blank_exam_path,
                metadata_dir=metadata_dir,
            )
            out_file = output_path / f"{pdf_file.stem}_answers.json"
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
    args = parser.parse_args()

    config = load_config()
    default_output = str(SKILL_DIR / config["paths"]["extracted"])

    if args.batch:
        results = extract_batch(
            args.batch,
            args.output or default_output,
            blank_exam_path=args.blank_exam,
            metadata_dir=args.metadata_dir,
        )
        summary_path = Path(args.output or default_output) / "_batch_summary.json"
        summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    if args.pdf:
        result = extract_answers(
            args.pdf,
            blank_exam_path=args.blank_exam,
            metadata_dir=args.metadata_dir,
        )
        output_dir = Path(args.output or default_output)
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / f"{Path(args.pdf).stem}_answers.json"
        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
