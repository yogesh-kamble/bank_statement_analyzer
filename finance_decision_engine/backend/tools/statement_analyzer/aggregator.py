from typing import List, Dict
from backend.core.models import Transaction
from collections import defaultdict
from backend.tools.statement_analyzer.cleaner import extract_merchant


def aggregate_transactions(transactions: List[Transaction]) -> Dict:
    total_spend = 0.0
    total_income = 0.0
    merchant_totals = defaultdict(float)
    for t in transactions:
        if t.type == "debit":
            total_spend += t.amount
            merchant = extract_merchant(t.description)
            merchant_totals[merchant] += t.amount
        elif t.type == "credit":
            total_income += t.amount

    return {
        "total_spend": round(total_spend, 2),
        "total_income": round(total_income, 2),
        "transaction_count": len(transactions),
        "merchant_totals": dict(merchant_totals)
    }