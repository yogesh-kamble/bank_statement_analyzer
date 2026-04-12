import csv
from typing import List
from models import Transaction


def normalize_amount(deposits: str, withdrawals: str) -> float:
    try:
        if withdrawals and withdrawals.strip():
            return -float(withdrawals)
        elif deposits and deposits.strip():
            return float(deposits)
    except ValueError:
        return 0.0

    return 0.0


def parse_icici_csv(file_path: str) -> List[Transaction]:
    transactions = []

    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            amount = normalize_amount(
                row.get("DEPOSITS", ""),
                row.get("WITHDRAWALS", "")
            )

            try:
                balance = float(row.get("BALANCE", 0))
            except ValueError:
                balance = 0.0

            txn = Transaction(
                date=row.get("DATE", ""),
                description=row.get("PARTICULARS", "").strip(),
                amount=amount,
                balance=balance
            )

            transactions.append(txn)

    return transactions