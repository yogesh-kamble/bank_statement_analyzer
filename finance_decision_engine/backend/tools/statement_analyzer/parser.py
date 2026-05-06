from typing import List
from backend.core.models import Transaction


def parse_transactions(data: List[dict]) -> List[Transaction]:
    transactions = []

    for item in data:
        transactions.append(
            Transaction(
                date=item["date"],
                amount=item["amount"],
                type=item["type"],
                description=item["description"]
            )
        )

    return transactions
