from typing import List
from models import Transaction, CategorizedTransaction


CATEGORY_RULES = {
    "food": ["swiggy", "zomato", "restaurant", "cafe"],
    "shopping": ["amazon", "flipkart", "myntra"],
    "bills": ["electricity", "rent", "recharge", "bill"],
    "transport": ["uber", "ola", "fuel", "petrol"],
}


def categorize(transaction: Transaction) -> str:
    desc = transaction.description.lower()

    for category, keywords in CATEGORY_RULES.items():
        if any(keyword in desc for keyword in keywords):
            return category

    return "other"


def categorize_transactions(transactions: List[Transaction]) -> List[CategorizedTransaction]:
    return [
        CategorizedTransaction(txn, categorize(txn))
        for txn in transactions
    ]