from __future__ import annotations


def normalize_assessment_bundle(payload: dict | list) -> dict:
    if isinstance(payload, list):
        payload = {"questions": payload}
    if not isinstance(payload, dict):
        raise ValueError("Assessment bundle must be a dict or questions list")

    questions = payload.get("questions", [])
    answers = payload.get("answers", [])
    total_points = payload.get("total_points", 0)

    if not isinstance(questions, list):
        raise ValueError('"questions" must be a list')
    if not isinstance(answers, list):
        raise ValueError('"answers" must be a list')

    normalized_questions: list[dict] = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        box = item.get("box") or {}
        normalized_questions.append(
            {
                "number": int(item.get("number", 0)),
                "page": int(item.get("page", 1)),
                "type": str(item.get("type", "객관식")),
                "box": {
                    "x": float(box["x"]),
                    "y": float(box["y"]),
                    "w": float(box["w"]),
                    "h": float(box["h"]),
                },
            }
        )

    normalized_answers: list[dict] = []
    for item in answers:
        if not isinstance(item, dict):
            continue
        normalized_answers.append(
            {
                "number": int(item.get("number", 0)),
                "page": int(item.get("page", 1)),
                "answer": str(item.get("answer", "")).strip(),
                "points": int(item.get("points", 0)),
                "type": str(item.get("type", "객관식")),
            }
        )

    return {
        "questions": normalized_questions,
        "answers": normalized_answers,
        "total_points": int(total_points or 0),
    }


def merge_assessment_bundle(existing: dict | None, incoming: dict, mode: str) -> dict:
    existing = existing or {}
    existing_questions = existing.get("questions", [])
    existing_answers = existing.get("answers", [])
    existing_total_points = int(existing.get("total_points", 0) or 0)

    if mode == "replace_all":
        return incoming

    if mode == "answers_only":
        questions = existing_questions if isinstance(existing_questions, list) else []
        return {
            "questions": questions,
            "answers": incoming.get("answers", []),
            "total_points": int(incoming.get("total_points", 0) or 0),
        }

    if mode == "questions_only":
        answers = existing_answers if isinstance(existing_answers, list) else []
        return {
            "questions": incoming.get("questions", []),
            "answers": answers,
            "total_points": existing_total_points,
        }

    raise ValueError(f"Unsupported save mode: {mode}")
