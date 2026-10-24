"""Deterministic explanations used when AI is disabled or fails/violates rules.

These are templated from the same FACTS, so the API response shape is
identical whether or not the AI layer is available.
"""
from typing import Any, Dict

from backend.ai.models import Explanation


def purchase_fallback(facts: Dict[str, Any]) -> Explanation:
    r = facts["results"]
    points = [
        f"Savings remaining after purchase: {r['savings_remaining']['display']}.",
        f"Emergency runway: {r['emergency_runway']['display']}.",
    ]
    if facts["payment_mode"] == "emi":
        points.insert(0, f"Monthly EMI: {r['monthly_emi']['display']} "
                         f"({r['emi_share_of_income']['display']} of income).")
        points.append(
            f"Monthly surplus after EMI: {r['monthly_surplus_after_emi']['display']}."
        )
    return Explanation(
        summary=f"Verdict: {facts['verdict']}. {facts['engine_headline']}",
        key_points=points,
        suggestions=[facts["engine_recommendation"]],
        source="fallback",
    )


def statement_fallback(facts: Dict[str, Any]) -> Explanation:
    points = [
        f"Net cash flow: {facts['net_cash_flow']['display']}.",
    ]
    if facts.get("savings_rate"):
        points.append(f"Savings rate: {facts['savings_rate']['display']}.")
    if facts["top_merchants"]:
        t = facts["top_merchants"][0]
        points.append(
            f"Top merchant: {t['merchant']} at {t['amount']['display']} "
            f"({t['share_of_spend']['display']} of spend)."
        )
    return Explanation(
        summary=(
            f"Income {facts['total_income']['display']} versus spending "
            f"{facts['total_spend']['display']} across "
            f"{facts['transaction_count']['display']} transactions."
        ),
        key_points=points,
        suggestions=["Review your largest spending categories for savings opportunities."],
        source="fallback",
    )
