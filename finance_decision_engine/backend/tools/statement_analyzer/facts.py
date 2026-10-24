"""Build the FACTS payload for a bank-statement summary.

All sums, shares and rates are computed here. Only aggregated figures and
merchant names from the known-merchant list are sent - never raw
transaction descriptions.
"""
from typing import Any, Dict

from backend.ai.formatting import inr, metric, pct

TOP_N = 5


def _share(part: float, whole: float) -> float:
    return round(part / whole * 100, 1) if whole > 0 else 0.0


def build_statement_facts(aggregated: Dict[str, Any]) -> Dict[str, Any]:
    spend = aggregated.get("total_spend", 0.0)
    income = aggregated.get("total_income", 0.0)
    merchants = aggregated.get("merchant_totals", {}) or {}

    net = round(income - spend, 2)
    savings_rate = _share(net, income) if income > 0 else 0.0

    known = {m: a for m, a in merchants.items() if m != "unknown"}
    top = sorted(known.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    unclassified = merchants.get("unknown", 0.0)

    return {
        "transaction_count": metric(
            aggregated.get("transaction_count", 0),
            str(aggregated.get("transaction_count", 0)),
        ),
        "total_income": metric(income, inr(income)),
        "total_spend": metric(spend, inr(spend)),
        "net_cash_flow": metric(net, inr(net)),
        "savings_rate": (
            metric(savings_rate, pct(savings_rate)) if income > 0 else None
        ),
        "top_merchants": [
            {
                "merchant": name,
                "amount": metric(round(amt, 2), inr(amt)),
                "share_of_spend": metric(_share(amt, spend), pct(_share(amt, spend))),
            }
            for name, amt in top
        ],
        "unclassified_spend": metric(round(unclassified, 2), inr(unclassified)),
        "unclassified_spend_share": metric(
            _share(unclassified, spend), pct(_share(unclassified, spend))
        ),
    }
