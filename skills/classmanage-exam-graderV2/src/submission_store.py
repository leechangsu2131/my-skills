from __future__ import annotations

import json
import re
from pathlib import Path

from answer_normalizer import normalize_objective_answer, normalize_short_answer
from grader import grade_submission_item
from project_store import ProjectPaths
from region_cropper import crop_question_region


STUDENT_PAGE_RE = re.compile(r"_stu(?P<student>\d+)_p(?P<page>\d+)\.png$", re.IGNORECASE)


def build_submission_manifest(file_names: list[str]) -> dict[str, dict]:
    grouped: dict[str, dict] = {}
    for name in sorted(file_names):
        match = STUDENT_PAGE_RE.search(name)
        if not match:
            continue
        student_id = f"stu{match.group('student')}"
        grouped.setdefault(student_id, {"student_id": student_id, "pages": []})
        grouped[student_id]["pages"].append(
            {"page": int(match.group("page")), "aligned_file": name}
        )
    return grouped


def list_students_from_aligned(aligned_dir: Path) -> list[str]:
    return sorted(
        path.name
        for path in aligned_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".png"
    )


def write_submission_manifests(
    paths: ProjectPaths,
    grouped: dict[str, dict],
    questions: list[dict],
) -> list[dict]:
    manifests: list[dict] = []
    questions_by_page: dict[int, list[dict]] = {}
    for question in questions:
        page = int(question.get("page", 1))
        questions_by_page.setdefault(page, []).append(question)

    for student_id, data in grouped.items():
        pages = sorted(data.get("pages", []), key=lambda item: item["page"])
        items: list[dict] = []
        for page_row in pages:
            page = page_row["page"]
            aligned_file = page_row["aligned_file"]
            for question in questions_by_page.get(page, []):
                qnum = int(question.get("number", 0))
                item_id = f"{student_id}_p{page}_q{qnum}"
                crop_rel = f"students/{student_id}/p{page}_q{qnum}.png"
                items.append(
                    {
                        "item_id": item_id,
                        "student_id": student_id,
                        "page": page,
                        "question_number": qnum,
                        "type": question.get("type", "객관식"),
                        "aligned_file": aligned_file,
                        "box": question.get("box", {}),
                        "crop_path": crop_rel,
                    }
                )

        manifest = {
            "student_id": student_id,
            "pages": pages,
            "items": items,
            "total_items": len(items),
        }
        out_path = paths.submissions_dir / f"{student_id}.json"
        out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        manifests.append(manifest)

    return manifests


def generate_reference_crops(paths: ProjectPaths, questions: list[dict]) -> int:
    count = 0
    for question in questions:
        page = int(question.get("page", 1))
        qnum = int(question.get("number", 0))
        template_path = paths.template_dir / f"blank_p{page}.png"
        if not template_path.exists():
            continue
        out_path = paths.crops_dir / "reference" / f"p{page}_q{qnum}.png"
        crop_question_region(template_path, question.get("box", {}), out_path)
        count += 1
    return count


def generate_student_crops(paths: ProjectPaths, manifests: list[dict]) -> int:
    count = 0
    for manifest in manifests:
        for item in manifest.get("items", []):
            aligned_path = paths.aligned_dir / item["aligned_file"]
            if not aligned_path.exists():
                continue
            out_path = paths.crops_dir / item["crop_path"]
            crop_question_region(aligned_path, item.get("box", {}), out_path)
            count += 1
    return count


def run_ocr_for_project(paths: ProjectPaths, engine) -> int:
    updated = 0
    for manifest_path in paths.submissions_dir.glob("*.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        changed = False

        for item in manifest.get("items", []):
            crop_path = paths.crops_dir / item.get("crop_path", "")
            if not crop_path.exists():
                continue

            ocr_result = engine.read_text(crop_path)
            candidates = ocr_result.get("candidates", [])
            best_text = ""
            best_confidence = 0.0
            if candidates:
                best = max(candidates, key=lambda row: float(row.get("confidence", 0.0)))
                best_text = str(best.get("text", ""))
                best_confidence = float(best.get("confidence", 0.0))

            qtype = str(item.get("type", "객관식"))
            if qtype == "객관식":
                normalized = normalize_objective_answer(best_text)
            else:
                normalized = normalize_short_answer(best_text)

            item["ocr"] = {"candidates": candidates}
            item["recognized_answer"] = normalized
            item["ocr_confidence"] = best_confidence

            if best_confidence < 0.75 or normalized == "":
                item["needs_review"] = True
                reasons = item.setdefault("review_reasons", [])
                if "low_ocr_confidence" not in reasons:
                    reasons.append("low_ocr_confidence")
            else:
                item["needs_review"] = False
                item["review_reasons"] = []

            changed = True

        if changed:
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            updated += 1

    return updated


def score_submission(submission: dict, answers: list[dict]) -> dict:
    answers_by_key = {
        (int(answer.get("page", 1)), int(answer.get("number", 0))): answer
        for answer in answers
        if isinstance(answer, dict)
    }
    total = 0
    earned = 0
    for item in submission.get("items", []):
        key = (int(item.get("page", 1)), int(item.get("question_number", 0)))
        answer = answers_by_key.get(key)
        if answer is None:
            item["is_correct"] = False
            item["points_possible"] = 0
            item["points_earned"] = 0
            continue
        scored = grade_submission_item(item, answer)
        item.update(scored)
        total += scored["points_possible"]
        earned += scored["points_earned"]
    submission["total_points"] = total
    submission["total_score"] = earned
    submission["needs_review_count"] = sum(1 for item in submission.get("items", []) if item.get("needs_review"))
    return submission


def score_project_submissions(paths: ProjectPaths, answers: list[dict]) -> int:
    count = 0
    for manifest_path in paths.submissions_dir.glob("*.json"):
        submission = json.loads(manifest_path.read_text(encoding="utf-8"))
        scored = score_submission(submission, answers)
        manifest_path.write_text(json.dumps(scored, ensure_ascii=False, indent=2), encoding="utf-8")
        count += 1
    return count


def load_all_submission_results(paths: ProjectPaths) -> list[dict]:
    submissions: list[dict] = []
    for manifest_path in sorted(paths.submissions_dir.glob("*.json")):
        submission = json.loads(manifest_path.read_text(encoding="utf-8"))
        submission.setdefault("student_id", manifest_path.stem)
        submission.setdefault("items", [])
        submission.setdefault("total_score", 0)
        submission.setdefault("total_points", 0)
        submission.setdefault("needs_review_count", sum(1 for item in submission.get("items", []) if item.get("needs_review")))
        submissions.append(submission)
    submissions.sort(key=lambda row: row.get("student_id", ""))
    return submissions


def load_submission_result(paths: ProjectPaths, student_id: str) -> dict | None:
    path = paths.submissions_dir / f"{student_id}.json"
    if not path.exists():
        return None
    submission = json.loads(path.read_text(encoding="utf-8"))
    submission.setdefault("student_id", student_id)
    submission.setdefault("items", [])
    submission.setdefault("needs_review_count", sum(1 for item in submission.get("items", []) if item.get("needs_review")))
    return submission
