from __future__ import annotations


OBJECTIVE_MAP = {
    "1": "①",
    "2": "②",
    "3": "③",
    "4": "④",
    "5": "⑤",
    "1)": "①",
    "2)": "②",
    "3)": "③",
    "4)": "④",
    "5)": "⑤",
    "o": "○",
    "O": "○",
}


def normalize_objective_answer(text: str) -> str:
    raw = str(text or "").strip().replace(" ", "")
    return OBJECTIVE_MAP.get(raw, raw)


def normalize_short_answer(text: str) -> str:
    raw = str(text or "").strip().replace(" ", "")
    return raw.lower()
