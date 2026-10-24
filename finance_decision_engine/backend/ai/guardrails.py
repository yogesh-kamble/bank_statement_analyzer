"""Post-generation check that the AI did not introduce numbers of its own.

Every number in the AI's text must match a number present in FACTS (either a
raw `value` or a figure inside a `display` string). Anything else means the
model calculated or invented something, and the output is rejected.
"""
import re
from typing import Any, Iterable, List, Set

from backend.ai.models import Explanation

_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _norm(x: float) -> float:
    return round(float(x), 2)


def numbers_in_text(text: str) -> List[float]:
    out = []
    for token in _NUM_RE.findall(text or ""):
        try:
            out.append(_norm(token.replace(",", "").rstrip(".")))
        except ValueError:
            continue
    return out


def collect_allowed_numbers(facts: Any) -> Set[float]:
    allowed: Set[float] = set()

    def walk(node: Any) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, (int, float)):
            allowed.add(_norm(node))
        elif isinstance(node, str):
            allowed.update(numbers_in_text(node))
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, Iterable):
            for v in node:
                walk(v)

    walk(facts)
    return allowed


def explanation_texts(e: Explanation) -> List[str]:
    return [e.summary, *e.key_points, *e.risks, *e.suggestions]


def find_unsupported_numbers(e: Explanation, facts: Any) -> List[float]:
    allowed = collect_allowed_numbers(facts)
    bad: List[float] = []
    for text in explanation_texts(e):
        for n in numbers_in_text(text):
            if n not in allowed and n not in bad:
                bad.append(n)
    return bad
