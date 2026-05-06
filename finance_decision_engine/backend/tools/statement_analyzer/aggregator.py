from typing import List, Dict
from backend.core.models import Transaction


def aggregate_transactions(transactions: List[Transaction]) -> Dict:
    total_spend = 0.0
    total_income = 0.0

    for t in transactions:
        if t.type == "debit":
            total_spend += t.amount
        elif t.type == "credit":
            total_income += t.amount

    return {
        "total_spend": round(total_spend, 2),
        "total_income": round(total_income, 2),
        "transaction_count": len(transactions)
    }