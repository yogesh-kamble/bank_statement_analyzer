"""Deterministic formatting helpers.

All numbers shown to the AI are pre-formatted here, so the model only ever
copies strings - it never needs to round, convert or format anything.
"""
from typing import Any, Dict


def inr(value: float) -> str:
    """Format a rupee amount with Indian digit grouping, e.g. 150000 -> ₹1,50,000."""
    sign = "-" if value < 0 else ""
    n = int(round(abs(value)))
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return f"{sign}₹{s}"


def pct(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


def months(value: int) -> str:
    return f"{value} month" + ("" if value == 1 else "s")


def metric(value: Any, display: str) -> Dict[str, Any]:
    """A fact the AI may quote: raw value (for validation) + display string (to copy)."""
    return {"value": value, "display": display}
